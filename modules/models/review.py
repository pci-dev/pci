from __future__ import annotations # for self-ref param type Post in save_posts_in_db()
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Iterable, List, Optional as _, cast
from gluon.contrib.appconfig import AppConfig
from models.recommendation import Recommendation
from pydal.objects import Row, Rows
from pydal import DAL

myconf = AppConfig(reload=True)
pciRRactivated = myconf.get("config.registered_reports", default=False)

class ReviewDuration(Enum):
    TWO_WEEK = 'Two weeks'
    THREE_WEEK = 'Three weeks'
    FOUR_WEEK = 'Four weeks'
    FIVE_WEEK = 'Five weeks'
    SIX_WEEK = 'Six weeks'
    SEVEN_WEEK = 'Seven weeks'
    EIGHT_WEEK = 'Eight weeks'


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
    NEED_EXTRA_REVIEW_TIME = 'Need extra review time'
    

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
    review_duration: _[str]
    anonymous_agreement: _[bool]
    suggested_reviewers_send: _[bool]
    due_date: _[datetime]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(_[Review], db.t_reviews[id])


    @staticmethod
    def get_by_recommendation_id(db: DAL, id: int, order_by: _[Any] = None):
        if order_by:
            return cast(Iterable[Review], db(db.t_reviews.recommendation_id == id).select(orderby=order_by))
        else:
            return cast(Iterable[Review], db(db.t_reviews.recommendation_id == id).select())
    

    @staticmethod
    def get_by_article_id_and_state(db: DAL, article_id: int, state: ReviewState):
        recommendations_id = cast(Rows, db(db.t_recommendations.article_id == article_id).select(db.t_recommendations.id))
        reviews = cast(List[Review],db((db.t_reviews.review_state == state.value) & (db.t_reviews.recommendation_id).belongs(recommendations_id)).select())
        return reviews
    
    
    @staticmethod
    def get_all_active_reviews(db: DAL, recommendation_id: int, user_id: int):
        reviews = db((db.t_reviews.recommendation_id == recommendation_id) & (db.t_reviews.reviewer_id == user_id) & (db.t_reviews.review_state != ReviewState.DECLINED_MANUALLY.value) & (db.t_reviews.review_state != ReviewState.DECLINED.value) & (db.t_reviews.review_state != ReviewState.CANCELLED.value)).select(
            orderby=db.t_reviews.id
        )
        return cast(List[Review], reviews)


    @staticmethod
    def accept_review(review: Review, anonymous_agreement: _[bool] = False, state: ReviewState = ReviewState.AWAITING_REVIEW):
        review.review_state = state.value
        review.no_conflict_of_interest = True
        review.acceptation_timestamp = datetime.now()
        review.anonymous_agreement = anonymous_agreement or False
        if review.review_duration:
            review.due_date = Review.get_due_date_from_review_duration(review)
        return review.update_record()
    

    @staticmethod
    def set_suggested_reviewers_send(review: Review):
        review.suggested_reviewers_send = True
        return review.update_record()
    
    
    @staticmethod
    def set_review_duration(review: Review, review_duration: str):
        review.review_duration = review_duration
        due_date = Review.get_due_date_from_review_duration(review)
        if due_date:
            review.due_date = due_date
        return review.update_record()
    

    @staticmethod
    def set_review_status(review: Review, state: ReviewState):
        review.review_state = state.value
        return review.update_record()


    @staticmethod
    def get_unfinished_reviews(db: DAL, recommendation: Recommendation):
        return cast(int, db((db.t_reviews.recommendation_id == recommendation.id) & (db.t_reviews.review_state.belongs(ReviewState.AWAITING_RESPONSE.value, ReviewState.AWAITING_REVIEW.value))).count())


    @staticmethod
    def is_reviewer_also_recommender(db: DAL, recommendation: Recommendation):
        return cast(bool, db((db.t_reviews.recommendation_id == recommendation.id) & (db.t_reviews.reviewer_id == recommendation.recommender_id)).count() == 1)


    @staticmethod
    def set_due_date(review: Review, due_date: datetime):
        if review.acceptation_timestamp and due_date <= review.acceptation_timestamp:
            raise ValueError(f"Date must be after acceptation date. ({datetime.strftime(review.acceptation_timestamp, '%Y-%m-%d')})")
        review.due_date = due_date
        review.update_record()
    

    @staticmethod
    def get_due_date_from_review_duration(review: Review):
            nb_days_from_duration = Review.get_review_days_from_duration(review)
            if review.acceptation_timestamp:
                return review.acceptation_timestamp + timedelta(nb_days_from_duration)
            else:
                return datetime.today() + timedelta(nb_days_from_duration)
    

    @staticmethod
    def get_review_days_from_duration(review: _[Review]):
        dow = datetime.today().weekday()
        duration: str = ''

        if review and review.review_duration:
            duration = review.review_duration
        else:
            duration = Review.get_default_review_duration()

        days_dict = {
                ReviewDuration.TWO_WEEK.value: 14,
                ReviewDuration.THREE_WEEK.value: 21,
                ReviewDuration.FOUR_WEEK.value: 28,
                ReviewDuration.FIVE_WEEK.value: 35,
                ReviewDuration.SIX_WEEK.value: 42,
                ReviewDuration.SEVEN_WEEK.value: 49,
                ReviewDuration.EIGHT_WEEK.value: 56,
                "Five working days": 7 if dow < 5 else (7 + (7-dow))
        }

        for key, value in days_dict.items():
            if key in duration:
                return value

        return 21
    

    @staticmethod
    def get_review_days_from_due_date(review: _[Review]):
        if review and review.due_date:
            if review.acceptation_timestamp:
                diff = review.acceptation_timestamp - review.due_date
            else:
                diff = datetime.today() - review.due_date
            return diff.days
        else:
            return Review.get_review_days_from_duration(review)


    @staticmethod
    def get_default_review_duration():
        return ReviewDuration.TWO_WEEK.value if pciRRactivated else ReviewDuration.THREE_WEEK.value

        