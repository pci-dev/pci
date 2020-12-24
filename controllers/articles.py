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
trgmLimit = myconf.take("config.trgm_limit") or 0.4

pciRRactivated = myconf.get("config.registered_reports", default=False)

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
            db.t_articles.i_am_an_author,
            db.t_articles.is_not_reviewed_elsewhere,
            db.t_articles.auto_nb_recommendations,
            limitby=(0, maxArticles),
            orderby=~db.t_articles.last_status_change,
        )

    recommendedArticlesList = []
    for row in queryRecommendedArticles:
        r = article_components.getRecommArticleRowCard(auth, db, response, row, withDate=True)
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
            A(current.T("See all recommendations"), _href=URL("articles", "all_recommended_articles"), _class="btn btn-default"),
            _style="text-align:center;",
        ),
        _class="pci-lastArticles-div",
    )


######################################################################################################################################################################
# Recommended articles search & list (public)
def recommended_articles():
    myVars = request.vars
    qyKwArr = []
    qyTF = []
    myVars2 = {}
    for myVar in myVars:
        if isinstance(myVars[myVar], list):
            myValue = (myVars[myVar])[1]
        else:
            myValue = myVars[myVar]
        if myVar == "qyKeywords":
            qyKw = myValue
            myVars2[myVar] = myValue
            qyKwArr = qyKw.split(" ")
        elif (myVar == "qyThemaSelect") and myValue:
            qyTF = [myValue]
            myVars2["qy_" + myValue] = True
        elif re.match("^qy_", myVar) and myValue == "on" and not ("qyThemaSelect" in myVars):
            qyTF.append(re.sub(r"^qy_", "", myVar))
            myVars2[myVar] = myValue

    filtered = db.executesql("SELECT * FROM search_articles(%s, %s, %s, %s, %s);", placeholders=[qyTF, qyKwArr, "Recommended", trgmLimit, True], as_dict=True)

    totalArticles = len(filtered)
    myRows = []
    for row in filtered:
        r = article_components.getRecommArticleRowCard(auth, db, response, Storage(row), withImg=True, withScore=False, withDate=True)
        if r:
            myRows.append(r)

    grid = DIV(
        DIV(DIV(T("%s items found") % (totalArticles), _class="pci-nResults"), DIV(myRows, _class="pci2-articles-list"), _class="pci-lastArticles-div"),
        _class="searchRecommendationsDiv",
    )

    searchForm = app_forms.searchByThematic(auth, db, myVars2)

    response.view = "default/gab_list_layout.html"
    return dict(
        titleIcon="search",
        pageTitle=getTitle(request, auth, db, "#RecommendedArticlesTitle"),
        customText=getText(request, auth, db, "#RecommendedArticlesText"),
        pageHelp=getHelp(request, auth, db, "#RecommendedArticles"),
        shareable=True,
        currentUrl=URL(c="about", f="recommended_articles", host=host, scheme=scheme, port=port),
        searchableList=True,
        searchForm=searchForm,
        grid=grid,
    )


######################################################################################################################################################################
# Recommendations of an article (public)
def rec():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

    # with_comments = True
    printable = "printable" in request.vars and request.vars["printable"] == "True"

    if printable is None or printable is False:
        with_comments = True
    else:
        with_comments = False

    as_pdf = "asPDF" in request.vars and request.vars["asPDF"] == "True"

    # security : Is content avalaible ?
    if "articleId" in request.vars:
        articleId = request.vars["articleId"]
    elif "id" in request.vars:
        articleId = request.vars["id"]
    else:
        session.flash = T("Unavailable")
        redirect(URL("articles", "recommended_articles", user_signature=True))

    # NOTE: check id is numeric!
    if not articleId.isdigit():
        session.flash = T("Unavailable")
        redirect(URL("articles", "recommended_articles", user_signature=True))

    art = db.t_articles[articleId]

    if art == None:
        session.flash = T("Unavailable")
        redirect(URL("articles", "recommended_articles", user_signature=True))
    # NOTE: security hole possible by articleId injection: Enforced checkings below.
    elif art.status != "Recommended":
        session.flash = T("Forbidden access")
        redirect(URL("articles", "recommended_articles", user_signature=True))

    if as_pdf:
        pdfQ = db((db.t_pdf.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == art.id)).select(db.t_pdf.id, db.t_pdf.pdf)
        if len(pdfQ) > 0:
            redirect(URL("default", "download", args=pdfQ[0]["pdf"]))
        else:
            session.flash = T("Unavailable")
            redirect(redirect(request.env.http_referer))

    # Set Page title
    finalRecomm = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()
    if finalRecomm:
        response.title = finalRecomm.recommendation_title or myconf.take("app.longname")
    else:
        response.title = myconf.take("app.longname")
    response.title = common_tools.getShortText(response.title, 64)

    nbRecomms = db((db.t_recommendations.article_id == art.id)).count()
    nbRevs = db((db.t_recommendations.article_id == art.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id)).count()
    nbReviews = nbRevs + (nbRecomms - 1)

    isStage2 = art.art_stage_1_id is not None
    stage1Link = None
    stage2List = None
    if pciRRactivated and isStage2:
        # stage1Link = A(T("Link to Stage 1"), _href=URL(c="manager", f="recommendations", vars=dict(articleId=art.art_stage_1_id)))
        urlArticle = URL(c="articles", f="rec", vars=dict(id=art.art_stage_1_id))
        stage1Link = common_small_html.mkRepresentArticleLightLinked(auth, db, art.art_stage_1_id, urlArticle)
    elif pciRRactivated and not isStage2:
        stage2Articles = db((db.t_articles.art_stage_1_id == articleId) & (db.t_articles.status == "Recommended")).select()
        stage2List = []
        for art_st_2 in stage2Articles:
            urlArticle = URL(c="articles", f="rec", vars=dict(id=art_st_2.id))
            stage2List.append(common_small_html.mkRepresentArticleLightLinked(auth, db, art_st_2.id, urlArticle))

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

    viewToRender = "controller/articles/public_article_recommendation.html"
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
        pciRRactivated=pciRRactivated,
        isStage2=isStage2,
        stage1Link=stage1Link,
        stage2List=stage2List,
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
def all_recommended_articles():
    allR = db.executesql("SELECT * FROM search_articles(%s, %s, %s, %s, %s);", placeholders=[[".*"], None, "Recommended", trgmLimit, True], as_dict=True)
    myRows = []
    for row in allR:
        r = article_components.getRecommArticleRowCard(auth, db, response, Storage(row), withImg=True, withScore=False, withDate=True)
        if r:
            myRows.append(r)
    n = len(allR)

    grid = DIV(
        DIV(DIV(T("%s items found") % (n), _class="pci-nResults"), DIV(myRows, _class="pci2-articles-list"), _class="pci-lastArticles-div"), _class="searchRecommendationsDiv"
    )

    response.view = "default/myLayout.html"
    return dict(
        titleIcon="book",
        pageTitle=getTitle(request, auth, db, "#AllRecommendedArticlesTitle"),
        customText=getText(request, auth, db, "#AllRecommendedArticlesText"),
        pageHelp=getHelp(request, auth, db, "#AllRecommendedArticles"),
        grid=grid,
        shareable=True,
        currentUrl=URL(c="articles", f="all_recommended_articles", host=host, scheme=scheme, port=port),
    )


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

