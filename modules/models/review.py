from datetime import datetime
from enum import Enum
from typing import Iterable, List, Union, cast
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
    review: Union[str, None]
    last_change: Union[datetime, None]
    is_closed: Union[bool, None]
    anonymously: Union[bool, None]
    review_state: Union[str, None]
    no_conflict_of_interest: Union[bool, None]
    review_pdf: Union[str, None]
    review_pdf_data: Union[bytes, None]
    acceptation_timestamp: Union[datetime, None]
    emailing: Union[str, None]
    quick_decline_key: Union[str, None]
    reviewer_details: Union[str, None]
    review_duration: Union[datetime, None]
    anonymous_agreement: Union[bool, None]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(Union[Review, None], db.t_reviews[id])


    @staticmethod
    def get_by_recommendation_id(db: DAL, id: int):
        return cast(Iterable[Review], db(db.t_reviews.recommendation_id == id).select())
    

    @staticmethod
    def get_by_article_id_and_state(db: DAL, article_id: int, state: ReviewState):
        recommendations_id = cast(Rows, db(db.t_recommendations.article_id == article_id).select(db.t_recommendations.id))
        reviews = cast(List[Review],db((db.t_reviews.review_state == state.value) & (db.t_reviews.recommendation_id).belongs(recommendations_id)).select())
        return reviews


