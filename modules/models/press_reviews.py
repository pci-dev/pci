from typing import Any, List, Optional as _, cast
from pydal.objects import Row
from gluon import current


class PressReview(Row):
    id: int
    recommendation_id: int
    contributor_id: _[int]


    @staticmethod
    def get_by_recommendation(recommendation_id: int, order_by: _[Any] = None):
        db = current.db
        if order_by:
            press_reviews = db((db.t_press_reviews.recommendation_id == recommendation_id)).select(orderby=db.t_press_reviews.id)
        else:
            press_reviews = db((db.t_press_reviews.recommendation_id == recommendation_id)).select()
        return cast(List[PressReview], press_reviews)

