from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, List, Optional as _, Union, cast, TypedDict
from gluon.html import A, SPAN
from gluon.tools import Auth
from models.group import Role
from pydal.objects import Row
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon import current

from models.recommendation import Recommendation

from app_modules.lang import Lang

myconf = AppConfig(reload=True)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)


class ArticleStage(Enum):
    STAGE_1 = 'STAGE 1'
    STAGE_2 = 'STAGE 2'


class ArticleStatus(Enum):
    NOT_CONSIDERED = 'Not considered' # Not considered
    PRE_RECOMMENDED = 'Pre-recommended' # Recommendation pending validation
    AWAITING_REVISION = 'Awaiting revision' # Awaiting revision
    RECOMMENDED = 'Recommended' # Recommended
    UNDER_CONSIDERATION = 'Under consideration' # Handling process underway
    REJECTED = 'Rejected' # Rejected
    PRE_REJECTED = 'Pre-rejected' # Rejection pending validation
    CANCELLED = 'Cancelled' # Cancelled
    AWAITING_CONSIDERATION = 'Awaiting consideration' # Preprint requiring a recommender
    PENDING = 'Pending' # Submission pending validation
    PRE_SUBMISSION = 'Pre-submission' # Pre-submission pending validation
    PRE_RECOMMENDED_PRIVATE = 'Pre-recommended-private' # Pre-recommended-private
    PRE_REVISION = 'Pre-revision' # Request for revision pending validation
    SCHEDULED_SUBMISSION_PENDING = 'Scheduled submission pending' # Scheduled submission pending Validation
    SCHEDULED_SUBMISSION_UNDER_CONSIDERATION = 'Scheduled submission under consideration' # Scheduled submission under consideration
    SCHEDULED_SUBMISSION_REVISION = 'Scheduled submission revision' # Scheduled submission awaiting revision
    PENDING_SURVEY = 'Pending-survey' # Pending-survey
    RECOMMENDED_PRIVATE = 'Recommended-private' # Recommended-private


@dataclass
class TranslatedFieldDict(TypedDict):
    lang: str
    content: str
    automated: bool
    public: _[bool]


class TranslatedFieldType(Enum):
    ABSTRACT = 'translated_abstract'
    TITLE = 'translated_title'
    KEYWORDS = 'translated_keywords'

    @staticmethod
    def get_corresponding_english_field(translated_field: 'TranslatedFieldType'):
        return translated_field.name.lower()


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
    data_doi: _[List[str]]
    scripts_used_for_result: _[str]
    scripts_doi: _[List[str]]
    codes_used_in_study: _[str]
    codes_doi: _[List[str]]
    suggest_reviewers: _[List[str]]
    competitors: _[List[str]]
    doi_of_published_article: _[str]
    coar_notification_id: _[str]
    pre_submission_token: _[str]
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
    methods_require_specific_expertise: _[str]


    @staticmethod
    def get_by_id(id: int):
        db = current.db
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
                if new_translation['public'] != None: 
                    current_translation['public'] = new_translation['public']
            else:
                translations.append(new_translation)
        else:
            if new_translation['public'] == None:
                new_translation['public'] = False
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

        if index_to_remove != None:
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
    def get_all_translations(article: 'Article', field: TranslatedFieldType):
        return cast(_[List[TranslatedFieldDict]], getattr(article, field.value))
            

    @staticmethod
    def already_translated(article: 'Article', field: TranslatedFieldType, lang: Lang, manual: bool = False):
        translation = Article.get_translation(article, field, lang)
        if not translation:
            return False
        
        if manual:
            return not translation['automated']
        
        return True


    @staticmethod
    def get_last_recommendation(article_id: int):
        db = current.db
        return cast(_[Recommendation], db(db.t_recommendations.article_id == article_id).select(orderby=db.t_recommendations.id).last())


    @staticmethod
    def get_last_recommendations(article_id: int, order_by: _[Any]):
        db = current.db
        if order_by:
            recommendations = db(db.t_recommendations.article_id == article_id).select(orderby=order_by)
        else:
            recommendations = db(db.t_recommendations.article_id == article_id).select()
        return cast(List[Recommendation], recommendations)
    

    @staticmethod
    def current_user_has_edit_translation_right(article: 'Article'):
        auth = cast(Auth, current.auth)
        is_author = bool(article.user_id == auth.user_id) \
                                and article.status not in (ArticleStatus.PENDING.value,
                                                        ArticleStatus.PRE_SUBMISSION.value,
                                                        ArticleStatus.REJECTED.value,
                                                        ArticleStatus.RECOMMENDED.value,
                                                        ArticleStatus.NOT_CONSIDERED.value,
                                                        ArticleStatus.CANCELLED.value)
        is_admin = bool(auth.has_membership(role=Role.ADMINISTRATOR.value)) # type: ignore
        return is_author or is_admin
    

    @staticmethod
    def get_by_status(article_status: List[ArticleStatus], order_by: _[Any] = None) -> List['Article']:
        db = current.db
        states_values: List[str] = []
        for status in article_status:
            states_values.append(status.value)

        if order_by:
            return db(db.t_articles.status.belongs(states_values)).select(orderby=order_by)
        else:
            return db(db.t_articles.status.belongs(states_values)).select()
        
    
    @staticmethod
    def create_prefilled_submission(user_id: int,
                                    doi: _[str] = None,
                                    authors: _[str] = None,
                                    coar_notification_id: _[str] = None,
                                    title: _[str] = None,
                                    abstract: _[str] = None,
                                    ms_version: _[str] = None,
                                    article_year: _[int] = None,
                                    preprint_server: _[str] = None,
                                    pre_submission_token: _[str] = None,
                                    **kwargs: Any):
        db = current.db
 
        article_id = db.t_articles.insert(
            user_id=user_id,
            doi=doi,
            authors=authors,
            status=ArticleStatus.PRE_SUBMISSION.value,
            coar_notification_id=coar_notification_id,
            title=title,
            abstract=abstract,
            ms_version=ms_version,
            article_year=article_year,
            preprint_server=preprint_server,
            pre_submission_token=pre_submission_token,
            **kwargs)

        return Article.get_by_id(article_id)
    

    @staticmethod
    def set_status(article: 'Article', status: ArticleStatus):
        article.status = status.value
        article.update_record()


    @staticmethod
    def remove_pre_submission_token(article: 'Article'):
        article.pre_submission_token = None
        article.update_record()

    
    @staticmethod
    def get_article_reference(article: 'Article', with_prefix: bool = True, html: bool = False):
        from app_modules.common_small_html import md_to_html

        title: Union[SPAN, str] = md_to_html(article.title)
        article_doi: _[Union[A, str]] = article.doi
        pci_long_name = str(current.db.conf.get('app.longname') or "")

        if html:
            article_doi = A(article_doi, _href=article_doi)
        else:
            title = title.flatten() # type: ignore

        return " ".join([
            "A recommendation of:" if with_prefix else "",
            f"{article.authors}",
            f"({article.article_year})",
            f"{title}.",
            f"{article.preprint_server},",
            f"ver.{article.ms_version}",
            f"peer-reviewed and recommended by {pci_long_name}",
            f"{article_doi}",
        ]) if not article.article_source \
        else " ".join([
            "A recommendation of:" if with_prefix else "",
            f"{article.authors}",
            f"{title}.",
            f"{article.article_source}",
            f"peer-reviewed and recommended by {pci_long_name}",
            f"{article_doi}",
        ])


def is_scheduled_submission(article: Article) -> bool:
    return scheduledSubmissionActivated and (
        article.scheduled_submission_date is not None
        or article.status.startswith("Scheduled submission")
        or (
            article.t_report_survey.select().first().q10 is not None
            and article.t_recommendations.count() == 1
        )
    )


def clean_vars_doi_list(var_doi: _[List[str]]):
    new_var_doi: List[str] = []
    if var_doi is None:
        return

    for el in var_doi:
        value = clean_vars_doi(el)
        if not value:
            continue
        new_var_doi.append(el)
    return new_var_doi


def clean_vars_doi(var_doi: _[str]):
    if var_doi is None:
        return

    value = var_doi.lower().strip()
    if re.match(r'^https?:?\/?\/?$', value):
        return ''
    else:
        return var_doi
