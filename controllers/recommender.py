# -*- coding: utf-8 -*-

import time
import re
import copy
import datetime
from dateutil.relativedelta import *
from typing import cast, Optional

from gluon.utils import web2py_uuid
from gluon.contrib.markdown import WIKI
from gluon.html import markmin_serializer

from app_modules.helper import *

from controller_modules import recommender_module
from controller_modules import user_module
from controller_modules import adjust_grid

from app_components import app_forms

from app_components import article_components
from app_components import ongoing_recommendation
from app_components import recommender_components

from app_modules import emailing_parts
from app_modules import common_tools
from app_modules import common_small_html
from app_modules import emailing_tools
from app_modules import emailing_vars
from app_modules import emailing

from models.user import User
from models.recommendation import Recommendation
from models.article import Article

from app_modules.common_small_html import md_to_html
from app_modules.emailing import isScheduledTrack

# to change to common
from controller_modules import admin_module


# frequently used constants
myconf = AppConfig(reload=True)
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
trgmLimit = myconf.get("config.trgm_limit") or 0.4

pciRRactivated = myconf.get("config.registered_reports", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()
Field.CC = db.Field.CC
######################################################################################################################################################################
def index():
    return my_awaiting_articles()

# Common function for articles needing attention
@auth.requires(auth.has_membership(role="recommender"))
def fields_awaiting_articles():
    myVars = request.vars

    articles = db.t_articles
    full_text_search_fields = [
        'id',
        'title',
        'authors',
        'thematics',
        'upload_timestamp',
    ]

    def article_html(art_id):
        return common_small_html.mkRepresentArticleLight(auth, db, art_id)

    articles.id.readable = True
    articles.id.represent = lambda text, row: article_html(row.id)
    articles.thematics.label = "Thematics fields"
    articles.thematics.type = "string"
    articles.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, zero=None)

    for a_field in articles.fields:
        if not a_field in full_text_search_fields:
            articles[a_field].readable = False

    articles.id.label = "Article"
    articles.upload_timestamp.represent = lambda t, row: common_small_html.mkLastChange(t)

    links = []
    links.append(dict(header=T(""), body=lambda row: recommender_module.mkViewEditArticleRecommenderButton(auth, db, row)))

    excluded = db.t_excluded_recommenders
    excluded_articles = db(
        excluded.excluded_recommender_id == auth.user_id
    )._select(excluded.article_id)
    query = (
        (articles.status == "Awaiting consideration")
      & ~articles.id.belongs(excluded_articles)
    )
    original_grid = SQLFORM.grid(
        query,
        searchable=True,
        editable=False,
        deletable=False,
        create=False,
        details=False,
        maxtextlength=250,
        paginate=10,
        csv=csv,
        exportclasses=expClass,
        buttons_placement=False,
        fields=[
            articles.id,
            articles.thematics,
            articles.upload_timestamp,
        ],
        links=links,
        orderby=articles.id,
        _class="web2py_grid action-button-absolute",
    )

    # options to be removed from the search dropdown:
    remove_options = ['t_articles.id']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'articles_temp', remove_options)

    response.view = "default/gab_list_layout.html"
    return dict(
        titleIcon="inbox",
        pageTitle=getTitle(request, auth, db, "#RecommenderAwaitingArticlesTitle"),
        customText=getText(request, auth, db, "#RecommenderArticlesAwaitingRecommendationText:InMyFields"),
        grid=grid,
        pageHelp=getHelp(request, auth, db, "#RecommenderArticlesAwaitingRecommendation:InMyFields"),
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def search_reviewers():
    myVars = request.vars
    reg_user = myVars["regUser"]

    excludeList = []
    myGoal = "4review"  # default
    for myVar in myVars:
        if isinstance(myVars[myVar], list):
            myValue = (myVars[myVar])[1]
        else:
            myValue = myVars[myVar]
        if myVar == "myGoal":
            myGoal = myValue
        elif myVar == "exclude":
            excludeList += myValue.split(",")
    recomm = None
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

    for i, val in enumerate(excludeList):
        try: excludeList[i] = int(val)
        except: pass

    if not recomm or (
            (recomm.recommender_id != auth.user_id)
            and not is_co_recommender(auth, db, recomm.id) and not auth.has_membership(role="manager")
        ):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    def collect_reviewer_stats(fr):
        nb_reviews = db((db.t_reviews.reviewer_id == fr['id']) & (db.t_reviews.review_state == "Review completed")).count()
        nb_recomm = db((db.t_recommendations.recommender_id == fr['id']) & (db.t_recommendations.recommendation_state == "Recommended")).count()
        nb_co_recomm = db((db.t_press_reviews.contributor_id == fr['id']) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id)).count()
        is_recomm = fr['id'] in user_module.getAllRecommenders(db)
        fr['reviewer_stat'] = [nb_reviews, nb_recomm, nb_co_recomm, is_recomm, fr['id']]

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
    users = db.auth_user

    for f in users.fields:
        if not f in full_text_search_fields:
            users[f].readable = False

    users.id.label = "Name"
    users.id.readable = True
    users.id.represent = lambda uid, row: DIV(
            common_small_html.mkReviewerInfo(auth, db, db.auth_user[uid]),
            _class="pci-w300Cell")

    users.thematics.label = "Thematics fields"
    users.thematics.type = "string"
    users.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, zero=None)

    pageTitle = getTitle(request, auth, db, "#RecommenderSearchReviewersTitle")
    customText = getText(request, auth, db, "#RecommenderSearchReviewersText")
    pageHelp = getHelp(request, auth, db, "#RecommenderSearchReviewers")

    if myGoal == "4review":
            header = T("")
            # use above defaults for: pageTitle, customText, pageHelp
    elif myGoal == "4press":
            header = T("Propose contribution")
            pageTitle = getTitle(request, auth, db, "#RecommenderSearchCollaboratorsTitle")
            customText = getText(request, auth, db, "#RecommenderSearchCollaboratorsText")
            pageHelp = getHelp(request, auth, db, "#RecommenderSearchCollaborators")

    links = [
        dict(
            header=header,
            body=lambda row: "" if row.id in excludeList else \
                recommender_module.mkSuggestReviewToButton(auth, db, row, recommId, myGoal, reg_user)
        )]

    original_grid = SQLFORM.smartgrid(
            users,
            create=False,
            buttons_placement=False,
            maxtextlength=250,
            paginate=100,
            csv=csv,
            exportclasses=expClass,
            fields=[
                users.id,
                users.thematics,
                users.keywords,
            ],
            links=links,
            orderby=users.id,
            _class="web2py_grid action-button-absolute",
    )

    # the grid is adjusted after creation to adhere to our requirements
    remove_options = ['auth_user.id']
    grid = adjust_grid.adjust_grid_basic(original_grid, 'reviewers', remove_options)

    response.view = "default/gab_list_layout.html"
    myFinalScript = common_tools.get_script("popover.js")

    return dict(
            pageHelp=pageHelp,
            titleIcon="search",
            pageTitle=pageTitle,
            customText=customText,
            myBackButton=common_small_html.mkBackButton(),
            myFinalScript=myFinalScript,
            grid=grid,
            absoluteButtonScript=common_tools.absoluteButtonScript,
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
        myScript = common_tools.get_script("new_submission.js")

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
    db.t_articles.user_id.represent = lambda userId, row: common_small_html.mkAnonymousArticleField(
            auth, db, row.anonymous_submission,
            common_small_html.get_name_from_details(row.submitter_details)
            or common_small_html.mkUser(auth, db, userId), row.id
    )
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
        db.t_articles.upload_timestamp.represent = lambda t, row: common_small_html.mkLastChange(t)
        db.t_articles.last_status_change.represent = lambda t, row: common_small_html.mkLastChange(t)
        db.t_articles._id.readable = True
        db.t_articles._id.represent = lambda text, row: common_small_html.mkRepresentArticleLight(auth, db, text)
        db.t_articles._id.label = T("Article")
    else:  # we are in grid's form
        db.t_articles._id.readable = False

    fields = [
            db.t_articles.art_stage_1_id,
            db.t_articles.last_status_change,
            db.t_articles.status,
            db.t_articles._id,
            db.t_articles.upload_timestamp,
            db.t_articles.anonymous_submission,
    ]
    if parallelSubmissionAllowed: fields += [
            db.t_articles.parallel_submission,
    ]
    fields += [
            db.t_articles.thematics,
            db.t_articles.keywords,
            db.t_articles.user_id,
            db.t_articles.auto_nb_recommendations,
            db.t_articles.submitter_details,
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
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def accept_new_article_to_recommend():
    actionFormUrl = None
    appLongName = None
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
        appLongName = myconf.take("app.longname")
        hiddenVarsForm = dict(articleId=articleId, ethics_approved=True)
        actionFormUrl = URL("recommender_actions", "do_accept_new_article_to_recommend")
        longname = myconf.take("app.longname")

    pageTitle = getTitle(request, auth, db, "#AcceptPreprintInfoTitle")
    customText = getText(request, auth, db, "#AcceptPreprintInfoText")

    response.view = "controller/recommender/accept_new_article_to_recommend.html"
    return dict(
        customText=customText, titleIcon="education", pageTitle=pageTitle, actionFormUrl=actionFormUrl, appLongName=appLongName, hiddenVarsForm=hiddenVarsForm, articleId=articleId, pciRRactivated=pciRRactivated
    )

######################################################################################################################################################################
# Display completed articles
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def completed_evaluations():
    resu = _my_recomms(["Recommended-private", "Recommended", "Rejected", "Cancelled"])
    resu["customText"] = getText(request, auth, db, "#RecommenderCompletedArticlesText")
    resu["titleIcon"] = "ok-sign"
    resu["pageTitle"] = getTitle(request, auth, db, "#RecommenderCompletedArticlesTitle")
    resu["pageHelp"] = getHelp(request, auth, db, "#RecommenderCompletedArticles")
    return resu

######################################################################################################################################################################
# Display non-completed articles
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def my_recommendations():
    pressReviews = request.vars["pressReviews"]
    resu = _my_recomms(["Pre-recommended", "Pre-rejected", "Pre-revision", "Pre-recommended-private", "Awaiting revision", "Under consideration", "Scheduled submission under consideration", "Scheduled submission pending", "Scheduled submission revision"], pressReviews=pressReviews)
    return resu

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def _my_recomms(statuses, pressReviews=None):
    response.view = "default/myLayout.html"

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    # goBack='%s://%s%s' % (request.env.wsgi_url_scheme, request.env.http_host, request.env.request_uri)
    goBack = URL(re.sub(r".*/([^/]+)$", "\\1", request.env.request_uri), scheme=scheme, host=host, port=port)

    links = [
            dict(header=T("Co-recommenders"), body=lambda row: common_small_html.mkCoRecommenders(
                auth, db, row.t_recommendations if "t_recommendations" in row else row, goBack)),
    ]
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
    query = (
          (db.t_recommendations.recommender_id == auth.user_id)
        & (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_recommendations.id == db.v_article_recommender.recommendation_id)
        &  (db.t_articles.status.belongs(statuses))
    )

    isPress = (pressReviews == True)
    if isPress:  ## NOTE: POST-PRINTS
        query = query & (db.t_articles.already_published == True)
        pageTitle = getTitle(request, auth, db, "#RecommenderMyRecommendationsPostprintTitle")
        customText = getText(request, auth, db, "#RecommenderMyRecommendationsPostprintText")
        db.t_recommendations.article_id.label = T("Postprint")
    else:  ## NOTE: PRE-PRINTS
        query = query & (db.t_articles.already_published == False)
        pageTitle = getTitle(request, auth, db, "#RecommenderMyRecommendationsPreprintTitle")
        customText = getText(request, auth, db, "#RecommenderMyRecommendationsPreprintText")
        fields += [
            db.t_recommendations.recommendation_state,
            db.t_recommendations.is_closed,
            db.t_recommendations.recommender_id,
        ]
        links += [
            dict(header=T("Reviews"), body=lambda row: recommender_components.getReviewsSubTable(auth, db, response, request, row.t_recommendations if "t_recommendations" in row else row)),
        ]
        db.t_recommendations.article_id.label = T("Preprint")

    links += [
            dict(
                header=T(""), body=lambda row: common_small_html.mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if "t_recommendations" in row else row)
            ),
    ]

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
        _class="web2py_grid action-button-absolute recommender-preprints-table",
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
        absoluteButtonScript=common_tools.absoluteButtonScript,
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
    db.t_articles.doi.label = T("Postprint DOI")
    myScript = common_tools.get_script("picture_rights_change_sync_uploaded_picture.js")

    fields = ["title", "authors", "article_source", "doi", "picture_rights_ok", "uploaded_picture", "abstract", "thematics", "keywords"]
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
        myFinalScript=myScript,
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
            "q1_1",
            "q1_2",
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
            "tracked_changes_url",
            "q25",
            "q26",
            "q26_details",
            "q27",
            "q27_details",
            "q28",
            "q28_details",
            "q29",
            "q30",
            "q30_details",
            "q31",
            "q32",
        ]

    form = SQLFORM(
        db.t_report_survey,
        survey.id,
        fields=fields,
        readonly=True,
    )

    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp(request, auth, db, "#RecommenderReportSurvey"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#RecommenderReportSurveyTitle"),
        customText=getText(request, auth, db, "#RecommenderReportSurveyText", maxWidth="800"),
        form=form,
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
    db.t_reviews.reviewer_id.represent = lambda text, row: TAG(row.reviewer_details) if row.reviewer_details else common_small_html.mkUserWithMail(auth, db, row.reviewer_id) if row else ""
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
        redirect(URL(c=request.controller, f=" "))
    if (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(URL(c=request.controller, f=" "))
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
        db.t_reviews.anonymous_agreement.writable = False
        db.t_reviews.anonymous_agreement.label = T("Name may be passed on to journal")
        db.t_reviews.no_conflict_of_interest.writable = False
        db.t_reviews.no_conflict_of_interest.label = T("No conflicts of interest")
        db.t_reviews.review.writable = auth.has_membership(role="manager")
        db.t_reviews.review_state.writable = auth.has_membership(role="manager")
        db.t_reviews.review_state.represent = lambda text, row: common_small_html.mkReviewStateDiv(auth, db, text)
        db.t_reviews.emailing.writable = False
        db.t_reviews.emailing.represent = lambda text, row: XML(text) if text else ""
        db.t_reviews.last_change.writable = True

        if pciRRactivated:
            db.t_reviews.review_pdf.label = T("Review files")

        if len(request.args) == 0 or (len(request.args) == 1 and request.args[0] == "auth_user"):  # grid view
            selectable = [(T("Re-open selected reviews"), lambda ids: [recommender_module.reopen_review(auth, db, ids)], "button btn btn-info")]
            db.t_reviews.review.represent = lambda text, row: DIV(WIKI(text or ""), _class="pci-div4wiki")
            db.t_reviews.emailing.readable = False
        else:  # form view
            selectable = None
            db.t_reviews.review.represent = lambda text, row: WIKI(text or "")
            db.t_reviews.emailing.readable = True
        if pciRRactivated:
            common_tools.divert_review_pdf_to_multi_upload()

        def onvalidation(form):
            files = form.vars.review_pdf
            review = db((db.t_reviews.recommendation_id == recommId) & (db.t_reviews.reviewer_id == form.vars.reviewer_id)).select().last()
            if type(files) == list and pciRRactivated:
                common_tools.handle_multiple_uploads(review, files)

        query = db.t_reviews.recommendation_id == recommId
        grid = SQLFORM.grid(
            query,
            details=True,
            editable=(lambda row:
                (auth.has_membership(role="manager") and row.reviewer_id != None)
            ),
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
            onvalidation=onvalidation,
            _class="web2py_grid action-button-absolute",
            upload=URL("default", "download")
        )

        # This script renames the "Add record" button
        myScript = common_tools.get_script("rename_add_record_button.js")

        return dict(
            pageHelp=getHelp(request, auth, db, "#RecommenderArticleReviews"),
            customText=getText(request, auth, db, "#RecommenderArticleReviewsText"),
            titleIcon="eye-open",
            pageTitle=getTitle(request, auth, db, "#RecommenderArticleReviewsTitle"),
            # myBackButton=common_small_html.mkBackButton(),
            content=myContents,
            grid=grid,
            myFinalScript=myScript,
            absoluteButtonScript=common_tools.absoluteButtonScript,
        )

######################################################################################################################################################################
def edit_reviewers(reviewersListSel, recomm, recommId=None, new_round=False, new_stage=False):
            reviewers_emails = [auth.user.email] # To prevent duplication
            reviewersIds = [auth.user_id]
            reviewersList = []
            current_reviewers_id = []
            for con in reviewersListSel:
                if con.review_state is None:  # delete this unfinished review declaration
                    db(db.t_reviews.id == con.id).delete()
                else:
                    reviewer_id = con.reviewer_id
                    if reviewer_id:
                        reviewer_email = db.auth_user[reviewer_id].email
                    elif con.reviewer_details:
                        reviewer_email = re.search(r'\[(.*?)\]', con.reviewer_details).group(1)
                    else:
                        reviewer_email = None

                    if recomm.recommender_id == reviewer_id:
                        selfFlag = True
                        if con.review_state == "Cancelled":
                            selfFlagCancelled = True
                    if reviewer_email != None and reviewer_email in reviewers_emails:
                        pass
                    else:
                        reviewers_emails.append(reviewer_email)
                        reviewersIds.append(reviewer_id)
                        display = LI(
                                TAG(con.reviewer_details) if con.reviewer_details else \
                                        common_small_html.mkUserWithMail(auth, db, reviewer_id),
                                " ",
                                B(T(" (YOU) ")) if reviewer_id == recomm.recommender_id else "",
                                I("(" + (con.review_state or "") + ")"), 
                                )
                        if new_round or new_stage:
                            current_reviewers = db((db.t_reviews.recommendation_id == recomm.id)).select(db.t_reviews.reviewer_id)
                            for i in current_reviewers:
                                current_reviewers_id.append(i.reviewer_id)
                            display = LI(
                                TAG(con.reviewer_details) if con.reviewer_details else \
                                        common_small_html.mkUserWithMail(auth, db, reviewer_id),
                                " ",
                                B(T(" (YOU) ")) if reviewer_id == recomm.recommender_id else "",
                                A( SPAN(current.T("Prepare an Invitation"), _class="btn btn-default"),
                                    _href=URL(c="recommender_actions", f="suggest_review_to", vars=dict(recommId=recommId, reviewerId=reviewer_id, new_round=new_round, new_stage=new_stage), user_signature=True)) \
                                        if reviewer_id not in current_reviewers_id else "",
                            )
                        
                        reviewersList.append(display)
                    
            return list(set(reviewersList)), reviewersIds


######################################################################################################################################################################
def get_prev_reviewers(article_id, recomm, new_round=False, new_stage=False):
    total_count = []
    recommList = db((db.t_recommendations.article_id == article_id)).select(db.t_recommendations.id, orderby=db.t_recommendations.id)
    for i in recommList:
        total_count.append(i.id)
    total_count.sort()
    prevRoundreviewersList = []
    latestRoundRecommId = None
    text = ""
    if new_stage:
        latestRoundRecommId = recomm.id
        prevRoundreviewersList = db((db.t_reviews.recommendation_id.belongs(total_count)) & (db.t_reviews.review_state == "Review completed")).select(
            db.t_reviews.id, db.t_reviews.reviewer_id, db.t_reviews.review_state, db.t_reviews.reviewer_details
        )
        text = "Choose a reviewer from Stage 1"
    if new_round:
        previousRoundRecommId = total_count[-2]
        latestRoundRecommId = max(total_count)
        prevRoundreviewersList = db((db.t_reviews.recommendation_id == previousRoundRecommId) & (db.t_reviews.review_state == "Review completed")).select(
            db.t_reviews.id, db.t_reviews.reviewer_id, db.t_reviews.review_state, db.t_reviews.reviewer_details
        )
        text = "Reviewers from the previous round of review"
    prevReviewersList, prevRoundreviewersIds = edit_reviewers(prevRoundreviewersList, recomm, latestRoundRecommId, new_round=new_round, new_stage=new_stage)
    prevRoundHeader = DIV(
        BUTTON(H4(B(text, SPAN(_class="caret"))), _class="collapsible2 active", _type="button"),
        DIV(P(UL(prevReviewersList)),
        _class="content2",              
        _style="width:100%; max-width: 1200px")) if prevRoundreviewersList else ""
    


    customText=getText(request, auth, db, "#RecommenderReinviteReviewersText")

    if not text: prevRoundHeader = ""

    return prevRoundHeader, customText


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
    reg_user, new_stage = False, False
    if article.report_stage == "STAGE 2":
        reg_user, new_stage = True, True
    if not recomm:
        return my_recommendations()
    co_recommender = is_co_recommender(auth, db, recomm.id)
    if (recomm.recommender_id != auth.user_id) and not co_recommender and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:  
        recomm_round = db((db.t_recommendations.article_id == article.id)).count()
        first_round_id = db((db.t_recommendations.article_id == article.id)).select(orderby=db.t_recommendations.id).first()
        no_of_first_round_reviews = db((db.t_reviews.recommendation_id == first_round_id)).count()
        prevRoundHeader = ""
        customText=getText(request, auth, db, "#RecommenderAddReviewersText")
        if (pciRRactivated and article.art_stage_1_id is not None) and ((recomm_round == 2 and no_of_first_round_reviews == 0) or (recomm_round == 1)):
            prevRoundHeader, customText = get_prev_reviewers(article.art_stage_1_id, recomm, new_stage=new_stage)
        elif recomm_round > 1:
            prevRoundHeader, customText = get_prev_reviewers(article.id, recomm, new_round=True)

        suggested_reviewers_by_author = ""
        suggested_reviewers_by_reviewers = ""
        oppossed_reviewers = ""
        if not pciRRactivated:
            if article.suggest_reviewers:
                (suggested_by_author, suggested_by_reviewers) = separate_suggestions(article.suggest_reviewers)
                if len(suggested_by_author) > 0:
                    suggested_reviewers_by_author = DIV(
                        BUTTON(H4(B("Reviewers suggested by the authors", SPAN(_class="caret"))), _class="collapsible2 active", _type="button"),
                        DIV(P(UL(suggested_by_author),
                            H5(B("You may invite them by clicking on one of the buttons below"))),
                            _class="content2"),
                        )
                if len(suggested_by_reviewers) > 0:
                    suggested_reviewers_by_reviewers = DIV()
                    suggested_reviewers_by_reviewers.append(BUTTON(H4(B("Alternative reviewers suggested by invited reviewers", SPAN(_class="caret"))), _class="collapsible2 active", _type="button"))
                    reviewer_box = DIV(_class="content2")
                    for reviewer in suggested_by_reviewers:
                        reviewer_ul = P("%s suggested:"%reviewer, UL(suggested_by_reviewers[reviewer]))
                        reviewer_box.append(reviewer_ul)
                    reviewer_box.append(H5(B("You may invite them by clicking on one of the buttons below")))
                    suggested_reviewers_by_reviewers.append(reviewer_box)
                        
            if article.competitors:
                oppossed_reviewers = DIV(
                    BUTTON(H4(B("Opposed reviewers"), T(" (reviewers that the authors suggest NOT to invite)"), SPAN(_class="caret"), ), _class="collapsible2 active", _type="button"),
                    DIV(P(UL(article.competitors)),
                          __class="content2"),)
        else:
            report = db(db.t_report_survey.article_id == recomm.article_id).select()
            if report:
                if report[0].q8:
                    suggested_reviewers_by_author = DIV(
                        BUTTON(H4(B("Reviewers suggested by the authors", SPAN(_class="caret"))), _class="collapsible2 active", _type="button"),
                        DIV(P(UL(report[0].q8),
                            H5(B("You may invite them by clicking on one of the buttons below"))),
                            _class="content2"),
                        )
                if report[0].q9:
                    oppossed_reviewers = DIV(
                        BUTTON(H4(B("Opposed reviewers"), T(" (reviewers that the authors suggest NOT to invite)"), SPAN(_class="caret"), ), _class="collapsible2 active", _type="button"),
                        DIV(P(UL(report[0].q9),),
                            _class="content2"),
                        )
            if article.suggest_reviewers:
                (suggested_by_author, suggested_by_reviewers) = separate_suggestions(article.suggest_reviewers)
                if len(suggested_by_reviewers) > 0:
                    suggested_reviewers_by_reviewers = DIV()
                    suggested_reviewers_by_reviewers.append(BUTTON(H4(B("Alternative reviewers suggested by invited reviewers", SPAN(_class="caret"))), _class="collapsible2 active", _type="button"))
                    reviewer_box = DIV(_class="content2")
                    for reviewer in suggested_by_reviewers:
                        reviewer_ul = P("%s suggested:"%reviewer, UL(suggested_by_reviewers[reviewer]))
                        reviewer_box.append(reviewer_ul)
                    reviewer_box.append(H5(B("You may invite them by clicking on one of the buttons below")))
                    suggested_reviewers_by_reviewers.append(reviewer_box)
        
        reviewersListSel = db((db.t_reviews.recommendation_id == recommId)).select(
            db.t_reviews.id, db.t_reviews.review_state, db.t_reviews.reviewer_id, db.t_reviews.reviewer_details
        )
        selfFlag = False
        selfFlagCancelled = False
        reviewersList, reviewersIds = edit_reviewers(reviewersListSel, recomm)
        excludeList = ",".join(map(str, filter(lambda x: x is not None, reviewersIds)))
        if len(reviewersList) > 0:
            myContents = DIV(
                BUTTON(H4(B("Reviewers already invited:", SPAN(_class="caret"))), _class="collapsible2 active", _type="button"),
                DIV(P(UL(reviewersList)),
                _class="content2",
                _style="width:100%; max-width: 1200px"))
        else:
            myContents = ""
        longname = myconf.take("app.longname")
        myUpperBtn = DIV(
            A(
                SPAN(current.T("Choose a reviewer from the %s database") % (longname), _class="btn btn-success"),
                _href=URL(c="recommender", f="search_reviewers", vars=dict(recommId=recommId, myGoal="4review", regUser=reg_user, exclude=excludeList)),
            ),
            A(
                SPAN(current.T("Choose a reviewer outside %s database") % (longname), _class="btn btn-default"),
                _href=URL(c="recommender", f="email_for_new_reviewer", vars=dict(recommId=recommId, new_stage=new_stage)),
            ),
            _style="margin-top:8px; margin-bottom:16px; text-align:left; max-width:1200px; width: 100%",
        )

        url = URL(c="manager", f="all_recommendations")
        if auth.user_id == recomm.recommender_id:
            url = URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False))
        elif co_recommender:
            url = URL(c="recommender", f="recommendations", vars=dict(articleId=recomm.article_id))

        myAcceptBtn = DIV(A(SPAN(T("Done"), _class="btn btn-info"), _href=url), _style="margin-top:16px; text-align:center;")
        myScript = common_tools.get_script("collapsibles.js")

        return dict(
            pageHelp=getHelp(request, auth, db, "#RecommenderAddReviewers"),
            customText=customText,
            titleIcon="search",
            pageTitle=getTitle(request, auth, db, "#RecommenderAddReviewersTitle"),
            myAcceptBtn=myAcceptBtn,
            content=myContents,
            prevContent=prevRoundHeader,
            suggested_reviewers_by_author=suggested_reviewers_by_author,
            suggested_reviewers_by_reviewers=suggested_reviewers_by_reviewers,
            oppossed_reviewers=oppossed_reviewers,
            form="",
            myUpperBtn=myUpperBtn,
            myFinalScript=myScript,
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
    art_authors = emailing.mkAuthors(art)
    art_title = md_to_html(art.title)
    art_doi = common_small_html.mkLinkDOI(recomm.doi or art.doi)
    # art_doi = (recomm.doi or art.doi)

    # aliases - for some templates
    articleTitle = art_title
    articleDoi = art_doi
    articleAuthors = art_authors

    linkTarget = None  # URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)

    if pciRRactivated:
        sched_sub_vars = emailing_vars.getPCiRRScheduledSubmissionsVars(art)
        scheduledSubmissionDate = sched_sub_vars["scheduledSubmissionDate"]
        scheduledSubmissionLatestReviewStartDate = sched_sub_vars["scheduledSubmissionLatestReviewStartDate"]
        scheduledReviewDueDate = sched_sub_vars["scheduledReviewDueDate"]
        snapshotUrl = sched_sub_vars["snapshotUrl"]

    if review.review_state == "Awaiting response":
        hashtag_template = "#DefaultReviewCancellation"
    if review.review_state == "Awaiting review":
        hashtag_template = "#DefaultReviewAlreadyAcceptedCancellation"

    hashtag_template = emailing_tools.getCorrectHashtag(hashtag_template, art)

    if "AlreadyAccepted" in hashtag_template and not "Scheduled" in hashtag_template:
        hashtag_template = "#DefaultReviewAlreadyAcceptedCancellation"

    mail_template = emailing_tools.getMailTemplateHashtag(db, hashtag_template)
    default_subject = emailing_tools.replaceMailVars(mail_template["subject"], locals())
    default_message = emailing_tools.replaceMailVars(mail_template["content"], locals())

    replyto = db(db.auth_user.id == auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
    replyto_address = "%s, %s" % (replyto.email, myconf.take("contacts.managers"))
    default_subject = emailing.patch_email_subject(default_subject, recomm.article_id)
    default_cc = '%s, %s'%(replyto.email, contact)

    form = SQLFORM.factory(
        Field("replyto", label=T("Reply-to"), type="string", length=250, default=replyto_address, writable=False),
        Field.CC(default=default_cc),
        Field(
            "reviewer_email",
            label=T("Reviewer email address"),
            type="string",
            length=250,
            default=reviewer.email,
            writable=False,
            requires=IS_EMAIL(error_message=T("invalid e-mail!")),
        ),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )
    form.element(_type="submit")["_value"] = T("Send email")
    form.element("textarea[name=message]")["_style"] = "height:500px;"

    if form.process().accepted:
        clean_cc_addresses, cc_errors = emailing_tools.clean_addresses(form.vars.cc)
        cc_addresses = emailing_tools.list_addresses(clean_cc_addresses)

        clean_replyto_adresses, replyto_errors = emailing_tools.clean_addresses(replyto_address)
        replyto_addresses = emailing_tools.list_addresses(clean_replyto_adresses)
        
        try:
            emailing.send_reviewer_invitation(
                session, auth, db, reviewId, replyto_addresses, cc_addresses, hashtag_template, request.vars["subject"], request.vars["message"], None, linkTarget
            )
            review.update_record(review_state="Cancelled")
        except Exception as e:
            session.flash = (session.flash or "") + T("Email failed.")
            raise e
        if auth.user_id == recomm.recommender_id:
            redirect(URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False)))
        else:
            redirect(URL(c="manager", f="all_recommendations"))

    reminder_hashtag = ["#ReminderReviewerReviewSoonDue", "#ReminderReviewerReviewDue", "#ReminderReviewerReviewOverDue"]
    emailing.delete_reminder_for_reviewer(db, reminder_hashtag, reviewId)
    emailing.delete_reminder_for_reviewer(db, ["#ReminderScheduledReviewComingSoon"], reviewId)
    
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
    articleTitle = md_to_html(art.title)
    articleAuthors = emailing.mkAuthors(art)

    default_subject = emailing_tools.replaceMailVars(mail_template["subject"], locals())
    default_message = emailing_tools.replaceMailVars(mail_template["content"], locals())

    default_subject = emailing.patch_email_subject(default_subject, recomm.article_id)

    req_is_email = IS_EMAIL(error_message=T("invalid e-mail!"))
    replyto = db(db.auth_user.id == auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()

    replyTo = ", ".join([replyto.email, contact])
    default_cc = '%s, %s'%(sender_email, contact)

    form = SQLFORM.factory(
        Field("reviewer_email", label=T("Reviewer email address"), type="string", length=250, requires=req_is_email, default=reviewer.email, writable=False),
        Field.CC(default=default_cc),
        Field("replyto", label=T("Reply-to"), type="string", length=250, default=replyTo, writable=False),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )
    form.element(_type="submit")["_value"] = T("Send email")
    form.element("textarea[name=message]")["_style"] = "height:500px;"

    if form.process().accepted:
        clean_replyto_adresses, replyto_errors = emailing_tools.clean_addresses(replyTo)
        request.vars["replyto"] = clean_replyto_adresses
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
def convert_string(value):
    if value == "True":
        return True
    else:
        return False

def get_review_duration_options(article):
    review_duration_choices = db.review_duration_choices
    review_duration_default = db.review_duration_default

    if isScheduledTrack(article):
        review_duration_default = db.review_duration_scheduled_track
        review_duration_choices = [review_duration_default]

    return dict(
            default=review_duration_default,
            requires=IS_IN_SET(review_duration_choices, zero=None),
            writable=True,
    )

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def email_for_registered_reviewer():
    response.view = "default/myLayout.html"

    recommendation_id = request.vars["recommId"]
    new_round = convert_string(request.vars["new_round"])
    new_stage = convert_string(request.vars["new_stage"])
    reg_user = convert_string(request.vars["regUser"])
    reviewer_id = request.vars["reviewerId"]

    if recommendation_id is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    
    recommendation = Recommendation.get_by_id(db, recommendation_id)
    if not recommendation:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
        return
    
    article = Article.get_by_id(db, recommendation.article_id)
    if not article:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
        return
    
    reviewer = User.get_by_id(db, reviewer_id)
    if not reviewer:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
        return

    
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

    sender: Optional[User] = None
    if auth.has_membership(role="manager"):
        sender = User.get_by_id(db, recommendation.recommender_id)
    else:
        sender = cast(User, auth.user)

    mail_vars = emailing_tools.getMailForReviewerCommonVars(auth, db, sender, article, recommendation, reviewer.last_name, new_round)

    parallelText = ""
    if parallelSubmissionAllowed:
        parallelText += (
            """Note that if the authors abandon the process at %(appLongName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appLongName)s website as recognition of their work and in order to enable critical discussion.\n"""
            % mail_vars
        )
        if article.parallel_submission:
            parallelText += (
                """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appLongName)s, and hope you will agree to review this preprint.\n"""
                % mail_vars
            )

    if pciRRactivated:
        rr_vars = emailing_vars.getRRInvitiationVars(db, article, new_stage)
        mail_vars = dict(mail_vars, **rr_vars)

    hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationRegisteredUser", article)
    if new_round:
        hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationNewRoundRegisteredUser", article)

    destPerson = common_small_html.mkUser(auth, db, reviewer_id).flatten()

    if pciRRactivated and new_stage:
        hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationRegisteredUserReturningReviewer", article)
    if pciRRactivated and reg_user:
        hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationRegisteredUserNewReviewer", article)

    mail_template = emailing_tools.getMailTemplateHashtag(db, hashtag_template)
    default_subject = emailing_tools.replaceMailVars(mail_template["subject"], mail_vars)
    default_message = emailing_tools.replaceMailVars(mail_template["content"], mail_vars)

    default_subject = emailing.patch_email_subject(default_subject, recommendation.article_id)
    
    replyto_address = "%s, %s" % (sender.email, myconf.take("contacts.managers"))
    default_cc = '%s, %s'%(sender.email, myconf.take("contacts.managers"))

    form = SQLFORM.factory(
        Field("review_duration", type="string", label=T("Review duration"), **get_review_duration_options(article)),
        Field("replyto", label=T("Reply-to"), type="string", length=250, default=replyto_address, writable=False),
        Field.CC(default_cc),
        Field(
            "reviewer_email",
            label=T("Reviewer e-mail address"),
            type="string",
            length=250,
            default=db.auth_user[reviewer_id].email,
            writable=False,
            requires=IS_EMAIL(error_message=T("invalid e-mail!")),
        ),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )
    form.element(_type="submit")["_value"] = T("Send e-mail")
    form.element("textarea[name=message]")["_style"] = "height:500px;"

    if form.process().accepted:

        reviewId = db.t_reviews.update_or_insert(recommendation_id=recommendation_id, reviewer_id=reviewer_id)
        review = db.t_reviews[reviewId]
        reviewer = db.auth_user[review.reviewer_id]
        destPerson = common_small_html.mkUser(auth, db, reviewer.id).flatten()

        if not review.quick_decline_key:
            review.quick_decline_key = web2py_uuid()
            review.update_record()

        linkTarget = URL(
                c="default",
                f="invitation_to_review",
                vars=dict(reviewId=review.id),
                scheme=scheme,
                host=host,
                port=port,
            )
        declineLinkTarget = URL(c="user_actions", f="decline_review", scheme=scheme, host=host, port=port, vars=dict(
            id=review.id,
            key=review.quick_decline_key,
        ))

        clean_cc_addresses, cc_errors = emailing_tools.clean_addresses(form.vars.cc)
        cc_addresses = emailing_tools.list_addresses(clean_cc_addresses)

        clean_replyto_adresses, replyto_errors = emailing_tools.clean_addresses(replyto_address)
        replyto_addresses = emailing_tools.list_addresses(clean_replyto_adresses)
        
        review.review_duration = form.vars.review_duration
        review.update_record()
        try:
                emailing.send_reviewer_invitation(
                    session,
                    auth,
                    db,
                    reviewId,
                    replyto_addresses,
                    cc_addresses,
                    hashtag_template,
                    request.vars["subject"],
                    request.vars["message"],
                    None,
                    linkTarget,
                    declineLinkTarget,
                    new_round,
                    True if new_stage or reg_user else False,
                )
        except Exception as e:
            session.flash = (session.flash or "") + T("E-mail failed.")
            raise e
        redirect(URL(c="recommender", f="reviewers", vars=dict(recommId=recommendation.id)))

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

    recommendation_id = request.vars["recommId"]
    new_stage = convert_string(request.vars["new_stage"])
    recommendation = Recommendation.get_by_id(db, recommendation_id)
    if not recommendation:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
        return
    
    if (recommendation.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    article = Article.get_by_id(db, recommendation.article_id)
    if not article:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    sender: Optional[User] = None
    if auth.has_membership(role="manager"):
        sender = User.get_by_id(db, recommendation.recommender_id)
    else:
        sender = cast(User, auth.user)
    
    mail_vars = emailing_tools.getMailForReviewerCommonVars(auth, db, sender, article, recommendation, request.vars["reviewer_last_name"])

    # NOTE: 4 parallel submission
    parallelText = ""
    if parallelSubmissionAllowed:
        parallelText += (
            """Note that if the authors abandon the process at %(appLongName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appLongName)s website as recognition of their work and in order to enable critical discussion.\n"""
            % mail_vars
        )
        if article.parallel_submission:
            parallelText += (
                """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appLongName)s, and hope you will agree to review this preprint.\n"""
                % mail_vars
            )

    if pciRRactivated:
        rr_vars = emailing_vars.getRRInvitiationVars(db, article, new_stage)
        mail_vars = dict(mail_vars, **rr_vars)


    recomm_round = db((db.t_recommendations.article_id == recommendation.article_id) & (db.t_recommendations.id <= recommendation.id)).count()
    if recomm_round > 1:
        hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationNewReviewerNewUserNextRound", article)
    else:
        hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationNewUser", article)
    mail_template = emailing_tools.getMailTemplateHashtag(db, hashtag_template)
    default_subject = emailing_tools.replaceMailVars(mail_template["subject"], mail_vars)
    default_message = emailing_tools.replaceMailVars(mail_template["content"], mail_vars)

    default_subject = emailing.patch_email_subject(default_subject, recommendation.article_id)

    replyto_address = "%s, %s" % (sender.email, myconf.take("contacts.managers"))
    default_cc = '%s, %s'%(sender.email, myconf.take('contacts.managers'))

    form = SQLFORM.factory(
        Field("review_duration", type="string", label=T("Review duration"), **get_review_duration_options(article)),
        Field("replyto", label=T("Reply-to"), type="string", length=250, default=replyto_address, writable=False),
        Field.CC(default=default_cc),
        Field("reviewer_first_name", label=T("Reviewer first name"), type="string", length=250, requires=IS_NOT_EMPTY()),
        Field("reviewer_last_name", label=T("Reviewer last name"), type="string", length=250, requires=IS_NOT_EMPTY()),
        Field("reviewer_email", label=T("Reviewer e-mail address"), type="string", length=250, requires=IS_NOT_EMPTY()),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )

    form.element(_type="submit")["_value"] = T("Send e-mail")

    if form.process().accepted:
        clean_cc_addresses, cc_errors = emailing_tools.clean_addresses(form.vars.cc)
        cc_addresses = emailing_tools.list_addresses(clean_cc_addresses)

        clean_replyto_adresses, replyto_errors = emailing_tools.clean_addresses(replyto_address)
        replyto_addresses = emailing_tools.list_addresses(clean_replyto_adresses)
        
        new_user_id = None
        clean_reviewer_email, clean_reviewer_errors = emailing_tools.clean_addresses(request.vars.reviewer_email.lower())
        request.vars.reviewer_email = clean_reviewer_email

        # NOTE adapt long-delay key for invitation
        reset_password_key = str((15 * 24 * 60 * 60) + int(time.time())) + "-" + web2py_uuid()

        # search for already-existing user
        existingUser = db(db.auth_user.email.upper() == request.vars["reviewer_email"].upper()).select().last()
        if existingUser:
            new_user_id = existingUser.id
            # NOTE: update reset_password_key if not empty with a fresh new one
            if existingUser.reset_password_key:
                existingUser.update_record(reset_password_key=reset_password_key)
                existingUser = None
            nbExistingReviews = db((db.t_reviews.recommendation_id == recommendation_id) & (db.t_reviews.reviewer_id == new_user_id)).count()
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
                    recommendation_id=recommendation_id,
                    reviewer_id=new_user_id,
                    review_state=None,                  # State will be validated after emailing
                    quick_decline_key=quickDeclineKey,
                    review_duration=form.vars.review_duration,
            )

            declineLinkTarget = URL(c="user_actions", f="decline_review", vars=dict(id=reviewId, key=quickDeclineKey),
                    scheme=scheme, host=host, port=port)
            if existingUser:
                    hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationRegisteredUser", article)
                    reset_password_key = None
                    linkTarget = URL(
                        c="default",
                        f="invitation_to_review",
                        vars=dict(reviewId=reviewId),
                        scheme=scheme,
                        host=host,
                        port=port,
                    )
            else:
                    if recomm_round > 1:
                        hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationNewReviewerNewUserNextRound", article)
                    else:
                        hashtag_template = emailing_tools.getCorrectHashtag("#DefaultReviewInvitationNewUser", article)
                    linkTarget = None

            try:
                    emailing.send_reviewer_invitation(
                        session,
                        auth,
                        db,
                        reviewId,
                        replyto_addresses,
                        cc_addresses,
                        hashtag_template,
                        request.vars["subject"],
                        request.vars["message"],
                        reset_password_key,
                        linkTarget,
                        declineLinkTarget,
                        new_stage=new_stage,
                    )
            except Exception as e:
                    session.flash = (session.flash or "") + T("E-mail failed.")
                    pass

        redirect(URL(c="recommender", f="reviewers", vars=dict(recommId=recommendation_id)))

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
            db.t_press_reviews.id, db.auth_user.id, db.t_press_reviews.contributor_details
        )
        contributorsList = []
        for con in contributorsListSel:
            contributorsList.append(
                LI(
                    TAG(con.t_press_reviews.contributor_details) if con.t_press_reviews.contributor_details else \
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
        db.t_press_reviews.contributor_id.represent = lambda text, row: TAG(row.contributor_details) if row.contributor_details else common_small_html.mkUserWithMail(auth, db, row.contributor_id) if row else ""  
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
            fields=[db.t_press_reviews.recommendation_id, db.t_press_reviews.contributor_id, db.t_press_reviews.contributor_details],
        )

        myScript = common_tools.get_script("contributions.js")
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
    scheduled_reject = request.vars["scheduled_reject"]
    isStage1 = art.art_stage_1_id is None
    isPress = None
    publish_now = True
    amICoRecommender = db((db.t_press_reviews.recommendation_id == recomm.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0
    if pciRRactivated and isStage1:
        survey = db(db.t_report_survey.article_id == art.id).select().last()
        publish_now = "IPA" in survey.q21
    if (recomm.recommender_id != auth.user_id) and not amICoRecommender and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    elif art.status not in ("Under consideration", "Pre-recommended", "Pre-revision", "Pre-cancelled", "Pre-recommended-private", "Scheduled submission pending"):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        nbCoRecomm = db(db.t_press_reviews.recommendation_id == recommId).count()
        isPress = art.already_published

        if pciRRactivated and isStage1:
            recommendPrivateDivPciRR = SPAN(
                INPUT(
                    _id="opinion_recommend_private",
                    _name="recommender_opinion",
                    _type="radio",
                    _value="do_recommend_private",
                    _checked=(recomm.recommendation_state == "Recommended"), 
                    _disabled=True if publish_now else False,
                ),
                B(current.T("I recommend this preprint")),
                BR(),
                current.T("but keep it private until a stage 2 is validated"),
                _class="pci-radio pci-recommend-private btn-success",
                _style="margin-top: 10px",
            )
        else:
            recommendPrivateDivPciRR = ""
        reject_radio = SPAN(
                        INPUT(_id="opinion_reject", _name="recommender_opinion", _type="radio", _value="do_reject", _checked=(recomm.recommendation_state == "Rejected")),
                        B(current.T("I reject this preprint")),
                        _class="pci-radio pci-reject btn-warning",
                    )
        triptyque = DIV(
            DIV(
                H3(current.T("Your decision")),
                DIV(
                    (DIV(
                        SPAN(
                            INPUT(
                                _id="opinion_recommend", _name="recommender_opinion", _type="radio", _value="do_recommend", _checked=(recomm.recommendation_state == "Recommended"), 
                                _disabled=False if publish_now else True
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
                    reject_radio) if not scheduled_reject else reject_radio,

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
            if (recomm.recommender_id == auth.user_id) or auth.has_membership(role="manager") or (amICoRecommender and pciRRactivated):
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

        if isPress or scheduled_reject:
            fields = ["no_conflict_of_interest", "recommendation_title", "recommendation_comments"]
        else:
            fields = ["no_conflict_of_interest", "recommendation_title", "recommendation_comments", "recommender_file", "recommender_file_data"]

        db.t_recommendations.recommendation_comments.requires = IS_NOT_EMPTY()

        form = SQLFORM(db.t_recommendations, record=recomm, deletable=False, fields=fields, showid=False, buttons=buttons, upload=URL("default", "download"))

        if scheduled_reject:
            customText = ""
            sched_sub_vars = emailing_vars.getPCiRRScheduledSubmissionsVars(art)
            scheduledSubmissionLatestReviewStartDate = sched_sub_vars["scheduledSubmissionLatestReviewStartDate"]
            scheduledReviewDueDate = sched_sub_vars["scheduledReviewDueDate"]
            recommenderName = common_small_html.mkUser(auth, db, recomm.recommender_id)
            mail_template = emailing_tools.getMailTemplateHashtag(db, "#SubmitterScheduledSubmissionDeskReject")

            description = myconf.take("app.description")
            longname = myconf.take("app.longname")
            appName = myconf.take("app.name")
            destPerson = common_small_html.mkUser(auth, db, art.user_id)
            articleTitle = md_to_html(art.title)

            default_subject = emailing_tools.replaceMailVars(mail_template["subject"], locals())
            default_message = emailing_tools.replaceMailVars(mail_template["content"], locals())
            default_subject = emailing.patch_email_subject(default_subject, art.id)

            form.vars.recommendation_title = recomm.recommendation_title or default_subject
            form.vars.recommendation_comments = recomm.recommendation_comments or default_message

        if isPress is False:
            form.insert(0, triptyque)

        if pciRRactivated and art.report_stage == "STAGE 2" and art.art_stage_1_id is not None:
            stage1_recomm = db((db.t_recommendations.article_id == art.art_stage_1_id)).select(orderby=db.t_recommendations.id).last()
            form.vars.recommendation_title = recomm.recommendation_title or stage1_recomm.recommendation_title
            form.vars.recommendation_comments = recomm.recommendation_comments or stage1_recomm.recommendation_comments

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
                if (recomm.recommender_id == auth.user_id) or auth.has_membership(role="manager") or (amICoRecommender and pciRRactivated):
                    session.flash = T("Recommendation saved and completed", lazy=False)
                    recomm.no_conflict_of_interest = form.vars.no_conflict_of_interest
                    recomm.recommendation_title = form.vars.recommendation_title
                    recomm.recommendation_comments = form.vars.recommendation_comments
                    recomm.recommender_file = form.vars.recommender_file
                    recomm.last_change = request.now
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
                    if  scheduled_reject is None:
                        common_tools.cancel_decided_article_pending_reviews(db, recomm)
                    recomm.update_record()
                    art.update_record()
                    redirect(URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=isPress)))
                else:
                    session.flash = T("Unauthorized: You need to be recommender or manager", lazy=False)
        elif form.errors:
            response.flash = T("Form has errors", lazy=False)

        if isPress is False:
            myScript = common_tools.get_script("edit_recommendation.js")
        else:
            myScript = common_tools.get_script("edit_recommendation_is_press.js")

        return dict(
            form=form,
            customText=customText,
            pageHelp=pageHelp,
            titleIcon="edit",
            pageTitle=pageTitle,
            myFinalScript=myScript,
            myBackButton=common_small_html.mkBackButton(),
            deleteFileButtonsScript=common_tools.get_script("add_delete_recommendation_file_buttons_recommender.js"),
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
    db.t_recommendations.recommender_id.represent = lambda uid, row: TAG(row.t_recommendations.recommender_details) if row.t_recommendations.recommender_details else common_small_html.mkUserWithMail(auth, db, uid)
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
            db.t_recommendations.recommender_details,
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
        absoluteButtonScript=common_tools.absoluteButtonScript,
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

    link_body = lambda row: A(
                (T("Scheduled") if row.removed_from_queue == False else T("Unscheduled")),
                _href=URL(c="admin_actions", f="toggle_shedule_mail_from_queue", vars=dict(emailId=row.id)),
                _class="btn btn-default",
                _style=("background-color: #3e3f3a;" if row.removed_from_queue == False else "background-color: #ce4f0c;"),
            ) if row.sending_status == "pending" else (recommender_module.mkEditResendButton(auth, db, row, reviewId, recommendation.id) if row.sending_status == "sent" else "")
    
    links = [
        dict(
            header="",
            body = link_body,
        )
    ]

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

    myScript = common_tools.get_script("replace_mail_content.js")
    return dict(
        titleIcon="send",
        pageTitle=getTitle(request, auth, db, "#RecommenderReviewEmailsTitle"),
        customText=getText(request, auth, db, "#RecommenderReviewEmailsText"),
        pageHelp=getHelp(request, auth, db, "#RecommenderReviewEmails"),
        myBackButton=common_small_html.mkBackButton(target=URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False), user_signature=True)),
        grid=grid,
        myFinalScript=myScript,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def article_reviews_emails():
    response.view = "default/myLayout.html"

    articleId = request.vars["articleId"]
    article = db.t_articles[articleId]
    recommendation = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.id).last()
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

    link_body = lambda row: A(
                (T("Scheduled") if row.removed_from_queue == False else T("Unscheduled")),
                _href=URL(c="admin_actions", f="toggle_shedule_mail_from_queue", vars=dict(emailId=row.id)),
                _class="btn btn-default",
                _style=("background-color: #3e3f3a;" if row.removed_from_queue == False else "background-color: #ce4f0c;"),
            ) if row.sending_status == "pending" else (recommender_module.mkEditResendButton(auth, db, row, articleId=articleId) if row.sending_status == "sent" else "")
    
    links = [
        dict(
            header="",
            body = link_body,
        )
    ]

    user_mail = db.auth_user[auth.user_id].email
    query = (db.mail_queue.article_id == articleId) & (db.mail_queue.cc_mail_addresses.ilike("%" + user_mail + "%") | db.mail_queue.dest_mail_address.ilike(user_mail) | db.mail_queue.replyto_addresses.ilike("%" + user_mail + "%"))

    original_grid = SQLFORM.grid(
        db(query),
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

    # options to be removed from the search dropdown:
    remove_options = ['mail_queue.sending_date', 'mail_queue.user_id', 'mail_queue.recommendation_id',
                      'mail_queue.article_id', 'mail_queue.review_id', 'mail_queue.reminder_count',
                      'mail_queue.sender_name']

    # options that must be handled as integers
    integer_fields = []

    # the grid is adjusted after creation to adhere to our requirements
    try: grid = adjust_grid.adjust_grid_basic(original_grid, 'mail_queue', remove_options, integer_fields)
    except: grid = original_grid


    myScript = common_tools.get_script("replace_mail_content.js")
    return dict(
        titleIcon="send",
        pageTitle=getTitle(request, auth, db, "#ArticleReviewsEmailsTitle"),
        customText=getText(request, auth, db, "#ArticleReviewsEmailsText"),
        pageHelp=getHelp(request, auth, db, "#ArticleReviewsEmails"),
        myBackButton=common_small_html.mkBackButton(),
        grid=original_grid,
        myFinalScript=myScript,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


def mail_form_processing(form):
    app_forms.update_mail_content_keep_editing_form(form, db, request, response)


def separate_suggestions(suggested_reviewers):
    suggested_by_author = []
    suggested_by_reviewers = []
    suggestor_2_suggestions = {}
    for reviewer in suggested_reviewers:
        if ' suggested:' in reviewer:
            suggestor_re = re.match('(.*) suggested:(.*)', reviewer)
            suggestor = suggestor_re.group(1)
            suggestion = suggestor_re.group(2)
            if suggestor in suggestor_2_suggestions.keys():
                suggestions = suggestor_2_suggestions[suggestor]
                suggestions.append(suggestion)
                suggestor_2_suggestions[suggestor] = suggestions
            else:
                suggestor_2_suggestions[suggestor] = [suggestion]
        else: suggested_by_author.append(reviewer)

    return suggested_by_author, suggestor_2_suggestions


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def edit_and_resend_email():
    response.view = "default/myLayout.html"
    mailId = request.vars["mailId"]
    articleId = request.vars['articleId']
    reviewId = request.vars['reviewId']
    recommId = request.vars['recommId']

    mail = db(db.mail_queue.id == mailId).select()[0]

    default_replyto = emailing_tools.to_string_addresses(mail.replyto_addresses)
    default_cc = emailing_tools.to_string_addresses(mail.cc_mail_addresses)

    form = SQLFORM.factory(
        Field("sending_date", label=T("Previous Sending Date"), type="string", length=250, default=mail.sending_date, writable=False),
        Field("dest_mail_address", label=T("Destination Email"), type="string", length=250, default=mail.dest_mail_address),
        Field("replyto", label=T("Reply-to"), type="string", length=250, default=default_replyto),
        Field("cc_mail_addresses", type="string", label=T("CC"), default=default_cc),
        Field("subject", label=T("Subject"), type="string", length=250, default=mail.mail_subject, required=True),
        Field("content", label=T("Content"), type="text", required=True),
    )
    form.element(_type="submit")["_value"] = T("Send e-mail")
    form.element("textarea[name=content]")["_style"] = "height:500px;"

    html_string = str(mail.mail_content)

    resent = False
    if form.process().accepted:
        try:
            emailing.resend_mail(
                session,
                auth, 
                db, 
                form,
                reviewId=reviewId,
                recommId=recommId,
                articleId=articleId)
            resent = True
        except Exception as e:
            session.flash = (session.flash or "") + T("E-mail failed.")
            raise e
        if reviewId != 'None': redirect(URL(c="recommender", f="review_emails", vars=dict(reviewId=reviewId)))
        else: redirect(URL(c="recommender", f="article_reviews_emails", vars=dict(articleId=articleId)))

    return dict(
        form=form,
        pageHelp=getHelp(request, auth, db, "#EmailForRegisterdReviewer"),
        titleIcon="envelope",
        html_string=html_string,
        resent=resent,
        pageTitle=getTitle(request, auth, db, "#EmailForRegisteredReviewerInfoTitle"),
        customText=getText(request, auth, db, "#EmailForRegisteredReviewerInfo"),
    )
