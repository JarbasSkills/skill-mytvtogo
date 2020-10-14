from mycroft.skills.common_play_skill import CommonPlaySkill, \
    CPSMatchLevel, CPSTrackStatus, CPSMatchType
from mycroft.skills.core import intent_file_handler
from pyvod import Collection, Media
from os.path import join, dirname, exists
from os import makedirs
import random
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

        # database bootstrap
        path = join(XDG_DATA_HOME, "json_database")
        if not exists(path):
            makedirs(path)
        path = join(path, "mytvtogo.jsondb")
        if not exists(path):
            copy(join(dirname(__file__), "res", "mytvtogo.jsondb"), path)

        # load channel catalog
        self.mytvtogo = Collection("MyTVToGo",
                    logo=join(dirname(__file__), "res", "MyTVToGo.png"),
                    db_path=path)

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
        self.handle_homescreen({}) 

    # homescreen
    def handle_homescreen(self, message):
        self.build_homescreen()
        
    # build_homescreen
    def build_homescreen(self):
        # build a model for MyTVToGo
        my_tv_to_go_dump = [ch.as_json() for ch in self.mytvtogo.entries]
        self.gui["mytvtogoHomeModel"] = my_tv_to_go_dump

        # set history model
        self.gui["historyModel"] = []

        self.gui.show_page("home.qml", override_idle=True)

    # play via GUI event
    def play_video_event(self, message):
        channel_data = message.data["modelData"]

        self.history_list.append(channel_data)
        self.historyDB["model"] = self.history_list
        self.historyDB.store()
        self.gui["historyModel"] = self.historyDB["model"]

        channel = Media.from_json(channel_data)
        url = str(channel.streams[0])

        self.gui.play_video(url, channel_data["title"])

    # clear history event
    def clear_history_event(self, message):
        self.historyDB.clear()

    # common play
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

    def match_lang(self, phrase):
        langs = []

        if self.voc_match(phrase, "pt"):
            langs.append("pt")
        if self.voc_match(phrase, "es"):
            langs.append("es")
        if self.voc_match(phrase, "en"):
            langs.append("en")
        if self.voc_match(phrase, "fr"):
            langs.append("fr")
        if self.voc_match(phrase, "de"):
            langs.append("de")
        if self.voc_match(phrase, "it"):
            langs.append("it")

        if langs:
            langs.append(self.lang)
            langs.append(self.lang.split("-")[0])
        return langs

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
        return tags

    def CPS_match_query_phrase(self, phrase, media_type):

        if not self.gui.connected:
            return None

        match, base_score = self.match_media_type(phrase, media_type)

        allowed_langs = self.match_lang(phrase)

        allowed_tags = self.match_topics(phrase, media_type)

        matches = []
        # TODO

        if not len(matches):
            self.log.debug("No MyTVtoGo matches")
            return None

        # TODO disambiguate
        best = matches[0][1]
        candidates = [m for m in matches if m[1] >= best - 0.1]
        self.log.debug("Candidate Channels: " + str(candidates))
        selected = random.choice(candidates)

        score = base_score + selected[1]

        if score >= 0.85:
            match = CPSMatchLevel.EXACT
        elif score >= 0.7:
            match = CPSMatchLevel.MULTI_KEY
        elif score >= 0.5:
            match = CPSMatchLevel.TITLE

        self.log.debug("Best MyTVtoGo channel: " + str(selected[0].as_json()))

        if match is not None:
            return (phrase, match, matches[0][0].as_json())
        return None

    def CPS_start(self, phrase, data):
        channel = Media.from_json(data)
        url = str(channel.streams[0])

        self.gui.play_video(url, channel.name or phrase)


def create_skill():
    return MyTVtoGoSkill()
