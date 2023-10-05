from __future__ import annotations # for self-ref param type Post in save_posts_in_db()
from datetime import datetime
from enum import Enum
from typing import List, Optional as _, cast
from models.press_reviews import PressReview
from pydal.objects import Row
from pydal import DAL

class RecommendationState(Enum):
    REJECTED = 'Rejected'
    AWAITING_REVISION = 'Awaiting revision'
    ONGOING = 'Ongoing'
    RECOMMENDED = 'Recommended'
    REVISION = 'Revision'


class Recommendation(Row):
    id: int
    article_id: int
    recommendation_comments: _[str]
    recommendation_timestamp: _[datetime]
    doi: _[str]
    recommender_id: int
    last_change: _[datetime]
    reply: _[str]
    is_closed: _[bool]
    is_press_review: _[bool]
    auto_nb_agreements: _[int]
    no_conflict_of_interest: _[bool]
    recommendation_title: _[str]
    recommendation_doi: _[str]
    recommendation_state: _[str]
    reply_pdf: _[str]
    reply_pdf_data: _[bytes]
    track_change: _[str]
    track_change_data: _[bytes]
    ms_version: _[str]
    recommender_file: _[str]
    recommender_file_data: _[bytes]
    recommender_details: _[str]
    author_last_change: _[datetime]
    validation_timestamp: _[datetime]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(_[Recommendation], db.t_recommendations[id])
    
    @staticmethod
    def get_by_article_id(db: DAL, article_id: int):
        return cast(List[Recommendation], db(db.t_recommendations.article_id == article_id).select())


    @staticmethod
    def get_co_recommenders(db: DAL, recommendation_id: int):
        return cast(List[PressReview], db((db.t_recommendations.id == recommendation_id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id))\
            .select(db.t_press_reviews.ALL, distinct=db.t_press_reviews.contributor_id))


    @staticmethod
    def get_current_round_number(db: DAL, recommendation: Recommendation):
        return cast(int, db((db.t_recommendations.article_id == recommendation.article_id) & (db.t_recommendations.id <= recommendation.id)).count())
