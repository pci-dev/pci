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

from app_components import app_forms

from app_components import article_components
from app_components import ongoing_recommendation
from app_components import recommender_components

from app_modules import common_tools
from app_modules import common_small_html

from controller_modules import admin_module

# frequently used constants
from app_modules.emailing import MAIL_HTML_LAYOUT, MAIL_DELAY

myconf = AppConfig(reload=True)

csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get("config.trgm_limit") or 0.4
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
not_considered_delay_in_days = myconf.get("config.unconsider_limit_days", default=20)

pciRRactivated = myconf.get("config.registered_reports", default=False)


######################################################################################################################################################################
## Menu Routes
######################################################################################################################################################################
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
@auth.requires(auth.has_membership(role="manager"))
def pending_articles():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    resu = _manage_articles(
        ["Pending", "Pre-recommended", "Pre-revision", "Pre-rejected", "Pre-recommended-private"], URL("manager", "pending_articles", host=host, scheme=scheme, port=port)
    )
    resu["customText"] = getText(request, auth, db, "#ManagerPendingArticlesText")
    resu["titleIcon"] = "time"
    resu["pageTitle"] = getTitle(request, auth, db, "#ManagerPendingArticlesTitle")
    resu["pageHelp"] = getHelp(request, auth, db, "#ManagePendingValidations")
    return resu


######################################################################################################################################################################
# Display ongoing articles and allow management
@auth.requires(auth.has_membership(role="manager"))
def ongoing_articles():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    resu = _manage_articles(["Awaiting consideration", "Under consideration", "Awaiting revision"], URL("manager", "ongoing_articles", host=host, scheme=scheme, port=port))
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
@auth.requires(auth.has_membership(role="manager"))
def _manage_articles(statuses, whatNext):
    response.view = "default/myLayout.html"

    if statuses:
        query = db.t_articles.status.belongs(statuses)
    else:
        query = db.t_articles

    db.t_articles.user_id.default = auth.user_id
    db.t_articles.user_id.writable = False
    db.t_articles.anonymous_submission.readable = False
    db.t_articles.user_id.represent = lambda text, row: SPAN(
        DIV(common_small_html.mkAnonymousArticleField(auth, db, row.anonymous_submission, "")), common_small_html.mkUserWithMail(auth, db, text)
    )

    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.art_stage_1_id.writable = False

    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(auth, db, text, showStage=pciRRactivated, stage1Id=row.art_stage_1_id)
    db.t_articles.status.writable = True
    db.t_articles.cover_letter.readable = True
    db.t_articles.cover_letter.writable = False
    db.t_articles.keywords.readable = False
    db.t_articles.keywords.writable = False
    db.t_articles.auto_nb_recommendations.readable = False
    db.t_articles.auto_nb_recommendations.writable = False
    db.t_articles._id.represent = lambda text, row: DIV(common_small_html.mkRepresentArticleLight(auth, db, text), _class="pci-w300Cell")
    db.t_articles._id.label = T("Article")
    db.t_articles.upload_timestamp.represent = lambda text, row: common_small_html.mkLastChange(row.upload_timestamp)
    db.t_articles.upload_timestamp.label = T("Submission date")
    db.t_articles.last_status_change.represent = lambda text, row: common_small_html.mkLastChange(row.last_status_change)
    db.t_articles.already_published.readable = False

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

    links = [
        dict(header=T("Recommenders"), body=lambda row: manager_module.mkRecommenderButton(row, auth, db)),
        # dict(header=T("Recommendation title"), body=lambda row: manager_module.mkLastRecommendation(auth, db, row.id)),
        dict(
            header=T("Actions"),
            body=lambda row: DIV(
                A(
                    SPAN(current.T("View / Edit")),
                    _href=URL(c="manager", f="recommendations", vars=dict(articleId=row.id), user_signature=True),
                    _class="buttontext btn btn-default pci-button pci-manager",
                    _title=current.T("View and/or edit review"),
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
    if parallelSubmissionAllowed:
        fields = [
            db.t_articles.art_stage_1_id,
            db.t_articles.last_status_change,
            db.t_articles.status,
            # db.t_articles.uploaded_picture,
            db.t_articles._id,
            db.t_articles.upload_timestamp,
            db.t_articles.already_published,
            # db.t_articles.parallel_submission,
            db.t_articles.auto_nb_recommendations,
            db.t_articles.user_id,
            # db.t_articles.thematics,
            db.t_articles.keywords,
            db.t_articles.anonymous_submission,
        ]
    else:
        fields = [
            db.t_articles.art_stage_1_id,
            db.t_articles.last_status_change,
            db.t_articles.status,
            # db.t_articles.uploaded_picture,
            db.t_articles._id,
            db.t_articles.upload_timestamp,
            db.t_articles.already_published,
            db.t_articles.auto_nb_recommendations,
            db.t_articles.user_id,
            # db.t_articles.thematics,
            db.t_articles.keywords,
            db.t_articles.anonymous_submission,
        ]

    grid = SQLFORM.grid(
        query,
        details=False,
        editable=False,
        deletable=False,
        create=False,
        searchable=True,
        maxtextlength=250,
        paginate=20,
        csv=csv,
        exportclasses=expClass,
        fields=fields,
        links=links,
        orderby=~db.t_articles.last_status_change,
        _class="web2py_grid action-button-absolute",
    )

    return dict(
        customText=getText(request, auth, db, "#ManagerArticlesText"),
        pageTitle=getTitle(request, auth, db, "#ManagerArticlesTitle"),
        grid=grid,
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "action_button_absolute.js"), _type="text/javascript"),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
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

    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        session.flash = T("Unavailable")
        redirect(request.env.http_referer)

    query = db.t_recommendations.article_id == articleId
    db.t_recommendations.recommender_id.default = auth.user_id
    db.t_recommendations.article_id.default = articleId
    db.t_recommendations.article_id.writable = False
    db.t_recommendations.last_change.writable = False
    db.t_recommendations.doi.represent = lambda text, row: common_small_html.mkDOI(text)
    db.t_pdf.pdf.represent = lambda text, row: A(IMG(_src=URL("static", "images/application-pdf.png")), _href=URL("default", "download", args=text)) if text else ""
    db.t_recommendations._id.readable = True
    if len(request.args) == 0:  # in grid
        db.t_recommendations.recommender_id.represent = lambda id, row: common_small_html.mkUserWithMail(auth, db, id)
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
    if not (art.already_published):
        links += [
            dict(
                header=T("Reviews"),
                body=lambda row: A(
                    (db.v_reviewers[(row.get("t_recommendations") or row).id]).reviewers or "ADD REVIEWER",
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
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "web2py_button_absolute.js"), _type="text/javascript"),
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
            excludeList += myValue.split(",")

    whatNext = request.vars["whatNext"]
    articleId = request.vars["articleId"]
    if articleId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        # We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
        temp_db = DAL("sqlite:memory")
        qy_recomm = temp_db.define_table(
            "qy_recomm",
            Field("id", type="integer"),
            Field("num", type="integer"),
            Field("score", type="double", label=T("Score"), default=0),
            Field("first_name", type="string", length=128, label=T("First name")),
            Field("last_name", type="string", length=128, label=T("Last name")),
            Field("email", type="string", length=512, label=T("e-mail")),
            Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
            Field("city", type="string", label=T("City"), represent=lambda t, r: t if t else ""),
            Field("country", type="string", label=T("Country"), represent=lambda t, r: t if t else ""),
            Field("laboratory", type="string", label=T("Department"), represent=lambda t, r: t if t else ""),
            Field("institution", type="string", label=T("Institution"), represent=lambda t, r: t if t else ""),
            Field("thematics", type="list:string", label=T("Thematic fields")),
            Field("excluded", type="boolean", label=T("Excluded")),
        )
        temp_db.qy_recomm.email.represent = lambda text, row: A(text, _href="mailto:" + text)
        qyKwArr = qyKw.split(" ")

        searchForm = app_forms.searchByThematic(auth, db, myVars)

        if searchForm.process(keepvalues=True).accepted:
            response.flash = None
        else:
            qyTF = []
            for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
                qyTF.append(thema.keyword)

        excludeList = [int(numeric_string) for numeric_string in excludeList]
        filtered = db.executesql("SELECT * FROM search_recommenders(%s, %s, %s);", placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
        for fr in filtered:
            qy_recomm.insert(**fr)

        links = [
            dict(header=T("Days since last recommendation"), body=lambda row: db.v_last_recommendation[row.id].days_since_last_recommendation),
            dict(
                header="",
                body=lambda row: ""
                if row.excluded
                else A(
                    SPAN(current.T("Suggest"), _class="btn btn-default pci-manager"),
                    _href=URL(c="manager_actions", f="suggest_article_to", vars=dict(articleId=articleId, recommenderId=row["id"], whatNext=whatNext), user_signature=True),
                    _class="button",
                ),
            ),
        ]
        temp_db.qy_recomm._id.readable = False
        temp_db.qy_recomm.uploaded_picture.readable = False
        temp_db.qy_recomm.num.readable = False
        temp_db.qy_recomm.score.readable = False
        temp_db.qy_recomm.excluded.readable = False
        grid = SQLFORM.grid(
            qy_recomm,
            editable=False,
            deletable=False,
            create=False,
            details=False,
            searchable=False,
            maxtextlength=250,
            paginate=1000,
            csv=csv,
            exportclasses=expClass,
            fields=[
                temp_db.qy_recomm.num,
                temp_db.qy_recomm.score,
                temp_db.qy_recomm.uploaded_picture,
                temp_db.qy_recomm.first_name,
                temp_db.qy_recomm.last_name,
                temp_db.qy_recomm.email,
                temp_db.qy_recomm.laboratory,
                temp_db.qy_recomm.institution,
                temp_db.qy_recomm.city,
                temp_db.qy_recomm.country,
                temp_db.qy_recomm.thematics,
                temp_db.qy_recomm.excluded,
            ],
            links=links,
            orderby=temp_db.qy_recomm.num,
            args=request.args,
        )

        response.view = "default/gab_list_layout.html"
        return dict(
            titleIcon="search",
            pageTitle=getTitle(request, auth, db, "#ManagerSearchRecommendersTitle"),
            pageHelp=getHelp(request, auth, db, "#ManagerSearchRecommenders"),
            customText=getText(request, auth, db, "#ManagerSearchRecommendersText"),
            myBackButton=common_small_html.mkBackButton(),
            searchForm=searchForm,
            grid=grid,
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
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "web2py_button_absolute.js"), _type="text/javascript"),
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

    if pciRRactivated:
        havingStage2Articles = db(db.t_articles.art_stage_1_id == articleId).count() > 0
        db.t_articles.cover_letter.readable = True
        db.t_articles.cover_letter.writable = True

        if not havingStage2Articles:
            db.t_articles.art_stage_1_id.requires = IS_EMPTY_OR(
                IS_IN_DB(db((db.t_articles.user_id == art.user_id) & (db.t_articles.art_stage_1_id == None) & (db.t_articles.id != art.id)), "t_articles.id", "%(title)s")
            )
            myFinalScript = SCRIPT(
                """
                    document.querySelector("#t_articles_art_stage_1_id option[value='']").innerHTML = "This is a stage 1 submission"
                """
            )
        else:
            db.t_articles.art_stage_1_id.requires = IS_EMPTY_OR([])
            myFinalScript = SCRIPT(
                """
                    document.querySelector("#t_articles_art_stage_1_id").value = "This is a stage 1 submission";
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
        db.t_articles.art_stage_1_id.readable = False
        db.t_articles.art_stage_1_id.writable = False

    form = SQLFORM(db.t_articles, articleId, upload=URL("default", "download"), deletable=True, showid=True)

    if form.process().accepted:
        response.flash = T("Article saved", lazy=False)
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
@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
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
            db.t_recommendations.last_change,
            # db.t_articles.status,
            db.t_recommendations._id,
            db.t_recommendations.article_id,
            db.t_recommendations.doi,
            # db.t_recommendations.recommendation_timestamp,
            db.t_recommendations.is_closed,
        ]
        links = [
            dict(header=T("Co-recommenders"), body=lambda row: common_small_html.mkCoRecommenders(auth, db, row.t_recommendations if "t_recommendations" in row else row, goBack)),
            dict(
                header=T(""), body=lambda row: common_small_html.mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if "t_recommendations" in row else row)
            ),
        ]
        db.t_recommendations.article_id.label = T("Postprint")
    else:  ## NOTE: PRE-PRINTS
        query = (db.t_recommendations.article_id == db.t_articles.id) & (db.t_articles.already_published == False) & (db.t_articles.status == "Under consideration")
        pageTitle = getTitle(request, auth, db, "#AdminAllRecommendationsPreprintTitle")
        customText = getText(request, auth, db, "#AdminAllRecommendationsPreprintText")
        fields = [
            db.t_articles.scheduled_submission_date,
            db.t_articles.art_stage_1_id,
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
        ]
        links = [
            dict(header=T("Co-recommenders"), body=lambda row: common_small_html.mkCoRecommenders(auth, db, row.t_recommendations if "t_recommendations" in row else row, goBack)),
            dict(header=T("Reviews"), body=lambda row: recommender_components.getReviewsSubTable(auth, db, response, row.t_recommendations if "t_recommendations" in row else row)),
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
    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(auth, db, text, showStage=pciRRactivated, stage1Id=row.art_stage_1_id)
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
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "action_button_absolute.js"), _type="text/javascript"),
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

    db.mail_queue.sending_status.writable = False
    db.mail_queue.sending_attempts.writable = False
    db.mail_queue.dest_mail_address.writable = False
    db.mail_queue.cc_mail_addresses.writable = False
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
                (T("Sheduled") if row.removed_from_queue == False else T("Unsheduled")),
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
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "web2py_button_absolute.js"), _type="text/javascript"),
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
    db.mail_queue.mail_subject.represent = lambda text, row: DIV(B(text), BR(), SPAN(row.mail_template_hashtag), _class="ellipsis-over-350")

    db.mail_queue.sending_status.writable = False
    db.mail_queue.sending_attempts.writable = False
    db.mail_queue.dest_mail_address.writable = False
    db.mail_queue.cc_mail_addresses.writable = False
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
                (T("Sheduled") if row.removed_from_queue == False else T("Unsheduled")),
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
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "web2py_button_absolute.js"), _type="text/javascript"),
    )


def mail_form_processing(form):
    form.errors = True
    mail = db.mail_queue[request.vars.id]

    content_saved = False
    try:
        content_begin = mail.mail_content.rindex("<!-- CONTENT START -->") + 22
        content_end = mail.mail_content.rindex("<!-- CONTENT END -->")

        new_content = mail.mail_content[0:content_begin]
        new_content += form.vars.mail_content
        new_content += mail.mail_content[content_end:-1]

        mail.mail_content = new_content
        mail.mail_subject = form.vars.mail_subject
        mail.sending_date = form.vars.sending_date
        mail.update_record()

        content_saved = True
    except:
        print("Error")

    if content_saved:
        args = request.args
        args[0] = "view"
        session.flash = T("Reminder saved")
