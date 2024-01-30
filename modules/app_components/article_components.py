# -*- coding: utf-8 -*-

import gc
import os
from typing import Dict, Union
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
from models.article import Article


myconf = AppConfig(reload=True)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

######################################################################################################################################################################
def getRecommArticleRowCard(auth, db, response, article, recomm, withImg=True, withScore=False, withDate=False, fullURL=False, withLastRecommOnly=False, orcid_exponant: bool = False):
    if fullURL:
        scheme = myconf.take("alerts.scheme")
        host = myconf.take("alerts.host")
        port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    else:
        scheme = False
        host = False
        port = False

    isStage2 = article.art_stage_1_id is not None
    stage1Url = None
    if isStage2:
        stage1Url = URL(c="articles", f="rec", vars=dict(id=article.art_stage_1_id))

    if recomm is None:
        return None

    recommAuthors = common_small_html.getRecommAndReviewAuthors(
                        auth, db, article=article,
                        with_reviewers=True, linked=True,
                        host=host, port=port, scheme=scheme,
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
                    scheme=scheme, host=host, port=port,
                    args=article.uploaded_picture,
                ),
                _alt="article picture",
                _class="pci-articlePicture",
            )

    recommShortText = DIV(WIKI(recomm.recommendation_comments or "", safe_mode=False), _class="fade-transparent-text")

    authors = common_tools.getShortText(article.authors, 500)

    # Scheduled submission
    doi_text = common_small_html.mkDOI(article.doi)
    if scheduledSubmissionActivated and article.scheduled_submission_date is not None:
      if article.status != "Recommended":
        doi_text = DIV(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(article.scheduled_submission_date))), BR())

    componentVars = dict(
        articleDate=date,
        articleUrl=URL(c="articles", f="rec", vars=dict(id=article.id), scheme=scheme, host=host, port=port),
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

    return XML(response.render("components/article_row_card.html", componentVars))


######################################################################################################################################################################
def getArticleTrackcRowCard(auth, db, response, article):
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    applongname = myconf.take("app.longname")

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
            articleImg=IMG(_src=URL(c="static", f="images/small-background.png", scheme=scheme, host=host, port=port), _class="pci-trackImg",),
            articleTitle=title,
            articleAuthor=authors,
            articleDoi=doi_text,
            articleStatus=article.status,
            articleStatusText=txt,
        )

        return XML(response.render("components/article_track_row_card.html", componentVars))

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
def getArticleInfosCard(auth, db, response, article: Article, printable,
        with_cover_letter=True,
        submittedBy=True,
        abstract=True,
        keywords=False,
    ):
    ## NOTE: article facts
    if article.uploaded_picture is not None and article.uploaded_picture != "":
        article_img = IMG(_alt="picture", _src=URL("static", "uploads", args=article.uploaded_picture))
    else:
        article_img = ""

    if printable:
        printableClass = "printable"
    else:
        printableClass = ""

    articleStage = None
    if pciRRactivated:
        if article.art_stage_1_id is not None or article.report_stage == "STAGE 2":
            articleStage = B(current.T("STAGE 2"))
        else:
            articleStage = B(current.T("STAGE 1"))

    # Scheduled submission
    doi_text = (common_small_html.mkDOI(article.doi)) if (article.doi) else SPAN("")
    if scheduledSubmissionActivated and  article.scheduled_submission_date is not None:
      if article.status != "Recommended":
        doi_text = DIV(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(article.scheduled_submission_date))), BR())

    doi_button = A(SPAN(current.T("Read preprint in preprint server"), _class="btn btn-success"), _href=article.doi, _target="blank")

    doi = sub(r"doi: *", "", (article.doi or ""))
    article_altmetric = XML("<div class='text-right altmetric-embed' data-badge-type='donut' data-badge-popover='left' data-hide-no-mentions='true' data-doi='%s'></div>" % doi)
    

    # info visibility policies
    recomm = db(db.t_recommendations.article_id == article.id).select().last()
    isRecommender = recomm and recomm.recommender_id == auth.user_id
    isReviewer = db(
            (db.t_reviews.reviewer_id == auth.user_id) &
            (db.t_recommendations.article_id == article.id) &
            (db.t_reviews.recommendation_id == db.t_recommendations.id) &
            (db.t_reviews.review_state.belongs("Awaiting review", "Review completed"))
    ).count() > 0
    isRecommended = article.status == "Recommended"

    if article.anonymous_submission and article.status != "Recommended" and not isRecommender:
        authors = "[anonymous submission]"
    else:
        authors = article.authors

    def policy_1():
        return (
            auth.has_membership(role="manager") or
            auth.has_membership(role="administrator")
            or
            isRecommender
        )

    def policy_2():
        return (
            policy_1()
            or
            isReviewer
            or
            isRecommended
        )
    
    translations: Dict[str, Dict[str, Union[XML, DIV]]] = {}
    if article.translated_title:
        for translated_title in article.translated_title:
            if not translated_title['public']:
                continue
            translations[translated_title['lang']] = dict(title=H3(translated_title['content']))

    if article.translated_abstract:
        for translated_abstract in article.translated_abstract:
            if not translated_abstract['public']:
                continue
            lang = translated_abstract['lang']
            translations.setdefault(lang, {})['abstract'] = XML(translated_abstract['content'])
            if translated_abstract['automated']:
                translations[lang]['automated'] = I('This is a version automatically generated. The authors and PCI decline all responsibility concerning its content')
            else:
                translations[lang]['automated'] = I('This is an author version: The autors endorse the responsability of its content.')
            
    if article.translated_keywords:
        for translated_keywords in article.translated_keywords:
            if not translated_keywords['public']:
                continue
            lang = translated_keywords['lang']
            translations.setdefault(lang, {})['keywords'] = I(translated_keywords['content'])

    articleContent = dict()
    articleContent.update(
        [
            ("articleVersion", SPAN(" " + current.T("version") + " " + article.ms_version) if article.ms_version else ""),
            ("articleSource", I(make_article_source(article) if isRecommended else "")),
            ("articleId", article.id),
            ("articleImg", article_img),
            ("articleTitle", md_to_html(article.title) or ""),
            ("articleAuthor", authors or ""),
            ("articleDoi", doi_text),
            ("doiButton", doi_button),
            ("article_altmetric", article_altmetric),
            ("printable", printable),
            ("printableClass", printableClass),
            ("pciRRactivated", pciRRactivated),
            ("articleStage", articleStage),
            ("isRecommended", isRecommended),
            ("translations", translations),
            ("Lang", Lang)
        ]
    )
    if article.data_doi and policy_2():
        article_data_doi = common_small_html.fetch_url(article.data_doi)
        articleContent.update([("dataDoi", UL(article_data_doi) if (article_data_doi) else SPAN(""))])

    if article.scripts_doi and policy_2():
        article_script_doi = common_small_html.fetch_url(article.scripts_doi)
        articleContent.update([("scriptDoi", UL(article_script_doi) if (article_script_doi) else SPAN(""))])

    if article.codes_doi and policy_2():
        article_code_doi = common_small_html.fetch_url(article.codes_doi)
        articleContent.update([("codeDoi", UL(article_code_doi) if (article_code_doi) else SPAN(""))])

    if article.suggest_reviewers and policy_1():
        suggested_by_author = common_tools.separate_suggestions(article.suggest_reviewers)[0]
        if len(suggested_by_author) > 0:
            articleContent.update([("suggestReviewers", UL(suggested_by_author or "", safe_mode=False))]) if not isRecommended else None

    if article.competitors and policy_1():
        articleContent.update([("competitors", UL(article.competitors or "", safe_mode=False))]) if not isRecommended else None

    if abstract:
        articleContent.update([("articleAbstract", WIKI(article.abstract or "", safe_mode=False))])

    if with_cover_letter and article.cover_letter is not None and not article.already_published and policy_1():
        articleContent.update([("coverLetter", WIKI(article.cover_letter or "", safe_mode=False))])

    if submittedBy:
        articleContent.update([("submittedBy", common_small_html.getArticleSubmitter(auth, db, article))])
    
    if keywords:
        articleContent.update([("articleKeywords", article.keywords)])

    if article.doi_of_published_article:
        button_text = "Now published in a journal"
        if "10.24072/pcjournal" in article.doi_of_published_article:
            button_text = "Now published in Peer Community Journal"
            
        articleContent.update([("publishedDoi",  A(
                SPAN(current.T(button_text), _class="btn btn-success"),
                _href=article.doi_of_published_article, _target="blank"))])
    return XML(response.render("components/article_infos_card.html", articleContent))

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
