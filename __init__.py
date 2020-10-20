from mycroft.skills.common_play_skill import CommonPlaySkill, \
    CPSMatchLevel, CPSTrackStatus, CPSMatchType
from mycroft.skills.core import intent_file_handler
from mycroft.util.parse import fuzzy_match, match_one
from pyvod import Collection, Media
from os.path import join, dirname, exists
from os import makedirs
import random
import re
from shutil import copy
from xdg import XDG_CACHE_HOME, XDG_DATA_HOME
from json_database import JsonStorageXDG


class MyTVtoGoSkill(CommonPlaySkill):

    def __init__(self):
        super().__init__("MyTVToGo")
        self.supported_media = [CPSMatchType.GENERIC,
                                CPSMatchType.MUSIC,
                                CPSMatchType.NEWS,
                                CPSMatchType.TV,
                                CPSMatchType.MOVIE]

        # database update
        path = join(XDG_DATA_HOME, "json_database")
        if not exists(path):
            makedirs(path)
        path = join(path, "mytvtogo.jsondb")
        copy(join(dirname(__file__), "res", "mytvtogo.jsondb"), path)

        # load channel catalog
        self.mytvtogo = Collection("MyTVToGo",
                    logo=join(dirname(__file__), "res", "MyTVToGo.png"),
                    db_path=path)
        self.channels = [ch.as_json() for ch in self.mytvtogo.entries]

        # History
        self.historyDB = JsonStorageXDG("mytvtogo-history")

        if "model" in self.historyDB:
            self.history_list = self.historyDB["model"]
        else:
            self.history_list = []

    def initialize(self):
        self.add_event('skill-mytvtogo.jarbasskills.home',
                       self.handle_homescreen)
        self.gui.register_handler("skill-mytvtogo.jarbasskills.play_event",
                                  self.play_video_event)
        self.gui.register_handler("skill-mytvtogo.jarbasskills.clear_history",
                                  self.play_video_event)

    def get_intro_message(self):
        self.speak_dialog("intro")
        
    @intent_file_handler('mytvtogohome.intent')
    def handle_homescreen_utterance(self, message):
        self.handle_homescreen(message)

    # homescreen
    def handle_homescreen(self, message):
        self.gui["mytvtogoHomeModel"] = self.channels
        self.gui["historyModel"] = []
        self.gui.show_page("Homescreen.qml", override_idle=True)

    # play via GUI event
    def play_video_event(self, message):
        channel_data = message.data["modelData"]
        self.play_channel(channel_data)

    # clear history event
    def clear_history_event(self, message):
        self.historyDB.clear()

    # common play
    def play_channel(self, channel_data):
        if not self.gui.connected:
            self.log.error("GUI is required for MyTVtoGo skill, "
                             "but no GUI connection was detected")
            raise RuntimeError
        # add to playback history
        self.history_list.append(channel_data)
        self.historyDB["model"] = self.history_list
        self.historyDB.store()
        self.gui["historyModel"] = self.historyDB["model"]
        # play video
        channel = Media.from_json(channel_data)
        url = str(channel.streams[0])
        self.gui.play_video(url, channel.name)

    def remove_voc(self, utt, voc_filename, lang=None):
        lang = lang or self.lang
        cache_key = lang + voc_filename

        if cache_key not in self.voc_match_cache:
            # trigger caching
            self.voc_match(utt, voc_filename, lang)

        if utt:
            # Check for matches against complete words
            for i in self.voc_match_cache[cache_key]:
                # Substitute only whole words matching the token
                utt = re.sub(r'\b' + i + r"\b", "", utt)

        return utt

    def match_media_type(self, phrase, media_type):
        match = None
        score = 0

        if self.voc_match(phrase,
                          "video") or media_type == CPSMatchType.VIDEO:
            score += 0.1
            match = CPSMatchLevel.GENERIC

        if self.voc_match(phrase,
                          "music") or media_type == CPSMatchType.MUSIC:
            score += 0.1
            match = CPSMatchLevel.GENERIC

        if self.voc_match(phrase, "tv") or media_type == CPSMatchType.TV:
            score += 0.5
            match = CPSMatchLevel.CATEGORY

        if self.voc_match(phrase, "news") or media_type == CPSMatchType.NEWS:
            score += 0.1
            match = CPSMatchLevel.CATEGORY

        if self.voc_match(phrase,
                          "movie") or media_type == CPSMatchType.MOVIE:
            score += 0.2
            match = CPSMatchLevel.CATEGORY

        return match, score

    def match_topics(self, phrase, media_type):
        tags = []
        if self.voc_match(phrase, "news") or media_type == CPSMatchType.NEWS:
            tags.append("News")

        if self.voc_match(phrase, "movie") or media_type == \
                CPSMatchType.MOVIE:
            tags.append("Movies")

        if self.voc_match(phrase, "music") or media_type == \
                CPSMatchType.MUSIC:
            tags.append("Music")

        if self.voc_match(phrase, "kids"):
            tags.append("Kids")
            tags.append("Cartoon")
            tags.append("Children")
        return tags

    def CPS_match_query_phrase(self, phrase, media_type):
        explicit_request = False
        leftover_text = phrase
        best_score = 0
        best_channel = None

        # match for skill name
        if self.voc_match(phrase, "mytvtogo"):
            explicit_request = True
            leftover_text = self.remove_voc(phrase, "mytvtogo")

        # dont match if gui is not connected
        if not self.gui.connected and not explicit_request:
            return None

        # see if media type is in query, base_score will depend if "tv" or
        # "movie" etc were requested vs "podcast"
        match, base_score = self.match_media_type(phrase, media_type)

        # filter channels by category (news, movies, kids, music ...)
        filtered_topics = self.match_topics(phrase, media_type)
        channels = list(self.channels)
        if filtered_topics:
            filtered_channels = []
            for ch in channels:
                for t in [t.lower() for t in filtered_topics]:
                    tags = [t.lower() for t in ch.get("tags", [])]
                    if t in tags:
                        filtered_channels.append(ch)
            channels = filtered_channels
            # we matched a category, increase match score
            if filtered_channels:
                base_score += 0.1

        # this skill was requested by name, ensure something is played
        if explicit_request:
            best_channel = random.choice(channels)

        # score tags
        for ch in channels:
            score = 0
            tags = ch.get("tags", [])
            if tags:
                # tag match bonus
                for tag in tags:
                    tag = tag.lower().strip()
                    if filtered_topics and tag not in filtered_topics:
                        continue
                    if tag in phrase:
                        score += 0.1
                        leftover_text = leftover_text.replace(tag, "")
                else:
                    # fuzzy bonus
                    if filtered_topics:
                        tag, tag_score = match_one(phrase, filtered_topics)
                    else:
                        tag, tag_score = match_one(phrase, ch["tags"])
                    score += tag_score

            if score > best_score:
                best_channel = ch
                best_score = score

        # match channel name
        for ch in channels:
            score = fuzzy_match(leftover_text,
                                ch["title"].lower().strip())
            if score > best_score:
                best_channel = ch
                best_score = score

        if not best_channel:
            self.log.debug("No MyTVtoGo matches")
            return None

        if explicit_request:
            score = 1.0
        else:
            score = base_score + best_score

        if score >= 0.85:
            match = CPSMatchLevel.EXACT
        elif score >= 0.7:
            match = CPSMatchLevel.MULTI_KEY
        elif score >= 0.5:
            match = CPSMatchLevel.TITLE

        self.log.debug("Best MyTVtoGo channel: " + best_channel["title"])

        if match is not None:
            return (leftover_text, match, best_channel)
        return None

    def CPS_start(self, phrase, data):
        self.play_channel(data)


def create_skill():
    return MyTVtoGoSkill()
