from __future__ import annotations # for self-ref param type Post in save_posts_in_db()
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Iterable, List, Optional as _, Tuple, cast
from models.article import is_scheduled_submission
from models.article import Article
from models.recommendation import Recommendation
from models.report_survey import ReportSurvey
from models.user import User
from pydal.objects import Row, Rows
from gluon import current

class ReviewDuration(Enum):
    FIVE_WORKING_DAY = 'Five working days'
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
    review_duration: _[str]
    anonymous_agreement: _[bool]
    suggested_reviewers_send: _[bool]
    due_date: _[datetime]


    @staticmethod
    def get_by_id(id: int):
        db = current.db
        return cast(_[Review], db.t_reviews[id])


    @staticmethod
    def get_by_recommendation_id(id: int, order_by: _[Any] = None):
        db = current.db
        if order_by:
            return cast(Iterable[Review], db(db.t_reviews.recommendation_id == id).select(orderby=order_by))
        else:
            return cast(Iterable[Review], db(db.t_reviews.recommendation_id == id).select())
    

    @staticmethod
    def get_by_article_id_and_state(article_id: int, state: ReviewState):
        db = current.db
        recommendations_id = cast(Rows, db(db.t_recommendations.article_id == article_id).select(db.t_recommendations.id))
        reviews = cast(List[Review],db((db.t_reviews.review_state == state.value) & (db.t_reviews.recommendation_id).belongs(recommendations_id)).select())
        return reviews
    
    
    @staticmethod
    def get_all_active_reviews(recommendation_id: int, user_id: int):
        db = current.db
        reviews = db((db.t_reviews.recommendation_id == recommendation_id) & (db.t_reviews.reviewer_id == user_id) & (db.t_reviews.review_state != ReviewState.DECLINED_MANUALLY.value) & (db.t_reviews.review_state != ReviewState.DECLINED.value) & (db.t_reviews.review_state != ReviewState.CANCELLED.value)).select(
            orderby=db.t_reviews.id
        )
        return cast(List[Review], reviews)


    @staticmethod
    def accept_review(review: Review, article: Article, anonymous_agreement: _[bool] = False, state: ReviewState = ReviewState.AWAITING_REVIEW):
        review.review_state = state.value
        review.no_conflict_of_interest = True
        review.acceptation_timestamp = datetime.now()
        review.anonymous_agreement = anonymous_agreement or False
        if review.review_duration:
            Review.set_review_duration(review, article, review.review_duration)
        return review.update_record()
    

    @staticmethod
    def set_suggested_reviewers_send(review: Review):
        review.suggested_reviewers_send = True
        return review.update_record()
    
    
    @staticmethod
    def set_review_duration(review: Review, article: Article, review_duration: str):
        review.review_duration = review_duration
        if not is_scheduled_submission(article):
            due_date = Review.get_due_date_from_review_duration(review)
            if due_date:
                Review.set_due_date(review, due_date)
        return review.update_record()
    

    @staticmethod
    def set_review_status(review: Review, state: ReviewState):
        review.review_state = state.value
        return review.update_record()


    @staticmethod
    def get_unfinished_reviews(recommendation: Recommendation):
        db = current.db
        return cast(int, db((db.t_reviews.recommendation_id == recommendation.id) & (db.t_reviews.review_state.belongs(ReviewState.AWAITING_RESPONSE.value, ReviewState.AWAITING_REVIEW.value))).count())


    @staticmethod
    def is_reviewer_also_recommender(recommendation: Recommendation):
        db = current.db
        return cast(bool, db((db.t_reviews.recommendation_id == recommendation.id) & (db.t_reviews.reviewer_id == recommendation.recommender_id)).count() == 1)


    @staticmethod
    def set_due_date(review: Review, due_date: datetime):
        if review.acceptation_timestamp and due_date <= review.acceptation_timestamp:
            raise ValueError(f"Date must be after acceptation date. ({datetime.strftime(review.acceptation_timestamp, '%Y-%m-%d')})")
        review.due_date = due_date
        review.update_record()
    

    @staticmethod
    def get_due_date(review: Review):
        if review.due_date:
            return review.due_date
        
        due_date: _[datetime] = None
        if current.isRR:
            due_date = Review.get_due_date_from_scheduled_submission_date(review)
        
        if not due_date:
            due_date = Review.get_due_date_from_review_duration(review)

        return due_date


    @staticmethod
    def get_due_date_from_review_duration(review: Review):
        nb_days_from_duration = Review.get_review_days_from_duration(review)
        if review.acceptation_timestamp:
            return review.acceptation_timestamp + timedelta(nb_days_from_duration)
        else:
            return datetime.today() + timedelta(nb_days_from_duration)
        

    @staticmethod
    def get_due_date_from_scheduled_submission_date(review: Review):
        recommendation = Recommendation.get_by_id(review.recommendation_id)
        if not recommendation:
            return None
        
        article = Article.get_by_id(recommendation.article_id)
        if not article:
            return None
        
        if not is_scheduled_submission(article):
            return None
        
        report_survey = ReportSurvey.get_by_article(article.id)

        if report_survey and report_survey.q10:
            review_start_date = report_survey.q10 + timedelta(days=7)
            review_due_date = review_start_date + timedelta(days=7)
            return review_due_date
    

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
            diff = datetime.today() - review.due_date
            return abs(diff.days)
        else:
            return Review.get_review_days_from_duration(review)


    @staticmethod
    def get_default_review_duration():
        return ReviewDuration.TWO_WEEK.value if current.isRR else ReviewDuration.THREE_WEEK.value

        
    @staticmethod
    def get_all_with_reviewer(reviews_states: List[ReviewState] = []):
        db = current.db
        if len(reviews_states) == 0:
            result = db(db.t_reviews.reviewer_id == db.auth_user.id).select(db.t_reviews.ALL, db.auth_user.ALL, orderby=db.auth_user.last_name|db.auth_user.first_name)
        else:
            states_values: List[str] = []
            for review_state in reviews_states:
                states_values.append(review_state.value)
            result = db((db.t_reviews.reviewer_id == db.auth_user.id) & (db.t_reviews.review_state.belongs(states_values))).select(orderby=db.auth_user.last_name|db.auth_user.first_name)

        formatted_result: List[Tuple[Review, User]] = []
        for line in result:
            formatted_result.append((line.t_reviews, line.auth_user))

        return formatted_result
    

    @staticmethod
    def get_all_by_user(reviewer_id: int, reviews_states: List[ReviewState] = []):
        db = current.db
        if len(reviews_states) == 0:
            result = db((db.t_reviews.reviewer_id == db.auth_user.id) & (db.t_reviews.reviewer_id == reviewer_id)).select(db.t_reviews.ALL, orderby=db.auth_user.last_name|db.auth_user.first_name)
        else:
            states_values: List[str] = []
            for review_state in reviews_states:
                states_values.append(review_state.value)
            result = db((db.t_reviews.reviewer_id == db.auth_user.id) & (db.t_reviews.review_state.belongs(states_values)) & (db.t_reviews.reviewer_id == reviewer_id)).select(db.t_reviews.ALL, orderby=db.auth_user.last_name|db.auth_user.first_name)
        return cast(List[Review], result)


    @staticmethod
    def change_reviews_state(reviewer_id: int, reviews_states: List[ReviewState], new_review_state: ReviewState):
        reviews = Review.get_all_by_user(reviewer_id, reviews_states)
        for review in reviews:
            Review.set_review_status(review, new_review_state)
        return reviews
        

    @staticmethod
    def get_reviewer_name(review: Review):
        reviewer = User.get_by_id(review.reviewer_id)
        if not reviewer:
            return "?"
        
        return User.get_name(reviewer)
    

    @staticmethod
    def get_reviewers_name(article_id: int) -> str:
        reviews = Review.get_by_article_id_and_state(article_id, ReviewState.REVIEW_COMPLETED)
        nb_anonymous = 0
        names: List[str] = []
        user_id: List[int] = []
        for review in reviews:
            if not review.anonymously and review.reviewer_id not in user_id:
                reviewer_name = Review.get_reviewer_name(review)
                if reviewer_name:
                    names.append(reviewer_name)
                if review.reviewer_id:
                    user_id.append(review.reviewer_id)
        
        user_id.clear()

        for review in reviews:
            if review.anonymously and review.reviewer_id not in user_id:
                nb_anonymous += 1
                if review.reviewer_id:
                    user_id.append(review.reviewer_id)
        
        if (nb_anonymous > 0):
            anonymous = str(nb_anonymous) + ' anonymous reviewer'
            if (nb_anonymous > 1):
                anonymous += 's'
            names.append(anonymous)
            
        formatted_names = ', '.join(names)

        return (formatted_names[::-1].replace(',', ' and'[::-1], 1))[::-1] 


    @staticmethod
    def are_equal(review_1: Review, review_2: Review):
        attributes = getattr(Review, '__annotations__', {})

        for attribute in attributes.keys():
            if attribute == 'last_change':
                continue
            
            if getattr(review_1, attribute, None) != getattr(review_2, attribute, None):
                return False
        return True
