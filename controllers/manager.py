# -*- coding: utf-8 -*-

import re
import datetime
import os
from typing import Any, Callable, Dict, List, Literal, Tuple, Union, cast, Optional


# sudo pip install tweepy
# import tweepy

# import html2text
from app_components.custom_validator import VALID_LIST_NAMES_MAIL
from gluon import IS_EMAIL, Field
from gluon.contrib.markdown import WIKI # type: ignore
from gluon.dal import Row
from gluon.contrib.appconfig import AppConfig # type: ignore

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
from app_modules.article_translator import ArticleTranslator

from models import suggested_recommender
from models.group import Group, Role
from models.mail_queue import MailQueue, SendingStatus
from models.review import Review

from app_modules.common_small_html import md_to_html, mkUser_U, represent_rdv_date

from controller_modules import admin_module
from gluon.sqlhtml import SQLFORM
from gluon.http import HTTP, redirect # type: ignore

from models.article import Article, ArticleStatus, clean_vars_doi, clean_vars_doi_list
from models.suggested_recommender import SuggestedRecommender
from models.user import User
from models.membership import Membership
from app_components.article_components import fix_web2py_list_str_bug_article_form

from app_modules.common_tools import URL, get_next
from pydal.validators import IS_IN_DB

request = current.request
session = current.session
db = current.db
auth = current.auth
response = current.response
T = current.T

myconf = AppConfig()

csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
not_considered_delay_in_days = myconf.get("config.unconsider_limit_days", default=20)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

scheme = myconf.take("alerts.scheme")
host = myconf.take("alerts.host")
port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()
ACCENT_COLOR = '#fcc24d'
Field.CC = db.Field.CC # type: ignore
######################################################################################################################################################################
## Menu Routes
######################################################################################################################################################################
def index():
    return pending_articles()

# Display ALL articles and allow management
@auth.requires(auth.has_membership(role="manager"))
def all_articles():
    resu = _manage_articles(order_by=db.t_articles.alert_date|~db.t_articles.last_status_change)
    resu["customText"] = getText("#ManagerAllArticlesText")
    resu["titleIcon"] = "book"
    resu["pageTitle"] = getTitle("#ManagerAllArticlesTitle")
    resu["pageHelp"] = getHelp("#ManageAllArticlesHelp")
    return resu

######################################################
@auth.requires(auth.has_membership(role="manager"))
def impersonate_users():
    fields = [
        db.auth_user.id,
        db.auth_user.first_name,
        db.auth_user.last_name,
        db.auth_user.email
    ]

    memberships = Membership.get_all([Role.ADMINISTRATOR, Role.DEVELOPER, Role.MANAGER])
    user_id_with_role: List[int] = []
    for membership in memberships:
        user_id_with_role.append(membership.user_id)

    grid = SQLFORM.grid(
                    (~db.auth_user.id.belongs(user_id_with_role)) & (db.auth_user.deleted == False),
                    fields=fields,
                    editable=False,
                    deletable=False,
                    create=False,
                    details=False,
                    searchable=True,
                    csv=False,
                    maxtextlength=250,
                    paginate=25,
                    links=[dict(header="", body=_impersonate_button)]
    )

    response.view = "default/myLayout.html"
    return dict(
        titleIcon="user",
        pageTitle=getTitle("#AdministrateUsersTitle"),
        pageHelp=getHelp("#AdministrateUsers"),
        customText=getText("#AdministrateUsersText"),
        grid=grid,
        
    )

def _impersonate_button(user: User):
    return A('Impersonate', _href=URL('manager', 'impersonate', args=user.id), _class="buttontext btn btn-default pci-button")

@current.auth.requires(current.auth.has_membership(role="manager"))
def impersonate():
    session, request, auth, db = current.session, current.request, current.auth, current.db

    if len(request.args) != 1:
        session.flash = 'Bad argument'
        return redirect(URL('default','index'))

    try:
        user_id = int(request.args[0])
    except ValueError:
        session.flash = 'Bad user id'
        return redirect(URL('default','index'))
    except Exception as e:
        session.flash = e
        return redirect(URL('default','index'))

    if Membership.has_membership(user_id, [Role.ADMINISTRATOR, Role.DEVELOPER, Role.MANAGER]):
        session.flash = "You can't impersonate this user"
        return redirect(URL('default','index'))
    
    if auth.is_impersonating():
        session.flash = 'You are already impersonating user'
        return redirect(URL('default','index'))
    
    if not auth.has_membership(Role.MANAGER.value):
        session.flash = 'You are not manager'
        return redirect(URL('default','index'))
    
    if not auth.has_permission('impersonate', db.auth_user, user_id):
        manager_group = Group.get_by_role(Role.MANAGER)
        if manager_group:
            auth.add_permission(manager_group.id, 'impersonate', db.auth_user, user_id)
        else:
            session.flash = 'Manager group is missing'
            return redirect(URL('default','index'))

    session.original_user_id = auth.user_id
    auth.impersonate(user_id)
    session.flash = f'Impersonal mode: You are logged as {auth.user.first_name} {auth.user.last_name} (user_id = {user_id})'
    return redirect(URL('default','index'))


def uninpersonate():
    auth, session = current.auth, current.session
    if auth.is_impersonating():
        silent_mode = session.silent_mode
        auth.impersonate(0)
        session.original_user_id = None
        session.silent_mode = silent_mode
        session.flash = 'You have left impersonal mode'
        return redirect(URL('manager','impersonate_users'))

    session.flash = 'You are not in impersonal mode'
    return redirect(URL('default','index'))


######################################################################################################################################################################
# Display pending articles and allow management
@auth.requires(auth.has_membership(role="manager") or is_recommender())
def pending_articles():
    states = ["Pending", "Pre-recommended", "Pre-revision", "Pre-rejected", "Pre-recommended-private"]

    resu = _manage_articles(states, show_not_considered_button=False)
    resu["customText"] = getText("#ManagerPendingArticlesText")
    resu["titleIcon"] = "time"
    resu["pageTitle"] = getTitle("#ManagerPendingArticlesTitle")
    resu["pageHelp"] = getHelp("#ManagePendingValidations")
    return resu

######################################################################################################################################################################
# Display articles in presubmission and allow management
@auth.requires(auth.has_membership(role="manager"))
def pending_surveys():
    resu = _manage_articles(
        ["Pending-survey"]
    )
    resu["customText"] = getText("#ManagerPendingSurveyReportsText")
    resu["titleIcon"] = "time"
    resu["pageTitle"] = getTitle("#ManagerPendingSurveyReportsTitle")
    resu["pageHelp"] = getHelp("#ManagerPendingSurveyReports")
    return resu


@auth.requires(auth.has_membership(role="manager"))
def presubmissions():
    resu = _manage_articles(
        ["Pre-submission"]
    )
    resu["customText"] = getText("#ManagePresubmittedArticlesText")
    resu["titleIcon"] = "warning-sign"
    resu["pageTitle"] = getTitle("#ManagePresubmittedArticlesTitle")
    resu["pageHelp"] = getHelp("#ManagePresubmittedArticles")
    return resu


######################################################################################################################################################################
# Display ongoing articles and allow management
@auth.requires(auth.has_membership(role=Role.MANAGER.value))
def ongoing_articles():
    resu = _manage_articles(
        [ArticleStatus.AWAITING_CONSIDERATION.value,
         ArticleStatus.UNDER_CONSIDERATION.value,
         ArticleStatus.AWAITING_REVISION.value,
         ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value,
         ArticleStatus.SCHEDULED_SUBMISSION_REVISION.value])
    resu["customText"] = getText("#ManagerOngoingArticlesText")
    resu["titleIcon"] = "refresh"
    resu["pageTitle"] = getTitle("#ManagerOngoingArticlesTitle")
    resu["pageHelp"] = getHelp("#ManageOngoingArticles")
    return resu


######################################################################################################################################################################
# Display completed articles and allow management
@auth.requires(auth.has_membership(role="manager"))
def completed_articles():
    db.t_articles.status.label = T("Outcome")
    resu = _manage_articles(["Cancelled", "Recommended", "Rejected", "Not considered"], order_by=~db.t_articles.last_status_change)
    resu["customText"] = getText("#ManagerCompletedArticlesText")
    resu["titleIcon"] = "ok-sign"
    resu["pageTitle"] = getTitle("#ManagerCompletedArticlesTitle")
    resu["pageHelp"] = getHelp("#ManageCompletedArticles")
    return resu


######################################################################################################################################################################
# Common function which allow management of articles filtered by status
@auth.requires(auth.has_membership(role=Role.MANAGER.value) or is_recommender())
def _manage_articles(statuses: Optional[List[str]] = None,
                     stats_query: Optional[Any] = None,
                     show_not_considered_button: bool = True,
                     order_by: ... = db.t_articles.alert_date|db.t_articles.rdv_date):
    if pciRRactivated:
        return _manage_articles_rr(statuses, stats_query, show_not_considered_button)
    
    response.view = "default/myLayout.html"

    last_recomms = db.executesql("select max(id) from t_recommendations group by article_id") if not statuses else \
                   db.executesql("select max(id) from t_recommendations where article_id in " +
                       "(select id from t_articles where status in ('" + "','".join(statuses) + "')) " +
                       "group by article_id")
    last_recomms = [x[0] for x in last_recomms]

    # articles
    t_articles = db.t_articles
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
        'alert_date',
        'keywords',
        'upload_timestamp',
        'thematics',
        'rdv_date',
        'remarks',
        'current_step'
    ]

    for a_field in t_articles.fields:
        if not a_field in full_text_search_fields:
            t_articles[a_field].readable = False
    
    def article_row(article_id: int, article: Article):
        return common_small_html.represent_article_manager_board(article)

    def alert_date_row(article_last_status_change: int, article: Article):
        return common_small_html.represent_alert_manager_board(article)
    
    def link_body_row(row: Article):
        return common_small_html.represent_link_column_manager_board(row)
    
    def represent_rdv_date(rdv_date: Optional[datetime.date], row: Article):
        return common_small_html.represent_rdv_date(row)
    
    def represent_article_status(status: Optional[str], row: Article):
        return common_small_html.represent_current_step_manager_board(row)

    def represent_remarks(remarks: Optional[str], row: Article):
        return TEXTAREA(remarks if remarks is not None else '',
                        _id=f"remarks_{row.id}",
                        _name=f"remarks_{row.id}",
                        _style="height: 100px; width: 330px; resize: none; background: transparent; border: 1px #dfd7ca solid; border-radius: 4px",
                        _oninput=f'remarksInputChange({row.id}, "{URL(c="manager", f="edit_remarks", scheme=True)}")')

    t_articles.id.readable = True
    t_articles.id.represent = article_row
    
    t_articles.thematics.label = "Thematics fields"
    t_articles.thematics.type = "string"
    t_articles.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword)

    t_articles.rdv_date.label = 'Your RDV'
    t_articles.rdv_date.readable = True
    t_articles.rdv_date.represent = represent_rdv_date

    t_articles.anonymous_submission.readable = False
    t_articles.report_stage.readable = False
    t_articles.request_submission_change.readable = False
    t_articles.art_stage_1_id.readable = False
    t_articles.upload_timestamp.readable = False
    t_articles.last_status_change.readbale = False
    t_articles.status.readable = False

    t_articles.user_id.label = 'Submitter'
    t_articles.user_id.readable = True

    t_articles.upload_timestamp.searchable = False
    t_articles.last_status_change.searchable = False

    t_articles.alert_date.represent = alert_date_row
    t_articles.alert_date.readable = True

    t_articles.current_step.represent = represent_article_status
    t_articles.current_step.label = 'Current status'
    t_articles.current_step.readable = True

    t_articles.remarks.readable = True
    t_articles.remarks.label = 'Remarks'
    t_articles.remarks.represent = represent_remarks

    t_articles.id.label = "Article"
    t_articles.keywords.label = "Keywords"

    links: List[Dict[str, Any]] = [
        dict(
            header=T("Actions"),
            body=link_body_row,
        ),
    ]
    if stats_query:
        query = stats_query
    else:
        #recomms.get(article_id)
        query = (db.t_articles.id == db.v_article_id.id)
        if statuses:
            query = query & db.t_articles.status.belongs(statuses)
        # recommenders only ever get here via menu "Recommender > Pending validation(s)"
        if pciRRactivated and is_recommender():
            query = db.pending_scheduled_submissions_query

    original_grid = SQLFORM.grid( # type: ignore
        query,
        searchable=True,
        details=False,
        editable=False,
        deletable=False,
        create=False,
        csv=csv,
        exportclasses=expClass,
        maxtextlength=250,
        paginate=50,
        fields=[
            t_articles.id,
            t_articles.alert_date,
            t_articles.last_status_change,
            t_articles.upload_timestamp,
            t_articles.user_id,
            t_articles.art_stage_1_id,
            t_articles.anonymous_submission,
            t_articles.title,
            t_articles.already_published,
            t_articles.report_stage,
            t_articles.request_submission_change,
            t_articles.ms_version,
            t_articles.doi,
            t_articles.doi_of_published_article,
            t_articles.rdv_date,
            t_articles.status,
            t_articles.current_step,
            t_articles.validation_timestamp,
            t_articles.remarks,
            t_articles.current_step_number
        ],
        links=links,
        left=db.v_article.on(db.t_articles.id == db.v_article.id),
        orderby=order_by,
        _class="web2py_grid manage-article",
    )

    # options to be removed from the search dropdown:
    remove_options = ['t_articles.upload_timestamp', 't_articles.last_status_change', 't_articles.anonymous_submission',
                      'v_article_id.id', 'v_article_id.id_str', 'v_article.id', 'v_article.title', 'v_article.authors',
                      'v_article.abstract', 'v_article.user_id', 'v_article.status', 'v_article.keywords', 'v_article.submission_date',
                      'v_article.reviewers', 'v_article.thematics', 'v_article.alert_date', 'v_article.rdv_date', 'v_article.current_step',
                      'v_article.remarks']
    integer_fields = ['t_articles.id', 't_articles.user_id']
    columns_to_hide = ['t_articles.user_id', 't_articles.title']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'articles', remove_options, integer_fields, columns_to_hide)

    return dict(
        customText=getText("#ManagerArticlesText"),
        pageTitle=getTitle("#ManagerArticlesTitle"),
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
        script=common_tools.get_script("manager.js")
    )


@auth.requires(auth.has_membership(role=Role.MANAGER.value))
def edit_rdv_date():
    try:
        article_id = int(request.vars.get("article_id"))
        new_date = request.vars.get("new_date")
        new_date = datetime.date.fromisoformat(request.vars.get("new_date")) if new_date else None
    except:
        response.flash = "Bad arguments"
        return HTTP(400, "Bad arguments")
    
    if new_date and datetime.date.today() > new_date:
        response.flash = "Date must be upper than the today date"
        return HTTP(403, "Date must be upper than the today date")

    article = Article.get_by_id(article_id)
    if not article:
        response.flash = "Article not found"
        return HTTP(404, f"Article with id {article_id} not found")
    
    try:
        Article.set_rdv_date(article, new_date)
    except:
        response.flash = "Error to update RDV date"
        return HTTP(500, "Error to update RDV date")

    return represent_rdv_date(article)


@auth.requires(auth.has_membership(role=Role.MANAGER.value))
def edit_remarks():
    try:
        article_id = int(request.vars.get("article_id"))
        remarks = str(request.vars.get("remarks"))
    except:
        response.flash = "Bad arguments"
        return HTTP(400, "Bad arguments")
    
    article = Article.get_by_id(article_id)
    if not article:
        response.flash = "Article not found"
        return HTTP(404, f"Article with id {article_id} not found")
    
    try:
        Article.set_remarks(article, remarks)
    except:
        response.flash = "Error to update remarks"
        return HTTP(500, "Error to update remarks")

    return HTTP(200, remarks)


@auth.requires(auth.has_membership(role=Role.MANAGER.value) or is_recommender())
def _manage_articles_rr(statuses: List[str], stats_query: Optional[Any] = None, show_not_considered_button: bool = True):
    response.view = "default/myLayout.html"

    # users
    def index_by(field: str, query: ...): return { x[field]: x for x in db(query).select() }

    users: Dict[int, User] = index_by("id", db.auth_user)
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
        'upload_timestamp',
        'thematics'
    ]   
    
    def article_row(article_id: int, article: Article):
        return DIV(common_small_html.mkRepresentArticleLight(article_id), _class="pci-w300Cell")
    
    def submitter_row(user_id: int, article: Article):
        return SPAN(
            DIV(common_small_html.mkAnonymousArticleField(article.anonymous_submission or False, "", article.id)),
            common_small_html.mk_user(users.get(article.user_id) if article.user_id else None),
        )
    
    def recommender_row(article_title: str, article: Article):
        article_id = article.id

        recomm = recomms.get(article_id)
        if not recomm:
            return DIV("no recommender")

        resu = DIV()
        resu.append(common_small_html.mk_user(users.get(recomm.recommender_id))) # type: ignore

        for co_recomm in co_recomms:
            if co_recomm.recommendation_id == recomm.id:
                resu.append(common_small_html.mk_user(users.get(co_recomm.contributor_id))) # type: ignore

        if len(resu) > 1:
            resu.insert(1, DIV(B("Co-recommenders:"))) # type: ignore

        return resu
    
    def status_row(article_status: str, article: Article):
        return common_small_html.mkStatusDiv(
        article_status,
        showStage=pciRRactivated,
        stage1Id=article.art_stage_1_id,
        reportStage=article.report_stage,
        submission_change=article.request_submission_change,
    )
    
    def upload_timestamp_row(upload_timestamp: datetime.datetime, article: Article):
        return common_small_html.mkLastChange(article.upload_timestamp)

    def last_status_change_row(last_status_change: datetime.datetime, article: Article):
        return common_small_html.mkLastChange(article.last_status_change)
    
    def link_body_row(row: Article):
        return DIV(
                A(
                    SPAN(current.T("View / Edit")),
                    _href=URL(c="manager", f="recommendations", vars=dict(articleId=row.id, recommender=auth.user_id)),
                    _class="buttontext btn btn-default pci-button pci-manager",
                    _title=current.T("View and/or edit"),
                ),
                ongoing_recommendation.set_not_considered_tiny_button(row.id)
                if (
                    row.status in (ArticleStatus.AWAITING_CONSIDERATION.value, ArticleStatus.PENDING.value, ArticleStatus.PRE_SUBMISSION.value)
                    and row.already_published is False and show_not_considered_button
                )
                else "",
                ongoing_recommendation.validate_stage_button(row) if row.status == ArticleStatus.PRE_SUBMISSION.value else "",
            )

    articles.id.readable = True
    articles.id.represent = article_row
    
    articles.thematics.label = "Thematics fields"
    articles.thematics.type = "string"
    articles.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword)
    
    articles.user_id.represent = submitter_row
    articles.user_id.label = 'Submitter'

    articles.title.represent = recommender_row
    articles.title.label = 'Recommenders'

    articles.anonymous_submission.readable = False
    articles.report_stage.readable = False
    articles.request_submission_change.readable = False
    articles.art_stage_1_id.readable = False
    articles.upload_timestamp.searchable = False
    articles.last_status_change.searchable = False

    articles.status.represent = status_row

    articles.upload_timestamp.represent = upload_timestamp_row
    articles.last_status_change.represent = last_status_change_row

    for a_field in articles.fields:
        if not a_field in full_text_search_fields:
            articles[a_field].readable = False

    articles.id.label = "Article"

    links: List[Dict[str, Any]] = [
        dict(
            header=T("Actions"),
            body=link_body_row,
        ),
    ]
    if stats_query:
        query = stats_query
    else:
        #recomms.get(article_id)
        query = (db.t_articles.id == db.v_article_id.id)
        if statuses:
            query = query & db.t_articles.status.belongs(statuses)
        # recommenders only ever get here via menu "Recommender > Pending validation(s)"
        if pciRRactivated and is_recommender():
            query = db.pending_scheduled_submissions_query
    original_grid = SQLFORM.grid( # type: ignore
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
            articles.title,
            articles.already_published,
            articles.report_stage,
            articles.request_submission_change,
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
                      'v_article.reviewers', 'v_article.thematics']
    integer_fields = ['t_articles.id', 't_articles.user_id']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'articles', remove_options, integer_fields)

    return dict(
        customText=getText("#ManagerArticlesText"),
        pageTitle=getTitle("#ManagerArticlesTitle"),
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
        script=common_tools.get_script("manager.js")
    )

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or is_recommender())
def recommendations():
    articleId = request.vars["articleId"]
    manager_authors = request.vars["manager_authors"]
    printable = "printable" in request.vars and request.vars["printable"] == "True"

    try: art = Article.get_by_id(articleId)
    except: art = None

    if art is None: return redirect(request.home)

    if manager_authors != None:
        art.update_record(manager_authors=manager_authors)

    if art.already_published:
        myContents = ongoing_recommendation.getPostprintRecommendation(art, printable, quiet=False)
    else:
        myContents = ongoing_recommendation.get_recommendation_process(art, printable)

    isStage2 = art.art_stage_1_id is not None
    stage1Link = None
    stage2List = None
    if pciRRactivated and isStage2:
        # stage1Link = A(T("Link to Stage 1"), _href=URL(c="manager", f="recommendations", vars=dict(articleId=art.art_stage_1_id)))
        urlArticle = URL(c="manager", f="recommendations", vars=dict(articleId=art.art_stage_1_id))
        stage1Link = common_small_html.mkRepresentArticleLightLinkedWithStatus(art.art_stage_1_id, urlArticle)
    elif pciRRactivated and not isStage2:
        stage2Articles = db(db.t_articles.art_stage_1_id == articleId).select()
        stage2List = []
        for art_st_2 in stage2Articles:
            urlArticle = URL(c="manager", f="recommendations", vars=dict(articleId=art_st_2.id))
            stage2List.append(common_small_html.mkRepresentArticleLightLinkedWithStatus(art_st_2.id, urlArticle))

    response.title = art.title or myconf.take("app.longname")

    recommHeaderHtml = article_components.get_article_infos_card(art, printable, True, for_manager=True)
    recommStatusHeader = ongoing_recommendation.getRecommStatusHeader(art, False, printable, quiet=False)
    
    manager_coauthor = common_tools.check_coauthorship(auth.user_id, art)
    if not manager_coauthor:
        set_not_considered_button = ongoing_recommendation.set_to_not_considered(art) if art.status in (ArticleStatus.AWAITING_CONSIDERATION.value, ArticleStatus.PRE_SUBMISSION.value) else None
        recommTopButtons = ongoing_recommendation.getRecommendationTopButtons(art, printable, quiet=False)
    else:
        set_not_considered_button = ''
        recommTopButtons = ''

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
            
        recommStatusHeader.append(crossref_clockss_toolbar(art))

    if printable:
        printableClass = "printable"
        response.view = "default/wrapper_printable.html"
    else:
        printableClass = ""
        response.view = "default/wrapper_normal.html"

    recommendation_process = ongoing_recommendation.getRecommendationProcessForSubmitter(art, printable)

    myScript = common_tools.get_script("recommended_articles.js")
    viewToRender = "default/recommended_articles.html"
    confirmationScript = common_tools.get_script("confirmation.js")

    return dict(
        isSubmitter=(art.user_id == auth.user_id),
        isManager=current.auth.has_membership(role=Role.MANAGER.value),
        isRecommender=user_is_in_recommender_team(art.id),
        recommendationProgression=recommendation_process['content'],
        isRecommAvalaibleToSubmitter=recommendation_process["isRecommAvalaibleToSubmitter"],
        viewToRender=viewToRender,
        recommHeaderHtml=recommHeaderHtml,
        recommStatusHeader=recommStatusHeader,
        recommTopButtons=recommTopButtons or "",
        printable=printable,
        pageHelp=getHelp("#ManagerRecommendations"),
        myContents=myContents,
        myBackButton=common_small_html.mkBackButton(),
        pciRRactivated=pciRRactivated,
        isStage2=isStage2,
        stage1Link=stage1Link,
        stage2List=stage2List,
        myFinalScript=myScript,
        script=common_tools.get_script("manager.js"),
        isPendingValidation=(art.status == "Pending" and not pciRRactivated),
        setNotConsideredButton=set_not_considered_button or "",
        confirmationScript=confirmationScript,
    )


def crossref_clockss_toolbar(article):
    return DIV(
        crossref_clockss_button(article),
        crossref_status(article),
        _style="width: fit-content; display: inline-block; margin-right: 25px;",
    )

def crossref_clockss_button(article: Row):
    return A(
        I(_class="glyphicon glyphicon-edit", _style="vertical-align:middle"),
        T("Crossref/Clockss"),
        _href=URL("crossref", f"post_form?article_id={article.id}"),
        _class="pci2-tool-link pci2-yellow-link",
        _style="margin-right: 15px;",
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
    twitter_client = Twitter()

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
    mastodon_client = Mastodon()

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
    
    manager_coauthor = common_tools.check_coauthorship(auth.user_id, art)
    if manager_coauthor:
        session.flash = T("You cannot access this page because you are a co-author of this submission")
        redirect(request.env.http_referer)
        return

    target = URL('manager','recommendations', vars=dict(articleId=articleId), user_signature=True)
    if "edit" in request.env.request_uri:
        target = URL('manager','manage_recommendations', vars=dict(articleId=articleId), user_signature=True)

    query = db.t_recommendations.article_id == articleId
    db.t_recommendations.recommender_id.default = auth.user_id
    db.t_recommendations.article_id.default = articleId
    db.t_recommendations.article_id.writable = False
    db.t_recommendations.last_change.writable = False
    db.t_recommendations.doi.represent = lambda text, row: common_small_html.mkDOI(text)
    db.t_pdf.pdf.represent = lambda text, row: A(IMG(_src=URL("static", "images/application-pdf.png")), _href=URL("default", "download", args=text)) if text else ""
    db.t_recommendations._id.readable = True
    if len(request.args) == 0:  # in grid
        db.t_recommendations.recommender_id.represent = lambda id, row: common_small_html.mkUserWithMail(id)
        db.t_recommendations.recommendation_state.represent = lambda state, row: common_small_html.mkContributionStateDiv((state or ""))
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
        return ", ".join([Review.get_reviewer_name(review) for review in reviews])

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
    myContents = DIV(DIV(article_components.get_article_infos_card(art, False, False), _class="pci2-content-900px"), _class="pci2-full-width pci2-flex-center")

    confirmationScript = common_tools.get_script("confirmation.js")

    return dict(
        myBackButton=common_small_html.mkBackButton(target=target),
        pageHelp=getHelp("#ManageRecommendations"),
        customText=getText("#ManageRecommendationsText"),
        titleIcon="edit",
        pageTitle=getTitle("#ManageRecommendationsTitle"),
        content=myContents,
        bottomContent=common_small_html.suggested_recommender_list(art.id),
        grid=grid,
        deleteFileButtonsScript=common_tools.get_script("add_delete_file_buttons_manager.js"),
        absoluteButtonScript=common_tools.absoluteButtonScript,
        confirmationScript=confirmationScript,
    )



######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def search_recommenders():
    whatNext = request.vars["whatNext"]
    previous = URL(args=request.args, vars=request.get_vars, host=True)
    articleId = request.vars["articleId"]
    if articleId is None:
        articleHeaderHtml = ""
    else:
        art = db.t_articles[articleId]
        articleHeaderHtml = article_components.get_article_infos_card(art, **article_components.for_search)

    excludeList = common_tools.get_exclude_suggested_recommender(articleId)
    excluded_by_submitter_query = db(db.t_excluded_recommenders.article_id == articleId).select()
    excluded_by_submitter = [m['excluded_recommender_id'] for m in excluded_by_submitter_query]

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
        'cv'
    ]

    for f in users.fields:
        if not f in full_text_search_fields:
            users[f].readable = False

    def limit_to_width(value, row):
        if value == None: return SPAN(_class="m230w")
        return SPAN(current.T("%s" %', '.join(value)), _class="m230w"),

    def limit_to_width_str(value, row):
        if value == None: return SPAN(_class="m230w")
        return SPAN(current.T("%s" %value), _class="m230w"),

    users.thematics.label = "Thematics fields"
    users.thematics.type = "string"
    users.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, zero=None)
    users.thematics.represent = limit_to_width

    users.keywords.represent = limit_to_width_str

    users.id.label = "Name"
    users.id.readable = True
    users.id.represent = lambda uid, row: DIV(
            common_small_html.mk_reviewer_info(db.auth_user[uid]),
            _class="pci-w300Cell")

    links = []
    if articleId:
        links += [
        dict(header="", body=lambda row: "" if row.auth_user.id in excludeList else DIV(A(
                SPAN(current.T("Suggest as recommender"), _class="buttontext btn btn-default pci-submitter"),
                _href=URL(c="manager_actions", f="suggest_article_to", vars=dict(articleId=articleId, recommenderId=row.auth_user.id, whatNext=whatNext), user_signature=True),
                _class="button",
                ),
                INPUT(_type="checkbox", _id='checkbox_suggest_%s'%(str(row.auth_user.id)), _class="multiple-choice-checks suggest", _onclick='update_parameter_for_selection(this)'),
                DIV(current.T("Excluded by author(s)"), _class="exclude_by_submitter") if row.auth_user.id in excluded_by_submitter else ""
                ),
            ),
        ]


    select_all_btn = DIV(A(
                         SPAN(current.T("CLICK HERE TO SUGGEST ALL SELECTED RECOMMENDERS"), _class="btn btn-success"),
                         _href=URL(c="manager_actions", f="suggest_all_selected", vars=dict(articleId=articleId, whatNext=whatNext, previous=previous, recommenderIds=''), user_signature=True),
                         _class="button select-all-btn",
                         _id="select-all-btn",
                         )
                        )

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
            users.id,
            users.thematics,
            users.keywords,
        ],
        links=links,
        orderby=(users.last_name, users.first_name),
        _class="web2py_grid action-button-absolute",
    )

    # fields that are integer and need to be treated differently
    integer_fields = []

    # options to be removed from the search dropdown:
    remove_options = ['auth_membership.id', 'auth_membership.user_id', 'auth_membership.group_id',
                      'auth_group.id', 'auth_group.role', 'auth_group.description']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'recommenders', remove_options, integer_fields)
    select_all_script = common_tools.get_script("select_all.js")

    response.view = "default/gab_list_layout.html"
    return dict(
        pageHelp=getHelp("#ManagerSearchRecommenders"),
        customText=getText("#ManagerSearchRecommendersText"),
        titleIcon="search",
        pageTitle=getTitle("#ManagerSearchRecommendersTitle"),
        myBackButton=common_small_html.mkBackButton(),
        myFinalScript=common_tools.get_script("popover.js"),
        grid=grid,
        articleHeaderHtml=articleHeaderHtml,
        selectAllBtn = select_all_btn,
        selectAllScript = select_all_script,
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

    manager_coauthor = common_tools.check_coauthorship(auth.user_id, art)
    if manager_coauthor:
        session.flash = T("You cannot access this page because you are a co-author of this submission")
        redirect(request.env.http_referer)
        return

    articleHeaderHtml = article_components.get_article_infos_card(art, **article_components.for_search)

    query = db.t_suggested_recommenders.article_id == articleId
    db.t_suggested_recommenders.article_id.readable = False
    db.t_suggested_recommenders.article_id.writable = False
    db.t_suggested_recommenders._id.readable = False
    db.t_suggested_recommenders.email_sent.readable = False
    db.t_suggested_recommenders.suggested_recommender_id.represent = lambda text, row: common_small_html.mkUserWithMail(text)
    links = []
    # if art.status == "Awaiting consideration":
    links.append(
        dict(
            header="Emails history",
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
        pageTitle=getTitle("#ManageSuggestedRecommendersTitle"),
        pageHelp=getHelp("#ManageSuggestedRecommenders"),
        customText=getText("#ManageSuggestedRecommendersText"),
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

    articleId = request.vars["articleId"]
    art = db.t_articles[articleId or None]

    if art == None:
        session.flash = f"no such article: articleId={articleId}"
        redirect(URL("manager", "all_articles"))  # it may have been deleted, so that's normal!

    manager_coauthor = common_tools.check_coauthorship(auth.user_id, art)
    if manager_coauthor:
        session.flash = T("You cannot access this page because you are a co-author of this submission")
        redirect(request.env.http_referer)
        return

    db.t_articles.status.writable = True
    db.t_articles.user_id.writable = True

    db.t_articles.cover_letter.readable = True
    db.t_articles.cover_letter.writable = True

    db.t_articles.request_submission_change.readable = False
    db.t_articles.request_submission_change.writable = False
    db.t_articles.manager_authors.readable = False

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

        db.t_articles.methods_require_specific_expertise.readable = False
        db.t_articles.methods_require_specific_expertise.writable = False

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

    try: article_manager_coauthors = art.manager_authors
    except: article_manager_coauthors = False
    managers = common_tools.get_managers()
    manager_checks = {}
    for m in managers:
        manager_checks[m[0]] = False
    if article_manager_coauthors:
        for amc in article_manager_coauthors.split(','):
            manager_checks[amc] = True
    manager_ids = [m[0] for m in managers]
    manager_label = [Field('manager_label', 'string', label='Tick the box in front of the following names (who are members of the managing board) if they are co-authors of the article')]
    manager_fields = [Field('chk_%s'%m[0], 'boolean', default=manager_checks[m[0]], label=m[1], widget=lambda field, value: SQLFORM.widgets.boolean.widget(field, value, _class='manager_checks', _onclick="check_checkboxes()")) for i,m in enumerate(managers)]

    form = SQLFORM(db.t_articles, articleId, upload=URL("static", "uploads"), deletable=True, showid=True, extra_fields = manager_label + manager_fields,)
    form.element(_type="submit")["_id"] = "submit-article-btn"
    
    ArticleTranslator.add_edit_translation_buttons(art, form)
    try:
        article_version = int(art.ms_version)
    except:
        article_version = art.ms_version

    prev_picture = art.uploaded_picture

    if type(db.t_articles.uploaded_picture.requires) == list: # non-RR see db.py
        not_empty = db.t_articles.uploaded_picture.requires.pop()

    data_doi_form = form.elements(_id="t_articles_results_based_on_data__row")
    if data_doi_form:
        data_code_script_label = LABEL("Data, code and scripts", SPAN(" * ", _style="color:red;"), _class="control-label col-sm-3", _style="margin-top: 12px")
        data_doi_form[0].insert(0, data_code_script_label)

    def onvalidation(form):
        if not pciRRactivated:
            if not prev_picture and form.vars.uploaded_picture == b"":
                form.errors.uploaded_picture = not_empty.error_message
            app_forms.checklist_validation(form)

            suggested_reviewers_value, suggested_reviewers_error = VALID_LIST_NAMES_MAIL(True, optional_email=True)(form.vars.suggest_reviewers)
            if suggested_reviewers_error:
                form.errors.suggest_reviewers = suggested_reviewers_error

            opposed_reviewers_reviewers_value, opposed_reviewers_reviewers_error = VALID_LIST_NAMES_MAIL(True, optional_email=True)(form.vars.opposed_reviewers)
            if opposed_reviewers_reviewers_error:
                form.errors.competitors = opposed_reviewers_reviewers_error

            form.vars.suggest_reviewers = suggested_reviewers_value
            form.vars.competitors = opposed_reviewers_reviewers_value

        form.vars.doi = clean_vars_doi(form.vars.doi)
        form.vars.data_doi = clean_vars_doi_list(form.vars.data_doi)
        form.vars.codes_doi = clean_vars_doi_list(form.vars.codes_doi)
        form.vars.scripts_doi = clean_vars_doi_list(form.vars.scripts_doi)

    if form.process(onvalidation=onvalidation).accepted:
        if form.vars.abstract != art.abstract or form.vars.title != art.title or form.vars.keywords != art.keywords:
            ArticleTranslator.launch_article_translation_for_default_langs_process(art.id, True)

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
        manager_ids = common_tools.extract_manager_ids(form, manager_ids)
        myVars = dict(articleId=art.id, manager_authors=manager_ids)
        redirect(URL(c=controller, f="recommendations", vars=myVars, user_signature=True))
    elif form.errors:
        response.flash = T("Form has errors", lazy=False)
        fix_web2py_list_str_bug_article_form(form)

    confirmationScript = common_tools.get_script("confirmation.js")
    article_form_common_script = common_tools.get_script("article_form_common.js")

    return dict(
        # myBackButton = common_small_html.mkBackButton(),
        pageHelp=getHelp("#ManagerEditArticle"),
        customText=getText("#ManagerEditArticleText"),
        titleIcon="edit",
        pageTitle=getTitle("#ManagerEditArticleTitle"),
        form=form,
        myFinalScript=[myFinalScript, article_form_common_script],
        confirmationScript=confirmationScript,
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

    manager_coauthor = common_tools.check_coauthorship(auth.user_id, art)
    if manager_coauthor:
        session.flash = T("You cannot access this page because you are a co-author of this submission")
        redirect(request.env.http_referer)
        return

    survey = db(db.t_report_survey.article_id == articleId).select().last()
    if survey is None:
        survey = db.t_report_survey.insert(article_id = articleId, temp_art_stage_1_id=art.art_stage_1_id)
        session.flash = T("New survey created")
        # redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))

    form = app_forms.report_survey(art, survey, "manager_edit")

    myScript = common_tools.get_script("fill_report_survey.js")
    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp("#ManagerReportSurvey"),
        titleIcon="edit",
        pageTitle=getTitle("#ManagerReportSurveyTitle"),
        customText=getText("#ManagerReportSurveyText", maxWidth="800"),
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
        customText=getText("#ManageCommentsText"),
        titleIcon="comment",
        pageTitle=getTitle("#ManageCommentsTitle"),
        pageHelp=getHelp("#ManageComments"),
        grid=grid,
    )

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def all_recommendations():
    isPress = ("pressReviews" in request.vars) and (request.vars["pressReviews"] == "True")
    goBack = URL(re.sub(r".*/([^/]+)$", "\\1", request.env.request_uri), scheme=scheme, host=host, port=port)
    query = (
          (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_articles.already_published == isPress)
        & (db.t_recommendations.id == db.v_article_recommender.recommendation_id)
        & (db.t_recommendations.id == db.v_reviewers.id)
        & (db.t_recommendations.id == db.v_recommendation_contributors.id)
    )
    query = (
          (db.t_recommendations.article_id == db.t_articles.id)
        & (db.t_articles.already_published == isPress)
        & (db.t_recommendations.id == db.v_article_recommender.recommendation_id)
        & (db.t_recommendations.id == db.v_reviewers.id)
        & (db.t_recommendations.id == db.v_recommendation_contributors.id)
        )

    if not isPress:
        query = query & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration", "Scheduled submission pending"))) 
    resu = _all_recommendations(goBack, query, isPress)
    return resu

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def _all_recommendations(goBack, query, isPress):
    response.view = "default/myLayout.html"

    if isPress:  ## NOTE: POST-PRINTS
        pageTitle = getTitle("#AdminAllRecommendationsPostprintTitle")
        customText = getText("#AdminAllRecommendationsPostprintText")
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
        ]
        links = [
            dict(
                header=T(""), body=lambda row: common_small_html.mkViewEditRecommendationsRecommenderButton(row.t_recommendations if "t_recommendations" in row else row)
            ),
        ]
        db.t_recommendations.article_id.label = T("Postprint")
    else:  ## NOTE: PRE-PRINTS
        pageTitle = getTitle("#AdminAllRecommendationsPreprintTitle")
        customText = getText("#AdminAllRecommendationsPreprintText")
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
        ]
        links = [
            dict(header=T("Reviews"), body=lambda row: recommender_components.getReviewsSubTable(row.t_recommendations if "t_recommendations" in row else row)),
            # dict(header=T('Actions'),            body=lambda row: common_small_html.mkViewEditRecommendationsRecommenderButton(row.t_recommendations if 't_recommendations' in row else row)),
            dict(
                header=T("Actions"),
                body=lambda row: DIV(manager_module.mkViewEditRecommendationsManagerButton(row.t_recommendations if "t_recommendations" in row else row)),
            ),
        ]
        db.t_recommendations.article_id.label = T("Preprint")

    db.t_recommendations.recommender_id.writable = False
    db.t_recommendations.doi.writable = False
    # db.t_recommendations.article_id.readable = False
    db.t_recommendations.article_id.writable = False
    db.t_recommendations._id.readable = False
    db.t_recommendations.recommender_id.readable = True
    db.t_recommendations.recommender_id.represent =  lambda id, row: DIV(common_small_html.mkUserWithMail(id) + HR(_class="column-merge-hr") + SPAN("Co-Recommenders") + common_small_html.mkCoRecommenders(row.t_recommendations if "t_recommendations" in row else row, goBack), _class="m230w")
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
    db.t_recommendations.article_id.represent = lambda aid, row: DIV(common_small_html.mkArticleCellNoRecomm(db.t_articles[aid]), _class="pci-w300Cell")

    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.art_stage_1_id.writable = False
    db.t_articles.report_stage.writable = False
    db.t_articles.report_stage.readable = False

    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDiv(
        text, showStage=pciRRactivated, stage1Id=row.t_articles.art_stage_1_id, reportStage=row.t_articles.report_stage
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
        _class="web2py_grid action-button-absolute manager-preprints-table",
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
                      't_articles.codes_used_in_study', 't_articles.record_id_version', 't_articles.record_url_version',
                      't_articles.manager_authors', 'v_recommendation_contributors.id']
    integer_fields = ['t_articles.id', 't_articles.user_id']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'articles', remove_options, integer_fields)
    confirmationScript = common_tools.get_script("confirmation.js")

    return dict(
        # myBackButton=common_small_html.mkBackButton(),
        pageHelp=getHelp("#AdminAllRecommendations"),
        titleIcon="education",
        pageTitle=pageTitle,
        customText=customText,
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
        confirmationScript=confirmationScript,
    )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def suggested_recommender_emails():
    response.view = "default/myLayout.html"

    suggRecommId = request.vars["suggRecommId"]
    articleId = request.vars["articleId"]

    suggested_recommender = User.get_by_id(suggRecommId)

    if not suggested_recommender:
        return f"no such recommender: {suggRecommId}"
    if suggested_recommender.deleted:
        return f"no such recommender: {suggRecommId}"

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
    db.mail_queue.mail_subject.represent = lambda text, row: DIV(B(text), BR(), SPAN(row.mail_template_hashtag), _class="ellipsis-over-350")
    db.mail_queue.cc_mail_addresses.widget = app_forms.cc_widget
    db.mail_queue.replyto_addresses.widget = app_forms.cc_widget

    db.mail_queue.sending_status.writable = False
    db.mail_queue.sending_attempts.writable = False
    db.mail_queue.dest_mail_address.writable = False
    db.mail_queue.user_id.writable = False
    db.mail_queue.mail_template_hashtag.writable = False
    db.mail_queue.reminder_count.writable = False
    db.mail_queue.article_id.readable = False
    db.mail_queue.recommendation_id.writable = False

    db.mail_queue.removed_from_queue.writable = False
    db.mail_queue.removed_from_queue.readable = False

    db.mail_queue.user_id.searchable = False
    db.mail_queue.review_id.searchable = False
    db.mail_queue.recommendation_id.searchable = False

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
        pageTitle=getTitle("#RecommenderReviewEmailsTitle"),
        customText=getText("#RecommenderReviewEmailsText"),
        pageHelp=getHelp("#RecommenderReviewEmails"),
        myBackButton=common_small_html.mkBackButton(target=URL(c="manager", f="suggested_recommenders", vars=dict(articleId=articleId), user_signature=True)),
        grid=grid,
        myFinalScript=myScript,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


@auth.requires(auth.has_membership(role="manager"))
def article_emails():
    response.view = "default/myLayout.html"

    articleId = request.vars["articleId"]
    article = db.t_articles[articleId or None]
    urlFunction = request.function
    urlController = request.controller

    if not article:
        session.flash = T(f"no such article: articleId={articleId}")
        redirect(request.env.http_referer or request.home)

    manager_coauthor = common_tools.check_coauthorship(auth.user_id, article)
    if manager_coauthor:
        session.flash = T("You cannot access this page because you are a co-author of this submission")
        redirect(request.env.http_referer or request.home)

    def represent_sending_status(text: str, row: MailQueue):
        return DIV(
            SPAN(admin_module.makeMailStatusDiv(text)),
            SPAN(I(T("Sending attempts : ")), B(row.sending_attempts), _style="font-size: 12px; margin-top: 5px"),
            _class="pci2-flex-column",
            _style="margin: 5px 10px;",
    )

    def represent_sending_date(text: str, row: MailQueue):
        return datetime.datetime.strptime(str(text), "%Y-%m-%d %H:%M:%S")

    def represent_mail_content(text: str, row: MailQueue):
        return XML(admin_module.sanitizeHtmlContent(text))
    
    def represent_mail_subject(text: str, row: MailQueue):
        return DIV(B(text), BR(), SPAN(row.mail_template_hashtag), _class="ellipsis-over-500")

    db.mail_queue.sending_status.represent = represent_sending_status

    db.mail_queue.id.readable = False
    db.mail_queue.sending_attempts.readable = False

    db.mail_queue.sending_date.represent = represent_sending_date
    db.mail_queue.mail_content.represent = represent_mail_content
    db.mail_queue.mail_subject.represent = represent_mail_subject
    db.mail_queue.cc_mail_addresses.widget = app_forms.cc_widget
    db.mail_queue.replyto_addresses.widget = app_forms.cc_widget
    db.mail_queue.bcc_mail_addresses.widget = app_forms.cc_widget

    db.mail_queue.sending_status.writable = False
    db.mail_queue.sending_attempts.writable = False
    db.mail_queue.dest_mail_address.writable = False
    db.mail_queue.user_id.writable = False
    db.mail_queue.mail_template_hashtag.writable = False
    db.mail_queue.reminder_count.writable = False
    db.mail_queue.article_id.readable = False
    db.mail_queue.recommendation_id.writable = False

    db.mail_queue.removed_from_queue.writable = False
    db.mail_queue.removed_from_queue.readable = False

    db.mail_queue.user_id.searchable = False
    db.mail_queue.review_id.searchable = False
    db.mail_queue.recommendation_id.searchable = False

    db.mail_queue.dest_mail_address.requires = IS_EMAIL()

    if len(request.args) > 2 and request.args[0] == "edit":
        db.mail_queue.mail_template_hashtag.readable = True
        
        mail = MailQueue.get_mail_by_id(request.args[2])
        if mail:
            dest_mail_address_writable = mail.sending_status == SendingStatus.PENDING.value
            db.mail_queue.dest_mail_address.writable = dest_mail_address_writable

            if dest_mail_address_writable and "dest_mail_address" in request.post_vars:
                dest_mail_address = request.post_vars["dest_mail_address"]
                _, error = IS_EMAIL()(dest_mail_address) # type: ignore
                if not error:
                    MailQueue.update_dest_mail_address(mail.id, dest_mail_address)
    else:
        db.mail_queue.mail_template_hashtag.readable = False
        db.mail_queue.dest_mail_address.writable = False

    link_body: Callable[[Any], Union[A, Literal['']]] = lambda row: A(
                (T("Scheduled") if row.removed_from_queue == False else T("Unscheduled")),
                _href=URL(c="admin_actions", f="toggle_shedule_mail_from_queue", vars=dict(emailId=row.id)),
                _class="btn btn-default",
                _style=("background-color: #3e3f3a;" if row.removed_from_queue == False else "background-color: #ce4f0c;"),
            ) if row.sending_status == "pending" else (admin_module.mkEditResendButton(row, urlFunction=urlFunction, urlController=urlController) if row.sending_status == "sent" else "")

    links = [
        dict(
            header="",
            body = link_body,
        )
    ]

    myScript = common_tools.get_script("replace_mail_content.js")

    if manager_coauthor: query = (db.mail_queue.article_id == articleId) & (db.mail_queue.mail_template_hashtag != '#RecommenderReviewerReviewCompleted')
    else: query = (db.mail_queue.article_id == articleId)

    grid: ... = SQLFORM.grid( # type: ignore
        query,
        details=True,
        editable=lambda row: (row.sending_status == "pending"), # type: ignore
        deletable=lambda row: (row.sending_status == "pending"), # type: ignore
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
            #db.mail_queue.cc_mail_addresses,
            #db.mail_queue.replyto_addresses,
            # db.mail_queue.user_id,
            db.mail_queue.mail_subject,
            db.mail_queue.dest_mail_address,
            db.mail_queue.mail_template_hashtag,
            db.mail_queue.article_id,
        ],
        links=links,
        links_placement="left",
        _class="web2py_grid action-button-absolute",
    )

    return dict(
        titleIcon="send",
        pageTitle=getTitle("#ArticleEmailsTitle"),
        customText=getText("#ArticleEmailsText"),
        pageHelp=getHelp("#ArticleEmails"),
        myBackButton=common_small_html.mkBackButton(target=URL('manager','recommendations', vars=dict(articleId=articleId), user_signature=True)), 
        grid=grid,
        myFinalScript=myScript,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


def mail_form_processing(form: ...):
    app_forms.update_mail_content_keep_editing_form(form)

@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="recommender"))
def send_submitter_generic_mail():
    response.view = "default/myLayout.html"

    def fail(message: str):
        session.flash = T(message)
        referrer = request.env.http_referer
        redirect(referrer if referrer else URL("default", "index"))

    articleId = int(request.vars["articleId"])
    art = Article.get_by_id(articleId)
    if not art:
        return fail("no article for review")
    
    recomm = Article.get_last_recommendation(art.id)
    author: Optional[User] = None
    if art.user_id:
        author = User.get_by_id(art.user_id)
    
    if not author:
        return fail("no author for article")
    
    if not author.email:
        return fail("author has not email")

    template = "#SubmitterGenericMail"
    mail_vars = emailing_tools.getMailCommonVars()

    if "revise_scheduled_submission" in request.args:
        template = "#SubmitterScheduledSubmissionDeskRevisionsRequired" 
        sched_sub_vars = emailing_vars.getPCiRRScheduledSubmissionsVars(art)
        mail_vars["scheduledSubmissionLatestReviewStartDate"] = sched_sub_vars["scheduledSubmissionLatestReviewStartDate"]
        mail_vars["scheduledReviewDueDate"] = sched_sub_vars["scheduledReviewDueDate"]
        if recomm:
            mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)

    mail_vars["description"] = myconf.take("app.description")
    mail_vars["longname"] = myconf.take("app.longname")
    mail_vars["appName"] = myconf.take("app.name")
    contact = myconf.take("contacts.managers")

    sender_email = db(db.auth_user.id == auth.user_id).select().last().email

    mail_template = emailing_tools.getMailTemplateHashtag(template)

    # template variables, along with all other locals()
    mail_vars["destPerson"] = common_small_html.mkUser(art.user_id)
    mail_vars["destAddress"] = author.email
    mail_vars["articleDoi"] = common_small_html.mkLinkDOI(art.doi)
    mail_vars["articleTitle"] = md_to_html(art.title)
    mail_vars["articleAuthors"] = emailing.mkAuthors(art)

    default_subject = emailing_tools.replaceMailVars(str(mail_template["subject"] or ""), mail_vars)
    default_message = emailing_tools.replaceMailVars(str(mail_template["content"] or ""), mail_vars)

    default_subject = emailing.patch_email_subject(default_subject, articleId)

    req_is_email = IS_EMAIL(error_message=T("invalid e-mail!"))
    replyto = db(db.auth_user.id == auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()

    replyTo = ", ".join([replyto.email, contact])
    default_cc = '%s, %s'%(sender_email, contact)

    form: ... = SQLFORM.factory( # type: ignore
        Field("author_email", label=T("Author email address"), type="string", length=250, requires=req_is_email, default=author.email, writable=False),
        Field.CC(default_cc),  # type: ignore
        Field("replyto", label=T("Reply-to"), type="string", length=250, default=replyTo, writable=False),
        Field("subject", label=T("Subject"), type="string", length=250, default=default_subject, required=True),
        Field("message", label=T("Message"), type="text", default=default_message, required=True),
    )
    form.element(_type="submit")["_value"] = T("Send email")
    form.element("textarea[name=message]")["_style"] = "height:500px;"

    if form.process().accepted:
        if pciRRactivated:
            art.request_submission_change = True
            art.update_record() # type: ignore
        request.vars["replyto"] = replyTo
        try:
            emailing.send_submitter_generic_mail(author.email, art.id, request.vars, template)
            emailing.send_submitter_generic_reminder("#ReminderRevisionsRequiredToYourSubmission", form.vars.subject, form.vars.message, mail_vars, art.id)
        except Exception as e:
            session.flash = (session.flash or "") + T("Email failed.")
            raise e
        if "Revision" in template:
            art.update_record(status="Scheduled submission revision") # type: ignore
            redirect(URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False)))
        else:
            redirect(URL(c="manager", f="presubmissions"))

    return dict(
        form=form,
        pageHelp=getHelp("#EmailForSubmitter"),
        titleIcon="envelope",
        pageTitle=getTitle("#EmailForSubmitterInfoTitle"),
        customText=getText("#EmailForSubmitterInfo"),
        myBackButton=common_small_html.mkBackButton(),
    )

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or auth.has_membership(role="administrator"))
def recommender_statistics():
    response.view = "default/myLayout.html"

    db.v_recommender_stats.id.represent = lambda id, row: common_small_html.mkUserWithMail(id, reverse=True)
    db.v_recommender_stats.total_invitations.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="total_invitations"))) if text != 0 else "0"
    db.v_recommender_stats.total_accepted.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="total_accepted"))) if text != 0 else "0"
    db.v_recommender_stats.total_completed.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="total_completed"))) if text != 0 else "0"
    db.v_recommender_stats.current_invitations.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="current_invitations"))) if text != 0 else "0"
    db.v_recommender_stats.current_assignments.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="current_assignments"))) if text != 0 else "0"
    db.v_recommender_stats.awaiting_revision.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="awaiting_revision"))) if text != 0 else "0"
    db.v_recommender_stats.requiring_action.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="requiring_action"))) if text != 0 else "0"
    db.v_recommender_stats.requiring_reviewers.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="requiring_reviewers"))) if text != 0 else "0"
    db.v_recommender_stats.required_reviews_completed.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="required_reviews_completed"))) if text != 0 else "0"
    db.v_recommender_stats.late_reviews.represent = lambda text, row: A(text, _href=URL("manager", "recommender_breakdown", vars=dict(recommenderId=row.id, action="late_reviews"))) if text != 0 else "0"

    grid = SQLFORM.grid(
        query = db.v_recommender_stats,
        details=True,
        editable=False,
        deletable=False,
        create=False,
        searchable=False,
        csv=False,
        paginate=None,
        maxtextlength=256,
        orderby=~db.v_recommender_stats.id,
        fields=[
            db.v_recommender_stats.id,
            db.v_recommender_stats.total_invitations,
            db.v_recommender_stats.total_accepted,
            db.v_recommender_stats.total_completed,
            db.v_recommender_stats.current_invitations,
            db.v_recommender_stats.current_assignments,
            db.v_recommender_stats.awaiting_revision,
            db.v_recommender_stats.requiring_action,
            db.v_recommender_stats.requiring_reviewers,
            db.v_recommender_stats.required_reviews_completed,
            db.v_recommender_stats.late_reviews
        ],
        _class="web2py_grid  statistics",
    )
    myScript = common_tools.get_script("statistics_table.js")

    return dict(
        titleIcon="stats",
        pageTitle=getTitle("#RecommenderStatisticsTitle"),
        customText=getText("#RecommenderStatisticsText"),
        pageHelp=getHelp("#RecommenderStatistics"),
        myBackButton=common_small_html.mkBackButton(),
        grid=grid,
        myFinalScript=myScript,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )

######################################################################################################################################################################
def fetch_query(action, recommenderId):
    subquery = db((db.t_articles.id == db.t_recommendations.article_id) &
              (db.t_articles.status == 'Under consideration') &
              (db.t_reviews.recommendation_id == db.t_recommendations.id ) &
              (db.t_recommendations.recommender_id == recommenderId))
    query = db((subquery.count(distinct=True) < 2) & (db.t_articles.report_stage == 'STAGE 1') |
           (subquery.count(distinct=True) == 0) & (db.t_articles.report_stage == 'STAGE 2')).select(db.t_articles.ALL, groupby=db.t_articles.id)

    complete_sb_query = db((db.t_articles.id == db.t_recommendations.article_id) &
                        (db.t_articles.status.belongs('Under consideration', 'Awaiting revision')) &
                        (db.t_reviews.recommendation_id == db.t_recommendations.id ) &
                        (db.t_recommendations.recommender_id == recommenderId))
    count_filter = db((db.t_reviews.acceptation_timestamp != None) & (db.t_reviews.review_state == 'Review completed'))
    complete_query = complete_sb_query.select(db.t_articles.ALL,
                            groupby=db.t_articles.id,
                            having=(count_filter.count() == db.t_reviews.id.count()))

    queries = {
        "total_invitations": get_recommendation_DAL_query(f"SELECT DISTINCT id FROM ( \
                                                                    SELECT DISTINCT art.id FROM t_articles art,  t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id = art.id and recomm.recommender_id={recommenderId} and recomm.id=v_art.recommendation_id \
                                                                    UNION ALL \
                                                                    SELECT DISTINCT art.id FROM t_articles art, t_suggested_recommenders ts WHERE ts.suggested_recommender_id={recommenderId} and ts.article_id = art.id ) AS total_invitations;",  False),
        "total_accepted" : ((db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommender_id==recommenderId) & (db.t_recommendations.id == db.v_article_recommender.recommendation_id)),
        "total_completed": ((db.t_articles.id==db.t_recommendations.article_id) & (db.t_articles.status.belongs('Recommended', 'Recommended-private', 'Rejected', 'Cancelled')) & (db.t_articles.report_stage.belongs('STAGE 1', 'STAGE 2')) &  (db.t_recommendations.recommender_id==recommenderId) & (db.t_recommendations.id == db.v_article_recommender.recommendation_id)),
        "current_invitations" : ((db.t_articles.id == db.t_suggested_recommenders.article_id) & (db.t_suggested_recommenders.suggested_recommender_id == recommenderId) & (db.t_articles.status == 'Awaiting consideration') & (db.t_suggested_recommenders.declined == False)),
        "current_assignments": ((db.t_articles.id==db.t_recommendations.article_id) & (db.t_articles.status.belongs('Under consideration', 'Awaiting revision', 'Scheduled submission revision', 'Scheduled submission under consideration')) & (db.t_articles.report_stage.belongs('STAGE 1', 'STAGE 2')) &  (db.t_recommendations.recommender_id==recommenderId)  & (db.t_recommendations.id == db.v_article_recommender.recommendation_id)),
        "awaiting_revision" : ((db.t_articles.id==db.t_recommendations.article_id) & (db.t_articles.status.belongs('Awaiting revision', 'Scheduled submission revision')) & (db.t_articles.report_stage.belongs('STAGE 1', 'STAGE 2')) &  (db.t_recommendations.recommender_id==recommenderId)  & (db.t_recommendations.id == db.v_article_recommender.recommendation_id)),
        "requiring_action" : get_recommendation_DAL_query(f"SELECT DISTINCT * FROM (\
                                                                   SELECT DISTINCT recomm.* AS nb  FROM t_articles art JOIN t_recommendations recomm ON art.id = recomm.article_id JOIN v_article_recommender v_art ON recomm.id = v_art.recommendation_id \
                                                                    LEFT JOIN ( \
                                                                            SELECT recommendation_id, \
                                                                                COUNT(CASE WHEN review_state = 'Awaiting review' THEN 1 ELSE NULL END) AS num_awaiting_reviews, \
                                                                                MAX(CASE WHEN review_state = 'Review completed' THEN 1 ELSE 0 END) AS has_completed_review \
                                                                            FROM t_reviews \
                                                                            GROUP BY recommendation_id \
                                                                    ) rev ON recomm.id = rev.recommendation_id \
                                                                    WHERE art.status = 'Under consideration' AND recomm.recommender_id = {recommenderId} AND COALESCE(rev.has_completed_review, 0) = 0 GROUP BY recomm.id, art.report_stage, rev.num_awaiting_reviews \
                                                                    HAVING ((art.report_stage = 'STAGE 1' AND COALESCE(rev.num_awaiting_reviews, 0) < 2) OR (art.report_stage = 'STAGE 2' AND COALESCE(rev.num_awaiting_reviews, 0) = 0)) \
                                                            UNION ALL\
                                                                   SELECT DISTINCT recomm.* AS nb FROM t_articles art JOIN t_recommendations recomm ON recomm.article_id = art.id JOIN t_reviews trev ON trev.recommendation_id = recomm.id JOIN v_article_recommender v_art ON recomm.id = v_art.recommendation_id LEFT JOIN t_reviews trew ON trew.recommendation_id = recomm.id AND trew.review_state = 'Awaiting review' WHERE art.status = 'Under consideration' AND recomm.recommender_id = {recommenderId} AND trev.review_state = 'Review completed' \
                                                                   GROUP BY recomm.id, art.id, recomm.recommender_id HAVING COUNT(trev.id) >= 2 AND SUM(CASE WHEN trew.id IS NULL THEN 0 ELSE 1 END) = 0) AS requiring_action"),
        "requiring_reviewers": get_recommendation_DAL_query(f"SELECT DISTINCT recomm.id FROM t_articles art JOIN t_recommendations recomm ON art.id = recomm.article_id JOIN v_article_recommender v_art ON recomm.id = v_art.recommendation_id \
                                                            LEFT JOIN ( \
                                                                    SELECT recommendation_id, \
                                                                        COUNT(CASE WHEN review_state = 'Awaiting review' THEN 1 ELSE NULL END) AS num_awaiting_reviews, \
                                                                        MAX(CASE WHEN review_state = 'Review completed' THEN 1 ELSE 0 END) AS has_completed_review \
                                                                    FROM t_reviews \
                                                                    GROUP BY recommendation_id \
                                                            ) rev ON recomm.id = rev.recommendation_id \
                                                            WHERE art.status = 'Under consideration' AND recomm.recommender_id = {recommenderId} AND COALESCE(rev.has_completed_review, 0) = 0 GROUP BY recomm.id, art.report_stage, rev.num_awaiting_reviews \
                                                            HAVING ((art.report_stage = 'STAGE 1' AND COALESCE(rev.num_awaiting_reviews, 0) < 2) OR (art.report_stage = 'STAGE 2' AND COALESCE(rev.num_awaiting_reviews, 0) = 0))"),
        "required_reviews_completed": get_recommendation_DAL_query(f"SELECT DISTINCT recomm.id FROM t_articles art JOIN t_recommendations recomm ON recomm.article_id = art.id JOIN t_reviews trev ON trev.recommendation_id = recomm.id JOIN v_article_recommender v_art ON recomm.id = v_art.recommendation_id LEFT JOIN t_reviews trew ON trew.recommendation_id = recomm.id AND trew.review_state = 'Awaiting review' WHERE art.status = 'Under consideration' AND recomm.recommender_id ={recommenderId} AND trev.review_state = 'Review completed' \
                                                                        GROUP BY recomm.id, art.id, recomm.recommender_id HAVING COUNT(trev.id) >= 2 AND SUM(CASE WHEN trew.id IS NULL THEN 0 ELSE 1 END) = 0"),
        "late_reviews": get_recommendation_DAL_query(f"SELECT DISTINCT recomm.id FROM t_articles art, t_reviews trev, t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id = art.id and trev.recommendation_id = recomm.id and recomm.recommender_id={recommenderId} and recomm.id=v_art.recommendation_id and recomm.recommendation_state = 'Ongoing' and trev.review_state = 'Awaiting review' and trev.acceptation_timestamp + convert_duration_to_sql_interval(trev.review_duration) < NOW()"),
    }
    return queries[action]


def get_recommendation_DAL_query(raw_sql_query_returning_recommendation_id: str, recommendation: bool=True):
    result = db.executesql(raw_sql_query_returning_recommendation_id)
    ids = []

    for line in result:
        id = line[0]
        if id not in ids:
            ids.append(line[0])
    if recommendation:
        return ((db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.id.belongs(ids)))
    return (db.t_articles.id.belongs(ids))

######################################################################################################################################################################
def recommender_breakdown():
    action = request.vars["action"]
    recommenderId = request.vars["recommenderId"]
    page_help_dict = {
        "total_invitations" : "#TotalInvitationStats",
        "total_accepted" : "#TotalAcceptedStats",
        "total_completed" : "#TotalCompletedStats",
        "current_invitations" : "#CurrentInvitationStats",
        "current_assignments" : "#CurrentAssignmentStats",
        "awaiting_revision" : "#AwaitingRevisionStats",
        "requiring_action" : "#RequiringActionStats",
        "requiring_reviewers" : "#RequiringReviewerStats",
        "required_reviews_completed" : "#RequiredReviewsCompletedStats",
        "late_reviews" : "#LateReviewStat"
    }
    goBack = URL(re.sub(r".*/([^/]+)$", "\\1", request.env.request_uri), scheme=scheme, host=host, port=port)
    query = fetch_query(action, recommenderId)
    if action == "total_invitations" or action == "current_invitations":
        resu = _manage_articles(None, stats_query=query)
    else:
        resu = _all_recommendations(goBack, query, False)
    resu["customText"] = getText(f"{page_help_dict[action]}Text")
    resu["titleIcon"] = "ok-sign"
    resu["pageTitle"] = getTitle(f"{page_help_dict[action]}Title")
    resu["pageHelp"] = getHelp(page_help_dict[action])
    return resu


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def email_for_recommender():
    response.view = "default/myLayout.html"
    articleId = request.vars["articleId"]
    lastRecomm = request.vars["lastRecomm"]

    if articleId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
        return
    
    if lastRecomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
        return
    
    article = db.t_articles[articleId]
    if not article:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
        return
    
    recomm = db.get_last_recomm(articleId)
    if not recomm:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
        return

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

    sender: Optional[User] = None
    if auth.has_membership(role="manager"):
        sender = User.get_by_id(recomm.recommender_id)
    else:
        sender = cast(User, auth.user)

    recommender = db(recomm.recommender_id == db.auth_user.id).select().last()
    hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderDecisionSentBack", article)
    mail_template = emailing_tools.getMailTemplateHashtag(hashtag_template)
    mail_vars = emailing_tools.getMailForRecommenderCommonVars(auth.user, article, recomm, recommender)

    subject = emailing_tools.replaceMailVars(mail_template["subject"], mail_vars)
    message = emailing_tools.replaceMailVars(mail_template["content"], mail_vars)

    replyto = db(db.auth_user.id == auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
    replyTo = ", ".join([replyto.email, contact])
    default_replyto = emailing_tools.to_string_addresses(replyTo)

    sender_email = db(db.auth_user.id == auth.user_id).select().last().email
    cc = '%s, %s'%(sender_email, contact)
    default_cc = emailing_tools.to_string_addresses(cc)

    form = SQLFORM.factory(
        Field("dest_mail_address", label=T("Destination Email"), type="string", length=250, default=recommender.email),
        Field("replyto", label=T("Reply-to"), type="string", length=250, default=default_replyto),
        Field("cc_mail_addresses", type="string", label=T("CC"), default=default_cc),
        Field("subject", label=T("Subject"), type="string", length=250, default=subject, required=True),
        Field("message", label=T("Message"), type="text", default=message, required=True),
    )

    form.element(_type="submit")["_value"] = T("Send e-mail")
    form.element("textarea[name=message]")["_style"] = "height:500px;"

    resent = False
    if form.process().accepted:
        try:
            emailing.send_to_recommender_decision_sent_back(form,
                                                            articleId,
                                                            lastRecomm,
                                                            hashtag_template)
            if article.status.startswith("Pre-"):
                recomm.is_closed = False
                recomm.recommendation_state = "Ongoing"
                recomm.update_record()
                article.status = "Under consideration" if not article.is_scheduled else "Scheduled submission pending"
                article.update_record()
            resent = True
        except Exception as e:
            session.flash = (session.flash or "") + T("E-mail failed.")
            raise e
        redirect(URL(c="manager", f="pending_articles"))

    return dict(
        form=form,
        pageHelp=getHelp("#EmailForRegisterdReviewer"),
        titleIcon="envelope",
        pageTitle=getTitle("#EmailForRegisteredReviewerInfoTitle"),
        customText=getText("#EmailForRegisteredReviewerInfo"),
    )


@auth.requires(auth.has_membership(role="manager"))
def manage_suggested_recommenders():
    query = (db.t_suggested_recommenders.recommender_validated == None) \
            & (db.t_suggested_recommenders.declined == False) \
            & (db.t_articles.id == db.t_suggested_recommenders.article_id) \
            & (db.auth_user.id == db.t_suggested_recommenders.suggested_recommender_id) \
            & (db.t_articles.status == ArticleStatus.AWAITING_CONSIDERATION.value)
    
    infos_by_article: Dict[int, Tuple[Article, List[Tuple[User, SuggestedRecommender]]]] = dict()

    elements = db(query).select()

    for element in elements:
        recommender: User = element['auth_user']
        article: Article = element['t_articles']
        sugg_recommender: SuggestedRecommender = element['t_suggested_recommenders']

        if article.id in infos_by_article:
            infos_by_article[article.id][1].append((recommender, sugg_recommender))
        else:
            infos_by_article[article.id] = (article, [(recommender, sugg_recommender)])
    
    html: ... = CENTER()
    next_url = URL(args=request.args, vars=request.get_vars, scheme=True)

    for article, sugg_recommenders in infos_by_article.values():
        html.append(H3(B(f"Article {article.id}: "), f"{article.title}"))

        list: ... = TBODY()
        for recommender, sugg_recommender in sugg_recommenders:
            li = TR(
                TD(mkUser_U(recommender, True, orcid=True)),
                TD(A(recommender.email, _href=f"mailto:{recommender.email}"), _style="padding-left: 10px; font-style: italic"),
                TD(A("Valid", _class="btn btn-success", 
                              _href=URL("manager", "do_valid_suggested_recommender",vars=dict(sugg_recommender_id=sugg_recommender.id, _next=next_url))),
                              _style="padding-left: 10px;"),
                TD(A("Reject", _class="btn btn-warning",
                               _href=URL("manager", "do_reject_suggested_recommender", vars=dict(sugg_recommender_id=sugg_recommender.id, _next=next_url))),
                               _style="padding-left: 10px"),
            )

            list.append(li)
        html.append(TABLE(list))

    if len(infos_by_article) == 0:
        html.append(B("There are no suggested recommenders to manage."))

    response.view = "default/myLayout.html"
    return dict(
        grid=html,
        pageHelp=getHelp("#EmailForRegisterdReviewer"),
        titleIcon="user",
        pageTitle="Manage suggested recommenders",
    )


@auth.requires(auth.has_membership(role="manager"))
def do_valid_suggested_recommender():
    try:
        next_url = get_next()
        sugg_recommender_id = int(request.vars.sugg_recommender_id)
    except:
        return HTTP(400, "Error in args")

    sugg_recommender = SuggestedRecommender.get_by_id(sugg_recommender_id)
    if sugg_recommender:
        sugg_recommender_name = User.get_name_by_id(sugg_recommender.suggested_recommender_id)
        sugg_recommender.update_record(recommender_validated=False) # type: ignore
    else:
        return HTTP(404, session.flash)

    session.flash = f"Suggested recommender {sugg_recommender_name} has been validated"

    if next_url:
        return redirect(next_url)
    else:
        return HTTP(200, session.flash)



@auth.requires(auth.has_membership(role="manager"))
def do_reject_suggested_recommender():
    try:
        next_url = get_next()
        sugg_recommender_id = int(request.vars.sugg_recommender_id)
    except:
        return HTTP(400, "Error in args")

    sugg_recommender = SuggestedRecommender.get_by_id(sugg_recommender_id)
    if sugg_recommender:
        sugg_recommender_name = User.get_name_by_id(sugg_recommender.suggested_recommender_id)
        sugg_recommender.update_record(recommender_validated=False) # type: ignore
    else:
        return HTTP(404, session.flash)

    session.flash = f"Suggested recommender {sugg_recommender_name} has been rejected"

    if next_url:
        return redirect(next_url)
    else:
        return HTTP(200, session.flash)
