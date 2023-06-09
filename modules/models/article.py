from datetime import datetime
from typing import Union, cast
from pydal.objects import Row
from pydal import DAL


class Article(Row):
    id: int
    title: Union[str, None]
    doi: Union[str, None]
    abstract: Union[str, None]
    upload_timestamp: Union[datetime, None]
    user_id: Union[int, None]
    authors: Union[str, None]
    thematics: Union[str, None]
    keywords: Union[str, None]
    auto_nb_recommendations: Union[int, None]
    suggested_recommender_id: Union[int, None]
    status: str
    last_status_change: Union[datetime, None]
    article_source: Union[str, None]
    already_published: Union[bool, None]
    picture_data: Union[bytes, None]
    uploaded_picture: Union[str, None]
    picture_rights_ok: Union[bool, None]
    ms_version: Union[str, None]
    anonymous_submission: Union[bool, None]
    cover_letter: Union[str, None]
    parallel_submission: Union[bool, None]
    is_searching_reviewers: Union[bool, None]
    art_stage_1_id: Union[int, None]
    scheduled_submission_date: Union[datetime, None]
    report_stage: Union[str, None]
    sub_thematics: Union[str, None]
    record_url_version: Union[str, None]
    record_id_version: Union[str, None]
    has_manager_in_authors: Union[bool, None]
    results_based_on_data: Union[str, None]
    data_doi: Union[str, None]
    scripts_used_for_result: Union[str, None]
    scripts_doi: Union[str, None]
    codes_used_in_study: Union[str, None]
    codes_doi: Union[str, None]
    suggest_reviewers: Union[str, None]
    competitors: Union[str, None]
    doi_of_published_article: Union[str, None]
    submitter_details: Union[str, None]
    request_submission_change: Union[bool, None]
    validation_timestamp: Union[datetime, None]
    preprint_server: Union[str, None]
    funding: Union[str, None]
    article_year: Union[int, None]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(Union[Article, None], db.t_articles[id])
