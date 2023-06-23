from datetime import datetime
from models.typing import _cast, _
from pydal.objects import Row
from pydal import DAL


class Article(Row):
    id: int
    title: _(str)
    doi: _(str)
    abstract: _(str)
    upload_timestamp: _(datetime)
    user_id: _(int)
    authors: _(str)
    thematics: _(str)
    keywords: _(str)
    auto_nb_recommendations: _(int)
    suggested_recommender_id: _(int)
    status: str
    last_status_change: _(datetime)
    article_source: _(str)
    already_published: _(bool)
    picture_data: _(bytes)
    uploaded_picture: _(str)
    picture_rights_ok: _(bool)
    ms_version: _(str)
    anonymous_submission: _(bool)
    cover_letter: _(str)
    parallel_submission: _(bool)
    is_searching_reviewers: _(bool)
    art_stage_1_id: _(int)
    scheduled_submission_date: _(datetime)
    report_stage: _(str)
    sub_thematics: _(str)
    record_url_version: _(str)
    record_id_version: _(str)
    has_manager_in_authors: _(bool)
    results_based_on_data: _(str)
    data_doi: _(str)
    scripts_used_for_result: _(str)
    scripts_doi: _(str)
    codes_used_in_study: _(str)
    codes_doi: _(str)
    suggest_reviewers: _(str)
    competitors: _(str)
    doi_of_published_article: _(str)
    submitter_details: _(str)
    request_submission_change: _(bool)
    validation_timestamp: _(datetime)
    preprint_server: _(str)
    funding: _(str)
    article_year: _(int)


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return _cast(Article, db.t_articles[id])
