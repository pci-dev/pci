from typing import Optional as _
from pydal.objects import Row


class PressReview(Row):
    id: int
    recommendation_id: int
    contributor_id: _[int]
    contributor_details: _[str]
