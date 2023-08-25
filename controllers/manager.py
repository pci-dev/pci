# -*- coding: utf-8 -*-

import re
import copy
import tempfile
import datetime
from datetime import timedelta
import glob
import os
from typing import List, cast

# sudo pip install tweepy
# import tweepy

import codecs

# import html2text
from gluon.contrib.markdown import WIKI
from gluon.dal import Row
from gluon.contrib.appconfig import AppConfig

from app_modules.helper import *

from controller_modules import manager_module
from controller_modules import adjust_grid

from app_components import app_forms

from app_components import article_components
from app_components import ongoing_recommendation
from app_components import recommender_components

from app_modules import common_tools
from app_modules import emailing_tools
from app_modules import common_small_html
from app_modules import emailing
from app_modules import emailing_vars
from app_modules import hypothesis
from app_modules.twitter import Twitter
from app_modules.mastodon import Mastodon

from app_modules.common_small_html import md_to_html

from controller_modules import admin_module
from gluon.sqlhtml import SQLFORM
from models.article import ArticleStatus


myconf = AppConfig(reload=True)

csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
not_considered_delay_in_days = myconf.get("config.unconsider_limit_days", default=20)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()
ACCENT_COLOR = '#fcc24d'
Field.CC = db.Field.CC
######################################################################################################################################################################
## Menu Routes
######################################################################################################################################################################
def index():
    return pending_articles()

# Display ALL articles and allow management
@auth.requires(auth.has_membership(role="manager"))
def all_articles():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    resu = _manage_articles(None, URL("manager", "all_articles", host=host, scheme=scheme, port=port))
    resu["customText"] = getText(request, auth, db, "#ManagerAllArticlesText")
    resu["titleIcon"] = "book"
    resu["pageTitle"] = getTitle(request, auth, db, "#ManagerAllArticlesTitle")
    resu["pageHelp"] = getHelp(request, auth, db, "#ManageAllArticlesHelp")
    return resu


######################################################################################################################################################################
# Display pending articles and allow management
@auth.requires(auth.has_membership(role="manager") or is_recommender(auth, request))
def pending_articles():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    states = ["Pending", "Pre-recommended", "Pre-revision", "Pre-rejected", "Pre-recommended-private"]

    resu = _manage_articles(states, URL("manager", "pending_articles", host=host, scheme=scheme, port=port))
    resu["customText"] = getText(request, auth, db, "#ManagerPendingArticlesText")
    resu["titleIcon"] = "time"
    resu["pageTitle"] = getTitle(request, auth, db, "#ManagerPendingArticlesTitle")
    resu["pageHelp"] = getHelp(request, auth, db, "#ManagePendingValidations")
    return resu

######################################################################################################################################################################
# Display articles in presubmission and allow management
@auth.requires(auth.has_membership(role="manager"))
def pending_surveys():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    resu = _manage_articles(
        ["Pending-survey"], URL("manager", "pending_surveys", host=host, scheme=scheme, port=port)
    )
    resu["customText"] = getText(request, auth, db, "#ManagerPendingSurveyReportsText")
    resu["titleIcon"] = "time"
    resu["pageTitle"] = getTitle(request, auth, db, "#ManagerPendingSurveyReportsTitle")
    resu["pageHelp"] = getHelp(request, auth, db, "#ManagerPendingSurveyReports")
    return resu


@auth.requires(auth.has_membership(role="manager"))
def presubmissions():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    resu = _manage_articles(
        ["Pre-submission"], URL("manager", "presubmissions", host=host, scheme=scheme, port=port)
    )
    resu["customText"] = getText(request, auth, db, "#ManagePresubmittedArticlesText")
    resu["titleIcon"] = "warning-sign"
    resu["pageTitle"] = getTitle(request, auth, db, "#ManagePresubmittedArticlesTitle")
    resu["pageHelp"] = getHelp(request, auth, db, "#ManagePresubmittedArticles")
    return resu


######################################################################################################################################################################
# Display ongoing articles and allow management
@auth.requires(auth.has_membership(role="manager"))
def ongoing_articles():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    resu = _manage_articles(["Awaiting consideration", "Under consideration", "Awaiting revision", "Scheduled submission under consideration", "Scheduled submission revision"], URL("manager", "ongoing_articles", host=host, scheme=scheme, port=port))
    resu["customText"] = getText(request, auth, db, "#ManagerOngoingArticlesText")
    resu["titleIcon"] = "refresh"
    resu["pageTitle"] = getTitle(request, auth, db, "#ManagerOngoingArticlesTitle")
    resu["pageHelp"] = getHelp(request, auth, db, "#ManageOngoingArticles")
    return resu


######################################################################################################################################################################
# Display completed articles and allow management
@auth.requires(auth.has_membership(role="manager"))
def completed_articles():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    db.t_articles.status.label = T("Outcome")
    resu = _manage_articles(["Cancelled", "Recommended", "Rejected", "Not considered"], URL("manager", "completed_articles", host=host, scheme=scheme, port=port))
    resu["customText"] = getText(request, auth, db, "#ManagerCompletedArticlesText")
    resu["titleIcon"] = "ok-sign"
    resu["pageTitle"] = getTitle(request, auth, db, "#ManagerCompletedArticlesTitle")
    resu["pageHelp"] = getHelp(request, auth, db, "#ManageCompletedArticles")
    return resu


######################################################################################################################################################################
# Common function which allow management of articles filtered by status
@auth.requires(auth.has_membership(role="manager") or is_recommender(auth, request))
def _manage_articles(statuses, whatNext, db=db):
    response.view = "default/myLayout.html"

    # users
    def index_by(field, query): return { x[field]: x for x in db(query).select() }

    users = index_by("id", db.auth_user)
    last_recomms = db.executesql("select max(id) from t_recommendations group by article_id") if not statuses else \
                   db.executesql("select max(id) from t_recommendations where article_id in " +
                       "(select id from t_articles where status in ('" + "','".join(statuses) + "')) " +
                       "group by article_id")
    last_recomms = [x[0] for x in last_recomms]
    recomms = index_by("article_id", db.t_recommendations.id.belongs(last_recomms))
    co_recomms = db(db.t_press_reviews.recommendation_id.belongs(last_recomms)).select()

    # articles
    articles = db.t_articles
    full_text_search_fields = [
        'id',
        'anonymous_submission',
        'user_id',
        'status',
        'title',
        'abstract',
        'authors',
        'art_stage_1_id',
        'report_stage',
        'request_submission_change',
        'last_status_change',
        'keywords',
        'submitter_details',
        'upload_timestamp'
    ]

    def mkUser(user_details, user_id):
        return TAG(user_details) if user_details else common_small_html._mkUser(users.get(user_id))

    def mkSubmitter(row):
        return SPAN(
            DIV(common_small_html.mkAnonymousArticleField(auth, db, row.anonymous_submission, "", row.id)),
            mkUser(row.submitter_details, row.user_id),
        )

    def mkRecommenders(row):
        article_id = row.id

        recomm = recomms.get(article_id)
        if not recomm:
            return DIV("no recommender")

        resu = DIV()
        resu.append(mkUser(recomm.recommender_details,recomm.recommender_id))

        for co_recomm in co_recomms:
            if co_recomm.recommendation_id == recomm.id:
                resu.append(mkUser(co_recomm.contributor_details, co_recomm.contributor_id))

        if len(resu) > 1:
            resu.insert(1, DIV(B("Co-recommenders:")))

        return resu
    
    articles.id.readable = True
    articles.id.represent = lambda text, row: DIV(common_small_html.mkRepresentArticleLight(auth, db, text), _class="pci-w300Cell")

    articles.user_id.represent = lambda txt, row: mkSubmitter(row)
    articles.user_id.label = 'Submitter'

    articles.title.represent = lambda txt, row: mkRecommenders(row)
    articles.title.label = 'Recommenders'

    articles.anonymous_submission.readable = False
    articles.report_stage.readable = False
    articles.request_submission_change.readable = False
    articles.art_stage_1_id.readable = False
    articles.upload_timestamp.searchable = False
    articles.last_status_change.searchable = False

    articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(
        auth, db, text, showStage=pciRRactivated, stage1Id=row.art_stage_1_id, reportStage=row.report_stage, submission_change=row.request_submission_change,
    )

    articles.upload_timestamp.represent = lambda text, row: common_small_html.mkLastChange(row.upload_timestamp)
    articles.last_status_change.represent = lambda text, row: common_small_html.mkLastChange(row.last_status_change)

    for a_field in articles.fields:
        if not a_field in full_text_search_fields:
            articles[a_field].readable = False

    articles.id.label = "Article"

    links = [
        dict(
            header=T("Actions"),
            body=lambda row: DIV(
                A(
                    SPAN(current.T("View / Edit")),
                    _href=URL(c="manager", f="recommendations", vars=dict(articleId=row.id, recommender=auth.user_id)),
                    _class="buttontext btn btn-default pci-button pci-manager",
                    _title=current.T("View and/or edit"),
                ),
                A(
                    TAG(current.T('Prepare email informing authors that preprint not considered')),
                    _onclick=f'showSetNotConsideredDialog({row.id}, "{URL(c="manager_actions", f="get_not_considered_dialog", vars=dict(articleId=row.id), user_signature=True)}")',
                    _class="buttontext btn btn-danger pci-button pci-manager",
                    _id=f"button-set-not-considered-{row.id}",
                    _title=current.T('Prepare email informing authors that preprint not considered'),
                    _style="width: 100px; white-space: normal; font-size: 9px; padding: 1px; line-height: 14px"
                )
                if (
                    (row.status == ArticleStatus.AWAITING_CONSIDERATION.value or row.status == ArticleStatus.PENDING.value)
                    and row.already_published is False
                )
                else "",
            ),
        ),
    ]
    
    #recomms.get(article_id)
    query = (db.t_articles.id == db.v_article_id.id)
    if statuses:
        query = query & db.t_articles.status.belongs(statuses)

    # recommenders only ever get here via menu "Recommender > Pending validation(s)"
    if pciRRactivated and is_recommender(auth, request):
        query = db.pending_scheduled_submissions_query
    
    original_grid = SQLFORM.grid(
        query,
        searchable=True,
        details=False,
        editable=False,
        deletable=False,
        create=False,
        csv=csv,
        exportclasses=expClass,
        maxtextlength=250,
        paginate=20,
        fields=[
            articles.last_status_change,
            articles.status,
            articles.id,
            articles.upload_timestamp,
            articles.user_id,
            articles.art_stage_1_id,
            articles.anonymous_submission,
            articles.submitter_details,
            articles.title,
            articles.already_published,
            articles.report_stage,
            articles.request_submission_change
        ],
        links=links,
        left=db.v_article.on(db.t_articles.id == db.v_article.id),
        orderby=~articles.last_status_change,
        _class="web2py_grid action-button-absolute",
    )

    # options to be removed from the search dropdown:
    remove_options = ['t_articles.upload_timestamp', 't_articles.last_status_change', 't_articles.anonymous_submission',
                      'v_article_id.id', 'v_article_id.id_str', 'v_article.id', 'v_article.title', 'v_article.authors',
                      'v_article.abstract', 'v_article.user_id', 'v_article.status', 'v_article.keywords', 'v_article.submission_date',
                      'v_article.reviewers']
    integer_fields = ['t_articles.id', 't_articles.user_id']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'articles', remove_options, integer_fields)

    return dict(
        customText=getText(request, auth, db, "#ManagerArticlesText"),
        pageTitle=getTitle(request, auth, db, "#ManagerArticlesTitle"),
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
        script=common_tools.get_script("manager.js")
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or is_recommender(auth, request))
def recommendations():
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    printable = "printable" in request.vars and request.vars["printable"] == "True"

    if art is None:
        session.flash = auth.not_authorized()
        redirect(URL('default','index'))

    if art.already_published:
        myContents = ongoing_recommendation.getPostprintRecommendation(auth, db, response, art, printable, quiet=False)
    else:
        myContents = ongoing_recommendation.getRecommendationProcess(auth, db, response, art, printable)

    isStage2 = art.art_stage_1_id is not None
    stage1Link = None
    stage2List = None
    if pciRRactivated and isStage2:
        # stage1Link = A(T("Link to Stage 1"), _href=URL(c="manager", f="recommendations", vars=dict(articleId=art.art_stage_1_id)))
        urlArticle = URL(c="manager", f="recommendations", vars=dict(articleId=art.art_stage_1_id))
        stage1Link = common_small_html.mkRepresentArticleLightLinkedWithStatus(auth, db, art.art_stage_1_id, urlArticle)
    elif pciRRactivated and not isStage2:
        stage2Articles = db(db.t_articles.art_stage_1_id == articleId).select()
        stage2List = []
        for art_st_2 in stage2Articles:
            urlArticle = URL(c="manager", f="recommendations", vars=dict(articleId=art_st_2.id))
            stage2List.append(common_small_html.mkRepresentArticleLightLinkedWithStatus(auth, db, art_st_2.id, urlArticle))

    response.title = art.title or myconf.take("app.longname")

    recommHeaderHtml = article_components.getArticleInfosCard(auth, db, response, art, printable, True)
    recommStatusHeader = ongoing_recommendation.getRecommStatusHeader(auth, db, response, art, "manager", request, False, printable, quiet=False)
    recommTopButtons = ongoing_recommendation.getRecommendationTopButtons(auth, db, art, printable, quiet=False)
    set_not_considered_button = ongoing_recommendation.set_to_not_considered(art) if art.status == ArticleStatus.AWAITING_CONSIDERATION.value else None

    recommendation = db.get_last_recomm(art)
    if (auth.has_membership(role="administrator")
        and recommendation
        and art.status == "Recommended"
    ):
        recommStatusHeader = TAG(recommStatusHeader)
        if not pciRRactivated:
            if hypothesis.Hypothesis.may_have_annotation(art.doi):
                recommStatusHeader.append(basic_hypothesis_button(art.id))

            twitter_button_element = twitter_button(art, recommendation)
            if twitter_button_element:
                recommStatusHeader.append(twitter_button_element)
            
            mastodon_button_element = mastodon_button(art, recommendation)
            if mastodon_button_element:
                recommStatusHeader.append(mastodon_button_element)
            
        recommStatusHeader.append(crossref_toolbar(art))

    if printable:
        printableClass = "printable"
        response.view = "default/wrapper_printable.html"
    else:
        printableClass = ""
        response.view = "default/wrapper_normal.html"

    myScript = common_tools.get_script("recommended_articles.js")
    viewToRender = "default/recommended_articles.html"
    return dict(
        viewToRender=viewToRender,
        recommHeaderHtml=recommHeaderHtml,
        recommStatusHeader=recommStatusHeader,
        recommTopButtons=recommTopButtons or "",
        printable=printable,
        pageHelp=getHelp(request, auth, db, "#ManagerRecommendations"),
        myContents=myContents,
        myBackButton=common_small_html.mkBackButton(),
        pciRRactivated=pciRRactivated,
        isStage2=isStage2,
        stage1Link=stage1Link,
        stage2List=stage2List,
        myFinalScript=myScript,
        script=common_tools.get_script("manager.js"),
        isPendingValidation=(art.status == "Pending" and not pciRRactivated),
        setNotConsideredButton=set_not_considered_button or ""
    )

def crossref_toolbar(article):
    return DIV(
        crossref_button(article),
        crossref_status(article),
        _style="width: fit-content; display: inline-block",
    )

def crossref_button(article: Row):
    return A(
        I(_class="glyphicon glyphicon-edit", _style="vertical-align:middle"),
        T("Crossref"),
        _href=URL("crossref", f"post_form?article_id={article.id}"),
        _class="pci2-tool-link pci2-yellow-link",
        _style="margin-right: 25px;",
    )

def basic_hypothesis_button(article_id: int):
    return SPAN(
        I(_class="glyphicon glyphicon-hourglass", _style='vertical-align:middle;'),
        T("Hypothes.is"),
        _class="pci2-tool-link",
        _style='display: inline-block; margin-right: 20px;',
        _id="hypothesis_button_container")


def color_hypothesis_button():
    article_id = cast(int, request.vars.article_id)
    article = cast(Row, db.t_articles[article_id])

    hypothesis_client = hypothesis.Hypothesis(article)
    already_send = hypothesis_client.has_already_annotation()

    icon_style = 'vertical-align:middle;'
    text_style = ''
    if not already_send:
        text_style = f'color: {ACCENT_COLOR}'
        icon_style += f'color: {ACCENT_COLOR}'

    return A(
        I(_class="glyphicon glyphicon-edit", _style=icon_style),
        T("Hypothes.is"),
        _href=URL("hypothesis", f"post_form?article_id={article.id}"),
        _class="pci2-tool-link pci2-yellow-link",
        _style=text_style
    ).xml()


def twitter_button(article, recommendation):
    twitter_client = Twitter(db)

    already_send = twitter_client.has_already_posted(article.id, recommendation.id)
    has_config = twitter_client.has_general_twitter_config() or twitter_client.has_specific_twitter_config()
    if not already_send and not has_config:
        return

    text_style = 'display: inline-block; margin-right: 20px;'
    icon_style = 'vertical-align:middle;'
    if not already_send:
        text_style += f'color: {ACCENT_COLOR}'
        icon_style += f'color: {ACCENT_COLOR}'

    return A(
        I(_class="glyphicon glyphicon-edit", _style=icon_style),
        T("Twitter"),
        _href=URL("twitter", f"post_form?article_id={article.id}"),
        _class="pci2-tool-link pci2-yellow-link",
        _style=text_style,
    )

def mastodon_button(article, recommendation):
    mastodon_client = Mastodon(db)

    already_send = mastodon_client.has_already_posted(article.id, recommendation.id)
    has_config = mastodon_client.has_mastodon_general_config() or mastodon_client.has_mastodon_specific_config()

    if not already_send and not has_config:
        return

    text_style = 'display: inline-block; margin-right: 20px;'
    icon_style = 'vertical-align:middle;'
    if not already_send:
        text_style += f'color: {ACCENT_COLOR}'
        icon_style += f'color: {ACCENT_COLOR}'

    return A(
        I(_class="glyphicon glyphicon-edit", _style=icon_style),
        T("Mastodon"),
        _href=URL("mastodon", f"post_form?article_id={article.id}"),
        _class="pci2-tool-link pci2-yellow-link",
        _style=text_style,
    )

def crossref_status(article):
    recomm = db.get_last_recomm(article)
    status_url = URL("crossref", f"get_status?recomm_id={recomm.id}")
    return SPAN(
        SCRIPT('''
        (function get_crossref_status(elt) {
            elt = elt || document.currentScript.parentNode
            req = new XMLHttpRequest()
            req.addEventListener("load", function() {
                status = this.responseText
                status_str = "✅,❌,,🏁".split(",")
                elt.innerHTML = status_str[status]

                if (status >= "2") setTimeout(function() {
                    get_crossref_status(elt)
                }, 1000)
            })
            req.open("get", "'''+str(status_url)+'''")
            req.send()
        })()
        '''),
    )

######################################################################################################################################################################
# Allow management of article recommendations
@auth.requires(auth.has_membership(role="manager"))
def manage_recommendations():
    response.view = "default/myLayout.html"

    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        redirect(URL(c="manager", f="all_recommendations"))

    query = db.t_recommendations.article_id == articleId
    db.t_recommendations.recommender_id.default = auth.user_id
    db.t_recommendations.article_id.default = articleId
    db.t_recommendations.article_id.writable = False
    db.t_recommendations.last_change.writable = False
    db.t_recommendations.doi.represent = lambda text, row: common_small_html.mkDOI(text)
    db.t_pdf.pdf.represent = lambda text, row: A(IMG(_src=URL("static", "images/application-pdf.png")), _href=URL("default", "download", args=text)) if text else ""
    db.t_recommendations._id.readable = True
    if len(request.args) == 0:  # in grid
        db.t_recommendations.recommender_id.represent = lambda id, row: TAG(row.recommender_details) if row.recommender_details else common_small_html.mkUserWithMail(auth, db, id)
        db.t_recommendations.recommendation_state.represent = lambda state, row: common_small_html.mkContributionStateDiv(auth, db, (state or ""))
        db.t_recommendations.recommendation_comments.represent = lambda text, row: DIV(WIKI(text or ""), _class="pci-div4wiki")
        db.t_recommendations.recommendation_timestamp.represent = lambda text, row: common_small_html.mkLastChange(text)
        db.t_recommendations.last_change.represent = lambda text, row: common_small_html.mkLastChange(text)
    else:  # in form
        db.t_recommendations.recommendation_comments.represent = lambda text, row: WIKI(text or "")

    links = [
        dict(
            header=T("Co-recommenders"),
            body=lambda row: A(
                (db.v_recommendation_contributors[(row.get("t_recommendations") or row).id]).contributors or "ADD CO-RECOMMENDER",
                _href=URL(c="recommender", f="contributions", vars=dict(recommId=(row.get("t_recommendations") or row).id)),
            ),
        )
    ]

    def getReviewers(row):
        reviews = db(db.t_reviews.recommendation_id==row.id).select()
        return ", ".join([common_small_html.get_name_from_details(
                            getReviewerDetails(review)) for review in reviews])

    def getReviewerDetails(review):
        return review.reviewer_details or (
                common_small_html.mkUserWithMail(auth, db, review.reviewer_id)
                .flatten())

    if not (art.already_published):
        links += [
            dict(
                header=T("Reviews"),
                body=lambda row: A(
                    getReviewers(row) or "ADD REVIEWER",
                    _href=URL(c="recommender", f="reviews", vars=dict(recommId=(row.get("t_recommendations") or row).id)),
                ),
            )
        ]
    # links += [dict(header=T('PDF'), body=lambda row: A(db(db.t_pdf.recommendation_id==row.id).select().last()['pdf'], _href=URL(c='admin', f='manage_pdf', vars=dict(keywords='t_pdf.recommendation_id="%s"'%row.id) )))]
    grid = SQLFORM.grid(
        query,
        editable=True,
        deletable=True,
        create=True,
        details=False,
        searchable=False,
        maxtextlength=1000,
        csv=csv,
        exportclasses=expClass,
        paginate=10
        # (gab) WARNING since python 3.8 this throw error, DKW
        # ,left=db.t_pdf.on(db.t_pdf.recommendation_id==db.t_recommendations.id)
        ,
        fields=[
            # db.t_recommendations.id,
            # db.t_recommendations.doi,
            # db.t_recommendations.ms_version,
            # db.t_recommendations.recommendation_timestamp,
            db.t_recommendations.last_change,
            db.t_recommendations.recommendation_state,
            db.t_recommendations.is_closed,
            db.t_recommendations.recommender_id,
            db.t_recommendations.recommender_details,
            # db.t_recommendations.recommendation_comments,
            # db.t_recommendations.reply,
            # db.t_recommendations.reply_pdf,
            # db.t_recommendations.track_change,
            # db.t_recommendations.recommender_file,
            # db.t_pdf.pdf,
        ],
        links=links,
        orderby=~db.t_recommendations.recommendation_timestamp,
        _class="web2py_grid action-button-absolute",
    )
    if grid.element(_title="Add record to database"):
        grid.element(_title="Add record to database")[0] = T("Manually add new round")
        grid.element(_title="Add record to database")["_title"] = T("Manually add new round of recommendation. Expert use!!")
    myContents = DIV(DIV(article_components.getArticleInfosCard(auth, db, response, art, False, False), _class="pci2-content-900px"), _class="pci2-full-width pci2-flex-center")

    return dict(
        myBackButton=common_small_html.mkBackButton(),
        pageHelp=getHelp(request, auth, db, "#ManageRecommendations"),
        customText=getText(request, auth, db, "#ManageRecommendationsText"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#ManageRecommendationsTitle"),
        content=myContents,
        grid=grid,
        deleteFileButtonsScript=common_tools.get_script("add_delete_file_buttons_manager.js"),
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )



######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def search_recommenders():
    whatNext = request.vars["whatNext"]
    articleId = request.vars["articleId"]
    if articleId is None:
        articleHeaderHtml = ""
    else:
        art = db.t_articles[articleId]
        articleHeaderHtml = article_components.getArticleInfosCard(auth, db, response, art, **article_components.for_search)

    excludeList = common_tools.get_exclude_list(request)
    if excludeList is None: return "invalid parameter: exclude"

    for rec in db(
            db.t_excluded_recommenders.article_id == articleId).select():
        excludeList.append(rec.excluded_recommender_id)

    users = db.auth_user
    full_text_search_fields = [
        'first_name',
        'last_name',
        'email',
        'laboratory',
        'institution',
        'city',
        'country',
        'thematics',
        'expertise',
        'keywords',
    ]

    for f in users.fields:
        if not f in full_text_search_fields:
            users[f].readable = False

    users.thematics.label = "Thematics fields"
    users.thematics.type = "string"
    users.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, zero=None)

    links = []
    if articleId:
        links += [
        dict(header="", body=lambda row: "" if row.auth_user.id in excludeList else A(
                SPAN(current.T("Suggest as recommender"), _class="buttontext btn btn-default pci-submitter"),
                _href=URL(c="manager_actions", f="suggest_article_to", vars=dict(articleId=articleId, recommenderId=row.auth_user.id, whatNext=whatNext), user_signature=True),
                _class="button",
            ),
        ),
    ]

    query = (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "recommender")

    db.auth_group.role.searchable = False

    original_grid = SQLFORM.grid(
        query,
        editable=False,
        deletable=False,
        create=False,
        details=False,
        searchable=dict(auth_user=True, auth_membership=False),
        selectable=None,
        maxtextlength=250,
        paginate=1000,
        csv=csv,
        exportclasses=expClass,
        fields=[
            users._id,
            users.uploaded_picture,
            users.first_name,
            users.last_name,
            users.laboratory,
            users.institution,
            users.city,
            users.country,
            users.thematics,
        ],
        links=links,
        orderby=users._id,
        _class="web2py_grid action-button-absolute",
    )

    # fields that are integer and need to be treated differently
    integer_fields = []

    # options to be removed from the search dropdown:
    remove_options = ['auth_membership.id', 'auth_membership.user_id', 'auth_membership.group_id',
                      'auth_group.id', 'auth_group.role', 'auth_group.description']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'recommenders', remove_options, integer_fields)

    response.view = "default/gab_list_layout.html"
    return dict(
        pageHelp=getHelp(request, auth, db, "#ManagerSearchRecommenders"),
        customText=getText(request, auth, db, "#ManagerSearchRecommendersText"),
        titleIcon="search",
        pageTitle=getTitle(request, auth, db, "#ManagerSearchRecommendersTitle"),
        myBackButton=common_small_html.mkBackButton(),
        grid=grid,
        articleHeaderHtml=articleHeaderHtml,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )



######################################################################################################################################################################
# Display suggested recommenders for a submitted article
# Logged users only (submission)
@auth.requires(auth.has_membership(role="manager"))
def suggested_recommenders():
    articleId = request.vars["articleId"]
    whatNext = request.vars["whatNext"]
    if articleId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    articleHeaderHtml = article_components.getArticleInfosCard(auth, db, response, art, **article_components.for_search)

    query = db.t_suggested_recommenders.article_id == articleId
    db.t_suggested_recommenders.article_id.readable = False
    db.t_suggested_recommenders.article_id.writable = False
    db.t_suggested_recommenders._id.readable = False
    db.t_suggested_recommenders.email_sent.readable = False
    db.t_suggested_recommenders.suggested_recommender_id.represent = lambda text, row: common_small_html.mkUserWithMail(auth, db, text)
    db.t_suggested_recommenders.emailing.readable = True
    if len(request.args) == 0:  # we are in grid
        db.t_suggested_recommenders.emailing.represent = lambda text, row: DIV(XML(text), _class="pci-emailingTD") if text else ""
    else:
        db.t_suggested_recommenders.emailing.represent = lambda text, row: XML(text) if text else ""
    links = []
    # if art.status == "Awaiting consideration":
    links.append(
        dict(
            header="",
            body=lambda row: A(
                T("View e-mails"),
                _class="btn btn-info pci-manager",
                _href=URL(c="manager", f="suggested_recommender_emails", vars=dict(suggRecommId=row.suggested_recommender_id, articleId=row.article_id)),
            )
            if not (row.declined)
            else "",
        )
    )

    addSuggestedRecommendersButton = A(
        current.T("Add suggested recommender"), _class="btn btn-default pci-manager", _href=URL(c="manager", f="search_recommenders", vars=request.vars, user_signature=True)
    )

    grid = SQLFORM.grid(
        query,
        details=True,
        editable=True,
        deletable=True,
        create=False,
        searchable=False,
        maxtextlength=250,
        paginate=100,
        csv=csv,
        exportclasses=expClass,
        fields=[
            db.t_suggested_recommenders.id,
            db.t_suggested_recommenders.article_id,
            db.t_suggested_recommenders.suggested_recommender_id,
            db.t_suggested_recommenders.declined,
            db.t_suggested_recommenders.email_sent,
            db.t_suggested_recommenders.emailing,
        ],
        field_id=db.t_suggested_recommenders.id,
        links=links,
        _class="web2py_grid action-button-absolute",
    )

    response.view = "default/myLayout.html"
    return dict(
        myBackButton=common_small_html.mkBackButton(target=URL(c="manager", f="recommendations", vars=dict(articleId=art.id), user_signature=True)),
        pageTitle=getTitle(request, auth, db, "#ManageSuggestedRecommendersTitle"),
        pageHelp=getHelp(request, auth, db, "#ManageSuggestedRecommenders"),
        customText=getText(request, auth, db, "#ManageSuggestedRecommendersText"),
        # myBackButton=common_small_html.mkBackButton(),
        addSuggestedRecommendersButton=addSuggestedRecommendersButton,
        grid=grid,
        articleHeaderHtml=articleHeaderHtml,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or (auth.has_membership(role="recommender") and pciRRactivated))
def edit_article():
    response.view = "default/myLayout.html"

    if not ("articleId" in request.vars):
        session.flash = T("Unavailable")
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art == None:
        # raise HTTP(404, "404: "+T('Unavailable'))
        redirect(URL("manager", "all_articles"))  # it may have been deleted, so that's normal!
    db.t_articles.status.writable = True
    db.t_articles.user_id.writable = True

    db.t_articles.cover_letter.readable = True
    db.t_articles.cover_letter.writable = True

    db.t_articles.request_submission_change.readable = False
    db.t_articles.request_submission_change.writable = False

    if not art.already_published: # != "postprint"
        db.t_articles.article_source.readable = False
        db.t_articles.article_source.writable = False

    myFinalScript = None
    if pciRRactivated:
        havingStage2Articles = db(db.t_articles.art_stage_1_id == articleId).count() > 0

        db.t_articles.results_based_on_data.readable = False
        db.t_articles.results_based_on_data.writable = False
        db.t_articles.data_doi.readable = False
        db.t_articles.data_doi.writable = False

        db.t_articles.cover_letter.label = "Cover letter"

        db.t_articles.scripts_used_for_result.readable = False
        db.t_articles.scripts_used_for_result.writable = False
        db.t_articles.scripts_doi.readable = False
        db.t_articles.scripts_doi.writable = False

        db.t_articles.codes_used_in_study.readable = False
        db.t_articles.codes_used_in_study.writable = False
        db.t_articles.codes_doi.readable = False
        db.t_articles.codes_doi.writable = False

        db.t_articles.funding.readable = False
        db.t_articles.funding.writable = False

        db.t_articles.suggest_reviewers.readable = False
        db.t_articles.suggest_reviewers.writable = False
        db.t_articles.competitors.readable = False
        db.t_articles.competitors.writable = False

        db.t_articles.report_stage.readable = True
        db.t_articles.report_stage.writable = True
        db.t_articles.sub_thematics.readable = True
        db.t_articles.sub_thematics.writable = True

        db.t_articles.record_url_version.readable = True
        db.t_articles.record_url_version.writable = True
        db.t_articles.record_id_version.readable = True
        db.t_articles.record_id_version.writable = True

        if art.report_stage == "STAGE 2":
            db.t_articles.art_stage_1_id.readable = True
            db.t_articles.art_stage_1_id.writable = True
        else:
            db.t_articles.art_stage_1_id.readable = False
            db.t_articles.art_stage_1_id.writable = False

        if not havingStage2Articles:
            db.t_articles.art_stage_1_id.requires = IS_EMPTY_OR(
                IS_IN_DB(db((db.t_articles.user_id == art.user_id) & (db.t_articles.art_stage_1_id == None) & (db.t_articles.id != art.id)), "t_articles.id", "%(title)s")
            )
        else:
            db.t_articles.art_stage_1_id.requires = IS_EMPTY_OR([])
            myFinalScript = common_tools.get_script("disable_stage1_article.js")
    else:
        myFinalScript = common_tools.get_script("new_field_responsiveness.js")
        db.t_articles.report_stage.readable = False
        db.t_articles.report_stage.writable = False

        db.t_articles.art_stage_1_id.readable = False
        db.t_articles.art_stage_1_id.writable = False

    if scheduledSubmissionActivated:
        db.t_articles.scheduled_submission_date.readable = True
        db.t_articles.scheduled_submission_date.writable = True
    else:
        db.t_articles.report_stage.readable = False
        db.t_articles.report_stage.writable = False
        db.t_articles.scheduled_submission_date.readable = False
        db.t_articles.scheduled_submission_date.writable = False

    if not pciRRactivated:
        db.t_articles.sub_thematics.readable = False
        db.t_articles.sub_thematics.writable = False
        db.t_articles.record_id_version.readable = False
        db.t_articles.record_id_version.writable = False
        db.t_articles.record_url_version.readable = False
        db.t_articles.record_url_version.writable = False

    form = SQLFORM(db.t_articles, articleId, upload=URL("static", "uploads"), deletable=True, showid=True)
    try:
        article_version = int(art.ms_version)
    except:
        article_version = art.ms_version

    prev_picture = art.uploaded_picture

    if type(db.t_articles.uploaded_picture.requires) == list: # non-RR see db.py
        not_empty = db.t_articles.uploaded_picture.requires.pop()

    def onvalidation(form):
        if not pciRRactivated:
            if not prev_picture and form.vars.uploaded_picture == b"":
                form.errors.uploaded_picture = not_empty.error_message
            app_forms.checklist_validation(form)

    if form.process(onvalidation=onvalidation).accepted:
        if form.vars.doi != art.doi:
            lastRecomm = db.get_last_recomm(art.id)
            if lastRecomm is not None:
                lastRecomm.doi = form.vars.doi
                lastRecomm.update_record()

        if prev_picture and form.vars.uploaded_picture:
            try: os.unlink(os.path.join(request.folder, "uploads", prev_picture))
            except: pass

        session.flash = T("Article saved", lazy=False)
        controller = "manager" if auth.has_membership(role="manager") else "recommender"
        redirect(URL(c=controller, f="recommendations", vars=dict(articleId=art.id), user_signature=True))
    elif form.errors:
        response.flash = T("Form has errors", lazy=False)

    return dict(
        # myBackButton = common_small_html.mkBackButton(),
        pageHelp=getHelp(request, auth, db, "#ManagerEditArticle"),
        customText=getText(request, auth, db, "#ManagerEditArticleText"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#ManagerEditArticleTitle"),
        form=form,
        myFinalScript=myFinalScript,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or (auth.has_membership(role="recommender") and pciRRactivated))
def edit_report_survey():
    response.view = "default/myLayout.html"

    if not ("articleId" in request.vars):
        session.flash = T("Unavailable")
        redirect(URL("all_articles", user_signature=True))
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art == None:
        session.flash = T("Unavailable")
        redirect(URL("all_articles", user_signature=True))

    survey = db(db.t_report_survey.article_id == articleId).select().last()
    if survey is None:
        survey = db.t_report_survey.insert(article_id = articleId, temp_art_stage_1_id=art.art_stage_1_id)
        session.flash = T("New survey created")
        # redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))

    form = app_forms.report_survey(auth, session, art, db, survey, "manager_edit")

    myScript = common_tools.get_script("fill_report_survey.js")
    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp(request, auth, db, "#ManagerReportSurvey"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#ManagerReportSurveyTitle"),
        customText=getText(request, auth, db, "#ManagerReportSurveyText", maxWidth="800"),
        form=form,
        myFinalScript=myScript,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def manage_comments():
    response.view = "default/myLayout.html"

    db.t_comments.parent_id.label = T("Parent comment")
    grid = SQLFORM.smartgrid(
        db.t_comments,
        create=False,
        fields=[db.t_comments.article_id, db.t_comments.comment_datetime, db.t_comments.user_id, db.t_comments.parent_id, db.t_comments.user_comment],
        linked_tables=["t_comments"],
        csv=csv,
        exportclasses=dict(t_comments=expClass),
        maxtextlength=250,
        paginate=25,
        orderby=~db.t_comments.comment_datetime,
    )
    return dict(
        customText=getText(request, auth, db, "#ManageCommentsText"),
        titleIcon="comment",
        pageTitle=getTitle(request, auth, db, "#ManageCommentsTitle"),
        pageHelp=getHelp(request, auth, db, "#ManageComments"),
        grid=grid,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def all_recommendations():
    response.view = "default/myLayout.html"

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    # goBack='%s://%s%s' % (request.env.wsgi_url_scheme, request.env.http_host, request.env.request_uri)
    goBack = URL(re.sub(r".*/([^/]+)$", "\\1", request.env.request_uri), scheme=scheme, host=host, port=port)

    isPress = ("pressReviews" in request.vars) and (request.vars["pressReviews"] == "True")

    query = (
          (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_articles.already_published == isPress)
        & (db.t_recommendations.id == db.v_article_recommender.recommendation_id)
        & (db.t_recommendations.id == db.v_reviewers.id)
    )
    if not isPress:
        query = query & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration", "Scheduled submission pending"))) 

    if isPress:  ## NOTE: POST-PRINTS
        pageTitle = getTitle(request, auth, db, "#AdminAllRecommendationsPostprintTitle")
        customText = getText(request, auth, db, "#AdminAllRecommendationsPostprintText")
        fields = [
            db.t_articles.scheduled_submission_date,
            db.t_articles.art_stage_1_id,
            db.t_articles.report_stage,
            db.t_recommendations.last_change,
            # db.t_articles.status,
            db.t_recommendations._id,
            db.t_recommendations.article_id,
            db.t_recommendations.doi,
            # db.t_recommendations.recommendation_timestamp,
            db.t_recommendations.is_closed,
            db.t_recommendations.recommender_details,
        ]
        links = [
            dict(header=T("Co-recommenders"), body=lambda row: common_small_html.mkCoRecommenders(auth, db, row.t_recommendations if "t_recommendations" in row else row, goBack)),
            dict(
                header=T(""), body=lambda row: common_small_html.mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if "t_recommendations" in row else row)
            ),
        ]
        db.t_recommendations.article_id.label = T("Postprint")
    else:  ## NOTE: PRE-PRINTS
        pageTitle = getTitle(request, auth, db, "#AdminAllRecommendationsPreprintTitle")
        customText = getText(request, auth, db, "#AdminAllRecommendationsPreprintText")
        fields = [
            db.t_articles.scheduled_submission_date,
            db.t_articles.art_stage_1_id,
            db.t_articles.report_stage,
            db.t_recommendations.last_change,
            # db.t_articles.status,
            db.t_recommendations._id,
            db.t_recommendations.article_id,
            db.t_recommendations.doi,
            # db.t_recommendations.recommendation_timestamp,
            db.t_recommendations.is_closed,
            db.t_recommendations.recommendation_state,
            db.t_recommendations.is_closed,
            db.t_recommendations.recommender_id,
            db.t_recommendations.recommender_details,
        ]
        links = [
            dict(header=T("Co-recommenders"), body=lambda row: common_small_html.mkCoRecommenders(auth, db, row.t_recommendations if "t_recommendations" in row else row, goBack)),
            dict(header=T("Reviews"), body=lambda row: recommender_components.getReviewsSubTable(auth, db, response, request, row.t_recommendations if "t_recommendations" in row else row)),
            # dict(header=T('Actions'),            body=lambda row: common_small_html.mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
            dict(
                header=T("Actions"),
                body=lambda row: DIV(manager_module.mkViewEditRecommendationsManagerButton(auth, db, row.t_recommendations if "t_recommendations" in row else row)),
            ),
        ]
        db.t_recommendations.article_id.label = T("Preprint")

    db.t_recommendations.recommender_id.writable = False
    db.t_recommendations.doi.writable = False
    # db.t_recommendations.article_id.readable = False
    db.t_recommendations.article_id.writable = False
    db.t_recommendations._id.readable = False
    db.t_recommendations.recommender_id.readable = True
    db.t_recommendations.recommender_id.represent =  lambda id, row: TAG(row.t_recommendations.recommender_details) if row.t_recommendations.recommender_details else common_small_html.mkUserWithMail(auth, db, id)
    db.t_recommendations.recommendation_state.readable = False
    db.t_recommendations.is_closed.readable = False
    db.t_recommendations.is_closed.writable = False
    db.t_recommendations.recommendation_timestamp.label = T("Started")
    db.t_recommendations.last_change.label = T("Last change")
    db.t_recommendations.last_change.represent = (
        lambda text, row: common_small_html.mkElapsedDays(row.t_recommendations.last_change) if "t_recommendations" in row else common_small_html.mkElapsedDays(row.last_change)
    )
    db.t_recommendations.recommendation_timestamp.represent = (
        lambda text, row: common_small_html.mkElapsedDays(row.t_recommendations.recommendation_timestamp)
        if "t_recommendations" in row
        else common_small_html.mkElapsedDays(row.recommendation_timestamp)
    )
    db.t_recommendations.article_id.represent = lambda aid, row: DIV(common_small_html.mkArticleCellNoRecomm(auth, db, db.t_articles[aid]), _class="pci-w300Cell")

    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.art_stage_1_id.writable = False
    db.t_articles.report_stage.writable = False
    db.t_articles.report_stage.readable = False

    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(
        auth, db, text, showStage=pciRRactivated, stage1Id=row.t_articles.art_stage_1_id, reportStage=row.t_articles.report_stage
    )

    db.t_recommendations.doi.readable = False
    db.t_recommendations.last_change.readable = True
    db.t_recommendations.recommendation_comments.represent = lambda text, row: DIV(WIKI(text or ""), _class="pci-div4wiki")

    db.t_articles.scheduled_submission_date.readable = False
    db.t_articles.scheduled_submission_date.writable = False

    original_grid = SQLFORM.grid(
        query,
        searchable=True,
        create=False,
        deletable=False,
        editable=False,
        details=False,
        maxtextlength=500,
        paginate=10,
        csv=csv,
        exportclasses=expClass,
        fields=fields,
        links=links,
        orderby=~db.t_recommendations.last_change,
        _class="web2py_grid action-button-absolute",
    )

    # options to be removed from the search dropdown:
    remove_options = ['t_recommendations.article_id', 'v_reviewers.id',
                      't_recommendations.ms_version', 't_recommendations.recommender_id', 't_recommendations.recommendation_title',
                      't_recommendations.recommendation_comments', 't_recommendations.recommendation_doi', 't_recommendations.recommendation_doi',
                      't_recommendations.recommendation_timestamp', 't_recommendations.validation_timestamp', 't_recommendations.last_change',
                      't_recommendations.no_conflict_of_interest', 't_recommendations.reply', 'v_article_recommender.recommendation_id',
                      't_articles.anonymous_submission', 't_articles.has_manager_in_authors', 't_articles.article_year',
                      't_articles.article_source', 't_articles.doi', 't_articles.preprint_server',
                      't_articles.ms_version', 't_articles.picture_rights_ok', 't_articles.upload_timestamp', 
                      't_articles.validation_timestamp', 't_articles.last_status_change', 't_articles.request_submission_change',
                      't_articles.funding', 't_articles.already_published', 't_articles.doi_of_published_article', 
                      't_articles.parallel_submission', 't_articles.is_searching_reviewers', 't_articles.sub_thematics', 
                      't_articles.results_based_on_data', 't_articles.scripts_used_for_result',
                      't_articles.codes_used_in_study', 't_articles.record_id_version', 't_articles.record_url_version']
    integer_fields = ['t_articles.id', 't_articles.user_id']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'articles', remove_options, integer_fields)
    
    return dict(
        # myBackButton=common_small_html.mkBackButton(),
        pageHelp=getHelp(request, auth, db, "#AdminAllRecommendations"),
        titleIcon="education",
        pageTitle=pageTitle,
        customText=customText,
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def suggested_recommender_emails():
    response.view = "default/myLayout.html"

    suggRecommId = request.vars["suggRecommId"]
    articleId = request.vars["articleId"]
    suggested_recommender = db.auth_user[suggRecommId]

    db.mail_queue.sending_status.represent = lambda text, row: DIV(
        SPAN(admin_module.makeMailStatusDiv(text)),
        SPAN(I(T("Sending attempts : ")), B(row.sending_attempts), _style="font-size: 12px; margin-top: 5px"),
        _class="pci2-flex-column",
        _style="margin: 5px 10px;",
    )

    db.mail_queue.id.readable = False
    db.mail_queue.sending_attempts.readable = False

    db.mail_queue.sending_date.represent = lambda text, row: datetime.datetime.strptime(str(text), "%Y-%m-%d %H:%M:%S")
    db.mail_queue.mail_content.represent = lambda text, row: XML(admin_module.sanitizeHtmlContent(text))
    db.mail_queue.mail_subject.represent = lambda text, row: B(text)
    db.mail_queue.article_id.represent = lambda art_id, row: DIV(common_small_html.mkRepresentArticleLightLinked(auth, db, art_id))
    db.mail_queue.mail_subject.represent = lambda text, row: DIV(B(text), BR(), SPAN(row.mail_template_hashtag), _class="ellipsis-over-350")
    db.mail_queue.cc_mail_addresses.widget = app_forms.cc_widget
    db.mail_queue.replyto_addresses.widget = app_forms.cc_widget

    db.mail_queue.sending_status.writable = False
    db.mail_queue.sending_attempts.writable = False
    db.mail_queue.dest_mail_address.writable = False
    db.mail_queue.user_id.writable = False
    db.mail_queue.mail_template_hashtag.writable = False
    db.mail_queue.reminder_count.writable = False
    db.mail_queue.article_id.writable = False
    db.mail_queue.recommendation_id.writable = False

    db.mail_queue.removed_from_queue.writable = False
    db.mail_queue.removed_from_queue.readable = False
    links = [
        dict(
            header="",
            body=lambda row: A(
                (T("Scheduled") if row.removed_from_queue == False else T("Unscheduled")),
                _href=URL(c="admin_actions", f="toggle_shedule_mail_from_queue", vars=dict(emailId=row.id)),
                _class="btn btn-default",
                _style=("background-color: #3e3f3a;" if row.removed_from_queue == False else "background-color: #ce4f0c;"),
            )
            if row.sending_status == "pending"
            else "",
        )
    ]

    if len(request.args) > 2 and request.args[0] == "edit":
        db.mail_queue.mail_template_hashtag.readable = True
    else:
        db.mail_queue.mail_template_hashtag.readable = False

    myScript = common_tools.get_script("replace_mail_content.js")

    grid = SQLFORM.grid(
        ((db.mail_queue.dest_mail_address == suggested_recommender.email) & (db.mail_queue.article_id == articleId) & (db.mail_queue.recommendation_id == None)),
        details=True,
        editable=lambda row: (row.sending_status == "pending"),
        deletable=lambda row: (row.sending_status == "pending"),
        create=False,
        searchable=True,
        csv=False,
        paginate=50,
        maxtextlength=256,
        orderby=~db.mail_queue.id,
        onvalidation=mail_form_processing,
        fields=[
            db.mail_queue.sending_status,
            db.mail_queue.removed_from_queue,
            db.mail_queue.sending_date,
            db.mail_queue.sending_attempts,
            db.mail_queue.dest_mail_address,
            db.mail_queue.cc_mail_addresses,
            db.mail_queue.replyto_addresses,
            # db.mail_queue.user_id,
            db.mail_queue.mail_subject,
            db.mail_queue.mail_template_hashtag,
            db.mail_queue.article_id,
        ],
        links=links,
        links_placement="left",
        _class="web2py_grid action-button-absolute",
    )

    return dict(
        titleIcon="send",
        pageTitle=getTitle(request, auth, db, "#RecommenderReviewEmailsTitle"),
        customText=getText(request, auth, db, "#RecommenderReviewEmailsText"),
        pageHelp=getHelp(request, auth, db, "#RecommenderReviewEmails"),
        myBackButton=common_small_html.mkBackButton(target=URL(c="manager", f="suggested_recommenders", vars=dict(articleId=articleId), user_signature=True)),
        grid=grid,
        myFinalScript=myScript,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


@auth.requires(auth.has_membership(role="manager"))
def article_emails():
    response.view = "default/myLayout.html"

    articleId = request.vars["articleId"]
    article = db.t_articles[articleId]

    db.mail_queue.sending_status.represent = lambda text, row: DIV(
        SPAN(admin_module.makeMailStatusDiv(text)),
        SPAN(I(T("Sending attempts : ")), B(row.sending_attempts), _style="font-size: 12px; margin-top: 5px"),
        _class="pci2-flex-column",
        _style="margin: 5px 10px;",
    )

    db.mail_queue.id.readable = False
    db.mail_queue.sending_attempts.readable = False

    db.mail_queue.sending_date.represent = lambda text, row: datetime.datetime.strptime(str(text), "%Y-%m-%d %H:%M:%S")
    db.mail_queue.mail_content.represent = lambda text, row: XML(admin_module.sanitizeHtmlContent(text))
    db.mail_queue.mail_subject.represent = lambda text, row: B(text)
    db.mail_queue.article_id.represent = lambda art_id, row: DIV(common_small_html.mkRepresentArticleLightLinked(auth, db, art_id))
    db.mail_queue.mail_subject.represent = lambda text, row: DIV(B(text), BR(), SPAN(row.mail_template_hashtag), _class="ellipsis-over-500")
    db.mail_queue.cc_mail_addresses.widget = app_forms.cc_widget
    db.mail_queue.replyto_addresses.widget = app_forms.cc_widget
    db.mail_queue.bcc_mail_addresses.widget = app_forms.cc_widget

    db.mail_queue.sending_status.writable = False
    db.mail_queue.sending_attempts.writable = False
    db.mail_queue.dest_mail_address.writable = False
    db.mail_queue.user_id.writable = False
    db.mail_queue.mail_template_hashtag.writable = False
    db.mail_queue.reminder_count.writable = False
    db.mail_queue.article_id.writable = False
    db.mail_queue.recommendation_id.writable = False

    db.mail_queue.removed_from_queue.writable = False
    db.mail_queue.removed_from_queue.readable = False

    if len(request.args) > 2 and request.args[0] == "edit":
        db.mail_queue.mail_template_hashtag.readable = True
    else:
        db.mail_queue.mail_template_hashtag.readable = False

    links = [
        dict(
            header="",
            body=lambda row: A(
                (T("Scheduled") if row.removed_from_queue == False else T("Unscheduled")),
                _href=URL(c="admin_actions", f="toggle_shedule_mail_from_queue", vars=dict(emailId=row.id)),
                _class="btn btn-default",
                _style=("background-color: #3e3f3a;" if row.removed_from_queue == False else "background-color: #ce4f0c;"),
            )
            if row.sending_status == "pending"
            else "",
        )
    ]

    myScript = common_tools.get_script("replace_mail_content.js")

    grid = SQLFORM.grid(
        ((db.mail_queue.article_id == articleId)),
        details=True,
        editable=lambda row: (row.sending_status == "pending"),
        deletable=lambda row: (row.sending_status == "pending"),
        create=False,
        searchable=False,
        csv=False,
        paginate=50,
        maxtextlength=256,
        orderby=~db.mail_queue.id,
        onvalidation=mail_form_processing,
        fields=[
            db.mail_queue.sending_status,
            db.mail_queue.removed_from_queue,
            db.mail_queue.sending_date,
            db.mail_queue.sending_attempts,
            db.mail_queue.dest_mail_address,
            #db.mail_queue.cc_mail_addresses,
            #db.mail_queue.replyto_addresses,
            # db.mail_queue.user_id,
            db.mail_queue.mail_subject,
            db.mail_queue.mail_template_hashtag,
            db.mail_queue.article_id,
        ],
        links=links,
        links_placement="left",
        _class="web2py_grid action-button-absolute",
    )

    return dict(
        titleIcon="send",
        pageTitle=getTitle(request, auth, db, "#ArticleEmailsTitle"),
        customText=getText(request, auth, db, "#ArticleEmailsText"),
        pageHelp=getHelp(request, auth, db, "#ArticleEmails"),
        myBackButton=common_small_html.mkBackButton(),
        grid=grid,
        myFinalScript=myScript,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


def mail_form_processing(form):
    app_forms.update_mail_content_keep_editing_form(form, db, request, response)

@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="recommender"))
def send_submitter_generic_mail():
    response.view = "default/myLayout.html"

    def fail(message):
        session.flash = T(message)
        referrer = request.env.http_referer
        redirect(referrer if referrer else URL("default", "index"))

    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    recomm = db.get_last_recomm(art)
    if art is None:
        fail("no article for review")
    author = db.auth_user[art.user_id]
    if author is None:
        fail("no author for article")

    template = "#SubmitterGenericMail"
    if "revise_scheduled_submission" in request.args:
        template = "#SubmitterScheduledSubmissionDeskRevisionsRequired" 
        sched_sub_vars = emailing_vars.getPCiRRScheduledSubmissionsVars(art)
        scheduledSubmissionLatestReviewStartDate = sched_sub_vars["scheduledSubmissionLatestReviewStartDate"]
        scheduledReviewDueDate = sched_sub_vars["scheduledReviewDueDate"]
        recommenderName = common_small_html.mkUser(auth, db, recomm.recommender_id)

    description = myconf.take("app.description")
    longname = myconf.take("app.longname")
    appName = myconf.take("app.name")
    contact = myconf.take("contacts.managers")

    sender_email = db(db.auth_user.id == auth.user_id).select().last().email

    mail_template = emailing_tools.getMailTemplateHashtag(db, template)

    # template variables, along with all other locals()
    destPerson = common_small_html.mkUser(auth, db, art.user_id)
    articleDoi = common_small_html.mkLinkDOI(art.doi)
    articleTitle = md_to_html(art.title)
    articleAuthors = emailing.mkAuthors(art)

    default_subject = emailing_tools.replaceMailVars(mail_template["subject"], locals())
    default_message = emailing_tools.replaceMailVars(mail_template["content"], locals())

    default_subject = emailing.patch_email_subject(default_subject, articleId)

    req_is_email = IS_EMAIL(error_message=T("invalid e-mail!"))
    replyto = db(db.auth_user.id == auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()

    replyTo = ", ".join([replyto.email, contact])

    form = SQLFORM.factory(
        Field("author_email", label=T("Author email address"), type="string", length=250, requires=req_is_email, default=author.email, writable=False),
        Field.CC(default=(sender_email, contact)),
        Field("replyto", label=T("Reply-to"), type="string", length=250, default=replyTo, writable=False),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )
    form.element(_type="submit")["_value"] = T("Send email")
    form.element("textarea[name=message]")["_style"] = "height:500px;"

    if form.process().accepted:
        if pciRRactivated:
            art.request_submission_change = True
            art.update_record()
        request.vars["replyto"] = replyTo
        try:
            emailing.send_submitter_generic_mail(session, auth, db, author.email, art.id, request.vars, template)
        except Exception as e:
            session.flash = (session.flash or "") + T("Email failed.")
            raise e
        if auth.has_membership(role="recommender"):
            if "Revision" in template:
                art.update_record(status="Scheduled submission revision")
            redirect(URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False)))
        else:
            redirectt(URL(c="manager", f="presubmissions"))

    return dict(
        form=form,
        pageHelp=getHelp(request, auth, db, "#EmailForSubmitter"),
        titleIcon="envelope",
        pageTitle=getTitle(request, auth, db, "#EmailForSubmitterInfoTitle"),
        customText=getText(request, auth, db, "#EmailForSubmitterInfo"),
        myBackButton=common_small_html.mkBackButton(),
    )
