from datetime import datetime
from enum import Enum
from typing import List, Optional as _, cast
from pydal.objects import Row
from pydal import DAL

class ArticleStatus(Enum):
    NOT_CONSIDERED = 'Not considered'
    PRE_RECOMMENDED = 'Pre-recommended'
    AWAITING_REVISION = 'Awaiting revision'
    RECOMMENDED = 'Recommended'
    UNDER_CONSIDERATION = 'Under consideration'
    REJECTED = 'Rejected'
    PRE_REJECTED = 'Pre-rejected'
    CANCELLED = 'Cancelled'
    AWAITING_CONSIDERATION = 'Awaiting consideration'
    PENDING = 'Pending'
    PRE_SUBMISSION = 'Pre-submission'
    PRE_RECOMMENDED_PRIVATE = 'Pre-recommended-private'
    PRE_REVISION = 'Pre-revision'
    SCHEDULED_SUBMISSION_PENDING = 'Scheduled submission pending'
    SCHEDULED_SUBMISSION_UNDER_CONSIDERATION = 'Scheduled submission under consideration'


class Article(Row):
    id: int
    title: _[str]
    doi: _[str]
    abstract: _[str]
    upload_timestamp: _[datetime]
    user_id: _[int]
    authors: _[str]
    thematics: _[str]
    keywords: _[str]
    auto_nb_recommendations: _[int]
    suggested_recommender_id: _[int]
    status: str
    last_status_change: _[datetime]
    article_source: _[str]
    already_published: _[bool]
    picture_data: _[bytes]
    uploaded_picture: _[str]
    picture_rights_ok: _[bool]
    ms_version: _[str]
    anonymous_submission: _[bool]
    cover_letter: _[str]
    parallel_submission: _[bool]
    is_searching_reviewers: _[bool]
    art_stage_1_id: _[int]
    scheduled_submission_date: _[datetime]
    report_stage: _[str]
    sub_thematics: _[str]
    record_url_version: _[str]
    record_id_version: _[str]
    has_manager_in_authors: _[bool]
    results_based_on_data: _[str]
    data_doi: _[str]
    scripts_used_for_result: _[str]
    scripts_doi: _[str]
    codes_used_in_study: _[str]
    codes_doi: _[str]
    suggest_reviewers: _[List[str]]
    competitors: _[List[str]]
    doi_of_published_article: _[str]
    submitter_details: _[str]
    request_submission_change: _[bool]
    validation_timestamp: _[datetime]
    preprint_server: _[str]
    funding: _[str]
    article_year: _[int]
    is_scheduled: bool


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(_[Article], db.t_articles[id])
