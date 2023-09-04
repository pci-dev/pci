from typing import List, Optional as _, cast
from pydal.objects import Row
from pydal import DAL


class SuggestedRecommender(Row):
    id: int
    article_id: int
    suggested_recommender_id: int
    email_sent: _[bool]
    declined: _[bool]
    emailing: _[str]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(_[SuggestedRecommender], db.t_suggested_recommenders[id])
    

    @staticmethod
    def get_suggested_recommender_by_article(db: DAL, article_id: int):
        return cast(_[List[SuggestedRecommender]], db(db.t_suggested_recommenders.article_id == article_id).select())
