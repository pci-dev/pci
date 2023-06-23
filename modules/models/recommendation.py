from datetime import datetime
from typing import Optional, cast
from pydal.objects import Row
from pydal import DAL


class Recommendation(Row):
    id: int
    article_id: int
    recommendation_comments: Optional[str]
    recommendation_timestamp: Optional[datetime]
    doi: Optional[str]
    recommender_id: int
    last_change: Optional[datetime]
    reply: Optional[str]
    is_closed: Optional[bool]
    is_press_review: Optional[bool]
    auto_nb_agreements: Optional[int]
    no_conflict_of_interest: Optional[bool]
    recommendation_title: Optional[str]
    recommendation_doi: Optional[str]
    recommendation_state: Optional[str]
    reply_pdf: Optional[str]
    reply_pdf_data: Optional[bytes]
    track_change: Optional[str]
    track_change_data: Optional[bytes]
    ms_version: Optional[str]
    recommender_file: Optional[str]
    recommender_file_data: Optional[bytes]
    recommender_details: Optional[str]
    author_last_change: Optional[datetime]
    validation_timestamp: Optional[datetime]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(Optional[Recommendation], db.t_recommendations[id])
