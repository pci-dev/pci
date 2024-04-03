from typing import List, Optional as _, cast
from pydal.objects import Row
from gluon import current


class SuggestedRecommender(Row):
    id: int
    article_id: int
    suggested_recommender_id: int
    email_sent: _[bool]
    declined: _[bool]
    emailing: _[str]


    @staticmethod
    def get_by_id(id: int):
        db = current.db
        return cast(_[SuggestedRecommender], db.t_suggested_recommenders[id])
    

    @staticmethod
    def get_suggested_recommender_by_article(article_id: int):
        db = current.db
        return cast(_[List[SuggestedRecommender]], db(db.t_suggested_recommenders.article_id == article_id).select())
