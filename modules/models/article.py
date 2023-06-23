from datetime import datetime
from typing import Optional, cast
from pydal.objects import Row
from pydal import DAL


class Article(Row):
    id: int
    title: Optional[str]
    doi: Optional[str]
    abstract: Optional[str]
    upload_timestamp: Optional[datetime]
    user_id: Optional[int]
    authors: Optional[str]
    thematics: Optional[str]
    keywords: Optional[str]
    auto_nb_recommendations: Optional[int]
    suggested_recommender_id: Optional[int]
    status: str
    last_status_change: Optional[datetime]
    article_source: Optional[str]
    already_published: Optional[bool]
    picture_data: Optional[bytes]
    uploaded_picture: Optional[str]
    picture_rights_ok: Optional[bool]
    ms_version: Optional[str]
    anonymous_submission: Optional[bool]
    cover_letter: Optional[str]
    parallel_submission: Optional[bool]
    is_searching_reviewers: Optional[bool]
    art_stage_1_id: Optional[int]
    scheduled_submission_date: Optional[datetime]
    report_stage: Optional[str]
    sub_thematics: Optional[str]
    record_url_version: Optional[str]
    record_id_version: Optional[str]
    has_manager_in_authors: Optional[bool]
    results_based_on_data: Optional[str]
    data_doi: Optional[str]
    scripts_used_for_result: Optional[str]
    scripts_doi: Optional[str]
    codes_used_in_study: Optional[str]
    codes_doi: Optional[str]
    suggest_reviewers: Optional[str]
    competitors: Optional[str]
    doi_of_published_article: Optional[str]
    submitter_details: Optional[str]
    request_submission_change: Optional[bool]
    validation_timestamp: Optional[datetime]
    preprint_server: Optional[str]
    funding: Optional[str]
    article_year: Optional[int]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(Optional[Article], db.t_articles[id])
