from datetime import datetime
from enum import Enum
from typing import Iterable, List, Optional as _, cast
from pydal.objects import Row, Rows
from pydal import DAL

class ReviewState(Enum):
    CANCELLED = 'Cancelled'
    ASK_FOR_REVIEW = 'Ask for review'
    DECLINED_BY_RECOMMENDER = 'Declined by recommender'
    AWAITING_REVIEW = 'Awaiting review'
    AWAITING_RESPONSE = 'Awaiting response'
    DECLINED_MANUALLY = 'Declined manually'
    WILLING_TO_REVIEW = 'Willing to review'
    DECLINED = 'Declined'
    REVIEW_COMPLETED = 'Review completed'
    

class Review(Row):
    id: int
    recommendation_id: int
    reviewer_id: int
    review: _[str]
    last_change: _[datetime]
    is_closed: _[bool]
    anonymously: _[bool]
    review_state: _[str]
    no_conflict_of_interest: _[bool]
    review_pdf: _[str]
    review_pdf_data: _[bytes]
    acceptation_timestamp: _[datetime]
    emailing: _[str]
    quick_decline_key: _[str]
    reviewer_details: _[str]
    review_duration: _[datetime]
    anonymous_agreement: _[bool]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(_[Review], db.t_reviews[id])


    @staticmethod
    def get_by_recommendation_id(db: DAL, id: int):
        return cast(Iterable[Review], db(db.t_reviews.recommendation_id == id).select())
    

    @staticmethod
    def get_by_article_id_and_state(db: DAL, article_id: int, state: ReviewState):
        recommendations_id = cast(Rows, db(db.t_recommendations.article_id == article_id).select(db.t_recommendations.id))
        reviews = cast(List[Review],db((db.t_reviews.review_state == state.value) & (db.t_reviews.recommendation_id).belongs(recommendations_id)).select())
        return reviews
    
    
    @staticmethod
    def get_all_active_reviews(db: DAL, recommendation_id: int, user_id: int):
        reviews = db((db.t_reviews.recommendation_id == recommendation_id) & (db.t_reviews.reviewer_id == user_id) & (db.t_reviews.review_state != "Declined manually") & (db.t_reviews.review_state != "Declined") & (db.t_reviews.review_state != "Cancelled")).select(
            orderby=db.t_reviews.id
        )
        return cast(List[Review], reviews)


