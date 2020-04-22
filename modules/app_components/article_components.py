# -*- coding: utf-8 -*-

import gc
import os
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
from app_modules import common_html
from app_modules import common_tools


myconf = AppConfig(reload=True)


######################################################################################################################################################################
def getRecommArticleRowCard(auth, db, response, article, withImg=True, withScore=False, withDate=False, fullURL=False):
    if fullURL:
        scheme = myconf.take("alerts.scheme")
        host = myconf.take("alerts.host")
        port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    else:
        scheme = False
        host = False
        port = False

    # Get Recommendation
    recomm = db((db.t_recommendations.article_id == article.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()
    if recomm is None:
        return None

    recommAuthors = common_small_html.getRecommAndReviewAuthors(auth, db, article=article, with_reviewers=True, linked=True, host=host, port=port, scheme=scheme)

    if withDate:
        date = common_small_html.mkLastChange(article.last_status_change)

    articleImg = ""
    if withImg:
        if article.uploaded_picture is not None and article.uploaded_picture != "":
            articleImg = IMG(
                _src=URL("default", "download", scheme=scheme, host=host, port=port, args=article.uploaded_picture), _alt="article picture", _class="pci-articlePicture",
            )

    recommShortText = common_tools.getShortText(recomm.recommendation_comments, 500) or ""

    authors = common_tools.getShortText(article.authors, 500) or ""

    # (gab) Where do i need to place this ?
    # if withScore:
    # 		resu.append(TD(row.score or '', _class='pci-lastArticles-date'))

    componentVars = dict(
        articleDate=date,
        articleUrl=URL(c="articles", f="rec", vars=dict(id=article.id, reviews=True), scheme=scheme, host=host, port=port),
        articleTitle=article.title,
        articleImg=articleImg,
        isAlreadyPublished=article.already_published,
        articleAuthor=authors,
        articleDoi=common_small_html.mkDOI(article.doi),
        recommendationAuthors=SPAN(recommAuthors),
        recommendationTitle=recomm.recommendation_title,
        recommendationShortText=WIKI(recommShortText),
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
        & (db.t_reviews.review_state.belongs("Under consideration", "Completed"))
    ).count(distinct=db.t_reviews.id)
    if nbReviews > 0:
        track = DIV(_class="pci-trackItem")
        link = common_small_html.mkDOI(article.doi)
        firstDate = article.upload_timestamp.strftime("%Y-%m-%d")
        lastDate = article.last_status_change.strftime("%Y-%m-%d")
        title = article.title
        if article.anonymous_submission:
            authors = "[anonymous submission]"
        else:
            authors = article.authors

        # pci-status
        if article.status == "Recommended":
            txt = DIV(SPAN(current.T(" was")), SPAN(current.T("UNDER REVIEW"), _class="pci-trackStatus default"), SPAN(SPAN("(", firstDate, " ➜ ", lastDate, ")"), ". "),)

        elif article.status == "Cancelled":
            txt = DIV(SPAN(current.T(" was")), SPAN(current.T("UNDER REVIEW"), _class="pci-trackStatus default"), SPAN("(", firstDate, " ➜ ", lastDate, "). "),)

        elif article.status == "Under consideration" or article.status == "Pre-recommended" or article.status == "Pre-rejected" or article.status == "Pre-revision":
            txt = DIV(SPAN(current.T(" is")), SPAN(current.T("UNDER REVIEW"), _class="pci-trackStatus info"), SPAN("(", current.T("Submitted on"), " ", firstDate, ")"),)

        elif article.status == "Awaiting revision":
            txt = DIV(SPAN(current.T(" was")), SPAN(current.T("UNDER REVIEW"), _class="pci-trackStatus default"), SPAN("(", current.T("Submitted on"), " ", firstDate, ")"),)

        else:
            return None

        componentVars = dict(
            articleId=article.id,
            articleImg=IMG(_src=URL(c="static", f="images/small-background.png", scheme=scheme, host=host, port=port), _class="pci-trackImg",),
            articleTitle=title,
            articleAuthor=authors,
            articleDoi=link,
            articleStatus=article.status,
            articleStatusText=txt,
        )

        return XML(response.render("components/article_track_row_card.html", componentVars))

    # no article reviews founded
    else:
        return None


######################################################################################################################################################################
def getArticleInfosCard(auth, db, response, art, printable, with_cover_letter=True, submittedBy=True):
    ## NOTE: article facts
    if art.uploaded_picture is not None and art.uploaded_picture != "":
        article_img = IMG(_alt="picture", _src=URL("default", "download", args=art.uploaded_picture))
    else:
        article_img = ""

    if printable:
        printableClass = "printable"
    else:
        printableClass = ""

    doi = sub(r"doi: *", "", (art.doi or ""))
    article_altmetric = XML("<div class='text-right altmetric-embed' data-badge-type='donut' data-badge-popover='left' data-hide-no-mentions='true' data-doi='%s'></div>" % doi)

    articleContent = dict()
    articleContent.update(
        [
            ("articleVersion", SPAN(" " + current.T("version") + " " + art.ms_version) if art.ms_version else ""),
            ("articleImg", article_img),
            ("articleTitle", art.title or ""),
            ("articleAuthor", art.authors or ""),
            ("articleAbstract", WIKI(art.abstract or "")),
            ("articleDoi", (common_small_html.mkDOI(art.doi)) if (art.doi) else SPAN("")),
            ("article_altmetric", article_altmetric),
            ("printable", printable),
            ("printableClass", printableClass),
        ]
    )

    if with_cover_letter and not art.already_published:
        articleContent.update([("coverLetter", WIKI(art.cover_letter or ""))])

    if submittedBy:
        articleContent.update([("submittedBy", common_small_html.getArticleSubmitter(auth, db, art))])

    return XML(response.render("components/article_infos_card.html", articleContent))