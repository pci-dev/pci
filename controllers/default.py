# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations
import os
import re
import time
from typing import Any, Optional, cast

from app_components import article_components
from app_modules.common_tools import get_article_id, get_next, get_reset_password_key, get_review_id
from app_modules.helper import *
from app_modules.common_small_html import complete_profile_dialog, invitation_to_review_form
from controller_modules import adjust_grid
from app_modules.emailing import send_conditional_acceptation_review_mail
from gluon import DAL
# -------------------------------------------------------------------------
# app configuration made easy. Look inside private/appconfig.ini
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
from gluon.contrib.appconfig import AppConfig
from gluon.globals import Request
from gluon.http import HTTP, redirect
from gluon.sqlhtml import SQLFORM
from gluon.utils import web2py_uuid

from models.article import Article
from models.recommendation import Recommendation
from models.review import Review, ReviewState
from models.user import User

# -------------------------------------------------------------------------
# This is a sample controller
# - index is the default action of any application
# - user is required for authentication and authorization
# - download is for downloading files uploaded in the db (does streaming)
# -------------------------------------------------------------------------


myconf = AppConfig(reload=True)
db = cast(DAL, db)

pciRRactivated = myconf.get("config.registered_reports", default=False)

if not myconf.get("smtp.server"):
    auth.settings.registration_requires_verification = False
    auth.settings.login_after_registration = True

######################################################################################################################################################################
def loading():
    return DIV(IMG(_alt="Loading...", _src=URL(c="static", f="images/loading.gif")), _id="loading", _style="text-align:center;")


######################################################################################################################################################################
# Home page (public)
def index():
    response.view = "default/index.html"

    recomms = db.get_last_recomms()

    def articleRow(row):
        return article_components.getRecommArticleRowCard(auth, db, response,
                        row,
                        recomms.get(row.id),
                        withDate=True)

    t_articles = db.v_article

    t_articles.id.represent = lambda text, row: articleRow(row)

    # make advanced search form field use simple dropdown widget
    t_articles.thematics.type = "string"
    t_articles.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, zero=None)

    for field in ("""
    anonymous_submission
    has_manager_in_authors
    doi
    preprint_server
    ms_version
    picture_rights_ok
    results_based_on_data
    scripts_used_for_result
    codes_used_in_study
    validation_timestamp
    user_id
    status
    last_status_change
    request_submission_change
    funding
    already_published
    doi_of_published_article
    parallel_submission
    article_source
    sub_thematics
    is_searching_reviewers
    report_stage
    art_stage_1_id
    record_url_version
    record_id_version
    scheduled_submission_date
    upload_timestamp
    """
    .split()): t_articles[field].readable = False

    try: original_grid = SQLFORM.grid(
        (t_articles.status == "Recommended"),
        maxtextlength=250,
        paginate=10,
        csv=False,
        fields=[
            t_articles.id,
            t_articles.title,
            t_articles.authors,
            t_articles.abstract,
            t_articles.anonymous_submission,
            t_articles.article_source,
            t_articles.last_status_change,
            t_articles.uploaded_picture,
            t_articles.status,
            t_articles.art_stage_1_id,
            t_articles.already_published,
            t_articles.doi,
            t_articles.thematics,
            t_articles.recommender,
            t_articles.reviewers,
            t_articles.submission_date,
            t_articles.scheduled_submission_date,
            ],
        orderby=~t_articles.last_status_change,
        _class="web2py_grid action-button-absolute",
    )
    except: original_grid = None

    integer_fields = ['v_article.article_year']
    remove_options = ['v_article.id']
    try: grid = adjust_grid.adjust_grid_basic(original_grid, 'main_articles', remove_options, integer_fields)
    except: grid = original_grid

    tweeterAcc = myconf.get("social.tweeter")
    mastodonAcc = myconf.get("social.mastodon")
    lastRecommTitle = H3(
        T("Latest recommendations"),
        A(
            SPAN(IMG(_alt="rss", _src=URL(c="static", f="images/rss.png"), _style="margin-right:8px;"),),
            _href=URL("about", "rss_info"),
            _class="btn pci-rss-btn",
            _style="float:right;",
        ),
        A(
            SPAN(IMG(_alt="mastodon", _src=URL(c="static", f="images/mastodon-logo.svg")),),
            _href="https://spore.social/%(mastodonAcc)s"%locals(),
            _class="btn pci-twitter-btn",
            _style="float:right;",
        ) if pciRRactivated else
        A(
            SPAN(IMG(_alt="twitter", _src=URL(c="static", f="images/twitter-logo.png")),),
            _href="https://twitter.com/%(tweeterAcc)s"%locals(),
            _class="btn pci-twitter-btn",
            _style="float:right;",
        ),

        _class="pci-pageTitleText",
        _style="margin-top: 15px; margin-bottom: 20px",
    )
    grid.element(".web2py_table").insert(0, lastRecommTitle) \
            if grid.element(".web2py_table") else None

    return dict(
            pageTitle=getTitle(request, auth, db, "#HomeTitle"),
            customText=getText(request, auth, db, "#HomeInfo"),
            pageHelp=getHelp(request, auth, db, "#Home"),
            grid = grid,
            shareable=True,
            currentUrl=URL(c="default", f="index"),
            pciRRactivated=pciRRactivated,
            panel=None,
        )


######################################################################################################################################################################
def user():
    response.view = "default/myLayoutBot.html"

    # """
    # exposes:
    # http://..../[app]/default/user/login
    # http://..../[app]/default/user/logout
    # http://..../[app]/default/user/register
    # http://..../[app]/default/user/profile
    # http://..../[app]/default/user/retrieve_password
    # http://..../[app]/default/user/change_password
    # http://..../[app]/default/user/bulk_register
    # use @auth.requires_login()
    # 	@auth.requires_membership('group name')
    # 	@auth.requires_permission('read','table name',record_id)
    # to decorate functions that need access control
    # also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
    # """

    if "_next" in request.vars:
        suite = cast(str, request.vars["_next"])
        if len(suite) < 4:
            suite = None
    else:
        suite = None
    if isinstance(suite, list):
        suite = suite[1]

    if "_formkey" in request.vars:
        fkey = cast(str, request.vars["_formkey"])
    else:
        fkey = None
    if isinstance(fkey, list):
        fkey = fkey[1]
    if fkey == "":
        fkey = None

    titleIcon = ""
    pageTitle = ""
    pageHelp = ""
    customText = ""
    myBottomText = ""

    form = auth()
    db.auth_user.registration_key.writable = False
    db.auth_user.registration_key.readable = False
    if request.args and len(request.args) > 0:

        if request.args[0] == "login":
            if auth.user_id:
                redirect(URL('default','index'))
            titleIcon = "log-in"
            pageTitle = getTitle(request, auth, db, "#LogInTitle")
            pageHelp = getHelp(request, auth, db, "#LogIn")
            customText = getText(request, auth, db, "#LogInText")
            form.add_button(T("Lost password?"), URL(c="default", f="user", args=["request_reset_password"]), _class="pci2-lost-password-link")
            # green color for submit button form
            form.element(_type="submit")["_class"] = "btn btn-success"
            # display "Lost password?" under login button
            form.element("#submit_record__row .col-sm-9")["_class"] = "pci2-flex-column pci2-flex-center"
            if suite:
                auth.settings.login_next = suite

        elif request.args[0] == "register":
            if auth.user_id:
                redirect(URL('default','index'))
            titleIcon = "edit"
            pageTitle = getTitle(request, auth, db, "#CreateAccountTitle")
            pageHelp = getHelp(request, auth, db, "#CreateAccount")
            customText = getText(request, auth, db, "#ProfileText")
            myBottomText = getText(request, auth, db, "#ProfileBottomText")
            db.auth_user.ethical_code_approved.requires = IS_IN_SET(["on"])
            form.element(_type="submit")["_class"] = "btn btn-success"
            form.element('#auth_user_password_two__label').components[0] = SPAN(T("Confirm Password")) + SPAN(" * ", _style="color:red;")
            if suite:
                auth.settings.register_next = suite
                check_already_registered(form)

        elif request.args[0] == "profile":
            titleIcon = "user"
            pageTitle = getTitle(request, auth, db, "#ProfileTitle")
            pageHelp = getHelp(request, auth, db, "#Profile")
            customText = getText(request, auth, db, "#ProfileText")
            myBottomText = getText(request, auth, db, "#ProfileBottomText")
            form.element(_type="submit")["_class"] = "btn btn-success"
            if suite:
                auth.settings.profile_next = suite

        elif request.args[0] == "request_reset_password":
            titleIcon = "lock"
            pageTitle = getTitle(request, auth, db, "#ResetPasswordTitle")
            pageHelp = getHelp(request, auth, db, "#ResetPassword")
            customText = getText(request, auth, db, "#ResetPasswordText")
            user = db(db.auth_user.email == request.vars["email"]).select().last()
            form.element(_type="submit")["_class"] = "btn btn-success"
            form.element(_name="email")["_value"] = request.vars.email
            if (fkey is not None) and (user is not None):
                reset_password_key = str(int(time.time())) + "-" + web2py_uuid()
                user.update_record(reset_password_key=reset_password_key)
                # emailing.send_to_reset_password(session, auth, db, user.id)
                # if suite:
                #     redirect(URL("default", "index", vars=dict(_next=suite)))  # squeeze normal functions
                # else:
                #     redirect(URL("default", "index"))  # squeeze normal functions
            if suite:
                auth.settings.request_reset_password_next = suite

        elif request.args[0] == "reset_password":
            titleIcon = "lock"
            pageTitle = getTitle(request, auth, db, "#ResetPasswordTitle")
            pageHelp = getHelp(request, auth, db, "#ResetPassword")
            customText = getText(request, auth, db, "#ResetPasswordText")
            vkey = get_reset_password_key(request)
            user = User.get_by_reset_password_key(db, vkey)
            form.element(_type="submit")["_class"] = "btn btn-success"
            if (vkey is not None) and (suite is not None) and (user is None):
                redirect(suite)
            if suite:
                auth.settings.reset_password_next = suite

        elif request.args[0] == "change_password":
            titleIcon = "lock"
            pageTitle = getTitle(request, auth, db, "#ChangePasswordTitle")
            customText = getText(request, auth, db, "#ResetPasswordText")
            form.element(_type="submit")["_class"] = "btn btn-success"

    return dict(titleIcon=titleIcon, pageTitle=pageTitle, customText=customText, myBottomText=myBottomText, pageHelp=pageHelp, form=form)


def check_already_registered(form):
    existing_user = db(db.auth_user.email.lower() == str(form.vars.email).lower()).select().last()
    if existing_user:
        form.errors.email = SPAN(
                T("This email is already registered"),
                T("; you may wish to "),
                A(T("reset your password"), _href=URL("user/request_reset_password", vars={"email":form.vars.email})),
        )


def show_account_menu_dialog():
    if session.show_account_menu_dialog:
        return
    
    current_user = cast(User, auth.user)
    if not current_user:
        return
    
    is_profile_completed = User.is_profile_completed(current_user)
    if is_profile_completed:
        return

    session.show_account_menu_dialog = True
    next = get_next(request)
    dialog = complete_profile_dialog(next)
    return dialog

######################################################################################################################################################################
def change_mail_form_processing(form):

    form.vars.new_email = form.vars.new_email.lower()

    if CRYPT()(form.vars.password_confirmation)[0] != db.auth_user[auth.user_id].password:
        form.errors.password_confirmation = "Incorrect Password"

    mail_already_used = db(db.auth_user.email == form.vars.new_email).count() >= 1
    if mail_already_used:
        form.errors.new_email = "E-mail already used"

    if form.vars.new_email != form.vars.email_confirmation.lower():
        form.errors.email_confirmation = "New e-mail and its confirmation does not match"

    if form.vars.new_email == db.auth_user[auth.user_id].email:
        form.errors.new_email = "E-mail is the same (case insensitive)"


@auth.requires_login()
def change_email():
    response.view = "default/myLayoutBot.html"
    form = FORM(
        DIV(
            LABEL(T("Password"), _class="control-label col-sm-3"),
            DIV(INPUT(_name="password_confirmation", _type="password", _class="form-control"), _class="col-sm-9"),
            SPAN(_class="help-block"),
            _class="form-group",
        ),
        DIV(
            LABEL(T("New e-mail address"), _class="control-label col-sm-3"),
            DIV(INPUT(_name="new_email", _class="form-control"), _class="col-sm-9"),
            SPAN(_class="help-block"),
            _class="form-group",
        ),
        DIV(
            LABEL(T("New e-mail address confirmation"), _class="control-label col-sm-3"),
            DIV(INPUT(_name="email_confirmation", _class="form-control"), _class="col-sm-9"),
            SPAN(_class="help-block"),
            _class="form-group",
        ),
        DIV(INPUT(_value=T("Change e-mail address"), _type="submit", _class="btn btn-success",), _class="form-group",),
    )

    if form.process(onvalidation=change_mail_form_processing).accepted:
        max_time = time.time()
        registeration_key = str((15 * 24 * 60 * 60) + int(max_time)) + "-" + web2py_uuid()
        recover_key = str((15 * 24 * 60 * 60) + int(max_time)) + "-" + web2py_uuid()

        user = db.auth_user[auth.user_id]

        emailing.send_change_mail(session, auth, db, auth.user_id, form.vars.new_email, registeration_key)
        emailing.send_recover_mail(session, auth, db, auth.user_id, user.email, recover_key)

        user.update_record(email=form.vars.new_email, registration_key=registeration_key, recover_email=user.email, recover_email_key=recover_key)

        redirect(URL("default", "user", args="logout"))

    response.flash = None

    return dict(titleIcon="envelope", pageTitle=getTitle(request, auth, db, "#ChangeMailTitle"), customText=getText(request, auth, db, "#ChangeMail"), form=form)

######################################################################################################################################################################

def invitation_to_review():
    more_delay = cast(bool, request.vars['more_delay'] == 'true')
    
    if not 'reviewId' in request.vars:
        session.flash = current.T('No review id found')
        redirect(URL('default','index'))
        return
    
    reviewId = int(request.vars['reviewId'])
    review = Review.get_by_id(db, reviewId)
    if not review or not review.recommendation_id:
        session.flash = current.T('No review found')
        redirect(URL('default','index'))
        return
    
    recommendation = Recommendation.get_by_id(db, review.recommendation_id)
    if not recommendation or not recommendation.article_id:
        session.flash = current.T('No recommendation found')
        redirect(URL('default','index'))
        return
    
    article = Article.get_by_id(db, recommendation.article_id)
    if not article:
        session.flash = current.T('No article found')
        redirect(URL('default','index'))
        return
    
    recommender = User.get_by_id(db, recommendation.recommender_id)
    if not recommender:
        session.flash = current.T('No recommender found')
        redirect(URL('default','index'))
        return

    reset_password_key = get_reset_password_key(request)
    user: Optional[User] = None

    if reset_password_key and not auth.user_id:
        user = User.get_by_reset_password_key(db, reset_password_key)
    elif auth.user_id:
        user = User.get_by_id(db, auth.user_id)
    
    if not user:
        redirect(URL(a='default', c='user', args='login', vars=dict(_next=URL(args=request.args, vars=request.vars))))
        return
    
    if user.id != review.reviewer_id:
        session.flash = current.T('Bad user')
        redirect(cast(str, URL('default','index')))
        return
    
    if review.review_state == ReviewState.DECLINED.value:
        redirect(URL(c='user_actions', f='decline_review',  vars=dict(reviewId=review.id, key=review.quick_decline_key)))
        return
    
    recommHeaderHtml = cast(XML, article_components.getArticleInfosCard(auth, db, response, article, printable=False))
    response.view = "default/invitation_to_review_preprint.html"

    form = invitation_to_review_form(request, auth, db, article, user, review, more_delay)

    if form.process().accepted:
        if request.vars.no_conflict_of_interest == 'yes' and request.vars.anonymous_agreement == 'yes' and request.vars.ethics_approved == 'true' and (request.vars.cgu_checkbox == 'yes' or user.ethical_code_approved):
            url_vars = dict(articleId=article.id, key=user.reset_password_key, reviewId=review.id)
            
            if more_delay and request.vars.review_duration and review.review_duration != request.vars.review_duration:
                Review.set_review_duration(review, request.vars.review_duration)
                url_vars['more_delay'] = 'true'
            
            action_form_url = cast(str, URL("default", "invitation_to_review_preprint_acceptation", vars=url_vars))
            redirect(action_form_url)

    if review.acceptation_timestamp:
        url_vars = dict(articleId=article.id, key=user.reset_password_key, reviewId=review.id)
        
        if review.review_state == ReviewState.AWAITING_REVIEW.value:
            action_form_url = cast(str, URL("default", "invitation_to_review_preprint_acceptation", vars=url_vars))
            redirect(action_form_url)
        elif review.review_state == ReviewState.AWAITING_RESPONSE.value or more_delay:
            url_vars['more_delay'] = 'true'
            action_form_url = cast(str, URL("default", "invitation_to_review_preprint_acceptation", vars=url_vars))
            redirect(action_form_url)
        elif review.review_state == ReviewState.DECLINED_BY_RECOMMENDER.value:
            redirect(URL(c="user_actions", f="accept_review_confirmed", vars=dict(reviewId=review.id)))
    
    return dict(recommHeaderHtml=recommHeaderHtml,
                isRecommender=False,
                isSubmitter=False,
                isAlreadyReviewer=False,
                review=review,
                user=user,
                recommender=recommender,
                pciRRactivated=pciRRactivated,
                form=form)
    

def invitation_to_review_acceptation():
    article_id = get_article_id(request)
    review_id = get_review_id(request)
    more_delay = cast(bool, request.vars['more_delay'] == 'true')

    if article_id and review_id:
        url_vars = dict(reviewId=review_id, _next=URL(c="user", f="recommendations", vars=dict(articleId=article_id)))
        session._reset_password_redirect = URL(c="user_actions", f="accept_review_confirmed", vars=url_vars)

        review = Review.get_by_id(db, review_id)
        if review and not review.acceptation_timestamp:
            if more_delay:
                Review.accept_review(review, True, ReviewState.AWAITING_RESPONSE)
                send_conditional_acceptation_review_mail(session, auth, db, review)
            else:
                Review.accept_review(review, True)

    reset_password_key = get_reset_password_key(request)
    user: Optional[User] = None
    if reset_password_key and not auth.user_id:
        user = User.get_by_reset_password_key(db, reset_password_key)
    elif auth.user_id:
        user = User.get_by_id(db, auth.user_id)
    
    if user and not user.ethical_code_approved:
        user.ethical_code_approved = True
        user.update_record()

    if user and auth.user_id:
        redirect(session._reset_password_redirect)

    form = auth.reset_password(session._reset_password_redirect)
    
    titleIcon = "user"
    pageTitle = cast(str, T("Create account"))
    customText = cast(str, T("Thanks for accepting to review this preprint. An email has been sent to your email address. You now need to define a password to login to “My Review” page and upload your review OR you can close this window and define your login (and upload) and post your review latter."))
    form.element(_type="submit")["_class"] = "btn btn-success"
    form.element(_type="submit")["_value"] = T("Create account")
    form.element(_id="no_table_new_password__label").components[0] = T('Define password')

    response.view = "default/myLayoutBot.html"

    return dict(titleIcon=titleIcon,
                pageTitle=pageTitle,
                customText=customText,
                form=form)

######################################################################################################################################################################
def recover_mail():
    if "key" in request.vars:
        recover_key = request.vars["key"]
    else:
        session.flash = T("Unavailable")
        redirect(URL("default", "index"))

    user = db(db.auth_user.recover_email_key == recover_key).select().last()
    if user is None:
        session.flash = T("Unavailable")
        redirect(URL("default", "index"))
    else:
        user.email = user.recover_email
        user.recover_email = None
        user.recover_email_key = None
        user.registration_key = None

        user.update_record()
        session.flash = T("E-mail succefully recovered")
        redirect(URL("default", "index"))


# @cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    if request.args[0].endswith(".pdf"):
        redirect(URL("default", "stream_pdf", args=request.args[0]))
    else:
        file_to_download = response.download(request, db)
        return file_to_download


def stream_pdf():
    filename = request.args[0]

    match_regex = re.match("(.*?)\.(.*?)\.", filename)

    if not match_regex:
        raise HTTP(404, "404: " + T("Unavailable"))

    table_name = match_regex.group(1)
    table_file_field = match_regex.group(2)

    row = db(db[table_name][table_file_field] == filename).select().first()

    if not row:
        raise HTTP(404, "404: " + T("Unavailable"))

    table_file_data_field = table_file_field + "_data"

    file_data_bytes = row[table_file_data_field]


    try:
        # create temp file
        filename = filename[:150] + ".pdf"
        attachments_dir = os.path.join(request.folder, "tmp", "attachments")
        os.makedirs(attachments_dir, exist_ok=True)
        file_to_download = os.path.join(attachments_dir, filename)
        temp_file = open(file_to_download, 'wb')
        temp_file.write(file_data_bytes)
        temp_file.close()

        # erase metadata
        os.system('exiftool -overwrite_original -all:all="" ' + file_to_download)

    except Exception as e:
        print("ERROR : metadata NOT erased")
        print(e)

    return response.stream(file_to_download)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()
