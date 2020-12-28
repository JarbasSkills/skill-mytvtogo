from ovos_utils.waiting_for_mycroft.common_play import CPSMatchType, CPSMatchLevel
from ovos_utils.skills.templates.media_collection import MediaCollectionSkill
from mycroft.skills.core import intent_file_handler
from pyvod import Collection
from os.path import join, dirname, exists, basename


class MyTVtoGoSkill(MediaCollectionSkill):

    def __init__(self):
        super().__init__("MyTVToGo")
        self.supported_media = [CPSMatchType.GENERIC,
                                CPSMatchType.MUSIC,
                                CPSMatchType.NEWS,
                                CPSMatchType.TV,
                                CPSMatchType.MOVIE]
        self.message_namespace = basename(dirname(__file__)) + ".jarbasskills"
        # database update
        path = join(dirname(__file__), "res", "mytvtogo.jsondb")
        logo = join(dirname(__file__), "res", "MyTVToGo.png")
        # load channel catalog
        self.media_collection = Collection("MyTVToGo", logo=logo, db_path=path)

    def get_intro_message(self):
        self.speak_dialog("intro")
        
    @intent_file_handler('home.intent')
    def handle_homescreen_utterance(self, message):
        self.handle_homescreen(message)

    # matching
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
            score += 0.1
            match = CPSMatchLevel.CATEGORY

        return match, score

    def augment_tags(self, phrase, media_type, tags=None):
        tags = tags or []
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

    def normalize_title(self, title):
        return self.remove_voc(title, "mytvtogo")

    def calc_final_score(self, phrase, base_score, match_level):
        score = base_score

        # match for skill name
        if self.voc_match(phrase, "mytvtogo"):
            score = 1.0

        if score >= 0.9:
            match_level = CPSMatchLevel.EXACT
        elif score >= 0.75:
            match_level = CPSMatchLevel.MULTI_KEY
        elif score >= 0.6:
            match_level = CPSMatchLevel.TITLE

        return score, match_level


def create_skill():
    return MyTVtoGoSkill()
