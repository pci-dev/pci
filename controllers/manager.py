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


myconf = AppConfig(reload=True)

# frequently used constants
from app_modules.emailing import MAIL_HTML_LAYOUT, MAIL_DELAY

csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get("config.trgm_limit") or 0.4
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
not_considered_delay_in_days = myconf.get("config.unconsider_limit_days", default=20)


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
    resu = _manage_articles(["Pending", "Pre-recommended", "Pre-revision", "Pre-rejected"], URL("manager", "pending_articles", host=host, scheme=scheme, port=port))
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
    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(auth, db, text)
    db.t_articles.status.writable = True
    db.t_articles.cover_letter.readable = True
    db.t_articles.cover_letter.writable = False
    db.t_articles.keywords.readable = False
    db.t_articles.keywords.writable = False
    db.t_articles.auto_nb_recommendations.readable = False
    db.t_articles.auto_nb_recommendations.writable = False
    db.t_articles._id.represent = lambda text, row: DIV(common_small_html.mkRepresentArticleLight(auth, db, text), _class="pci-w200Cell")
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
                    SPAN(current.T("Check & Edit")),
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
        _class="web2py_grid action-button-absolute"
    )

    absoluteButtonScript = SCRIPT(common_tools.get_template("script", "action_button_absolute.js"), _type="text/javascript")

    return dict(customText=getText(request, auth, db, "#ManagerArticlesText"), pageTitle=getTitle(request, auth, db, "#ManagerArticlesTitle"), grid=grid, myFinalScript=absoluteButtonScript)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def suggested_recommender_emails():
    response.view = "default/info.html"

    srId = request.vars["srId"]
    sr = db.t_suggested_recommenders[srId]
    if sr is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    myContents = DIV()
    myContents.append(SPAN(B(T("Suggested recommender: ")), common_small_html.mkUserWithMail(auth, db, sr.suggested_recommender_id)))
    myContents.append(H2(T("Emails:")))
    myContents.append(DIV(XML((sr.emailing or "<b>None yet</b>")), _style="margin-left:20px; border-left:1px solid #cccccc; padding-left:4px;"))
    return dict(
        pageHelp=getHelp(request, auth, db, "#ManagerSuggestedRecommenderEmails"),
        customText=getText(request, auth, db, "#ManagerSuggestedRecommenderEmailsText"),
        titleIcon="envelope",
        pageTitle=getTitle(request, auth, db, "#ManagerSuggestedRecommenderEmailsTitle"),
        myBackButton=common_small_html.mkBackButton(),
        message=myContents,
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
        myContents = ongoing_recommendation.getRecommendationProcess(auth, db, response, art, printable, quiet=False)

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
        myBackButton=common_small_html.mkBackButton()
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
                (db.v_recommendation_contributors[(row.get("t_recommendations") or row).id]).contributors or "ADD",
                _href=URL(c="recommender", f="contributions", vars=dict(recommId=(row.get("t_recommendations") or row).id)),
            ),
        )
    ]
    if not (art.already_published):
        links += [
            dict(
                header=T("Reviews"),
                body=lambda row: A(
                    (db.v_reviewers[(row.get("t_recommendations") or row).id]).reviewers or "ADD",
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
            db.t_recommendations.id,
            db.t_recommendations.doi,
            db.t_recommendations.ms_version,
            db.t_recommendations.recommendation_timestamp,
            db.t_recommendations.last_change,
            db.t_recommendations.recommendation_state,
            db.t_recommendations.is_closed,
            db.t_recommendations.recommender_id,
            db.t_recommendations.recommendation_comments,
            db.t_recommendations.reply,
            db.t_recommendations.reply_pdf,
            db.t_recommendations.track_change,
            db.t_recommendations.recommender_file,
            db.t_pdf.pdf,
        ],
        links=links,
        orderby=~db.t_recommendations.recommendation_timestamp,
    )
    if grid.element(_title="Add record to database"):
        grid.element(_title="Add record to database")[0] = T("Manually add new round")
        grid.element(_title="Add record to database")["_title"] = T("Manually add new round of recommendation. Expert use!!")
    myContents = DIV(DIV(article_components.getArticleInfosCard(auth, db, response, art, False, False), _class="pci2-content-900px"), _class="pci2-full-width pci2-flex-center")

    return dict(
        # myBackButton = common_small_html.mkBackButton(),
        pageHelp=getHelp(request, auth, db, "#ManageRecommendations"),
        customText=getText(request, auth, db, "#ManageRecommendationsText"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#ManageRecommendationsTitle"),
        content=myContents,
        grid=grid,
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
            Field("email", type="string", length=512, label=T("email")),
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
    db.t_suggested_recommenders._id.readable = False
    db.t_suggested_recommenders.email_sent.readable = False
    db.t_suggested_recommenders.suggested_recommender_id.represent = lambda text, row: common_small_html.mkUserWithMail(auth, db, text)
    db.t_suggested_recommenders.emailing.readable = True
    if len(request.args) == 0:  # we are in grid
        db.t_suggested_recommenders.emailing.represent = lambda text, row: DIV(XML(text), _class="pci-emailingTD") if text else ""
    else:
        db.t_suggested_recommenders.emailing.represent = lambda text, row: XML(text) if text else ""
    links = []
    if art.status == "Awaiting consideration":
        links.append(
            dict(
                header="",
                body=lambda row: A(
                    T("Prepare a reminder"), _class="btn btn-info pci-manager", _href=URL(c="manager_actions", f="send_suggested_recommender_reminder", vars=dict(suggRecommId=row.id))
                )
                if not (row.declined)
                else "",
            )
        )

    addSuggestedRecommendersButton = A(current.T("Add suggested recommender"), _class="btn btn-default pci-manager", _href=URL(c="manager", f="search_recommenders", vars=request.vars, user_signature=True))

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
            db.t_suggested_recommenders.suggested_recommender_id,
            db.t_suggested_recommenders.declined,
            db.t_suggested_recommenders.email_sent,
            db.t_suggested_recommenders.emailing,
        ],
        field_id=db.t_suggested_recommenders.id,
        links=links,
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
def email_article_to_recommenders():
    response.view = "default/myLayout.html"

    if "articleId" in request.vars and request.vars["articleId"]:
        articleId = request.vars["articleId"]
        art = db.t_articles[articleId]
    if "ids" in request.vars and request.vars["ids"]:
        ids = request.vars["ids"]
    if "comeback" in request.vars and request.vars["comeback"]:
        comeback = request.vars["comeback"]

    if art is None or ids is None or len(ids) == 0:
        raise HTTP(404, "404: " + T("Unavailable"))
    else:
        scheme = myconf.take("alerts.scheme")
        host = myconf.take("alerts.host")
        port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
        site_url = URL(c="default", f="index", scheme=scheme, host=host, port=port)
        description = myconf.take("app.description")
        longname = myconf.take("app.longname")
        contact = myconf.take("contacts.managers")
        art_authors = art.authors
        art_title = art.title
        art_doi = art.doi
        linkTarget = URL(c="recommender", f="article_details", vars=dict(articleId=art.id), scheme=scheme, host=host, port=port)
        linkHelp = URL(c="help", f="help_generic", scheme=scheme, host=host, port=port)
        default_subject = "%(longname)s: Preprint available for recommenders" % locals()
        default_message = common_tools.get_template("text", "default_preprint_avalaible_for_recommenders.txt") % locals()

    report = []
    selRec = []
    for rid in ids:
        selRec.append(LI(common_small_html.mkUserWithMail(auth, db, rid)))
    myContents = DIV(H3(T("To each selected recommender:")), UL(selRec), _style="margin-left:400px;")
    form = SQLFORM.factory(
        # Field('replyto', label=T('Reply-to'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default=replyto_address, writable=False),
        # Field('bcc', label=T('BCC'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default='%s, %s'%(replyto.email, contact), writable=False),
        # Field('reviewer_email', label=T('Reviewer email address'), type='string', length=250, default=reviewer.email, writable=False, requires=IS_EMAIL(error_message=T('invalid email!'))),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )
    form.element(_type="submit")["_value"] = T("Send email so selected recommenders")
    form.element("textarea[name=message]")["_style"] = "height:550px;"

    if form.process().accepted:
        response.flash = None
        mySubject = request.vars["subject"]
        myContent = request.vars["message"]
        myMessage = render(filename=MAIL_HTML_LAYOUT, context=dict(content=XML(WIKI(myContent)), footer=mkFooter()))
        for rid in ids:
            destPerson = common_small_html.mkUserWithMail(auth, db, rid)
            destAddress = db.auth_user[rid].email
            mail_resu = False
            try:
                mail_resu = mail.send(to=[destAddress], cc=contact, subject=mySubject, message=myMessage)
            except:
                pass
            if mail_resu:
                report.append("email sent to %s" % destPerson.flatten())
            else:
                report.append("email NOT SENT to %s" % destPerson.flatten())
            time.sleep(MAIL_DELAY)

        print("\n".join(report))
        if session.flash is None:
            session.flash = "; ".join(report)
        else:
            session.flash += "; " + "; ".join(report)
        if comeback:
            redirect(comeback)
        else:
            redirect(request.env.http_referer)

    return dict(
        content=myContents,
        form=form,
        pageHelp=getHelp(request, auth, db, "#EmailToWarnRecommendersHelp"),
        titleIcon="envelope",
        pageTitle=getTitle(request, auth, db, "#EmailToWarnRecommendersTitle"),
        customText=getText(request, auth, db, "#EmailToWarnRecommendersInfoText"),
        myBackButton=common_small_html.mkBackButton(),
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
                header=T("Actions"), body=lambda row: DIV(manager_module.mkViewEditRecommendationsManagerButton(auth, db, row.t_recommendations if "t_recommendations" in row else row))
            ),
        ]
        db.t_recommendations.article_id.label = T("Preprint")

    db.t_recommendations.recommender_id.writable = False
    db.t_recommendations.doi.writable = False
    # db.t_recommendations.article_id.readable = False
    db.t_recommendations.article_id.writable = False
    db.t_recommendations._id.readable = False
    # db.t_recommendations._id.represent = lambda rId, row: common_small_html.mkArticleCellNoRecommFromId(auth, db, rId)
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
    db.t_recommendations.article_id.represent = lambda aid, row: DIV(common_small_html.mkArticleCellNoRecomm(auth, db, db.t_articles[aid]), _class="pci-w200Cell")
    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(auth, db, text)
    db.t_recommendations.doi.readable = False
    db.t_recommendations.last_change.readable = True
    db.t_recommendations.recommendation_comments.represent = lambda text, row: DIV(WIKI(text or ""), _class="pci-div4wiki")
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
        _class="web2py_grid action-button-absolute"
    )

    absoluteButtonScript = SCRIPT(common_tools.get_template("script", "action_button_absolute.js"), _type="text/javascript")

    return dict(
        # myBackButton=common_small_html.mkBackButton(),
        pageHelp=getHelp(request, auth, db, "#AdminAllRecommendations"),
        titleIcon="education",
        pageTitle=pageTitle,
        customText=customText,
        grid=grid,
        myFinalScript=absoluteButtonScript
    )

