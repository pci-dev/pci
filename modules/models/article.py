from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional as _, cast, TypedDict
from pydal.objects import Row
from pydal import DAL
from gluon.contrib.appconfig import AppConfig
from gluon import current

from models.recommendation import Recommendation

from app_modules.lang import Lang

myconf = AppConfig(reload=True)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

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

@dataclass
class TranslatedFieldDict(TypedDict):
    lang: str
    content: str
    automated: bool


class TranslatedFieldType(Enum):
    ABSTRACT = 'translated_abstract'
    TITLE = 'translated_title'
    KEYWORDS = 'translated_keywords'


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
    coar_notification_id: _[str]
    request_submission_change: _[bool]
    validation_timestamp: _[datetime]
    preprint_server: _[str]
    funding: _[str]
    article_year: _[int]
    is_scheduled: bool
    manager_authors: _[str]
    translated_abstract: _[List[TranslatedFieldDict]]
    translated_title: _[List[TranslatedFieldDict]]
    translated_keywords: _[List[TranslatedFieldDict]]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(_[Article], db.t_articles[id])
    

    @staticmethod
    def add_or_update_translation(article: 'Article', field: TranslatedFieldType, new_translation: TranslatedFieldDict):
        lang = Lang.get_lang_by_code(new_translation['lang'])
        translations = getattr(article, field.value)

        if translations:
            current_translation = Article.get_translation(article,  field, lang)
            if current_translation:
                if current_translation['automated'] or not new_translation['automated']:
                    current_translation['content'] = new_translation['content']
                    current_translation['automated'] = new_translation['automated']
            else:
                translations.append(new_translation)
        else:
            setattr(article, field.value, [new_translation])

        article.update_record()


    @staticmethod
    def delete_translation(article: 'Article', field: TranslatedFieldType, lang: Lang):
        translations: _[List[TranslatedFieldDict]] = getattr(article, field.value)
        if not translations:
            return
        
        index_to_remove: _[int] = None
        for i in range(0, len(translations)):
            translation = translations[i]
            if translation['lang'] == lang.value.code:
                index_to_remove = i
                break

        if index_to_remove:
            translations.pop(index_to_remove)
            article.update_record()
        

    @staticmethod
    def get_translation(article: 'Article', field: TranslatedFieldType, lang: Lang):
        translations: _[List[TranslatedFieldDict]] = getattr(article, field.value)
        if not translations:
            return None
        
        for translation in translations:
            if translation['lang'] == lang.value.code:
                return translation
            

    @staticmethod
    def already_translated(article: 'Article', field: TranslatedFieldType, lang: Lang):
        return Article.get_translation(article, field, lang) != None


    @staticmethod
    def get_last_recommendation(article_id: int):
        db = current.db
        return cast(_[Recommendation], db(db.t_recommendations.article_id == article_id).select().last())


    @staticmethod
    def get_last_recommendations(article_id: int, order_by: _[Any]):
        db = current.db
        if order_by:
            recommendations = db(db.t_recommendations.article_id == article_id).select(orderby=order_by)
        else:
            recommendations = db(db.t_recommendations.article_id == article_id).select()
        return cast(List[Recommendation], recommendations)


def is_scheduled_submission(article: Article) -> bool:
    return scheduledSubmissionActivated and (
        article.scheduled_submission_date is not None
        or article.status.startswith("Scheduled submission")
        or (
            article.t_report_survey.select().first().q10 is not None
            and article.t_recommendations.count() == 1
        )
    )
