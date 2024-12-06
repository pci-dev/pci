# -*- coding: utf-8 -*-

import gc
import os
from typing import Any, Dict, Optional, cast
from gluon.globals import Response
from models.group import Role
from models.recommendation import Recommendation
from models.review import ReviewState
import pytz, datetime
from re import sub, match
from copy import deepcopy
import datetime
from datetime import timedelta
from dateutil.relativedelta import *
from collections import OrderedDict

import io
from PIL import Image

from gluon import current, IS_IN_DB
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail
from gluon.sqlhtml import *


from app_modules import common_small_html
from app_modules import common_tools
from app_modules.common_small_html import md_to_html
from app_modules.lang import Lang
from models.article import Article, ArticleStage, ArticleStatus


myconf = AppConfig(reload=True)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

######################################################################################################################################################################
def getRecommArticleRowCard(article: Article,
                            recomm: Recommendation,
                            withImg: bool = True,
                            withScore: bool = False,
                            withDate: bool = False,
                            fullURL: bool = False,
                            withLastRecommOnly: bool = False,
                            orcid_exponant: bool = False):

    isStage2 = article.art_stage_1_id is not None
    stage1Url = None
    if isStage2:
        stage1Url = URL(c="articles", f="rec", vars=dict(id=article.art_stage_1_id))

    if recomm is None:
        return None

    recommAuthors = common_small_html.getRecommAndReviewAuthors(
                        article=article,
                        with_reviewers=True, linked=True,
                        fullURL=fullURL,
                        recomm=recomm, this_recomm_only=True,
                        orcid_exponant=orcid_exponant
                        )

    if withDate:
        date = common_small_html.mkLastChange(article.last_status_change)

    articleImg = ""
    if withImg:
        if article.uploaded_picture is not None and article.uploaded_picture != "":
            articleImg = IMG(
                _src=URL(
                    "static", "uploads",
                    scheme=fullURL,
                    args=article.uploaded_picture,
                ),
                _alt="article picture",
                _class="pci-articlePicture",
            )

    recommShortText = DIV(WIKI(recomm.recommendation_comments or "", safe_mode=''), _class="fade-transparent-text")

    authors = common_tools.getShortText(article.authors, 500)

    # Scheduled submission
    doi_text = common_small_html.mkDOI(article.doi)
    if scheduledSubmissionActivated and article.scheduled_submission_date is not None:
      if article.status != "Recommended":
        doi_text = DIV(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(article.scheduled_submission_date))), BR())

    componentVars = dict(
        articleDate=date,
        articleUrl=URL(c="articles", f="rec", vars=dict(id=article.id), scheme=fullURL),
        articleTitle=md_to_html(article.title),
        articleImg=articleImg,
        isAlreadyPublished=article.already_published,
        articleAuthor=authors,
        articleDoi=doi_text,
        recommendationAuthors=SPAN(recommAuthors),
        recommendationTitle=md_to_html(recomm.recommendation_title),
        recommendationShortText=WIKI(recommShortText, safe_mode=False),
        pciRRactivated=pciRRactivated,
        isStage2=isStage2,
        stage1Url=stage1Url,
    )

    return XML(current.response.render("components/article_row_card.html", componentVars))


######################################################################################################################################################################
def getArticleTrackcRowCard(article):
    db = current.db

    nbReviews = db(
        (db.t_recommendations.article_id == article.id)
        & (db.t_reviews.recommendation_id == db.t_recommendations.id)
        & (db.t_reviews.review_state.belongs("Awaiting review", "Review completed"))
    ).count(distinct=db.t_reviews.id)
    if nbReviews > 0:
        track = DIV(_class="pci-trackItem")
        
        firstDate = article.upload_timestamp.strftime(DEFAULT_DATE_FORMAT)
        lastDate = article.last_status_change.strftime(DEFAULT_DATE_FORMAT)
        title = md_to_html(article.title)
        if article.anonymous_submission:
            authors = "[anonymous submission]"
        else:
            authors = article.authors
        # pci-status
        if article.status == "Recommended":
            txt = DIV(SPAN(current.T(" was")), SPAN(current.T("UNDER REVIEW"), _class="pci-trackStatus default"), SPAN(SPAN("(", firstDate, " ➜ ", lastDate, ")"), ". "),)

        elif article.status == "Cancelled":
            txt = DIV(SPAN(current.T(" was")), SPAN(current.T("UNDER REVIEW"), _class="pci-trackStatus default"), SPAN("(", firstDate, " ➜ ", lastDate, "). "),)

        elif (
            article.status == "Under consideration"
            or article.status == "Pre-recommended"
            or article.status == "Pre-recommended-private"
            or article.status == "Pre-rejected"
            or article.status == "Pre-revision"
        ):
            txt = DIV(SPAN(current.T(" is")), SPAN(current.T("UNDER REVIEW"), _class="pci-trackStatus info"), SPAN("(", current.T("Submitted on"), " ", firstDate, ")"),)

        elif article.status == "Awaiting revision":
            txt = DIV(SPAN(current.T(" was")), SPAN(current.T("UNDER REVIEW"), _class="pci-trackStatus default"), SPAN("(", current.T("Submitted on"), " ", firstDate, ")"),)

        else:
            return None

        # Scheduled submission
        doi_text = common_small_html.mkDOI(article.doi)
        if scheduledSubmissionActivated and  article.scheduled_submission_date is not None:
            doi_text = DIV(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(article.scheduled_submission_date))), BR())

        componentVars = dict(
            articleId=article.id,
            articleImg=IMG(_src=URL(c="static", f="images/small-background.png", scheme=True), _class="pci-trackImg",),
            articleTitle=title,
            articleAuthor=authors,
            articleDoi=doi_text,
            articleStatus=article.status,
            articleStatusText=txt,
        )

        return XML(current.response.render("components/article_track_row_card.html", componentVars))

    # no article reviews founded
    else:
        return None


class article_infocard_for_search_screens:
  def __init__(_):
    _.printable = False
    _.keywords = True
    _.abstract = False
    _.with_cover_letter = False

for_search = article_infocard_for_search_screens().__dict__

######################################################################################################################################################################
def get_article_infos_card(article: Article, printable: bool,
        with_cover_letter: bool = True,
        with_version: bool = True,
        submitted_by: bool = True,
        abstract: bool = True,
        keywords: bool = False,
        for_manager: bool = False
    ):

    auth, db = current.auth, current.db

    article_img = ""
    if article.uploaded_picture is not None and article.uploaded_picture != "":
        article_img = IMG(_alt="picture", _src=URL("static", "uploads", args=article.uploaded_picture))
        
    printable_class = ""
    if printable:
        printable_class = "printable"

    article_stage = None
    if pciRRactivated:
        if article.art_stage_1_id is not None or article.report_stage == ArticleStage.STAGE_2.value:
            article_stage = B(current.T(ArticleStage.STAGE_2.value))
        else:
            article_stage = B(current.T(ArticleStage.STAGE_1.value))

    # Scheduled submission
    doi_text = (common_small_html.mkDOI(article.doi)) if (article.doi) else SPAN("")
    if scheduledSubmissionActivated and  article.scheduled_submission_date is not None:
      if article.status != ArticleStatus.RECOMMENDED.value:
        doi_text = DIV(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(article.scheduled_submission_date))), BR())

    if article.already_published:
        doi_button_text = "Read article in journal"
    else:
        doi_button_text = current.T("Read preprint in preprint server")
    doi_button = A(SPAN(doi_button_text, _class="btn btn-success"), _href=article.doi, _target="blank")

    doi = sub(r"doi: *", "", (article.doi or ""))
    article_altmetric = XML("<div class='text-right altmetric-embed' data-badge-type='donut' data-badge-popover='left' data-hide-no-mentions='true' data-doi='%s'></div>" % doi)
    

    # info visibility policies
    recommendation = Article.get_last_recommendation(article.id)
    is_recommender = bool(recommendation and recommendation.recommender_id == auth.user_id)
    is_reviewer = bool(db(
            (db.t_reviews.reviewer_id == auth.user_id) &
            (db.t_recommendations.article_id == article.id) &
            (db.t_reviews.recommendation_id == db.t_recommendations.id) &
            (db.t_reviews.review_state.belongs(ReviewState.AWAITING_REVIEW.value, ReviewState.REVIEW_COMPLETED.value))
    ).count() > 0)
    is_recommended_article = article.status == ArticleStatus.RECOMMENDED.value

    if article.anonymous_submission and not is_recommended_article and not is_recommender:
        authors = "[anonymous submission]"
    else:
        authors = article.authors

    policy_1 = bool(auth.has_membership(role=Role.MANAGER.value) or auth.has_membership(role=Role.ADMINISTRATOR.value) or (is_recommender and not is_recommended_article))
    policy_2 = bool(policy_1 or is_reviewer or is_recommended_article)

    article_content: Dict[str, Any] = dict()
    article_content.update(
        [
            ("articleVersion", SPAN(" " + current.T("version") + " " + article.ms_version) if with_version and article.ms_version else ""),
            ("articleSource", I(make_article_source(article) if is_recommended_article else "")),
            ("articleId", article.id),
            ("articleImg", article_img),
            ("articleTitle", md_to_html(article.title) or ""),
            ("articleAuthor", authors or ""),
            ("articleDoi", doi_text),
            ("doiButton", doi_button),
            ("article_altmetric", article_altmetric),
            ("printable", printable),
            ("printableClass", printable_class),
            ("pciRRactivated", pciRRactivated),
            ("articleStage", article_stage),
            ("isRecommended", is_recommended_article),
            ("translations", _get_article_translation(article)),
            ("Lang", Lang),
            ("for_manager", for_manager),
        ]
    )
    if article.data_doi and policy_2:
        article_data_doi = common_small_html.fetch_url(article.data_doi)
        if len(article_data_doi) > 0:
            article_content.update([("dataDoi", UL(article_data_doi) if (article_data_doi) else SPAN(""))])

    if article.scripts_doi and policy_2:
        article_script_doi = common_small_html.fetch_url(article.scripts_doi)
        if len(article_script_doi) > 0:
            article_content.update([("scriptDoi", UL(article_script_doi) if (article_script_doi) else SPAN(""))])

    if article.codes_doi and policy_2:
        article_code_doi = common_small_html.fetch_url(article.codes_doi)
        if len(article_code_doi) > 0:
            article_content.update([("codeDoi", UL(article_code_doi) if (article_code_doi) else SPAN(""))])

    if article.suggest_reviewers and policy_1:
        suggested_by_author = common_tools.separate_suggestions(article.suggest_reviewers)[0]
        if len(suggested_by_author) > 0:
            article_content.update([("suggestReviewers", UL(suggested_by_author or "", safe_mode=False))]) if not is_recommended_article else None

    if article.competitors and policy_1:
        article_content.update([("competitors", UL(article.competitors or "", safe_mode=False))]) if not is_recommended_article else None

    if abstract:
        article_content.update([("articleAbstract", WIKI(article.abstract or "", safe_mode=''))])

    if with_cover_letter and article.cover_letter is not None and not article.already_published and (
            policy_1 or (
                auth.has_membership(role=Role.RECOMMENDER.value)
                and not (recommendation and recommendation.recommender_id)
            )
        ):
        article_content.update([("coverLetter", WIKI(article.cover_letter or "", safe_mode=''))])

    if submitted_by:
        article_content.update([("submittedBy", common_small_html.getArticleSubmitter(article))])
    
    if keywords:
        article_content.update([("articleKeywords", article.keywords)])

    if article.methods_require_specific_expertise and policy_1:
        article_content.update([("articleMethodsRequireSpecificExpertise", article.methods_require_specific_expertise)])

    if article.doi_of_published_article:
        button_text = "Now published in a journal"
        if "10.24072/pcjournal" in article.doi_of_published_article:
            button_text = "Now published in Peer Community Journal"
            
        article_content.update([("publishedDoi",  A(
                SPAN(current.T(button_text), _class="btn btn-success"),
                _href=article.doi_of_published_article, _target="blank"))])
    return XML(current.response.render("components/article_infos_card.html", article_content))


def _get_article_translation(article: Article):
    translations: Dict[str, Dict[str, str]] = {}

    if article.translated_title:
        for translated_title in article.translated_title:
            if not translated_title['public']:
                continue
            translations[translated_title['lang']] = dict(title=str(H3(translated_title['content'])))

    if article.translated_abstract:
        for translated_abstract in article.translated_abstract:
            if not translated_abstract['public']:
                continue
            lang = translated_abstract['lang']
            translations.setdefault(lang, {})['abstract'] = translated_abstract['content']
            if translated_abstract['automated']:
                translations[lang]['automated'] = str(I('This is an automatically generated version. The authors and PCI decline all responsibility concerning its content'))
            else:
                translations[lang]['automated'] = str(I('This is an author-verified version. The authors endorse the responsibility for its content.'))
            
    if article.translated_keywords:
        for translated_keywords in article.translated_keywords:
            if not translated_keywords['public']:
                continue
            lang = translated_keywords['lang']
            translations.setdefault(lang, {})['keywords'] = str(I(translated_keywords['content']))

    if len(translations) > 0:
        en = {Lang.EN.value.code: dict(
            title=str(H3(article.title or "")),
            abstract=article.abstract or "",
            keywords=str(I(article.keywords or "")))}
        langs = list(translations.keys())
        langs.sort()
        translations = {lang: translations[lang] for lang in langs}
        return {**en, **translations}
    else:
        return translations


def make_article_source(article):
    if pciRRactivated:
        return ""

    if article.article_source:
        return article.article_source

    year = article.article_year
    preprint_server = article.preprint_server
    pci_name  = myconf.take("app.longname")
    version = article.ms_version
    article_source = f"({year}), {preprint_server}, ver.{version}, peer-reviewed and recommended by {pci_name}"
    return article_source


def fix_web2py_list_str_bug_article_form(form: SQLFORM):
    comment_style = "display: block; margin-top: 5px; margin-bottom: 10px; color: #7f8177; list-style: none;"

    suggest_reviewers_input = cast(Optional[DIV], form.element(_id="t_articles_suggest_reviewers_grow_input")) # type: ignore
    if suggest_reviewers_input:
        suggest_reviewers_input.append(SPAN(form.custom.comment.suggest_reviewers.components, _style=comment_style)) # type: ignore

    opposed_reviewers_input = cast(Optional[DIV], form.element(_id="t_articles_competitors_grow_input")) # type: ignore
    if opposed_reviewers_input:
        opposed_reviewers_input.append(SPAN(form.custom.comment.competitors.components, _style=comment_style)) # type: ignore

    data_doi_input = cast(Optional[DIV], form.element(_id="t_articles_data_doi_grow_input")) # type: ignore
    if data_doi_input:
        data_doi_input['_style'] = comment_style
        data_doi_input.append(form.custom.comment.data_doi) # type: ignore

    script_doi_input = cast(Optional[DIV], form.element(_id="t_articles_scripts_doi_grow_input")) # type: ignore
    if script_doi_input:
        script_doi_input.append(SPAN(form.custom.comment.scripts_doi, _style=comment_style)) # type: ignore

    codes_doi_input = cast(Optional[DIV], form.element(_id="t_articles_codes_doi_grow_input")) # type: ignore
    if codes_doi_input:
        codes_doi_input['style'] = comment_style
        codes_doi_input.append(SPAN(form.custom.comment.codes_doi, _style=comment_style)) # type: ignore
