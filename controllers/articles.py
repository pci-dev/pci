# -*- coding: utf-8 -*-

import re
import copy

from gluon.storage import Storage
from gluon.contrib.markdown import WIKI

from datetime import datetime, timedelta, date
from dateutil import parser
from gluon.contrib.appconfig import AppConfig
from lxml import etree

from app_modules.helper import *

from app_components import app_forms

from app_components import article_components
from app_components import public_recommendation

from app_modules import old_common
from app_modules import common_tools


myconf = AppConfig(reload=True)

# frequently used constants
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get("config.trgm_limit") or 0.4

pciRRactivated = myconf.get("config.registered_reports", default=False)

######################################################################################################################################################################
def index():
    redirect(URL('default','index'))

######################################################################################################################################################################
@cache.action(time_expire=30, cache_model=cache.ram, quick="V")
def last_recomms():
    if "maxArticles" in request.vars:
        maxArticles = int(request.vars["maxArticles"])
    else:
        maxArticles = 10
    myVars = copy.deepcopy(request.vars)
    myVars["maxArticles"] = myVars["maxArticles"] or 10
    myVarsNext = copy.deepcopy(myVars)
    myVarsNext["maxArticles"] = int(myVarsNext["maxArticles"]) + 10

    queryRecommendedArticles = None

    if queryRecommendedArticles is None:
        queryRecommendedArticles = db(
            (db.t_articles.status == "Recommended") & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommendation_state == "Recommended")
        ).iterselect(
            db.t_articles.art_stage_1_id,
            db.t_articles.id,
            db.t_articles.title,
            db.t_articles.authors,
            db.t_articles.article_source,
            db.t_articles.doi,
            db.t_articles.picture_rights_ok,
            db.t_articles.uploaded_picture,
            db.t_articles.abstract,
            db.t_articles.upload_timestamp,
            db.t_articles.user_id,
            db.t_articles.status,
            db.t_articles.last_status_change,
            db.t_articles.thematics,
            db.t_articles.keywords,
            db.t_articles.already_published,
            db.t_articles.auto_nb_recommendations,
            db.t_articles.scheduled_submission_date,
            limitby=(0, maxArticles),
            orderby=~db.t_articles.last_status_change,
        )

    recomms = db.get_last_recomms()

    recommendedArticlesList = []
    for row in queryRecommendedArticles:
        r = article_components.getRecommArticleRowCard(auth, db, response, row, recomms.get(row.id), withDate=True)
        if r:
            recommendedArticlesList.append(r)

    if len(recommendedArticlesList) == 0:
        return DIV(I(T("Coming soon...")))

    if len(recommendedArticlesList) < maxArticles:
        moreState = " disabled"
    else:
        moreState = ""
    return DIV(
        DIV(recommendedArticlesList, _class="pci2-articles-list"),
        DIV(
            A(
                current.T("More..."),
                _id="moreLatestBtn",
                _onclick="ajax('%s', ['qyThemaSelect', 'maxArticles'], 'lastRecommendations')" % (URL("articles", "last_recomms", vars=myVarsNext, user_signature=True)),
                _class="btn btn-default" + moreState,
            ),
            _style="text-align:center;",
        ),
        # Reload mathjax to display math formula (and not latex code)
        SCRIPT("MathJax.typeset();", _type='text/javascript'),
        _class="pci-lastArticles-div",
    )


######################################################################################################################################################################
# Recommendations of an article (public)
def rec():
    articleId = request.vars.get("articleId") or request.vars.get("id")
    printable = request.vars.get("printable") == "True"
    with_comments = not printable
    as_pdf = request.vars.get("asPDF") == "True"

    if not articleId:
        session.flash = T("No parameter id (or articleId)")
        redirect(URL("articles", "recommended_articles"))

    # Remove "reviews" vars from url
    if "reviews" in request.vars:
        redirect(URL(c="articles", f="rec", vars=dict(id=articleId)))

    if not articleId.isdigit():
        session.flash = T("Article id must be a digit")
        redirect(URL("articles", "recommended_articles"))

    art = db.t_articles[articleId]

    if art == None:
        session.flash = T("No such article: id=") + articleId
        redirect(URL("articles", "recommended_articles"))

    if art.status != "Recommended":
        session.flash = T("Access denied: item not recommended yet")
        redirect(URL("articles", "recommended_articles"))

    if as_pdf:
        pdfQ = db((db.t_pdf.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == art.id)).select(db.t_pdf.id, db.t_pdf.pdf)
        if len(pdfQ) > 0:
            redirect(URL("default", "download", args=pdfQ[0]["pdf"]))
        else:
            session.flash = T("Unavailable")
            redirect(redirect(request.env.http_referer))

    # Set Page title
    finalRecomm = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()
    if not finalRecomm:
        session.flash = T("Item not recommended yet")
        redirect(URL("articles", "recommended_articles"))

    response.title = finalRecomm.recommendation_title
    response.title = common_tools.getShortText(response.title, 64)

    nbRecomms = db((db.t_recommendations.article_id == art.id)).count()
    nbRevs = db((db.t_recommendations.article_id == art.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id)).count()
    nbReviews = nbRevs + (nbRecomms - 1)

    # Recommendation Header and Metadata
    recommendationHeader = public_recommendation.getArticleAndFinalRecommendation(auth, db, response, art, finalRecomm, printable)
    recommHeaderHtml = recommendationHeader["headerHtml"]
    recommMetadata = recommendationHeader["recommMetadata"]

    if len(recommMetadata) > 0:
        response.meta = recommMetadata

    reviewRounds = DIV(public_recommendation.getPublicReviewRoundsHtml(auth, db, response, art.id))

    commentsTreeAndForm = None
    if with_comments:
        # Get user comments list and form
        commentsTreeAndForm = public_recommendation.getRecommCommentListAndForm(auth, db, response, session, art.id, request.vars["replyTo"])

    if printable:
        printableClass = "printable"
        response.view = "default/wrapper_printable.html"
    else:
        printableClass = ""
        response.view = "default/wrapper_normal.html"

    viewToRender = "controller/articles/public_article_recommendation.html" #xxx
    return dict(
        viewToRender=viewToRender,
        withComments=with_comments,
        printableUrl=URL(c="articles", f="rec", vars=dict(articleId=articleId, printable=True), user_signature=True),
        currentUrl=URL(c="articles", f="rec", vars=dict(articleId=articleId), host=host, scheme=scheme, port=port),
        shareButtons=True,
        nbReviews=nbReviews,
        recommHeaderHtml=recommHeaderHtml,
        reviewRounds=reviewRounds,
        commentsTreeAndForm=commentsTreeAndForm,
        printableClass=printableClass,
        myBackButton=common_small_html.mkBackButton(),
    )


######################################################################################################################################################################
def tracking():
    tracking = myconf.get("config.tracking", default=False)
    if tracking is False:
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    else:
        article_list = DIV(_class="pci2-articles-list")

        query_already_published_articles = db(db.t_articles.already_published == False).select(orderby=~db.t_articles.last_status_change)

        for article in query_already_published_articles:
            article_html_card = article_components.getArticleTrackcRowCard(auth, db, response, article)
            if article_html_card:
                article_list.append(article_html_card)

        response.view = "default/gab_list_layout.html"
        resu = dict(
            pageHelp=getHelp(request, auth, db, "#Tracking"),
            titleIcon="tasks",
            pageTitle=getTitle(request, auth, db, "#TrackingTitle"),
            customText=getText(request, auth, db, "#TrackingText"),
            grid=DIV(article_list, _class="pci2-flex-center"),
        )
        return resu


######################################################################################################################################################################
def pub_reviews():
    myContents = DIV()
    tracking = myconf.get("config.tracking", default=False)
    if tracking is False:
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    elif "articleId" in request.vars:
        articleId = request.vars["articleId"]
    elif "id" in request.vars:
        articleId = request.vars["id"]
    else:
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    # NOTE: check id is numeric!
    if not articleId.isdigit():
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))

    art = db.t_articles[articleId]
    myContents = None
    if art is None:
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    elif art.status != "Cancelled":
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    else:
        myContents = DIV(old_common.reviewsOfCancelled(auth, db, art))

    response.view = "default/myLayout.html"
    resu = dict(
        titleIcon="eye-open",
        pageTitle=getTitle(request, auth, db, "#TrackReviewsTitle"),
        pageHelp=getHelp(request, auth, db, "#TrackReviews"),
        customText=getText(request, auth, db, "#TrackReviewsText"),
        grid=myContents,
    )
    return resu
