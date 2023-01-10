# -*- coding: utf-8 -*-

import re
import copy
import tempfile
import datetime
from datetime import timedelta
import glob
import os

# sudo pip install tweepy
# import tweepy

import codecs

# import html2text
from gluon.contrib.markdown import WIKI

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

from app_modules.common_small_html import md_to_html

from controller_modules import admin_module


myconf = AppConfig(reload=True)

csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
not_considered_delay_in_days = myconf.get("config.unconsider_limit_days", default=20)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()
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
    if is_recommender(auth, request):
        states = ["Scheduled submission pending"]
    else:
        states = ["Pending", "Pre-recommended", "Pre-revision", "Pre-rejected", "Pre-recommended-private", "Scheduled submission pending"]


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
    resu = _manage_articles(["Awaiting consideration", "Under consideration", "Awaiting revision", "Scheduled submission under consideration"], URL("manager", "ongoing_articles", host=host, scheme=scheme, port=port))
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

    if statuses:
        query = db.t_articles.status.belongs(statuses)
    else:
        query = db.t_articles

    # recommenders only ever get here via menu "Recommender > Pending validation(s)"
    if pciRRactivated and is_recommender(auth, request):
        query = db.pending_scheduled_submissions_query

    def index_by(field, query): return { x[field]: x for x in db(query).select() }

    users = index_by("id", db.auth_user)
    last_recomms = db.executesql("select max(id) from t_recommendations group by article_id") if not statuses else \
                   db.executesql("select max(id) from t_recommendations where article_id in " +
                       "(select id from t_articles where status in ('" + "','".join(statuses) + "')) " +
                       "group by article_id")
    last_recomms = [x[0] for x in last_recomms]
    recomms = index_by("article_id", db.t_recommendations.id.belongs(last_recomms))
    co_recomms = db(db.t_press_reviews.recommendation_id.belongs(last_recomms)).select()

    # We use an in-memory table to add computed fields to the grid, so they are searchable
    _db = db
    db = DAL("sqlite:memory")

    t_articles = db.define_table(
        "t_articles",

        # original table fields required for display code below
        Field("status", type="string", label=T("Article status")),
        Field("last_status_change", type="datetime", label=T("Last status change")),
        Field("upload_timestamp", type="datetime"),
        Field("user_id", type="integer", readable=False),
        Field("art_stage_1_id", type="integer", readable=False),
        Field("report_stage", type="string", readable=False),
        Field("keywords", type="string", readable=False),
        Field("submitter_details", type="string", readable=False),
        Field("already_published", type="boolean", readable=False),
        Field("anonymous_submission", type="boolean", readable=False),
        Field("request_submission_change", type="boolean", readable=False),

        # original fields used in advanced search
        Field("title", type="string",),
        Field("authors", type="string",),

        # additional computed fields for plain-text search
        Field("submitter", type="string", label=T("Submitter"),
            represent=lambda txt, row: mkSubmitter(row),
        ),
        Field("recommenders", type="string", label=T("Recommenders"),
            represent=lambda txt, row: mkRecommenders(row),
        ),
    )

    def mkUser(user_details, user_id):
        return TAG(user_details) if user_details else common_small_html._mkUser(users.get(user_id))

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

    def mkSubmitter(row):
        return SPAN(
            DIV(common_small_html.mkAnonymousArticleField(None, None, row.anonymous_submission, "")),
            mkUser(row.submitter_details, row.user_id),
        )

    _ = _db.t_articles
    fields = [
            _.art_stage_1_id,
            _.report_stage,
            _.last_status_change,
            _.status,
            _._id,
            _.upload_timestamp,
            _.already_published,
            _.user_id,
            _.keywords,
            _.submitter_details,
            _.anonymous_submission,
            _.request_submission_change,
            _.title,
            _.authors,
    ]
    for row in _db(query).select(*fields):
        row['submitter'] = mkSubmitter(row).flatten()
        row['recommenders'] = mkRecommenders(row).flatten()
        t_articles.insert(**row)

    query = t_articles

    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(
        auth, _db, text, showStage=pciRRactivated, stage1Id=row.art_stage_1_id, reportStage=row.report_stage
    )

    db.t_articles.request_submission_change.represent = lambda text, row: T('YES') if row.request_submission_change == True else T("NO") 
    db.t_articles.request_submission_change.label = T('Changes requested?')
    db.t_articles._id.represent = lambda text, row: DIV(common_small_html.mkRepresentArticleLight(auth, _db, text), _class="pci-w300Cell")
    db.t_articles._id.label = T("Article")
    db.t_articles.upload_timestamp.represent = lambda text, row: common_small_html.mkLastChange(row.upload_timestamp)
    db.t_articles.upload_timestamp.label = T("Submission date")
    db.t_articles.last_status_change.represent = lambda text, row: common_small_html.mkLastChange(row.last_status_change)

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

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
                    SPAN(current.T('Set "Not')),
                    BR(),
                    SPAN(current.T('considered"')),
                    _href=URL(c="manager_actions", f="set_not_considered", vars=dict(articleId=row.id), user_signature=True),
                    _class="buttontext btn btn-danger pci-button pci-manager",
                    _title=current.T('Set this preprint as "Not considered"'),
                )
                if (
                    row.status == "Awaiting consideration"
                    and row.already_published is False
                    and datetime.datetime.now() - row.upload_timestamp > timedelta(days=not_considered_delay_in_days)
                )
                else "",
            ),
        ),
    ]
    fields = [
            db.t_articles.art_stage_1_id,
            db.t_articles.report_stage,
            db.t_articles.last_status_change,
            db.t_articles.status,
            db.t_articles._id,
            db.t_articles.upload_timestamp,
            db.t_articles.already_published,
            db.t_articles.user_id,
            db.t_articles.submitter,
            db.t_articles.keywords,
            db.t_articles.submitter_details,
            db.t_articles.recommenders,
            db.t_articles.anonymous_submission,
    ]
    if statuses is not None and "Pre-submission" in statuses:
        fields += [db.t_articles.request_submission_change]
        fields.pop(11) # .remove(t_articles.recommenders) won't work, for Field.__eq__


    original_grid = SQLFORM.grid(
        query,
        details=False,
        editable=False,
        deletable=False,
        create=False,
        searchable=dict(auth_user=True, auth_membership=False),
        maxtextlength=250,
        paginate=20,
        csv=csv,
        exportclasses=expClass,
        fields=fields,
        links=links,
        orderby=~db.t_articles.last_status_change,
        _class="web2py_grid action-button-absolute",
    )

    # options to be removed from the search dropdown:
    remove_options = ['t_articles.id', 't_articles.upload_timestamp',  't_articles.status',
                  't_articles.last_status_change', 't_status_article.status',
                  't_status_article.color_class', 't_status_article.explaination', 't_status_article.priority_level',
                  't_articles.has_manager_in_authors', 't_articles.picture_rights_ok',
                  't_articles.results_based_on_data', 't_articles.scripts_used_for_result',
                  't_articles.codes_used_in_study', 't_articles.validation_timestamp',
                  't_articles.user_id', 't_articles.request_submission_change', 't_articles.already_published',
                  't_articles.doi_of_published_article', 't_articles.is_searching_reviewers', 't_articles.report_stage',
                  't_articles.art_stage_1_id', 't_articles.record_url_version', 't_articles.sub_thematics',
                  't_articles.record_id_version']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'articles', remove_options)

    return dict(
        customText=getText(request, auth, _db, "#ManagerArticlesText"),
        pageTitle=getTitle(request, auth, _db, "#ManagerArticlesTitle"),
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or is_recommender(auth, request))
def recommendations():
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    printable = "printable" in request.vars and request.vars["printable"] == "True"

    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

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

    # New recommendation function (WIP)
    finalRecomm = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()
    recommHeaderHtml = article_components.getArticleInfosCard(auth, db, response, art, printable, True)
    recommStatusHeader = ongoing_recommendation.getRecommStatusHeader(auth, db, response, art, "manager", request, False, printable, quiet=False)
    recommTopButtons = ongoing_recommendation.getRecommendationTopButtons(auth, db, art, printable, quiet=False)

    if printable:
        printableClass = "printable"
        response.view = "default/wrapper_printable.html"
    else:
        printableClass = ""
        response.view = "default/wrapper_normal.html"

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
        return ", ".join([re.sub(r'<span><span>([^<]+)</span>.*', r'\1',
                            getReviewerDetails(review)) for review in reviews])

    def getReviewerDetails(review):
        return review.reviewer_details or (
                str(common_small_html.mkUserWithMail(auth, db, review.reviewer_id))
                    .replace("<span>?</span>", "?"))

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
        deleteFileButtonsScript=SCRIPT(common_tools.get_template("script", "add_delete_file_buttons_manager.js"), _type="text/javascript"),
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )



######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def search_recommenders():
    myVars = request.vars
    qyKw = ""
    qyTF = []
    excludeList = []
    articleId = None
    for myVar in myVars:
        if isinstance(myVars[myVar], list):
            myValue = (myVars[myVar])[1]
        else:
            myValue = myVars[myVar]
        if myVar == "qyKeywords":
            qyKw = myValue
        elif re.match("^qy_", myVar) and myValue == "on":
            qyTF.append(re.sub(r"^qy_", "", myVar))
        elif myVar == "exclude":
            myValue = myVars[myVar]
            myValue = myValue.split(",") if type(myValue) is str else myValue
            excludeList = list(map(int, myValue))

    whatNext = request.vars["whatNext"]
    articleId = request.vars["articleId"]
    if articleId is None:
        articleHeaderHtml = ""
    else:
        art = db.t_articles[articleId]
        articleHeaderHtml = article_components.getArticleInfosCard(auth, db, response, art, **article_components.for_search)
        excluded_recommenders = db(db.t_excluded_recommenders.article_id == art.id).select()
        for recommender in excluded_recommenders:
            excludeList.append(recommender.excluded_recommender_id)

    if True:
        # We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
        temp_db = DAL("sqlite:memory")
        qy_recomm = temp_db.define_table(
            "qy_recomm",
            Field("id", type="integer"),
            Field("num", type="integer"),
            Field("roles", type="string"),
            Field("score", type="double", label=T("Score"), default=0),
            Field("first_name", type="string", length=128, label=T("First name")),
            Field("last_name", type="string", length=128, label=T("Last name")),
            Field("email", type="string", length=512, label=T("e-mail")),
            Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
            Field("city", type="string", label=T("City"), represent=lambda t, r: t if t else ""),
            Field("country", type="string", label=T("Country"), represent=lambda t, r: t if t else ""),
            Field("laboratory", type="string", label=T("Department"), represent=lambda t, r: t if t else ""),
            Field("institution", type="string", label=T("Institution"), represent=lambda t, r: t if t else ""),
            Field("thematics", type="string", label=T("Thematic Fields"), requires=IS_IN_DB(db, db.t_thematics.keyword, zero=None)),
            Field("keywords", type="string", label=T("Keywords")),
            Field("expertise", type="string", label=T("Areas of expertise")),
            Field("excluded", type="boolean", label=T("Excluded")),
            Field("any", type="string", label=T("All fields")),
        )
        #temp_db.qy_recomm.email.represent = lambda text, row: A(text, _href="mailto:" + text)
        qyKwArr = qyKw.split(" ")

        #searchForm = app_forms.searchByThematic(auth, db, myVars)
        #if searchForm.process(keepvalues=True).accepted:
        #    response.flash = None
        #else:
        qyTF = []
        for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
            qyTF.append(thema.keyword)

        #excludeList = [int(numeric_string) for numeric_string in excludeList]
        filtered = db.executesql("SELECT * FROM search_recommenders(%s, %s, %s) WHERE country is not null;", placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)

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
            "keywords",
        ]

        users_ids = [ fr['id'] for fr in filtered ]
        keywords = { user.id: user.keywords for user in db(db.auth_user.id.belongs(users_ids)).select() }
        expertise = { user.id: user.cv for user in db(db.auth_user.id.belongs(users_ids)).select() }
        for fr in filtered:
            fr['keywords'] = keywords[fr['id']] or ""
            fr['expertise'] = expertise[fr['id']] or ""
            qy_recomm.insert(**fr, any=" ".join([str(fr[k]) if k in full_text_search_fields else "" for k in fr]))

        links = []
        if articleId:
            links += [
            dict(
                header="",
                body=lambda row: ""
                if row.excluded
                else A(
                    SPAN(current.T("Suggest as recommender"), _class="buttontext btn btn-default pci-submitter"),
                    _href=URL(c="manager_actions", f="suggest_article_to", vars=dict(articleId=articleId, recommenderId=row["id"], whatNext=whatNext), user_signature=True),
                    _class="button",
                ),
            ),
        ]
        #temp_db.qy_recomm._id.readable = False
        temp_db.qy_recomm.uploaded_picture.readable = False
        temp_db.qy_recomm.num.readable = False
        temp_db.qy_recomm.roles.readable = False
        temp_db.qy_recomm.score.readable = False
        temp_db.qy_recomm.excluded.readable = False
        selectable = None

        original_grid = SQLFORM.smartgrid(
            qy_recomm,
            editable=False,
            deletable=False,
            create=False,
            details=False,
            searchable=dict(auth_user=True, auth_membership=False),
            selectable=selectable,
            maxtextlength=250,
            paginate=1000,
            csv=csv,
            exportclasses=expClass,
            fields=[
                temp_db.qy_recomm._id,
                temp_db.qy_recomm.num,
                temp_db.qy_recomm.score,
                temp_db.qy_recomm.uploaded_picture,
                temp_db.qy_recomm.first_name,
                temp_db.qy_recomm.last_name,
                temp_db.qy_recomm.laboratory,
                temp_db.qy_recomm.institution,
                temp_db.qy_recomm.city,
                temp_db.qy_recomm.country,
                temp_db.qy_recomm.thematics,
                temp_db.qy_recomm.excluded,
            ],
            links=links,
            orderby=temp_db.qy_recomm.num,
            _class="web2py_grid action-button-absolute",
        )

        # options to be removed from the search dropdown:
        remove_options = ['qy_recomm.id']

        # the grid is adjusted after creation to adhere to our requirements
        grid = adjust_grid.adjust_grid_basic(original_grid, 'recommenders', remove_options)

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
@auth.requires(auth.has_membership(role="manager"))
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

        db.t_articles.preprint_server.readable = False
        db.t_articles.preprint_server.writable = False

        db.t_articles.results_based_on_data.readable = False
        db.t_articles.results_based_on_data.writable = False
        db.t_articles.data_doi.readable = False
        db.t_articles.data_doi.writable = False

        db.t_articles.scripts_used_for_result.readable = False
        db.t_articles.scripts_used_for_result.writable = False
        db.t_articles.scripts_doi.readable = False
        db.t_articles.scripts_doi.writable = False

        db.t_articles.codes_used_in_study.readable = False
        db.t_articles.codes_used_in_study.writable = False
        db.t_articles.codes_doi.readable = False
        db.t_articles.codes_doi.writable = False

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
            myFinalScript = SCRIPT(
                """
                    document.querySelector("#t_articles_art_stage_1_id").disabled = true;

                    var parent = document.querySelector("#t_articles_art_stage_1_id__row > div");
                    var text = document.createTextNode( "This article already have some related stages 2.");
                    var child = document.createElement('span');

                    child.style.color = "#fcc24d"
                    child.style.fontWeight = "bold"
                    child.style.fontStyle = "italic"

                    child.appendChild(text);
                    parent.appendChild(child);
                """
            )
    else:
        myFinalScript = SCRIPT(common_tools.get_template("script", "new_field_responsiveness.js"))
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
        redirect(URL(c="manager", f="recommendations", vars=dict(articleId=art.id), user_signature=True))
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
@auth.requires(auth.has_membership(role="manager"))
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

    myScript = common_tools.get_template("script", "fill_report_survey.js")
    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp(request, auth, db, "#ManagerReportSurvey"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#ManagerReportSurveyTitle"),
        customText=getText(request, auth, db, "#ManagerReportSurveyText", maxWidth="800"),
        form=form,
        myFinalScript=SCRIPT(myScript),
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
    if isPress:  ## NOTE: POST-PRINTS
        query = (db.t_recommendations.article_id == db.t_articles.id) & (db.t_articles.already_published == True)
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
        query = (db.t_recommendations.article_id == db.t_articles.id) & (db.t_articles.already_published == False) & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration")))
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

    grid = SQLFORM.grid(
        query,
        searchable=False,
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

    myScript = SCRIPT(common_tools.get_template("script", "replace_mail_content.js"), _type="text/javascript")

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

    myScript = SCRIPT(common_tools.get_template("script", "replace_mail_content.js"), _type="text/javascript")

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

@auth.requires(auth.has_membership(role="manager"))
def send_submitter_generic_mail():
    response.view = "default/myLayout.html"

    def fail(message):
        session.flash = T(message)
        referrer = request.env.http_referer
        redirect(referrer if referrer else URL("default", "index"))

    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        fail("no article for review")
    author = db.auth_user[art.user_id]
    if author is None:
        fail("no author for article")

    description = myconf.take("app.description")
    longname = myconf.take("app.longname")
    appName = myconf.take("app.name")
    contact = myconf.take("contacts.managers")

    sender_email = db(db.auth_user.id == auth.user_id).select().last().email

    mail_template = emailing_tools.getMailTemplateHashtag(db, "#SubmitterGenericMail")

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
            emailing.send_submitter_generic_mail(session, auth, db, author.email, art, request.vars)
        except Exception as e:
            session.flash = (session.flash or "") + T("Email failed.")
            raise e
        redirect(URL(c="manager", f="presubmissions"))

    return dict(
        form=form,
        pageHelp=getHelp(request, auth, db, "#EmailForSubmitter"),
        titleIcon="envelope",
        pageTitle=getTitle(request, auth, db, "#EmailForSubmitterInfoTitle"),
        customText=getText(request, auth, db, "#EmailForSubmitterInfo"),
        myBackButton=common_small_html.mkBackButton(),
    )
