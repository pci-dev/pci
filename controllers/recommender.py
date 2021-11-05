# -*- coding: utf-8 -*-

import time
import re
import copy
import datetime
from dateutil.relativedelta import *

from gluon.utils import web2py_uuid
from gluon.contrib.markdown import WIKI
from gluon.html import markmin_serializer

from app_modules.helper import *

from controller_modules import recommender_module

from app_components import app_forms

from app_components import article_components
from app_components import ongoing_recommendation
from app_components import recommender_components

from app_modules import common_tools
from app_modules import common_small_html
from app_modules import emailing_tools
from app_modules import emailing_vars

# to change to common
from controller_modules import admin_module


# frequently used constants
myconf = AppConfig(reload=True)
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
trgmLimit = myconf.take("config.trgm_limit") or 0.4

pciRRactivated = myconf.get("config.registered_reports", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

######################################################################################################################################################################
def index():
    return my_awaiting_articles()

# Common function for articles needing attention
@auth.requires(auth.has_membership(role="recommender"))
def fields_awaiting_articles():
    myVars = request.vars
    # We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
    temp_db = DAL("sqlite:memory")
    qy_art = temp_db.define_table(
        "qy_art",
        Field("id", type="integer"),
        Field("num", type="integer"),
        Field("score", type="double", label=T("Score"), default=0),
        Field("title", type="text", label=T("Title")),
        Field("authors", type="text", label=T("Authors")),
        Field("article_source", type="string", label=T("Source")),
        Field("doi", type="string", label=T("DOI")),
        Field("abstract", type="text", label=T("Abstract")),
        Field("upload_timestamp", type="datetime", default=request.now, label=T("Submission date")),
        Field("thematics", type="string", length=1024, label=T("Thematic fields")),
        Field("keywords", type="text", label=T("Keywords")),
        Field("auto_nb_recommendations", type="integer", label=T("Rounds of reviews"), default=0),
        Field("status", type="string", length=50, default="Pending", label=T("Status")),
        Field("last_status_change", type="datetime", default=request.now, label=T("Last status change")),
        Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
        Field("already_published", type="boolean", label=T("Postprint")),
        Field("anonymous_submission", type="boolean", label=T("Anonymous submission")),
        Field("parallel_submission", type="boolean", label=T("Parallel submission")),
        Field("art_stage_1_id", type="integer"),
    )
    myVars = request.vars
    qyKw = ""
    qyTF = []

    for myVar in myVars:
        if isinstance(myVars[myVar], list):
            myValue = (myVars[myVar])[1]
        else:
            myValue = myVars[myVar]
        if myVar == "qyKeywords":
            qyKw = myValue
        elif re.match("^qy_", myVar) and myValue == "on":
            qyTF.append(re.sub(r"^qy_", "", myVar))
    qyKwArr = qyKw.split(" ")

    searchForm = app_forms.searchByThematic(auth, db, myVars)

    filtered = db.executesql("SELECT * FROM search_articles_new(%s, %s, %s, %s, %s);", placeholders=[qyTF, qyKwArr, "Awaiting consideration", trgmLimit, True], as_dict=True)

    for fr in filtered:
        qy_art.insert(**fr)

    temp_db.qy_art.auto_nb_recommendations.readable = False
    temp_db.qy_art.uploaded_picture.represent = lambda text, row: (IMG(_src=URL("default", "download", args=text), _width=100)) if (text is not None and text != "") else ("")
    temp_db.qy_art.authors.represent = lambda text, row: common_small_html.mkAnonymousArticleField(auth, db, row.anonymous_submission, (text or ""))
    temp_db.qy_art.anonymous_submission.represent = lambda anon, row: common_small_html.mkAnonymousMask(auth, db, anon or False)
    temp_db.qy_art.anonymous_submission.readable = False
    temp_db.qy_art.parallel_submission.represent = lambda p, r: SPAN("//", _class="pci-parallelSubmission") if p else ""
    temp_db.qy_art.parallel_submission.readable = False
    temp_db.qy_art.thematics.readable = False
    temp_db.qy_art.keywords.readable = False

    if len(request.args) == 0:  # in grid
        temp_db.qy_art._id.readable = True
        temp_db.qy_art._id.represent = lambda text, row: common_small_html.mkRepresentArticleLight(auth, db, text)
        temp_db.qy_art._id.label = T("Article")
        temp_db.qy_art.title.readable = False
        temp_db.qy_art.authors.readable = False
        # temp_db.qy_art.status.readable = False
        temp_db.qy_art.article_source.readable = False
        temp_db.qy_art.upload_timestamp.represent = lambda t, row: common_small_html.mkLastChange(t)
        temp_db.qy_art.last_status_change.represent = lambda t, row: common_small_html.mkLastChange(t)
        # temp_db.qy_art.abstract.represent = lambda text, row: DIV(WIKI(text or ""), _class="pci-div4wiki")
        temp_db.qy_art.art_stage_1_id.readable = False
        temp_db.qy_art.art_stage_1_id.writable = False
        temp_db.qy_art.status.represent = lambda text, row: common_small_html.mkStatusDiv(auth, db, row.status, showStage=pciRRactivated, stage1Id=row.art_stage_1_id)
        temp_db.qy_art.num.readable = False
        temp_db.qy_art.score.readable = False
    else:
        temp_db.qy_art._id.readable = False
        temp_db.qy_art.num.readable = False
        temp_db.qy_art.score.readable = False
        temp_db.qy_art.doi.represent = lambda text, row: common_small_html.mkDOI(text)
        # temp_db.qy_art.abstract.represent = lambda text, row: WIKI(text or "")

    links = []
    # links.append(dict(header=T('Suggested recommenders'), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders))
    links.append(dict(header=T(""), body=lambda row: recommender_module.mkViewEditArticleRecommenderButton(auth, db, row)))
    if parallelSubmissionAllowed:
        fields = [
            temp_db.qy_art.art_stage_1_id,
            temp_db.qy_art.num,
            temp_db.qy_art.score,
            temp_db.qy_art.last_status_change,
            temp_db.qy_art.status,
            temp_db.qy_art.uploaded_picture,
            temp_db.qy_art._id,
            temp_db.qy_art.title,
            temp_db.qy_art.authors,
            temp_db.qy_art.article_source,
            temp_db.qy_art.upload_timestamp,
            temp_db.qy_art.anonymous_submission,
            temp_db.qy_art.parallel_submission,
            # temp_db.qy_art.abstract,
            temp_db.qy_art.thematics,
            temp_db.qy_art.keywords,
            temp_db.qy_art.auto_nb_recommendations,
        ]
    else:
        fields = [
            temp_db.qy_art.art_stage_1_id,
            temp_db.qy_art.num,
            temp_db.qy_art.score,
            temp_db.qy_art.last_status_change,
            temp_db.qy_art.status,
            temp_db.qy_art.uploaded_picture,
            temp_db.qy_art._id,
            temp_db.qy_art.title,
            temp_db.qy_art.authors,
            temp_db.qy_art.article_source,
            temp_db.qy_art.upload_timestamp,
            temp_db.qy_art.anonymous_submission,
            # temp_db.qy_art.abstract,
            temp_db.qy_art.thematics,
            temp_db.qy_art.keywords,
            temp_db.qy_art.auto_nb_recommendations,
        ]

    grid = SQLFORM.grid(
        temp_db.qy_art,
        searchable=False,
        editable=False,
        deletable=False,
        create=False,
        details=False,
        maxtextlength=250,
        paginate=10,
        csv=csv,
        exportclasses=expClass,
        fields=fields,
        links=links,
        orderby=temp_db.qy_art.num,
        _class="web2py_grid action-button-absolute",
    )

    response.view = "default/gab_list_layout.html"
    return dict(
        # pageTitle=T('Articles requiring a recommender'),
        titleIcon="inbox",
        pageTitle=getTitle(request, auth, db, "#RecommenderAwaitingArticlesTitle"),
        customText=getText(request, auth, db, "#RecommenderArticlesAwaitingRecommendationText:InMyFields"),
        grid=grid,
        pageHelp=getHelp(request, auth, db, "#RecommenderArticlesAwaitingRecommendation:InMyFields"),
        searchableList=True,
        searchForm=searchForm,
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "web2py_button_absolute.js"), _type="text/javascript"),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def search_reviewers():
    # We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
    temp_db = DAL("sqlite:memory")
    qy_reviewers = temp_db.define_table(
        "qy_reviewers",
        Field("id", type="integer"),
        Field("num", type="integer"),
        Field("score", type="double", label=T("Score"), default=0),
        Field("first_name", type="string", length=128, label=T("First name")),
        Field("last_name", type="string", length=128, label=T("Last name")),
        Field("email", type="string", length=512, label=T("e-mail")),
        Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
        Field("city", type="string", label=T("City")),
        Field("country", type="string", label=T("Country")),
        Field("laboratory", type="string", label=T("Department")),
        Field("institution", type="string", label=T("Institution")),
        Field("thematics", type="list:string", label=T("Thematic fields")),
        Field("roles", type="string", length=1024, label=T("Roles")),
        Field("excluded", type="boolean", label=T("Excluded")),
    )
    temp_db.qy_reviewers.email.represent = lambda text, row: A(text, _href="mailto:" + text)
    myVars = request.vars
    qyKw = ""
    qyTF = []
    excludeList = []
    myGoal = "4review"  # default
    for myVar in myVars:
        if isinstance(myVars[myVar], list):
            myValue = (myVars[myVar])[1]
        else:
            myValue = myVars[myVar]

        if myVar == "qyKeywords":
            qyKw = myValue
        elif myVar == "myGoal":
            myGoal = myValue
        elif myVar == "exclude":
            excludeList += myValue.split(",")
        elif re.match("^qy_", myVar) and myValue == "on":
            qyTF.append(re.sub(r"^qy_", "", myVar))

    if "recommId" in request.vars:
        recommId = request.vars["recommId"]
        if recommId:
            recomm = db.t_recommendations[recommId]
            if recomm:
                excludeList.append(recomm.recommender_id)
                art = db.t_articles[recomm.article_id]
                if art:
                    uid = art.user_id
                    if uid:
                        excludeList.append(uid)

    qyKwArr = qyKw.split(" ")
    searchForm = app_forms.searchByThematic(auth, db, myVars, allowBlank=True)
    if searchForm.process(keepvalues=True).accepted:
        response.flash = None
    else:
        qyTF = []
        for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
            qyTF.append(thema.keyword)

    filtered = db.executesql("SELECT * FROM search_reviewers(%s, %s, %s);", placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
    for fr in filtered:
        qy_reviewers.insert(**fr)

    temp_db.qy_reviewers._id.readable = False
    temp_db.qy_reviewers.uploaded_picture.readable = False
    temp_db.qy_reviewers.excluded.readable = False
    links = []
    if "recommId" in request.vars:
        recommId = request.vars["recommId"]
        links.append(dict(header=T("Days since last recommendation"), body=lambda row: db.v_last_recommendation[row.id].days_since_last_recommendation))
        if myGoal == "4review":
            links.append(dict(header=T("Select"), body=lambda row: "" if row.excluded else recommender_module.mkSuggestReviewToButton(auth, db, row, recommId, myGoal)))
            # pageTitle = T('Search for reviewers')
            pageTitle = getTitle(request, auth, db, "#RecommenderSearchReviewersTitle")
            customText = getText(request, auth, db, "#RecommenderSearchReviewersText")
            pageHelp = getHelp(request, auth, db, "#RecommenderSearchReviewers")
        elif myGoal == "4press":
            links.append(
                dict(header=T("Propose contribution"), body=lambda row: "" if row.excluded else recommender_module.mkSuggestReviewToButton(auth, db, row, recommId, myGoal))
            )
            # pageTitle = T('Search for collaborators')
            pageTitle = getTitle(request, auth, db, "#RecommenderSearchCollaboratorsTitle")
            customText = getText(request, auth, db, "#RecommenderSearchCollaboratorsText")
            pageHelp = getHelp(request, auth, db, "#RecommenderSearchCollaborators")
    
    if (recomm is not None) and (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        temp_db.qy_reviewers.num.readable = False
        temp_db.qy_reviewers.score.readable = False
        grid = SQLFORM.grid(
            qy_reviewers,
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
                temp_db.qy_reviewers.num,
                temp_db.qy_reviewers.score,
                temp_db.qy_reviewers.uploaded_picture,
                temp_db.qy_reviewers.first_name,
                temp_db.qy_reviewers.last_name,
                temp_db.qy_reviewers.email,
                temp_db.qy_reviewers.laboratory,
                temp_db.qy_reviewers.institution,
                temp_db.qy_reviewers.city,
                temp_db.qy_reviewers.country,
                temp_db.qy_reviewers.thematics,
                temp_db.qy_reviewers.excluded,
            ],
            links=links,
            orderby=temp_db.qy_reviewers.num,
            args=request.args,
        )

        response.view = "default/gab_list_layout.html"
        return dict(
            pageHelp=pageHelp,
            titleIcon="search",
            pageTitle=pageTitle,
            customText=customText,
            myBackButton=common_small_html.mkBackButton(),
            searchForm=searchForm,
            grid=grid,
        )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def article_details():
    printable = "printable" in request.vars
    articleId = None
    if "articleId" in request.vars:
        articleId = request.vars["articleId"]
        art = db.t_articles[articleId]

    if articleId is None or art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    else:
        amIAllowed = (
            db(
                ((db.t_recommendations.article_id == articleId) & (db.t_recommendations.recommender_id == auth.user_id))
                | (
                    (db.t_suggested_recommenders.article_id == articleId)
                    & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
                    & (db.t_suggested_recommenders.declined == False)
                )
            ).count()
            > 0
        )
        if (amIAllowed is False) and (art.status == "Awaiting consideration") and (auth.has_membership(role="recommender")):
            amIAllowed = True

        if amIAllowed:
            alreadyUnderProcess = db((db.t_recommendations.article_id == articleId) & (db.t_recommendations.recommender_id != auth.user_id)).count() > 0

            if alreadyUnderProcess:
                contact = myconf.take("contacts.managers")
                myContents = DIV(
                    SPAN(
                        "Another recommender has already selected this article (DOI: ",
                        common_small_html.mkDOI(art.doi),
                        "), for which you were considering handling the evaluation. If you wish, we can inform the recommender handling this article that you would like to be a co-recommender or a reviewer (which would be much appreciated). If you are willing to help in this way, simply send us a message at: ",
                    ),
                    A(contact, _href="mailto:%s" % contact),
                    SPAN(" stating that you want to become a co-recommender or a reviewer, and we will alert the recommender."),
                    BR(),
                    SPAN(
                        "Otherwise, you may",
                        A(T("decline"), _href=URL("recommender_actions", "decline_new_article_to_recommend", vars=dict(articleId=articleId)), _class="btn btn-info"),
                    ),
                    SPAN(" this suggestion."),
                    _class="pci-alreadyUnderProcess",
                )
            else:
                if art.already_published:
                    myContents = ongoing_recommendation.getPostprintRecommendation(auth, db, response, art, printable, quiet=False)
                else:
                    myContents = ongoing_recommendation.getRecommendationProcess(auth, db, response, art, printable)

            isStage2 = art.art_stage_1_id is not None
            stage1Link = None
            stage2List = None
            if pciRRactivated and isStage2:
                # stage1Link = A(T("Link to Stage 1"), _href=URL(c="manager", f="recommendations", vars=dict(articleId=art.art_stage_1_id)))
                urlArticle = URL(c="recommender", f="recommendations", vars=dict(articleId=art.art_stage_1_id))
                stage1Link = common_small_html.mkRepresentArticleLightLinkedWithStatus(auth, db, art.art_stage_1_id, urlArticle)
            elif pciRRactivated and not isStage2:
                stage2Articles = db(db.t_articles.art_stage_1_id == articleId).select()
                stage2List = []
                for art_st_2 in stage2Articles:
                    urlArticle = URL(c="recommender", f="recommendations", vars=dict(articleId=art_st_2.id))
                    stage2List.append(common_small_html.mkRepresentArticleLightLinkedWithStatus(auth, db, art_st_2.id, urlArticle))

            response.title = art.title or myconf.take("app.longname")

            finalRecomm = (
                db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()
            )
            recommHeaderHtml = article_components.getArticleInfosCard(auth, db, response, art, printable, True)
            recommStatusHeader = ongoing_recommendation.getRecommStatusHeader(auth, db, response, art, "recommender", request, False, printable, quiet=False)
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
                recommTopButtons=recommTopButtons or "",
                recommHeaderHtml=recommHeaderHtml,
                recommStatusHeader=recommStatusHeader,
                printable=printable,
                pageHelp=getHelp(request, auth, db, "#RecommenderArticlesRequiringRecommender"),
                myContents=myContents,
                myBackButton=common_small_html.mkBackButton(),
                pciRRactivated=pciRRactivated,
                isStage2=isStage2,
                stage1Link=stage1Link,
                stage2List=stage2List,
            )
        else:
            raise HTTP(403, "403: " + T("Access denied"))


######################################################################################################################################################################
# (gab) Should improve (need specific view):
@auth.requires(auth.has_membership(role="recommender"))
def new_submission():
    response.view = "default/info.html"

    ethics_not_signed = not (db.auth_user[auth.user_id].ethical_code_approved)
    if ethics_not_signed:
        redirect(URL(c="about", f="ethics", vars=dict(_next=URL())))
    else:
        c = getText(request, auth, db, "#ConflictsForRecommenders")
        myEthical = DIV(
            FORM(
                DIV(
                    SPAN(
                        INPUT(_type="checkbox", _name="no_conflict_of_interest", _id="no_conflict_of_interest", _value="yes", value=False),
                        LABEL(T("I declare that I have no conflict of interest with the authors or the content of the article")),
                    ),
                    DIV(c),
                    _style="padding:16px;",
                ),
                INPUT(_type="submit", _value=T("Recommend a postprint"), _class="btn btn-success pci-panelButton pci-recommender"),
                hidden=dict(ethics_approved=True),
                _action=URL("recommender", "direct_submission"),
                _style="text-align:center;",
            ),
            _class="pci-embeddedEthic",
        )
        myScript = SCRIPT(common_tools.get_template("script", "new_submission.js"))

    customText = DIV(getText(request, auth, db, "#NewRecommendationInfo"), myEthical, _class="pci2-flex-column pci2-align-items-center")

    return dict(titleIcon="edit", pageTitle=getTitle(request, auth, db, "#RecommenderBeforePostprintSubmissionTitle"), customText=customText, myFinalScript=myScript)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def my_awaiting_articles():
    response.view = "default/myLayout.html"

    query = (
        (db.t_articles.status == "Awaiting consideration")
        & (db.t_articles._id == db.t_suggested_recommenders.article_id)
        & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
        & (db.t_suggested_recommenders.declined == False)
    )
    db.t_articles.user_id.writable = False
    db.t_articles.user_id.represent = lambda userId, row: common_small_html.mkAnonymousArticleField(auth, db, row.anonymous_submission, common_small_html.mkUser(auth, db, userId))
    # db.t_articles.doi.represent = lambda text, row: common_small_html.mkDOI(text)
    db.t_articles.auto_nb_recommendations.readable = False
    db.t_articles.anonymous_submission.readable = False
    db.t_articles.anonymous_submission.writable = False

    db.t_articles.abstract.readable = False
    db.t_articles.keywords.readable = False

    db.t_articles.status.writable = False
    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.art_stage_1_id.writable = False
    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(auth, db, text, showStage=pciRRactivated, stage1Id=row.art_stage_1_id)
    if len(request.args) == 0:  # we are in grid
        # db.t_articles.doi.readable = False
        # db.t_articles.authors.readable = False
        # db.t_articles.title.readable = False
        db.t_articles.upload_timestamp.represent = lambda t, row: common_small_html.mkLastChange(t)
        db.t_articles.last_status_change.represent = lambda t, row: common_small_html.mkLastChange(t)
        db.t_articles._id.readable = True
        db.t_articles._id.represent = lambda text, row: common_small_html.mkRepresentArticleLight(auth, db, text)
        db.t_articles._id.label = T("Article")
        # db.t_articles.abstract.represent = lambda text, row: DIV(WIKI(text or ""), _class="pci-div4wiki")
    else:  # we are in grid's form
        db.t_articles._id.readable = False
        # db.t_articles.abstract.represent = lambda text, row: WIKI(text)
    if parallelSubmissionAllowed:
        fields = [
            db.t_articles.art_stage_1_id,
            db.t_articles.last_status_change,
            db.t_articles.status,
            db.t_articles._id,
            db.t_articles.upload_timestamp,
            db.t_articles.anonymous_submission,
            db.t_articles.parallel_submission,
            # db.t_articles.abstract,
            db.t_articles.thematics,
            db.t_articles.keywords,
            db.t_articles.user_id,
            db.t_articles.auto_nb_recommendations,
        ]
    else:
        fields = [
            db.t_articles.art_stage_1_id,
            db.t_articles.last_status_change,
            db.t_articles.status,
            db.t_articles._id,
            db.t_articles.upload_timestamp,
            db.t_articles.anonymous_submission,
            # db.t_articles.abstract,
            db.t_articles.thematics,
            db.t_articles.keywords,
            db.t_articles.user_id,
            db.t_articles.auto_nb_recommendations,
        ]

    grid = SQLFORM.grid(
        query,
        searchable=False,
        editable=False,
        deletable=False,
        create=False,
        details=False,
        maxtextlength=250,
        paginate=10,
        csv=csv,
        exportclasses=expClass,
        fields=fields,
        links=[
            dict(header=T("Suggested recommenders"), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders),
            dict(header=T(""), body=lambda row: DIV(recommender_module.mkViewEditArticleRecommenderButton(auth, db, row))),
        ],
        orderby=~db.t_articles.upload_timestamp,
        _class="web2py_grid action-button-absolute",
    )

    return dict(
        titleIcon="envelope",
        pageHelp=getHelp(request, auth, db, "#RecommenderSuggestedArticles"),
        customText=getText(request, auth, db, "#RecommenderSuggestedArticlesText"),
        pageTitle=getTitle(request, auth, db, "#RecommenderSuggestedArticlesTitle"),
        grid=grid,
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "action_button_absolute.js"), _type="text/javascript"),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def accept_new_article_to_recommend():
    actionFormUrl = None
    appLongname = None
    hidenVarsForm = None

    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    if articleId is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    ethics_not_signed = not (db.auth_user[auth.user_id].ethical_code_approved)
    if ethics_not_signed:
        redirect(URL(c="about", f="ethics"))
    else:
        appLongname = myconf.take("app.longname")
        hiddenVarsForm = dict(articleId=articleId, ethics_approved=True)
        actionFormUrl = URL("recommender_actions", "do_accept_new_article_to_recommend")
        longname = myconf.take("app.longname")

    pageTitle = getTitle(request, auth, db, "#AcceptPreprintInfoTitle")
    customText = getText(request, auth, db, "#AcceptPreprintInfoText")

    response.view = "controller/recommender/accept_new_article_to_recommend.html"
    return dict(
        customText=customText, titleIcon="education", pageTitle=pageTitle, actionFormUrl=actionFormUrl, appLongname=appLongname, hiddenVarsForm=hiddenVarsForm, articleId=articleId, pciRRactivated=pciRRactivated
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def my_recommendations():
    response.view = "default/myLayout.html"

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    # goBack='%s://%s%s' % (request.env.wsgi_url_scheme, request.env.http_host, request.env.request_uri)
    goBack = URL(re.sub(r".*/([^/]+)$", "\\1", request.env.request_uri), scheme=scheme, host=host, port=port)

    isPress = ("pressReviews" in request.vars) and (request.vars["pressReviews"] == "True")
    if isPress:  ## NOTE: POST-PRINTS
        query = (db.t_recommendations.recommender_id == auth.user_id) & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_articles.already_published == True)
        pageTitle = getTitle(request, auth, db, "#RecommenderMyRecommendationsPostprintTitle")
        customText = getText(request, auth, db, "#RecommenderMyRecommendationsPostprintText")
        fields = [
            db.t_articles.scheduled_submission_date,
            db.t_recommendations.last_change,
            db.t_articles.status,
            db.t_articles.art_stage_1_id,
            db.t_recommendations._id,
            db.t_recommendations.article_id,
            db.t_recommendations.doi,
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
        query = (db.t_recommendations.recommender_id == auth.user_id) & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_articles.already_published == False)
        pageTitle = getTitle(request, auth, db, "#RecommenderMyRecommendationsPreprintTitle")
        customText = getText(request, auth, db, "#RecommenderMyRecommendationsPreprintText")
        fields = [
            db.t_articles.scheduled_submission_date,
            db.t_recommendations.last_change,
            db.t_articles.status,
            db.t_articles.art_stage_1_id,
            db.t_recommendations._id,
            db.t_recommendations.article_id,
            db.t_recommendations.doi,
            db.t_recommendations.is_closed,
            db.t_recommendations.recommendation_state,
            db.t_recommendations.is_closed,
            db.t_recommendations.recommender_id,
        ]
        links = [
            dict(header=T("Co-recommenders"), body=lambda row: common_small_html.mkCoRecommenders(auth, db, row.t_recommendations if "t_recommendations" in row else row, goBack)),
            dict(header=T("Reviews"), body=lambda row: recommender_components.getReviewsSubTable(auth, db, response, request, row.t_recommendations if "t_recommendations" in row else row)),
            dict(
                header=T(""), body=lambda row: common_small_html.mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if "t_recommendations" in row else row)
            ),
        ]
        db.t_recommendations.article_id.label = T("Preprint")

    db.t_recommendations.recommender_id.writable = False
    db.t_recommendations.doi.writable = False
    db.t_recommendations.article_id.writable = False
    db.t_recommendations._id.readable = False
    db.t_recommendations.recommender_id.readable = False
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
    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(auth, db, text, showStage=pciRRactivated, stage1Id=row.t_articles.art_stage_1_id)
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

    if isPress:  ## NOTE: POST-PRINTS
        titleIcon = "certificate"
    else:  ## NOTE: PRE-PRINTS
        titleIcon = "education"

    return dict(
        # myBackButton=common_small_html.mkBackButton(),
        pageHelp=getHelp(request, auth, db, "#RecommenderMyRecommendations"),
        titleIcon=titleIcon,
        pageTitle=pageTitle,
        customText=customText,
        grid=grid,
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "web2py_button_absolute.js"), _type="text/javascript"),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def direct_submission():
    response.view = "default/myLayout.html"

    theUser = db.auth_user[auth.user_id]
    if "ethics_approved" in request.vars:
        theUser.ethical_code_approved = True
        theUser.update_record()
    if not (theUser.ethical_code_approved):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    noConflict = False
    if "no_conflict_of_interest" in request.vars:
        if request.vars["no_conflict_of_interest"] == "yes":
            noConflict = True
    db.t_articles.user_id.default = None
    db.t_articles.user_id.writable = False
    db.t_articles.status.default = "Under consideration"
    db.t_articles.status.writable = False
    db.t_articles.already_published.readable = False
    db.t_articles.already_published.writable = False
    db.t_articles.already_published.default = True
    myScript = """jQuery(document).ready(function(){
					
					if(jQuery('#t_articles_picture_rights_ok').prop('checked')) {
						jQuery('#t_articles_uploaded_picture').prop('disabled', false);
					} else {
						jQuery('#t_articles_uploaded_picture').prop('disabled', true);
					}
					jQuery('#t_articles_picture_rights_ok').change(function(){
								if(jQuery('#t_articles_picture_rights_ok').prop('checked')) {
									jQuery('#t_articles_uploaded_picture').prop('disabled', false);
								} else {
									jQuery('#t_articles_uploaded_picture').prop('disabled', true);
									jQuery('#t_articles_uploaded_picture').val('');
								}
					});
				});
	"""
    fields = ["title", "authors", "article_source", "doi", "picture_rights_ok", "uploaded_picture", "abstract", "thematics", "keywords", "picture_data"]
    form = SQLFORM(db.t_articles, fields=fields, keepvalues=True, submit_button=T("Continue..."), hidden=dict(no_conflict_of_interest="yes" if noConflict else "no"))
    if form.process().accepted:
        articleId = form.vars.id
        recommId = db.t_recommendations.insert(
            article_id=articleId, recommender_id=auth.user_id, doi=form.vars.doi, recommendation_state="Ongoing", no_conflict_of_interest=noConflict
        )
        redirect(
            URL(c="recommender", f="add_contributor", vars=dict(recommId=recommId, goBack=URL("recommender", "my_recommendations", vars=dict(pressReviews=True)), onlyAdd=False))
        )
    return dict(
        pageHelp=getHelp(request, auth, db, "#RecommenderDirectSubmission"),
        # myBackButton=common_small_html.mkBackButton(),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#RecommenderDirectSubmissionTitle"),
        customText=getText(request, auth, db, "#RecommenderDirectSubmissionText"),
        form=form,
        myFinalScript=SCRIPT(myScript),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def recommendations():
    printable = "printable" in request.vars and request.vars["printable"] == "True"
    articleId = request.vars["articleId"]

    art = db.t_articles[articleId]
    if art is None:
        print("Missing article %s" % articleId)
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    # NOTE: 2018-09-05 bug corrected by splitting the query and adding counts; weird but it works
    authCount = db((db.t_recommendations.recommender_id == auth.user_id) & (db.t_recommendations.article_id == articleId)).count()
    authCount += db(
        ((db.t_press_reviews.contributor_id == auth.user_id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id)) & (db.t_recommendations.article_id == articleId)
    ).count()

    # is allowed if is recommender of a step 2 (user will not have any possible actions, just to observe recommendation process)
    if pciRRactivated and art.art_stage_1_id is None:
        authCount += db(
            (db.t_articles.art_stage_1_id == articleId) & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommender_id == auth.user_id)
        ).count()

    amIAllowed = authCount > 0
    if not (amIAllowed):
        print("Not allowed: userId=%s, articleId=%s" % (auth.user_id, articleId))
        # print(db._lastsql)
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        if art.already_published:
            myContents = ongoing_recommendation.getPostprintRecommendation(auth, db, response, art, printable, quiet=False)
        else:
            myContents = ongoing_recommendation.getRecommendationProcess(auth, db, response, art, printable)

        isStage2 = art.art_stage_1_id is not None
        stage1Link = None
        stage2List = None
        if pciRRactivated and isStage2:
            # stage1Link = A(T("Link to Stage 1"), _href=URL(c="manager", f="recommendations", vars=dict(articleId=art.art_stage_1_id)))
            urlArticle = URL(c="recommender", f="recommendations", vars=dict(articleId=art.art_stage_1_id))
            stage1Link = common_small_html.mkRepresentArticleLightLinkedWithStatus(auth, db, art.art_stage_1_id, urlArticle)
        elif pciRRactivated and not isStage2:
            stage2Articles = db(db.t_articles.art_stage_1_id == articleId).select()
            stage2List = []
            for art_st_2 in stage2Articles:
                urlArticle = URL(c="recommender", f="recommendations", vars=dict(articleId=art_st_2.id))
                stage2List.append(common_small_html.mkRepresentArticleLightLinkedWithStatus(auth, db, art_st_2.id, urlArticle))

        response.title = art.title or myconf.take("app.longname")

        # New recommendation function (WIP)
        finalRecomm = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()
        recommHeaderHtml = article_components.getArticleInfosCard(auth, db, response, art, printable, True)
        recommStatusHeader = ongoing_recommendation.getRecommStatusHeader(auth, db, response, art, "recommender", request, False, printable, quiet=False)
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
            recommStatusHeader=recommStatusHeader,
            recommHeaderHtml=recommHeaderHtml,
            recommTopButtons=recommTopButtons or "",
            printable=printable,
            pageHelp=getHelp(request, auth, db, "#RecommenderOtherRecommendations"),
            myContents=myContents,
            myBackButton=common_small_html.mkBackButton(),
            pciRRactivated=pciRRactivated,
            isStage2=isStage2,
            stage1Link=stage1Link,
            stage2List=stage2List,
        )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def show_report_survey():
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
        session.flash = T("Unavailable")
        redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=articleId), user_signature=True))

    db.t_report_survey._id.readable = False
    db.t_report_survey._id.writable = False

    if art.report_stage == "STAGE 1":  # STAGE 1 survey
        fields = [
            "q1", 
            "q2", 
            "q3",
            "q4",
            # "q5",
            "q6",
            "q7",
            "q8",
            "q9",
            "q10",
            "q11",
            "q11_details",
            "q12",
            "q12_details",
            "q13",
            "q13_details",
            "q14",
            "q15",
            "q16",
            "q17",
            "q18",
            "q19",
            "q20",
            "q21",
            "q22",
            "q23",
            "q24",
            "q24_1",
            "q24_1_details",
            "q32",
        ]

    else:  # STAGE 2 survey
        db.t_report_survey.temp_art_stage_1_id.requires = IS_IN_DB(
            db((db.t_articles.user_id == art.user_id) & (db.t_articles.art_stage_1_id == None)), "t_articles.id", 'Stage 2 of "%(title)s"'
        )

        fields = [
            "temp_art_stage_1_id",
            "q25",
            "q26",
            "q26_details",
            "q27",
            "q27_details",
            "q28",
            "q28_details",
            "q29",
            "q30",
            "q31",
            "q32",
        ]

    form = SQLFORM(
        db.t_report_survey,
        survey.id,
        fields=fields,
        readonly=True,
    )

    if form.process().accepted:
        doUpdateArticle = False
        if form.vars.Q10 is not None:
            art.scheduled_submission_date = form.vars.Q10
            art.doi = None
            doUpdateArticle = True

        if form.vars.temp_art_stage_1_id is not None:
            art.art_stage_1_id = form.vars.temp_art_stage_1_id
            doUpdateArticle = True

        if doUpdateArticle == True:
            art.update_record()

        session.flash = T("Article submitted", lazy=False)
        redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))
    elif form.errors:
        response.flash = T("Form has errors", lazy=False)

    myScript = common_tools.get_template("script", "fill_report_survey.js")
    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp(request, auth, db, "#RecommenderReportSurvey"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#RecommenderReportSurveyTitle"),
        customText=getText(request, auth, db, "#RecommenderReportSurveyText", maxWidth="800"),
        form=form,
        myFinalScript=SCRIPT(myScript),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def one_review():
    response.view = "default/myLayout.html"

    revId = request.vars["reviewId"]
    rev = db.t_reviews[revId]
    form = ""
    if rev == None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm == None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    db.t_reviews._id.readable = False
    db.t_reviews.reviewer_id.writable = False
    db.t_reviews.reviewer_id.represent = lambda text, row: common_small_html.mkUserWithMail(auth, db, row.reviewer_id) if row else ""
    db.t_reviews.anonymously.default = True
    db.t_reviews.anonymously.writable = auth.has_membership(role="manager")
    db.t_reviews.review.writable = auth.has_membership(role="manager")
    db.t_reviews.review_state.writable = auth.has_membership(role="manager")
    db.t_reviews.review_state.represent = lambda text, row: common_small_html.mkReviewStateDiv(auth, db, text)
    db.t_reviews.review.represent = lambda text, row: WIKI(text or "", safe_mode=False)
    form = SQLFORM(
        db.t_reviews,
        record=revId,
        readonly=True,
        fields=["reviewer_id", "no_conflict_of_interest", "anonymously", "review", "review_pdf"],
        showid=False,
        upload=URL("default", "download"),
    )
    return dict(
        pageHelp=getHelp(request, auth, db, "#RecommenderArticleOneReview"),
        customText=getText(request, auth, db, "#RecommenderArticleOneReviewText"),
        titleIcon="eye-open",
        pageTitle=getTitle(request, auth, db, "#RecommenderArticleOneReviewTitle"),
        myBackButton=common_small_html.mkBackButton(),
        form=form,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def reviews():
    response.view = "default/myLayout.html"

    recommId = request.vars["recommId"]
    recomm = db.t_recommendations[recommId]
    if recomm == None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        myContents = T(
            'If you want to give a reviewer who has completed his/her review an opportunity to modify the review, please check the reviewer below then click on the black button entitled "Re-open selected reviews"'
        )
        db.t_reviews._id.readable = False
        db.t_reviews.recommendation_id.default = recommId
        db.t_reviews.recommendation_id.writable = False
        db.t_reviews.recommendation_id.readable = False
        db.t_reviews.reviewer_id.writable = auth.has_membership(role="manager")
        db.t_reviews.reviewer_id.default = auth.user_id
        db.t_reviews.reviewer_id.represent = lambda text, row: TAG(row.reviewer_details) \
                if row.reviewer_details else common_small_html.mkUserWithMail(auth, db, row.reviewer_id)
        db.t_reviews.anonymously.default = True
        db.t_reviews.anonymously.writable = auth.has_membership(role="manager")
        db.t_reviews.review.writable = auth.has_membership(role="manager")
        db.t_reviews.review_state.writable = auth.has_membership(role="manager")
        db.t_reviews.review_state.represent = lambda text, row: common_small_html.mkReviewStateDiv(auth, db, text)
        db.t_reviews.emailing.writable = False
        db.t_reviews.emailing.represent = lambda text, row: XML(text) if text else ""
        db.t_reviews.last_change.writable = True

        if len(request.args) == 0 or (len(request.args) == 1 and request.args[0] == "auth_user"):  # grid view
            selectable = [(T("Re-open selected reviews"), lambda ids: [recommender_module.reopen_review(auth, db, ids)], "button btn btn-info")]
            db.t_reviews.review.represent = lambda text, row: DIV(WIKI(text or ""), _class="pci-div4wiki")
            db.t_reviews.emailing.readable = False
        else:  # form view
            selectable = None
            db.t_reviews.review.represent = lambda text, row: WIKI(text or "")
            db.t_reviews.emailing.readable = True

        query = db.t_reviews.recommendation_id == recommId
        grid = SQLFORM.grid(
            query,
            details=True,
            editable=lambda row: auth.has_membership(role="manager") or (row.review_state != "Review completed" and row.reviewer_id is None),
            deletable=auth.has_membership(role="manager"),
            create=auth.has_membership(role="manager"),
            searchable=False,
            maxtextlength=250,
            paginate=100,
            csv=csv,
            exportclasses=expClass,
            fields=[
                db.t_reviews.recommendation_id,
                db.t_reviews.reviewer_id,
                db.t_reviews.anonymously,
                db.t_reviews.review_state,
                db.t_reviews.acceptation_timestamp,
                db.t_reviews.last_change,
                db.t_reviews.review,
                db.t_reviews.review_pdf,
                db.t_reviews.emailing,
                db.t_reviews.reviewer_details,
            ],
            selectable=selectable,
            _class="web2py_grid action-button-absolute",
            upload=URL("default", "download")
        )

        # This script renames the "Add record" button
        myScript = SCRIPT(
            """$(function() { 
						$('span').filter(function(i) {
								return $(this).attr("title") ? $(this).attr("title").indexOf('"""
            + T("Add record to database")
            + """') != -1 : false;
							})
							.each(function(i) {
								$(this).text('"""
            + T("Add a review")
            + """').attr("title", '"""
            + T("Add a new review from scratch")
            + """');
							});
						})""",
            _type="text/javascript",
        )

        return dict(
            pageHelp=getHelp(request, auth, db, "#RecommenderArticleReviews"),
            customText=getText(request, auth, db, "#RecommenderArticleReviewsText"),
            titleIcon="eye-open",
            pageTitle=getTitle(request, auth, db, "#RecommenderArticleReviewsTitle"),
            # myBackButton=common_small_html.mkBackButton(),
            content=myContents,
            grid=grid,
            myFinalScript=myScript,
            absoluteButtonScript=SCRIPT(common_tools.get_template("script", "web2py_button_absolute.js"), _type="text/javascript"),
        )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def reviewers():
    response.view = "default/myLayout.html"

    recommId = request.vars["recommId"]
    recomm = db.t_recommendations[recommId]

    if recomm:
        article= db.t_articles[recomm.article_id]
        if article.user_id == auth.user_id:
            session.flash = auth.not_authorized()
            redirect(request.env.http_referer)
    if not recomm:
        return my_recommendations()
    if (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        reviewersListSel = db((db.t_reviews.recommendation_id == recommId)).select(
            db.t_reviews.id, db.t_reviews.review_state, db.t_reviews.reviewer_id, db.t_reviews.reviewer_details
        )
        reviewersList = []
        reviewersIds = [auth.user_id]
        selfFlag = False
        selfFlagCancelled = False
        for con in reviewersListSel:
            if con.review_state is None:  # delete this unfinished review declaration
                db(db.t_reviews.id == con.id).delete()
            else:
                reviewer_id = con.reviewer_id
                if recomm.recommender_id == reviewer_id:
                    selfFlag = True
                    if con.review_state == "Cancelled":
                        selfFlagCancelled = True
                reviewersIds.append(reviewer_id)
                reviewersList.append(
                    LI(
                        TAG(con.reviewer_details) if con.reviewer_details else \
                                common_small_html.mkUserWithMail(auth, db, reviewer_id),
                        " ",
                        B(T(" (YOU) ")) if reviewer_id == recomm.recommender_id else "",
                        I("(" + (con.review_state or "") + ")"),
                    )
                )
        excludeList = ",".join(map(str, filter(lambda x: x is not None, reviewersIds)))
        if len(reviewersList) > 0:
            myContents = DIV(H3(T("Reviewers already invited:")), UL(reviewersList), _style="width:100%; max-width: 1200px")
        else:
            myContents = ""
        longname = myconf.take("app.longname")
        myUpperBtn = DIV(
            A(
                SPAN(current.T("Choose a reviewer from the %s database") % (longname), _class="btn btn-success"),
                _href=URL(c="recommender", f="search_reviewers", vars=dict(recommId=recommId, myGoal="4review", exclude=excludeList)),
            ),
            A(
                SPAN(current.T("Choose a reviewer outside %s database") % (longname), _class="btn btn-default"),
                _href=URL(c="recommender", f="email_for_new_reviewer", vars=dict(recommId=recommId)),
            ),
            _style="margin-top:8px; margin-bottom:16px; text-align:left; max-width:1200px; width: 100%",
        )
        if auth.user_id == recomm.recommender_id:
            myAcceptBtn = DIV(
                A(SPAN(T("Done"), _class="btn btn-info"), _href=URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False))),
                _style="margin-top:16px; text-align:center;",
            )
        else:
            myAcceptBtn = DIV(A(SPAN(T("Done"), _class="btn btn-info"), _href=URL(c="manager", f="all_recommendations")), _style="margin-top:16px; text-align:center;")
        return dict(
            pageHelp=getHelp(request, auth, db, "#RecommenderAddReviewers"),
            customText=getText(request, auth, db, "#RecommenderAddReviewersText"),
            titleIcon="search",
            pageTitle=getTitle(request, auth, db, "#RecommenderAddReviewersTitle"),
            myAcceptBtn=myAcceptBtn,
            content=myContents,
            form="",
            myUpperBtn=myUpperBtn,
        )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def cancel_email_to_registered_reviewer():
    reviewId = request.vars["reviewId"]
    if reviewId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    review = db.t_reviews[reviewId]
    if review is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recommId = review.recommendation_id
    db(db.t_reviews.id == reviewId).delete()
    # session.flash = T('Reviewer "%s" cancelled') % (common_small_html.mkUser(auth, db, review.reviewer_id).flatten())
    redirect(URL(c="recommender", f="reviewers", vars=dict(recommId=recommId)))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def send_review_cancellation():
    response.view = "default/myLayout.html"

    reviewId = request.vars["reviewId"]
    if reviewId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    review = db.t_reviews[reviewId]
    if review is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.t_recommendations[review.recommendation_id]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    art = db.t_articles[recomm.article_id]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    reviewer = db.auth_user[review.reviewer_id]
    if reviewer is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    destPerson = common_small_html.mkUser(auth, db, reviewer.id).flatten()

    sender = None
    if auth.user_id == recomm.recommender_id:
        sender = common_small_html.mkUser(auth, db, recomm.recommender_id).flatten()
    elif auth.has_membership(role="manager"):
        sender = "The Managing Board of " + myconf.get("app.longname") + " on behalf of " + common_small_html.mkUser(auth, db, recomm.recommender_id).flatten()

    description = myconf.take("app.description")
    longname = myconf.take("app.longname")
    appName = myconf.take("app.name")
    contact = myconf.take("contacts.managers")
    art_authors = "[undisclosed]" if (art.anonymous_submission) else art.authors
    art_title = art.title
    art_doi = common_small_html.mkLinkDOI(recomm.doi or art.doi)
    # art_doi = (recomm.doi or art.doi)
    linkTarget = None  # URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
    if (review.review_state or "Awaiting response") == "Awaiting response":
        hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewCancellation", art)
        mail_template = emailing_tools.getMailTemplateHashtag(db, hashtag_template)
        default_subject = emailing_tools.replaceMailVars(mail_template["subject"], locals())
        default_message = emailing_tools.replaceMailVars(mail_template["content"], locals())

    else:
        pass
    replyto = db(db.auth_user.id == auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
    replyto_address = "%s, %s" % (replyto.email, myconf.take("contacts.managers"))
    form = SQLFORM.factory(
        Field("replyto", label=T("Reply-to"), type="string", length=250, requires=IS_EMAIL(error_message=T("invalid email!")), default=replyto_address, writable=False),
        Field("cc", label=T("CC"), type="string", length=250, requires=IS_EMAIL(error_message=T("invalid email!")), default="%s, %s" % (replyto.email, contact), writable=False),
        Field(
            "reviewer_email",
            label=T("Reviewer email address"),
            type="string",
            length=250,
            default=reviewer.email,
            writable=False,
            requires=IS_EMAIL(error_message=T("invalid email!")),
        ),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )
    form.element(_type="submit")["_value"] = T("Send email")
    form.element("textarea[name=message]")["_style"] = "height:500px;"

    if form.process().accepted:
        try:
            review.update_record(review_state="Cancelled")
            emailing.send_reviewer_invitation(
                session, auth, db, reviewId, replyto_address, myconf.take("contacts.managers"), hashtag_template, request.vars["subject"], request.vars["message"], None, linkTarget
            )
        except Exception as e:
            session.flash = (session.flash or "") + T("Email failed.")
            raise e
        if auth.user_id == recomm.recommender_id:
            redirect(URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False)))
        else:
            redirect(URL(c="manager", f="all_recommendations"))

    return dict(
        form=form,
        pageHelp=getHelp(request, auth, db, "#EmailForRegisterdReviewer"),
        titleIcon="envelope",
        pageTitle=getTitle(request, auth, db, "#EmailForRegisteredReviewerInfoTitle"),
        customText=getText(request, auth, db, "#EmailForRegisteredReviewerInfo"),
        myBackButton=common_small_html.mkBackButton(),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def send_reviewer_generic_mail():
    response.view = "default/myLayout.html"

    def fail(message):
        session.flash = T(message)
        referrer = request.env.http_referer
        redirect(referrer if referrer else URL("default", "index"))

    reviewId = request.vars["reviewId"]
    if reviewId is None:
        fail("no review specified")
    review = db.t_reviews[reviewId]
    if review is None:
        fail(f"no such review: {reviewId}")
    recomm = db.t_recommendations[review.recommendation_id]
    if recomm is None:
        fail("no recommendation for review")
    art = db.t_articles[recomm.article_id]
    if art is None:
        fail("no article for review")
    reviewer = db.auth_user[review.reviewer_id]
    if reviewer is None:
        fail("no reviewer for review")

    description = myconf.take("app.description")
    longname = myconf.take("app.longname")
    appName = myconf.take("app.name")
    contact = myconf.take("contacts.managers")

    sender_email = db(db.auth_user.id == auth.user_id).select().last().email

    mail_template = emailing_tools.getMailTemplateHashtag(db, "#ReviewerGenericMail")

    # template variables, along with all other locals()
    destPerson = common_small_html.mkUser(auth, db, review.reviewer_id)
    recommenderPerson = common_small_html.mkUser(auth, db, auth.user_id)
    articleDoi = common_small_html.mkLinkDOI(recomm.doi or art.doi)
    articleTitle = art.title
    articleAuthors = "[undisclosed]" if (art.anonymous_submission) else art.authors

    default_subject = emailing_tools.replaceMailVars(mail_template["subject"], locals())
    default_message = emailing_tools.replaceMailVars(mail_template["content"], locals())

    req_is_email = IS_EMAIL(error_message=T("invalid email!"))

    form = SQLFORM.factory(
        Field("reviewer_email", label=T("Reviewer email address"), type="string", length=250, requires=req_is_email, default=reviewer.email, writable=False),
        Field("cc", label=T("CC"), type="string", length=250, requires=IS_EMPTY_OR(req_is_email), default=sender_email, writable=True),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )
    form.element(_type="submit")["_value"] = T("Send email")
    form.element("textarea[name=message]")["_style"] = "height:500px;"

    if form.process().accepted:
        try:
            emailing.send_reviewer_generic_mail(session, auth, db, reviewer.email, recomm, request.vars)
        except Exception as e:
            session.flash = (session.flash or "") + T("Email failed.")
            raise e
        if auth.user_id == recomm.recommender_id:
            redirect(URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False)))
        else:
            redirect(URL(c="manager", f="all_recommendations"))

    return dict(
        form=form,
        pageHelp=getHelp(request, auth, db, "#EmailForRegisterdReviewer"),
        titleIcon="envelope",
        pageTitle=getTitle(request, auth, db, "#EmailForRegisteredReviewerInfoTitle"),
        customText=getText(request, auth, db, "#EmailForRegisteredReviewerInfo"),
        myBackButton=common_small_html.mkBackButton(),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def email_for_registered_reviewer():
    response.view = "default/myLayout.html"

    reviewId = request.vars["reviewId"]
    if reviewId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    review = db.t_reviews[reviewId]
    if review is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.t_recommendations[review.recommendation_id]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    art = db.t_articles[recomm.article_id]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    reviewer = db.auth_user[review.reviewer_id]
    if reviewer is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    replyto = db(db.auth_user.id == recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
    if replyto is None:
        session.flash = T("Recommender for the article doesn't exist", lazy=False)
        redirect(request.env.http_referer)
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    destPerson = common_small_html.mkUser(auth, db, reviewer.id).flatten()

    sender = None
    if auth.user_id == recomm.recommender_id:
        sender = common_small_html.mkUser(auth, db, recomm.recommender_id).flatten()
    elif auth.has_membership(role="manager"):
        sender = "The Managing Board of " + myconf.get("app.longname") + " on behalf of " + common_small_html.mkUser(auth, db, recomm.recommender_id).flatten()

    description = myconf.take("app.description")
    longname = myconf.take("app.longname") # DEPRECATED: for compatibility purpose; to be removed after checkings
    appLongName = myconf.take("app.longname")
    appName = myconf.take("app.name")
    art_authors = "[undisclosed]" if (art.anonymous_submission) else art.authors
    art_title = art.title
    art_doi = common_small_html.mkLinkDOI(recomm.doi or art.doi)

    reviewLimitText = str(myconf.get("config.review_limit_text", default="three weeks"))

    if not review.quick_decline_key:
        review.quick_decline_key = web2py_uuid()
        review.update_record()

    linkTarget = URL(c="user", f="my_reviews", vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
    declineLinkTarget = URL(c="user_actions", f="decline_review", scheme=scheme, host=host, port=port, vars=dict(
        id=review.id,
        key=review.quick_decline_key,
    ))
    parallelText = ""
    if parallelSubmissionAllowed:
        parallelText += (
            """Note that if the authors abandon the process at %(appLongName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appLongName)s website as recognition of their work and in order to enable critical discussion.\n"""
            % locals()
        )
        if art.parallel_submission:
            parallelText += (
                """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appLongName)s, and hope you will agree to review this preprint.\n"""
                % locals()
            )
    
    if pciRRactivated:
        report_surey = db(db.t_report_survey.article_id == art.id).select().last()
        pci_rr_vars = emailing_vars.getPCiRRinvitationTexts(report_surey)
        programmaticRR_invitation_text = pci_rr_vars["programmaticRR_invitation_text"]
        signedreview_invitation_text = pci_rr_vars["signedreview_invitation_text"]

    hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationRegisterUser", art)
    mail_template = emailing_tools.getMailTemplateHashtag(db, hashtag_template)
    default_subject = emailing_tools.replaceMailVars(mail_template["subject"], locals())
    default_message = emailing_tools.replaceMailVars(mail_template["content"], locals())

    # replyto = db(db.auth_user.id==auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()

    replyto_address = "%s, %s" % (replyto.email, myconf.take("contacts.managers"))
    form = SQLFORM.factory(
        Field("replyto", label=T("Reply-to"), type="string", length=250, requires=IS_EMAIL(error_message=T("invalid e-mail!")), default=replyto_address, writable=False),
        Field(
            "cc",
            label=T("CC"),
            type="string",
            length=250,
            requires=IS_EMAIL(error_message=T("invalid e-mail!")),
            default="%s, %s" % (replyto.email, myconf.take("contacts.managers")),
            writable=False,
        ),
        Field(
            "reviewer_email",
            label=T("Reviewer e-mail address"),
            type="string",
            length=250,
            default=reviewer.email,
            writable=False,
            requires=IS_EMAIL(error_message=T("invalid e-mail!")),
        ),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )
    form.element(_type="submit")["_value"] = T("Send e-mail")
    form.element("textarea[name=message]")["_style"] = "height:500px;"

    if form.process().accepted:
        try:
            emailing.send_reviewer_invitation(
                session,
                auth,
                db,
                reviewId,
                replyto_address,
                myconf.take("contacts.managers"),
                hashtag_template,
                request.vars["subject"],
                request.vars["message"],
                None,
                linkTarget,
                declineLinkTarget,
            )
        except Exception as e:
            session.flash = (session.flash or "") + T("E-mail failed.")
            raise e
        redirect(URL(c="recommender", f="reviewers", vars=dict(recommId=recomm.id)))

    return dict(
        form=form,
        pageHelp=getHelp(request, auth, db, "#EmailForRegisterdReviewer"),
        titleIcon="envelope",
        pageTitle=getTitle(request, auth, db, "#EmailForRegisteredReviewerInfoTitle"),
        customText=getText(request, auth, db, "#EmailForRegisteredReviewerInfo"),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def email_for_new_reviewer():
    response.view = "default/myLayout.html"

    recommId = request.vars["recommId"]
    recomm = db.t_recommendations[recommId]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    art = db.t_articles[recomm.article_id]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    sender = None
    if auth.user_id == recomm.recommender_id:
        sender = common_small_html.mkUser(auth, db, recomm.recommender_id).flatten()
    elif auth.has_membership(role="manager"):
        sender = "The Managing Board of " + myconf.get("app.longname") + " on behalf of " + common_small_html.mkUser(auth, db, recomm.recommender_id).flatten()

    description = myconf.take("app.description")
    longname = myconf.take("app.longname") # DEPRECATED
    appLongName = myconf.take("app.longname")
    appName = myconf.take("app.name")
    thematics = myconf.take("app.thematics")
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    site_url = URL(c="default", f="index", scheme=scheme, host=host, port=port)
    art_authors = "[Undisclosed]" if (art.anonymous_submission) else art.authors
    art_title = art.title
    art_doi = common_small_html.mkLinkDOI(recomm.doi or art.doi)

    reviewLimitText = str(myconf.get("config.review_limit_text", default="three weeks"))

    # NOTE: 4 parallel submission
    parallelText = ""
    if parallelSubmissionAllowed:
        parallelText += (
            """Note that if the authors abandon the process at %(appLongName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appLongName)s website as recognition of their work and in order to enable critical discussion.\n"""
            % locals()
        )
        if art.parallel_submission:
            parallelText += (
                """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appLongName)s, and hope you will agree to review this preprint.\n"""
                % locals()
            )
    
    # PCi RR specific mail vars based on report survey answers
    if pciRRactivated:
        report_surey = db(db.t_report_survey.article_id == art.id).select().last()
        pci_rr_vars = emailing_vars.getPCiRRinvitationTexts(report_surey)
        programmaticRR_invitation_text = pci_rr_vars["programmaticRR_invitation_text"]
        signedreview_invitation_text = pci_rr_vars["signedreview_invitation_text"]
    
    hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationNewUser", art)
    mail_template = emailing_tools.getMailTemplateHashtag(db, hashtag_template)
    default_subject = emailing_tools.replaceMailVars(mail_template["subject"], locals())
    default_message = emailing_tools.replaceMailVars(mail_template["content"], locals())

    replyto = db(db.auth_user.id == recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
    replyto_address = "%s, %s" % (replyto.email, myconf.take("contacts.managers"))
    form = SQLFORM.factory(
        Field("replyto", label=T("Reply-to"), type="string", length=250, requires=IS_EMAIL(error_message=T("invalid e-mail!")), default=replyto_address, writable=False),
        Field(
            "cc",
            label=T("CC"),
            type="string",
            length=250,
            requires=IS_EMAIL(error_message=T("invalid e-mail!")),
            default="%s, %s" % (replyto.email, myconf.take("contacts.managers")),
            writable=False,
        ),
        Field("reviewer_first_name", label=T("Reviewer first name"), type="string", length=250, required=True),
        Field("reviewer_last_name", label=T("Reviewer last name"), type="string", length=250, required=True),
        Field("reviewer_email", label=T("Reviewer e-mail address"), type="string", length=250, requires=IS_EMAIL(error_message=T("invalid e-mail!"))),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )

    form.element(_type="submit")["_value"] = T("Send e-mail")

    if form.process().accepted:
        new_user_id = None
        request.vars.reviewer_email = request.vars.reviewer_email.lower()

        # search for already-existing user
        existingUser = db(db.auth_user.email.upper() == request.vars["reviewer_email"].upper()).select().last()
        if existingUser:
            new_user_id = existingUser.id
            # NOTE: update reset_password_key if not empty with a fresh new one
            if existingUser.reset_password_key is not None and existingUser.reset_password_key != "":
                max_time = time.time()
                # NOTE adapt long-delay key for invitation
                reset_password_key = str((15 * 24 * 60 * 60) + int(max_time)) + "-" + web2py_uuid()
                existingUser.update_record(reset_password_key=reset_password_key)
                existingUser = None
            nbExistingReviews = db((db.t_reviews.recommendation_id == recommId) & (db.t_reviews.reviewer_id == new_user_id)).count()
        else:
            # create user
            try:
                my_crypt = CRYPT(key=auth.settings.hmac_key)
                crypt_pass = my_crypt(auth.random_password())[0]
                new_user_id = db.auth_user.insert(
                    first_name=request.vars["reviewer_first_name"],
                    last_name=request.vars["reviewer_last_name"],
                    email=request.vars["reviewer_email"],
                    password=crypt_pass,
                )
                # reset password link
                new_user = db.auth_user(new_user_id)
                max_time = time.time()
                # NOTE adapt long-delay key for invitation
                reset_password_key = str((15 * 24 * 60 * 60) + int(max_time)) + "-" + web2py_uuid()
                new_user.update_record(reset_password_key=reset_password_key)
                nbExistingReviews = 0
                session.flash = T('User "%(reviewer_email)s" created.') % (request.vars)
            except:
                session.flash = T("User creation failed :-(")
                redirect(request.env.http_referer)

        if nbExistingReviews > 0:
            session.flash = T('User "%(reviewer_email)s" have already been invited. E-mail cancelled.') % (request.vars)
        else:
            # Create review
            quickDeclineKey = web2py_uuid()

            # BUG : managers could invite recommender as reviewer (incoherent status)
            reviewId = db.t_reviews.insert(
                    recommendation_id=recommId,
                    reviewer_id=new_user_id,
                    review_state=None,                  # State will be validated after emailing
                    quick_decline_key=quickDeclineKey,
            )

            linkTarget = URL(c="user", f="my_reviews", vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)

            if existingUser:
                try:
                    hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationRegisterUser", art)

                    linkTarget = URL(c="user", f="my_reviews", vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
                    declineLinkTarget = URL(c="user_actions", f="decline_review", vars=dict(
                        id=reviewId,
                        key=quickDeclineKey,
                    ),
                    scheme=scheme, host=host, port=port)

                    emailing.send_reviewer_invitation(
                        session,
                        auth,
                        db,
                        reviewId,
                        replyto_address,
                        myconf.take("contacts.managers"),
                        hashtag_template,
                        request.vars["subject"],
                        request.vars["message"],
                        None,
                        linkTarget,
                        declineLinkTarget,
                    )
                except Exception as e:
                    session.flash = (session.flash or "") + T("E-mail failed.")
                    pass
            else:
                try:
                    hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationNewUser", art)

                    declineLinkTarget = URL(c="user_actions", f="decline_review", vars=dict(
                        id=reviewId,
                        key=quickDeclineKey,
                    ),
                    scheme=scheme, host=host, port=port)

                    emailing.send_reviewer_invitation(
                        session,
                        auth,
                        db,
                        reviewId,
                        replyto_address,
                        myconf.take("contacts.managers"),
                        hashtag_template,
                        request.vars["subject"],
                        request.vars["message"],
                        reset_password_key,
                        linkTarget,
                        declineLinkTarget,
                    )
                except Exception as e:
                    session.flash = (session.flash or "") + T("E-mail failed.")
                    pass

        redirect(URL(c="recommender", f="reviewers", vars=dict(recommId=recommId)))

    return dict(
        form=form,
        pageHelp=getHelp(request, auth, db, "#EmailForNewReviewer"),
        titleIcon="envelope",
        pageTitle=getTitle(request, auth, db, "#EmailForNewReviewerInfoTitle"),
        customText=getText(request, auth, db, "#EmailForNewReviewerInfo"),
        myBackButton=common_small_html.mkBackButton(),
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def add_contributor():
    response.view = "default/myLayout.html"

    recommId = request.vars["recommId"]
    onlyAdd = request.vars["onlyAdd"] or True
    goBack = request.vars["goBack"]
    recomm = db.t_recommendations[recommId]
    if (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        roleClass = " pci-manager" if (recomm.recommender_id != auth.user_id) and auth.has_membership(role="manager") else " pci-recommender"
        art = db.t_articles[recomm.article_id]
        contributorsListSel = db((db.t_press_reviews.recommendation_id == recommId) & (db.t_press_reviews.contributor_id == db.auth_user.id)).select(
            db.t_press_reviews.id, db.auth_user.id
        )
        contributorsList = []
        for con in contributorsListSel:
            contributorsList.append(
                LI(
                    common_small_html.mkUserWithMail(auth, db, con.auth_user.id),
                    A(
                        T("Delete"),
                        _class="btn btn-warning pci-smallBtn " + roleClass,
                        _href=URL(c="recommender_actions", f="del_contributor", vars=dict(pressId=con.t_press_reviews.id)),
                        _title=T("Delete this co-recommender"),
                    ),  # , _style='margin-left:8px; color:red;'),
                )
            )
        if len(contributorsList) > 0:
            myContents = DIV(
                LABEL(T("Co-recommenders:")),
                UL(contributorsList),
            )
        else:
            myContents = ""

        myAcceptBtn = DIV(common_small_html.mkBackButton("Done", target=goBack), _style="width:100%; text-align:center;")
        myBackButton = ""
        db.t_press_reviews._id.readable = False
        db.t_press_reviews.recommendation_id.default = recommId
        db.t_press_reviews.recommendation_id.writable = False
        db.t_press_reviews.recommendation_id.readable = False
        db.t_press_reviews.contributor_id.writable = True
        db.t_press_reviews.contributor_id.label = T("Select a co-recommender")
        db.t_press_reviews.contributor_id.represent = lambda text, row: common_small_html.mkUserWithMail(auth, db, row.contributor_id) if row else ""
        alreadyCo = db((db.t_press_reviews.recommendation_id == recommId) & (db.t_press_reviews.contributor_id != None))._select(db.t_press_reviews.contributor_id)
        otherContribsQy = db(
            (db.auth_user._id != auth.user_id)
            & (db.auth_user._id == db.auth_membership.user_id)
            & (db.auth_membership.group_id == db.auth_group._id)
            & (db.auth_group.role == "recommender")
            & (~db.auth_user.id.belongs(alreadyCo))
        )
        db.t_press_reviews.contributor_id.requires = IS_IN_DB(otherContribsQy, db.auth_user.id, "%(last_name)s, %(first_name)s")
        form = SQLFORM(db.t_press_reviews)
        form.element(_type="submit")["_value"] = T("Add")
        form.element(_type="submit")["_class"] = "btn btn-info " + roleClass
        if form.process().accepted:
            redirect(URL(c="recommender", f="add_contributor", vars=dict(recommId=recomm.id, goBack=goBack, onlyAdd=onlyAdd)))
        if art.already_published and onlyAdd is False:
            myAcceptBtn = DIV(
                A(
                    SPAN(current.T("Add a co-recommender later"), _class="btn btn-info" + roleClass),
                    _href=URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id)),
                )
                if len(contributorsListSel) == 0
                else "",
                A(
                    SPAN(current.T("Write / Edit your recommendation"), _class="btn btn-default" + roleClass),
                    _href=URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id)),
                ),
                _style="margin-top:64px; text-align:center;",
            )
        return dict(
            myBackButton=myBackButton,
            pageHelp=getHelp(request, auth, db, "#RecommenderAddContributor"),
            customText=getText(request, auth, db, "#RecommenderAddContributorText"),
            titleIcon="link",
            pageTitle=getTitle(request, auth, db, "#RecommenderAddContributorTitle"),
            content=myContents,
            form=form,
            myAcceptBtn=myAcceptBtn,
        )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def contributions():
    response.view = "default/myLayout.html"

    recommId = request.vars["recommId"]
    recomm = db.t_recommendations[recommId]
    if (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        myContents = recommender_module.mkRecommendationFormat(auth, db, recomm)
        query = db.t_press_reviews.recommendation_id == recommId
        db.t_press_reviews._id.readable = False
        db.t_press_reviews.recommendation_id.default = recommId
        db.t_press_reviews.recommendation_id.writable = False
        db.t_press_reviews.recommendation_id.readable = False
        db.t_press_reviews.contributor_id.writable = True
        db.t_press_reviews.contributor_id.represent = lambda text, row: common_small_html.mkUserWithMail(auth, db, row.contributor_id) if row else ""
        alreadyCo = db(db.t_press_reviews.recommendation_id == recommId)._select(db.t_press_reviews.contributor_id)
        otherContribsQy = db(
            (db.auth_user._id != auth.user_id)
            & (db.auth_user._id == db.auth_membership.user_id)
            & (db.auth_membership.group_id == db.auth_group._id)
            & (db.auth_group.role == "recommender")
            & (~db.auth_user.id.belongs(alreadyCo))
        )
        db.t_press_reviews.contributor_id.requires = IS_IN_DB(otherContribsQy, db.auth_user.id, "%(last_name)s, %(first_name)s")
        grid = SQLFORM.grid(
            query,
            details=False,
            editable=False,
            deletable=True,
            create=True,
            searchable=False,
            maxtextlength=250,
            paginate=100,
            csv=csv,
            exportclasses=expClass,
            fields=[db.t_press_reviews.recommendation_id, db.t_press_reviews.contributor_id],
        )
        
        myScript = SCRIPT(common_tools.get_template("script", "contributions.js"), _type="text/javascript")
        return dict(
            pageHelp=getHelp(request, auth, db, "#RecommenderContributionsToPressReviews"),
            customText=getText(request, auth, db, "#RecommenderContributionsToPressReviewsText"),
            pageTitle=getTitle(request, auth, db, "#RecommenderContributionsToPressReviewsTitle"),
            contents=myContents,
            grid=grid,
            # myAcceptBtn = myAcceptBtn,
            myFinalScript=myScript,
        )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def edit_recommendation():
    response.view = "default/myLayout.html"

    recommId = request.vars["recommId"]
    recomm = db.t_recommendations[recommId]
    art = db.t_articles[recomm.article_id]
    isPress = None

    amICoRecommender = db((db.t_press_reviews.recommendation_id == recomm.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0

    if (recomm.recommender_id != auth.user_id) and not amICoRecommender and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    elif art.status not in ("Under consideration", "Pre-recommended", "Pre-revision", "Pre-cancelled", "Pre-recommended-private"):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        nbCoRecomm = db(db.t_press_reviews.recommendation_id == recommId).count()
        isPress = art.already_published

        isStage1 = art.art_stage_1_id is None
        if pciRRactivated and isStage1:
            recommendPrivateDivPciRR = SPAN(
                INPUT(
                    _id="opinion_recommend_private",
                    _name="recommender_opinion",
                    _type="radio",
                    _value="do_recommend_private",
                    _checked=(recomm.recommendation_state == "Recommended"),
                ),
                B(current.T("I recommend this preprint")),
                BR(),
                current.T("but keep it private until a stage 2 is validated"),
                _class="pci-radio pci-recommend-private btn-success",
                _style="margin-top: 10px",
            )
        else:
            recommendPrivateDivPciRR = ""

        triptyque = DIV(
            DIV(
                H3(current.T("Your decision")),
                DIV(
                    DIV(
                        SPAN(
                            INPUT(
                                _id="opinion_recommend", _name="recommender_opinion", _type="radio", _value="do_recommend", _checked=(recomm.recommendation_state == "Recommended")
                            ),
                            B(current.T("I recommend this preprint")),
                            _class="pci-radio pci-recommend btn-success",
                        ),
                        recommendPrivateDivPciRR,
                        _class="pci2-flex-column",
                    ),
                    SPAN(
                        INPUT(_id="opinion_revise", _name="recommender_opinion", _type="radio", _value="do_revise", _checked=(recomm.recommendation_state == "Revision")),
                        B(current.T("This preprint merits a revision")),
                        _class="pci-radio pci-review btn-default",
                    ),
                    SPAN(
                        INPUT(_id="opinion_reject", _name="recommender_opinion", _type="radio", _value="do_reject", _checked=(recomm.recommendation_state == "Rejected")),
                        B(current.T("I reject this preprint")),
                        _class="pci-radio pci-reject btn-warning",
                    ),
                    _class="pci2-flex-row pci2-justify-center pci2-align-items-start",
                ),
                # TEST # SPAN(INPUT(_id='opinion_none', _name='recommender_opinion', _type='radio', _value='none', _checked=(recomm.recommendation_state=='?')), current.T('I still hesitate'), _class='pci-radio btn-default'),
                _style="padding:8px; margin-bottom:12px;",
            ),
            _style="text-align:center;",
        )
        buttons = [
            INPUT(_type="Submit", _name="save", _class="btn btn-info", _value="Save"),
        ]
        if isPress:
            # buttons += [INPUT(_type='Submit', _name='terminate', _class='btn btn-success', _value='Save and submit your recommendation')]
            db.t_recommendations.no_conflict_of_interest.writable = False
        else:
            if (recomm.recommender_id == auth.user_id) or auth.has_membership(role="manager"):
                buttons += [INPUT(_type="Submit", _name="terminate", _class="btn btn-success", _value="Save and submit your decision")]
        db.t_recommendations.recommendation_state.readable = False
        db.t_recommendations.recommendation_state.writable = False
        if isPress:
            db.t_recommendations.recommendation_title.label = T("Recommendation title")
            db.t_recommendations.recommendation_comments.label = T("Recommendation")
            customText = getText(request, auth, db, "#RecommenderEditRecommendationText")
            pageHelp = getHelp(request, auth, db, "#RecommenderEditRecommendation")
            pageTitle = getTitle(request, auth, db, "#RecommenderEditRecommendationTitle")
        else:
            db.t_recommendations.recommendation_title.label = T("Decision or recommendation title")
            db.t_recommendations.recommendation_comments.label = T("Decision or recommendation")
            customText = getText(request, auth, db, "#RecommenderEditDecisionText")
            pageHelp = getHelp(request, auth, db, "#RecommenderEditDecision")
            pageTitle = getTitle(request, auth, db, "#RecommenderEditDecisionTitle")

        if isPress:
            fields = ["no_conflict_of_interest", "recommendation_title", "recommendation_comments"]
        else:
            fields = ["no_conflict_of_interest", "recommendation_title", "recommendation_comments", "recommender_file", "recommender_file_data"]

        db.t_recommendations.recommendation_comments.requires = IS_NOT_EMPTY()

        form = SQLFORM(db.t_recommendations, record=recomm, deletable=False, fields=fields, showid=False, buttons=buttons, upload=URL("default", "download"))
        if isPress is False:
            form.insert(0, triptyque)

        if form.process().accepted:
            if form.vars.save:
                if form.vars.recommender_opinion == "do_recommend":
                    recomm.recommendation_state = "Recommended"
                elif form.vars.recommender_opinion == "do_recommend_private":
                    recomm.recommendation_state = "Recommended"
                elif form.vars.recommender_opinion == "do_revise":
                    recomm.recommendation_state = "Revision"
                elif form.vars.recommender_opinion == "do_reject":
                    recomm.recommendation_state = "Rejected"
                # print form.vars.no_conflict_of_interest
                if form.vars.no_conflict_of_interest:
                    recomm.no_conflict_of_interest = True
                recomm.recommendation_title = form.vars.recommendation_title
                recomm.recommendation_comments = form.vars.recommendation_comments
                # manual bypass:
                rf = request.vars.recommender_file
                if rf is not None:
                    if hasattr(rf, "value"):
                        recomm.recommender_file_data = rf.value
                        recomm.recommender_file = rf
                    elif hasattr(request.vars, "recommender_file__delete") and request.vars.recommender_file__delete == "on":
                        recomm.recommender_file_data = None
                        recomm.recommender_file = None
                recomm.update_record()
                session.flash = T("Recommendation saved", lazy=False)
                redirect(URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=isPress)))
            elif form.vars.terminate:
                if (recomm.recommender_id == auth.user_id) or auth.has_membership(role="manager"):
                    session.flash = T("Recommendation saved and completed", lazy=False)
                    recomm.no_conflict_of_interest = form.vars.no_conflict_of_interest
                    recomm.recommendation_title = form.vars.recommendation_title
                    recomm.recommendation_comments = form.vars.recommendation_comments
                    recomm.recommender_file = form.vars.recommender_file
                    # manual bypass:
                    rf = request.vars.recommender_file
                    if rf is not None:
                        if hasattr(rf, "value"):
                            recomm.recommender_file_data = rf.value
                            recomm.recommender_file = rf
                        elif hasattr(request.vars, "recommender_file__delete") and request.vars.recommender_file__delete == "on":
                            recomm.recommender_file_data = None
                            recomm.recommender_file = None
                    if isPress is False:
                        if form.vars.recommender_opinion == "do_recommend":
                            recomm.recommendation_state = "Recommended"
                            art.status = "Pre-recommended"
                        elif form.vars.recommender_opinion == "do_recommend_private":
                            recomm.recommendation_state = "Recommended"
                            art.status = "Pre-recommended-private"
                        elif form.vars.recommender_opinion == "do_revise":
                            recomm.recommendation_state = "Revision"
                            art.status = "Pre-revision"
                        elif form.vars.recommender_opinion == "do_reject":
                            recomm.recommendation_state = "Rejected"
                            art.status = "Pre-rejected"
                    else:
                        recomm.recommendation_state = "Recommended"
                        art.status = "Pre-recommended"
                    recomm.update_record()
                    art.update_record()
                    redirect(URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=isPress)))
                else:
                    session.flash = T("Unauthorized: You need to be recommender or manager", lazy=False)
        elif form.errors:
            response.flash = T("Form has errors", lazy=False)

        if isPress is False:
            myScript = common_tools.get_template("script", "edit_recommendation.js")
        else:
            myScript = common_tools.get_template("script", "edit_recommendation_is_press.js")

        return dict(
            form=form,
            customText=customText,
            pageHelp=pageHelp,
            titleIcon="edit",
            pageTitle=pageTitle,
            myFinalScript=SCRIPT(myScript),
            myBackButton=common_small_html.mkBackButton(),
            deleteFileButtonsScript=SCRIPT(common_tools.get_template("script", "add_delete_recommendation_file_buttons_recommender.js"), _type="text/javascript"),
        )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def my_co_recommendations():
    response.view = "default/myLayout.html"

    query = (
        (db.t_press_reviews.contributor_id == auth.user_id)
        & (db.t_press_reviews.recommendation_id == db.t_recommendations.id)
        & (db.t_recommendations.article_id == db.t_articles.id)
    )
    db.t_press_reviews.contributor_id.writable = False
    db.t_press_reviews.recommendation_id.writable = False
    db.t_articles._id.readable = False
    db.t_recommendations._id.label = T("Recommendation")
    db.t_recommendations._id.represent = lambda rId, row: common_small_html.mkArticleCellNoRecommFromId(auth, db, rId)
    db.t_articles.status.writable = False
    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.art_stage_1_id.writable = False
    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(auth, db, text, showStage=pciRRactivated, stage1Id=row.t_articles.art_stage_1_id)
    db.t_press_reviews._id.readable = False
    db.t_recommendations.recommender_id.represent = lambda uid, row: common_small_html.mkUserWithMail(auth, db, uid)
    db.t_recommendations.article_id.readable = False
    db.t_articles.already_published.represent = lambda press, row: common_small_html.mkJournalImg(auth, db, press)

    db.t_articles.scheduled_submission_date.readable = False
    db.t_articles.scheduled_submission_date.writable = False

    grid = SQLFORM.grid(
        query,
        searchable=False,
        deletable=False,
        create=False,
        editable=False,
        details=False,
        maxtextlength=500,
        paginate=10,
        csv=csv,
        exportclasses=expClass,
        fields=[
            db.t_articles.scheduled_submission_date,
            db.t_articles.art_stage_1_id,
            db.t_articles.last_status_change,
            db.t_articles.status,
            db.t_articles.uploaded_picture,
            db.t_recommendations._id,
            db.t_articles._id,
            db.t_articles.already_published,
            db.t_recommendations.article_id,
            db.t_recommendations.recommender_id,
        ],
        links=[
            dict(
                header=T("Other co-recommenders"), body=lambda row: recommender_module.mkOtherContributors(auth, db, row.t_recommendations if "t_recommendations" in row else row)
            ),
            dict(
                header=T(""),
                body=lambda row: A(
                    SPAN(current.T("View"), _class="btn btn-default pci-button"),
                    _href=URL(c="recommender", f="recommendations", vars=dict(articleId=row.t_articles.id)),
                    _class="button",
                    _title=current.T("View this co-recommendation"),
                ),
            ),
        ],
        orderby=~db.t_articles.last_status_change | ~db.t_press_reviews.id,
        _class="web2py_grid action-button-absolute",
    )
    myContents = ""
    return dict(
        pageHelp=getHelp(request, auth, db, "#RecommenderMyPressReviews"),
        customText=getText(request, auth, db, "#RecommenderMyPressReviewsText"),
        titleIcon="link",
        pageTitle=getTitle(request, auth, db, "#RecommenderMyPressReviewsTitle"),
        # myBackButton=common_small_html.mkBackButton(),
        contents=myContents,
        grid=grid,
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "web2py_button_absolute.js"), _type="text/javascript"),
    )


######################################################################################################################################################################
# @auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
# def review_emails():
# response.view = "default/info.html"

# revId = request.vars["reviewId"]
# rev = db.t_reviews[revId]
# myContents = DIV()
# myContents.append(SPAN(B(T("Reviewer: ")), common_small_html.mkUserWithMail(auth, db, rev.reviewer_id)))
# myContents.append(H2(T("E-mails:")))
# myContents.append(
#     DIV(
#         # WIKI((rev.emailing or '*None yet*'), safe_mode=False)
#         XML((rev.emailing or "<b>None yet</b>")),
#         _style="margin-left:20px; border-left:1px solid #cccccc; padding-left:4px;",
#     )
# )
# return dict(
#     pageHelp=getHelp(request, auth, db, "#RecommenderReviewEmails"),
#     customText=getText(request, auth, db, "#RecommenderReviewEmailsText"),
#     titleIcon="envelope",
#     pageTitle=getTitle(request, auth, db, "#RecommenderReviewEmailsTitle"),
#     myBackButton=common_small_html.mkBackButton(),
#     message=myContents,
# )


@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def review_emails():
    response.view = "default/myLayout.html"

    reviewId = request.vars["reviewId"]
    review = db.t_reviews[reviewId]
    if not review:
        redirect(URL(c="recommender", f="my_recommendations"))

    recommendation = db.t_recommendations[review.recommendation_id]

    amICoRecommender = db((db.t_press_reviews.recommendation_id == recommendation.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0

    if (recommendation.recommender_id != auth.user_id) and not amICoRecommender and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

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

    reviewer = db.auth_user[review.reviewer_id]
    reviewerEmail = reviewer.email if reviewer else None
    grid = SQLFORM.grid(
        ((db.mail_queue.dest_mail_address == reviewerEmail) & (db.mail_queue.recommendation_id == recommendation.id)),
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
        myBackButton=common_small_html.mkBackButton(target=URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False), user_signature=True)),
        grid=grid,
        myFinalScript=myScript,
        absoluteButtonScript=SCRIPT(common_tools.get_template("script", "web2py_button_absolute.js"), _type="text/javascript"),
    )


@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def article_reviews_emails():
    response.view = "default/myLayout.html"

    articleId = request.vars["articleId"]
    article = db.t_articles[articleId]
    recommendation = db(db.t_recommendations.article_id == articleId).select().last()
    amICoRecommender = db((db.t_press_reviews.recommendation_id == recommendation.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0

    if (recommendation.recommender_id != auth.user_id) and not amICoRecommender and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    reviews = db(db.t_reviews.recommendation_id == recommendation.id).select()
    reviewers = []
    for review in reviews:
        reviewer = db.auth_user[review.reviewer_id]
        if reviewer:
            reviewers.append(reviewer["email"])

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
        db((db.mail_queue.article_id == articleId) & (db.mail_queue.dest_mail_address.belongs(reviewers))),
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
        pageTitle=getTitle(request, auth, db, "#ArticleReviewsEmailsTitle"),
        customText=getText(request, auth, db, "#ArticleReviewsEmailsText"),
        pageHelp=getHelp(request, auth, db, "#ArticleReviewsEmails"),
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
