from datetime import datetime
from typing import Iterable, Union, cast
from pydal.objects import Row
from pydal import DAL


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
