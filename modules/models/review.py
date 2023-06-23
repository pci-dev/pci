from datetime import datetime
from enum import Enum
from typing import Iterable, List, Optional, cast
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
    review: Optional[str]
    last_change: Optional[datetime]
    is_closed: Optional[bool]
    anonymously: Optional[bool]
    review_state: Optional[str]
    no_conflict_of_interest: Optional[bool]
    review_pdf: Optional[str]
    review_pdf_data: Optional[bytes]
    acceptation_timestamp: Optional[datetime]
    emailing: Optional[str]
    quick_decline_key: Optional[str]
    reviewer_details: Optional[str]
    review_duration: Optional[datetime]
    anonymous_agreement: Optional[bool]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(Optional[Review], db.t_reviews[id])


    @staticmethod
    def get_by_recommendation_id(db: DAL, id: int):
        return cast(Iterable[Review], db(db.t_reviews.recommendation_id == id).select())
    

    @staticmethod
    def get_by_article_id_and_state(db: DAL, article_id: int, state: ReviewState):
        recommendations_id = cast(Rows, db(db.t_recommendations.article_id == article_id).select(db.t_recommendations.id))
        reviews = cast(List[Review],db((db.t_reviews.review_state == state.value) & (db.t_reviews.recommendation_id).belongs(recommendations_id)).select())
        return reviews


