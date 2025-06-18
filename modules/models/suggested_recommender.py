from enum import Enum
import secrets
from typing import Any, List, Optional as _, cast
from .article import Article, ArticleStatus
from pydal.objects import Row


class SuggestedBy(Enum):
    AUTHORS = 'Authors'
    THEMSELVES = 'Themselves'
    MANAGERS = 'Managers'


class SuggestedRecommender(Row):
    id: int
    article_id: int
    suggested_recommender_id: int
    email_sent: _[bool]
    declined: _[bool]
    emailing: _[str]
    quick_decline_key: _[str]
    recommender_validated: _[bool]
    suggested_by: _[str]


    @staticmethod
    def get_by_id(id: int):
        db = current.db
        return cast(_[SuggestedRecommender], db.t_suggested_recommenders[id])


    @staticmethod
    def get_by_article_and_user_id(article_id: int, user_id: int, declined: _[bool] = None) -> _['SuggestedRecommender']:
        db = current.db
        query = (db.t_suggested_recommenders.article_id == article_id) & (db.t_suggested_recommenders.suggested_recommender_id == user_id)
        if declined is not None:
            query = query & (db.t_suggested_recommenders.declined == declined)

        suggested_recommender = db(query).select().first()
        return suggested_recommender


    @staticmethod
    def delete_sugg_recommender(sugg_recommender_id: int):
        db = current.db
        db(db.t_suggested_recommenders.id == sugg_recommender_id).delete()
        current.db.commit()


    @staticmethod
    def get_by_article(article_id: int,
                       recommender_validated_unset: bool = False,
                       declined: _[bool] = None,
                       suggested_by: _[SuggestedBy] = None) -> List['SuggestedRecommender']:
        db = current.db
        query = (db.t_suggested_recommenders.article_id == article_id)

        if recommender_validated_unset:
            query = query & (db.t_suggested_recommenders.recommender_validated == None)

        if declined is not None:
            query = query & (db.t_suggested_recommenders.declined == declined)

        if suggested_by is not None:
            query = query & (db.t_suggested_recommenders.suggested_by == suggested_by.value)

        return db(query).select()


    @staticmethod
    def get_validated(article_id: int) -> List['SuggestedRecommender']:
        db = current.db

        query = (db.t_suggested_recommenders.article_id == article_id) \
              & (db.t_suggested_recommenders.declined == False) \
              & (db.t_suggested_recommenders.recommender_validated == True)

        return db(query).select()


    @staticmethod
    def least_one_validated(article_id: int):
        sugg_recommender_validated = SuggestedRecommender.get_validated(article_id)
        return len(sugg_recommender_validated) > 0


    @staticmethod
    def get_all(recommender_validated_unset: bool = False, declined: _[bool] = None, article_status: List[ArticleStatus] = []) -> List['SuggestedRecommender']:
        db = current.db

        query: _[Any] = None

        if recommender_validated_unset:
            sub_query = (db.t_suggested_recommenders.recommender_validated == None)
            if not query:
                query = sub_query
            else:
                query = query & sub_query

        if declined is not None:
            sub_query = (db.t_suggested_recommenders.declined == declined)
            if not query:
                query = sub_query
            else:
                query = query & sub_query

        if len(article_status) > 0:
            articles = Article.get_by_status(article_status)
            article_ids = [a.id for a in articles]
            query = query & (db.t_suggested_recommenders.article_id.belongs(article_ids))

        return db(query).select()


    @staticmethod
    def nb_suggested_recommender(article_id: int, declined: bool = False, just_validated: bool = False):
        db = current.db
        query = (db.t_suggested_recommenders.article_id == article_id)
        if declined:
            query = query & (db.t_suggested_recommenders.declined == True)
        if just_validated:
            query = query & (db.t_suggested_recommenders.recommender_validated == True)
        return int(db(query).count())


    @staticmethod
    def get_suggested_recommender_by_quick_decline_key(quick_decline_key: str):
        db = current.db
        suggested_recommender: _[SuggestedRecommender] = db(db.t_suggested_recommenders.quick_decline_key == quick_decline_key).select().first()
        return suggested_recommender


    @staticmethod
    def decline(suggested_recommender: 'SuggestedRecommender'):
        suggested_recommender.declined = True
        suggested_recommender.update_record() # type: ignore
        current.db.commit()


    @staticmethod
    def add_suggested_recommender(recommender_id: int,
                                  article_id: int,
                                  suggested_by: SuggestedBy,
                                  recommender_validated: _[bool] = None):
        db = current.db
        quick_decline_key = secrets.token_urlsafe(64)

        sugg_recommender = SuggestedRecommender.get_by_article_and_user_id(article_id, recommender_id)
        if sugg_recommender:
            SuggestedRecommender.delete_sugg_recommender(sugg_recommender.id)

        try:
          db.t_suggested_recommenders.update_or_insert(
            suggested_recommender_id=recommender_id,
            article_id=article_id,
            quick_decline_key=quick_decline_key,
            recommender_validated=recommender_validated,
            suggested_by=suggested_by.value)
        except:
            pass # ignore dup key errors (article_id, suggested_recommender_id)


    @staticmethod
    def already_request_willing_to_recommend(article_id: int, recommender_id: int):
        sugg_recommender = SuggestedRecommender.get_by_article_and_user_id(article_id, recommender_id)
        if not sugg_recommender:
            return False
        else:
            return sugg_recommender.suggested_by == SuggestedBy.THEMSELVES.value
