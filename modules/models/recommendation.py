from datetime import datetime
from typing import Union, cast
from pydal.objects import Row
from pydal import DAL


class Recommendation(Row):
    id: int
    article_id: int
    recommendation_comments: Union[str, None]
    recommendation_timestamp: Union[datetime, None]
    doi: Union[str, None]
    recommender_id: int
    last_change: Union[datetime, None]
    reply: Union[str, None]
    is_closed: Union[bool, None]
    is_press_review: Union[bool, None]
    auto_nb_agreements: Union[int, None]
    no_conflict_of_interest: Union[bool, None]
    recommendation_title: Union[str, None]
    recommendation_doi: Union[str, None]
    recommendation_state: Union[str, None]
    reply_pdf: Union[str, None]
    reply_pdf_data: Union[bytes, None]
    track_change: Union[str, None]
    track_change_data: Union[bytes, None]
    ms_version: Union[str, None]
    recommender_file: Union[str, None]
    recommender_file_data: Union[bytes, None]
    recommender_details: Union[str, None]
    author_last_change: Union[datetime, None]
    validation_timestamp: Union[datetime, None]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(Union[Recommendation, None], db.t_recommendations[id])
