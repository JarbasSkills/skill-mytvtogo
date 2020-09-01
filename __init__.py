from mycroft.skills.common_play_skill import CommonPlaySkill, \
    CPSMatchLevel, CPSTrackStatus, CPSMatchType
from ipytv import IPTV
from ipytv.db import Channel
from ipytv.collections import NewsChannels, MyTVToGo, MusicChannels, \
    Portugal, Spain, US, France, Italy
import random


class IPTVSkill(CommonPlaySkill):

    def __init__(self):
        super().__init__("IP TV")
        self.supported_media = [CPSMatchType.GENERIC, CPSMatchType.MUSIC,
                                CPSMatchType.NEWS, CPSMatchType.TV,
                                CPSMatchType.MOVIE]

        # NOTE self.lang is taken into account during search for scoring
        self.iptv = IPTV(lang=self.lang)

    def initialize(self):
        self.add_event('skill-iptv.jarbasskills.home',
                       self.handle_homescreen)

    def get_intro_message(self):
        self.speak_dialog("intro")

    # homescreen
    def handle_homescreen(self, message):
        pass

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

        matches = self.iptv.search(phrase,
                                   tag_whitelist=allowed_tags,
                                   lang_whitelist=allowed_langs,
                                   max_res=5)

        if not len(matches):
            self.log.debug("No user IPTV matches, looking up default channels")

            if "pt" in allowed_langs:
                matches = Portugal.search(phrase,
                                          tag_whitelist=allowed_tags,
                                          lang_whitelist=allowed_langs,
                                          max_res=3)
            elif "es" in allowed_langs:
                matches = Spain.search(phrase,
                                       tag_whitelist=allowed_tags,
                                       lang_whitelist=allowed_langs,
                                       max_res=3)
            elif "fr" in allowed_langs:
                matches = France.search(phrase,
                                        tag_whitelist=allowed_tags,
                                        lang_whitelist=allowed_langs,
                                        max_res=3)
            elif "it" in allowed_langs:
                matches = Italy.search(phrase,
                                       tag_whitelist=allowed_tags,
                                       lang_whitelist=allowed_langs,
                                       max_res=3)

            elif "en" in allowed_langs:
                matches = US.search(phrase,
                                    tag_whitelist=allowed_tags,
                                    lang_whitelist=allowed_langs,
                                    max_res=3)

            else:
                matches = MyTVToGo.search(phrase,
                                          tag_whitelist=allowed_tags,
                                          lang_whitelist=allowed_langs,
                                          max_res=3)
                matches += NewsChannels.search(phrase,
                                               tag_whitelist=allowed_tags,
                                               max_res=3)
                matches += MusicChannels.search(phrase,
                                                tag_whitelist=allowed_tags,
                                                max_res=3)
                if self.lang.startswith("pt"):
                    matches += Portugal.search(phrase,
                                              tag_whitelist=allowed_tags,
                                              max_res=3)
                elif self.lang.startswith("es"):
                    matches += Spain.search(phrase,
                                              tag_whitelist=allowed_tags,
                                              max_res=3)
                elif self.lang.startswith("en"):
                    matches += US.search(phrase,
                                              tag_whitelist=allowed_tags,
                                              max_res=3)
                elif self.lang.startswith("fr"):
                    matches += France.search(phrase,
                                              tag_whitelist=allowed_tags,
                                              max_res=3)
                elif self.lang.startswith("it"):
                    matches += Italy.search(phrase,
                                              tag_whitelist=allowed_tags,
                                              max_res=3)
                matches = sorted(matches, key=lambda k: k[1], reverse=True)

        if not len(matches):
            self.log.debug("No IPTV matches")
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

        self.log.debug("Best TV channel: " + str(selected[0].as_json()))

        if match is not None:
            return (phrase, match, matches[0][0].as_json())
        return None

    def CPS_start(self, phrase, data):
        channel = Channel.from_json(data)
        url = str(channel.best_stream)
        self.gui.play_video(url, channel.name or phrase)


def create_skill():
    return IPTVSkill()
