import secrets
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
    quick_decline_key: _[str]
    recommender_validated: _[bool]


    @staticmethod
    def get_by_id(id: int):
        db = current.db
        return cast(_[SuggestedRecommender], db.t_suggested_recommenders[id])


    @staticmethod
    def get_by_article_and_user_id(article_id: int, user_id: int):
        db = current.db
        suggested_recommender: _[SuggestedRecommender] = db((db.t_suggested_recommenders.article_id == article_id) & (db.t_suggested_recommenders.suggested_recommender_id == user_id)).select().first()
        return suggested_recommender


    @staticmethod
    def get_suggested_recommender_by_article(article_id: int):
        db = current.db
        return cast(_[List[SuggestedRecommender]], db(db.t_suggested_recommenders.article_id == article_id).select())


    @staticmethod
    def nb_suggested_recommender(article_id: int, declined: bool = False):
        db = current.db
        if declined:
            return int(db((db.t_suggested_recommenders.article_id == article_id) & (db.t_suggested_recommenders.declined == True)).count())
        else:
            return int(db(db.t_suggested_recommenders.article_id == article_id).count())


    @staticmethod
    def get_suggested_recommender_by_quick_decline_key(quick_decline_key: str):
        db = current.db
        suggested_recommender: _[SuggestedRecommender] = db(db.t_suggested_recommenders.quick_decline_key == quick_decline_key).select().first()
        return suggested_recommender


    @staticmethod
    def decline(suggested_recommender: 'SuggestedRecommender'):
        suggested_recommender.declined = True
        suggested_recommender.update_record()
        current.db.commit()


    @staticmethod
    def add_suggested_recommender(recommender_id: int, article_id: int):
        db = current.db
        quick_decline_key = secrets.token_urlsafe(64)
        db.t_suggested_recommenders.update_or_insert(
            suggested_recommender_id=recommender_id,
            article_id=article_id,
            quick_decline_key=quick_decline_key)
