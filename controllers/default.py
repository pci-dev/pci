# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations
import os
import re
import time
from typing import Any, Optional, cast

from app_components import article_components
from models.article import is_scheduled_submission
from app_modules.common_tools import delete_user_from_PCI, get_article_id, get_next, get_reset_password_key, get_review_id
from app_modules.helper import *
from app_modules.common_small_html import complete_orcid_dialog, complete_profile_dialog, invitation_to_review_form, unsubscribe_checkbox
from controller_modules import adjust_grid
from app_modules.emailing import send_conditional_acceptation_review_mail, send_unsubscription_alert_for_manager
from app_modules import emailing
from app_modules.orcid import OrcidTools
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
from models.membership import Membership
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
    if request.env.request_method == 'HEAD':
        response.headers = { "link": (
            '<' + URL("coar_notify", "inbox", scheme=True) + '>' +
            '; rel="http://www.w3.org/ns/ldp#inbox"'
        )}
        return ""

    response.view = "default/index.html"

    recomms = db.get_last_recomms()

    def articleRow(row):
        return article_components.getRecommArticleRowCard(auth, db, response,
                        row,
                        recomms.get(row.id),
                        withDate=True,
                        orcid_exponant=True)

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
    manager_authors
    """
    .split()): t_articles[field].readable = False

    try:
      original_grid = SQLFORM.grid(
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
    except:
        raise HTTP(418, "I'm a teapot")


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
            if grid and grid.element(".web2py_table") else None

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

    if request.args and len(request.args) > 0 and request.args[0] == 'logout':
        if request.vars and len(request.vars) > 0 and request.vars['unsubscribe']:
            auth.settings.logout_next = URL('default','unsubscribe_page')

    form = auth()
    db.auth_user.registration_key.writable = False
    db.auth_user.registration_key.readable = False
    if request.args and len(request.args) > 0:

        if request.args[0] == "login":
            if auth.user_id:
                redirect(URL('default','index'))

            intercept_reset_password_login()

            titleIcon = "log-in"
            pageTitle = getTitle(request, auth, db, "#LogInTitle")
            pageHelp = getHelp(request, auth, db, "#LogIn")
            customText = getText(request, auth, db, "#LogInText")

            form.add_button(T("Lost password?"), get_lost_password_url(),
                    _class="pci2-lost-password-link")
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
            OrcidTools.add_orcid_auth_user_form(session, request, form,
                    URL(c="default", f="user", args="register", scheme=True, vars={"_next": suite or ""}))
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
            if not (auth.has_membership(role="recommender") and pciRRactivated):
                form.element("#auth_user_email_options__row")["_style"] = "display: none;"
            form.element(_name="orcid")["_maxlength"] = 19

            OrcidTools.add_orcid_auth_user_form(session, request, form,
                    URL(c="default", f="user", args="profile", scheme=True, vars={"_next": suite or ""}))
            form.components[1].insert(len(form.components[1]) - 1, unsubscribe_checkbox())
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
            if suite:
                auth.settings.request_reset_password_next = suite

        elif request.args[0] == "reset_password":
            titleIcon = "lock"
            pageTitle = getTitle(request, auth, db, "#ResetPasswordTitle")
            pageHelp = getHelp(request, auth, db, "#ResetPassword")
            customText = getText(request, auth, db, "#ResetPasswordText")
            vkey = get_reset_password_key(request)
            user = User.get_by_reset_password_key(vkey)
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

    return dict(titleIcon=titleIcon,
                pageTitle=pageTitle,
                customText=customText,
                myBottomText=myBottomText,
                pageHelp=pageHelp,
                form=form,
                myFinalScript=OrcidTools.get_orcid_formatter_script())


def intercept_reset_password_login(_next=request.vars._next):
    from urllib.parse import parse_qs
    key = parse_qs(str(_next)).get("key")
    key = key[0] if key else None

    if not key: return
    if not db.auth_user(reset_password_key=key): return

    redirect(URL("reset_password", vars=dict(_key=key, _next=_next)))


def get_user_from_article(_next):
    if "edit_my_article?articleId=" in _next:
        m = re.match(".*articleId=(\d+).*", _next)
        article_id = m.group(1) if m else None
        article = db.t_articles[article_id]
    else:
        article = None

    return db.auth_user[article.user_id] if article else None


def get_lost_password_url(user=None):
    _next = request.vars._next or ""
    user = user or get_user_from_article(_next)

    if user:
        return URL("default", "email_reset_password",
                vars=dict(user_id=user.id, _next=_next))
    else:
        return URL("default", "user", args=["request_reset_password"])


def email_reset_password():
    user = db.auth_user[request.vars.user_id]
    if not user: return "no user specified"

    reset_password_key = str(int(time.time())) + "-" + web2py_uuid()
    user.update_record(reset_password_key=reset_password_key)

    link = URL("default", "reset_password", scheme=True, vars=dict(
        _key=reset_password_key,
        _next=request.vars._next,
    ))
    emailing.send_reset_password(user, link)

    session.flash = "reset password email sent to: " + user.email
    redirect(request.home)


def reset_password():
    _key = request.vars._key
    _next = request.vars._next or request.home

    if not db.auth_user(reset_password_key=_key):
        session.flash = "reset_password: invalid _key"
        redirect(request.home)

    if type(_next) is list: _next = _next.pop()

    session._reset_password_key = _key
    form = auth.reset_password(_next)

    form.element(_type="submit")["_class"] = "btn btn-success"

    response.view = "default/myLayoutBot.html"
    return dict(
            titleIcon="lock",
            pageTitle=getTitle(request, auth, db, "#ResetPasswordTitle"),
            customText=getText(request, auth, db, "#ResetPasswordText"),
            pageHelp=getHelp(request, auth, db, "#ResetPassword"),
            form=form)


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
    if is_profile_completed and current_user.orcid:
        return

    session.show_account_menu_dialog = True
    
    dialog = None
    if not is_profile_completed:
        next = get_next(request)
        dialog = complete_profile_dialog(next)
    elif not current_user.orcid and not current_user.no_orcid:
        dialog = complete_orcid_dialog(db)
    return dialog


def orcid_choice():
    payload: Any = request.vars
    if not payload.value or payload.value not in ('yes', 'no'):
        return

    current_user = User.get_by_id(auth.user_id)
    if not current_user:
        response.flash = T('No user found')
        return
    
    if payload.value == 'yes' and payload.orcid and len(payload.orcid) == 19:
        User.set_orcid(current_user, payload.orcid)
        response.flash = T('ORCID saved!')

    if payload.value == 'no':
        User.set_no_orcid(current_user)
        response.flash = T('Preference saved!')
    

def redirect_ORCID_authentication():
    OrcidTools.redirect_ORCID_authentication(session, request)


@auth.requires_signature()
def unsubscribe():
    user_id = cast(Optional[int], auth.user_id)
    if not user_id:
        return redirect(URL("default", "index"))
    
    current_user = User.get_by_id(user_id)
    if not current_user:
        return redirect(URL("default", "index"))
    
    send_unsubscription_alert_for_manager(auth, db)

    try:
        delete_user_from_PCI(current_user)
    except Exception as e:
        session.flash = f"User not deleted: {e}"
        return redirect(URL("default", "index"))
    
    response.cookies['unsubscribe'] = True
    redirect(URL("default", "user", args='logout', vars=dict(unsubscribe=True), user_signature=True))


def unsubscribe_page():
    if auth.user_id:
        return redirect(URL("default", "index"))
    
    if 'unsubscribe' in request.cookies and request.cookies['unsubscribe'].value:
        response.cookies['unsubscribe'] = False
        response.cookies['unsubscribe']['expires'] = 0
    else:
        return redirect(URL("default", "index"))
    
    response.view = "default/myLayoutBot.html"

    pageTitle = f"Your account has been successfully deleted."
    customText = "You can re-register at any time using the same email address or a different one.."

    return dict(pageTitle=pageTitle,
                customText=customText)


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
        try:
            new_email = cast(str, form.vars.new_email)
            recover_email_key = User.change_email(auth.user_id, new_email)
            emailing.send_change_mail(session, auth, db, auth.user_id, new_email, recover_email_key)
            session.flash = f"An email has been sent to {new_email} to confirm it"
        except Exception as e:
            session.flash = f"Error: {e}"
        finally:
            return redirect(URL('default', 'index'))

    response.flash = None
    return dict(titleIcon="envelope", pageTitle=getTitle(request, auth, db, "#ChangeMailTitle"), customText=getText(request, auth, db, "#ChangeMail"), form=form)


def confirm_new_address():
    recover_email_key = cast(Optional[str], request.vars['recover_email_key'])
    if not recover_email_key:
        session.flash = 'Invalid address'
        return redirect(URL('default', 'index'))
    
    if auth.user_id:
        current_user = User.get_by_id(auth.user_id)
        if current_user:
            if current_user.recover_email_key is None or current_user.recover_email_key != recover_email_key:
                session.flash = 'Bad user'
                return redirect(URL('default', 'index'))
    
    try:
        User.confirm_change_email(recover_email_key)
    except Exception as e:
        session.flash = f"Unable to change email: {e}"
        return redirect(URL('default', 'index'))
    
    if auth.user_id:
        session.flash = 'Email changed successfully'
        return redirect(URL('default', 'index'))
    
    response.view = 'default/myLayoutBot.html'
    pageTitle = "Your email address has been successfully changed."
    customText = "You can now log in with your new email address.."
    return dict(pageTitle=pageTitle, customText=customText)


######################################################################################################################################################################

def invitation_to_review():
    more_delay = cast(bool, request.vars['more_delay'] == 'true')
    
    if not 'reviewId' in request.vars:
        session.flash = current.T('No review id found')
        redirect(URL('default','index'))
        return
    
    reviewId = int(request.vars['reviewId'])
    review = Review.get_by_id(reviewId)
    if not review or not review.recommendation_id:
        session.flash = current.T('No review found')
        redirect(URL('default','index'))
        return
    
    recommendation = Recommendation.get_by_id(db, review.recommendation_id)
    if not recommendation or not recommendation.article_id:
        session.flash = current.T('No recommendation found')
        redirect(URL('default','index'))
        return
    
    article = Article.get_by_id(recommendation.article_id)
    if not article:
        session.flash = current.T('No article found')
        redirect(URL('default','index'))
        return
    
    recommender = User.get_by_id(recommendation.recommender_id)
    if not recommender:
        session.flash = current.T('No recommender found')
        redirect(URL('default','index'))
        return
    
    if pciRRactivated and article.report_stage == "STAGE 1" and (article.is_scheduled or is_scheduled_submission(article)):
        more_delay = False

    reset_password_key = get_reset_password_key(request)
    user: Optional[User] = None

    if reset_password_key and not auth.user_id:
        user = User.get_by_reset_password_key(reset_password_key)
    elif auth.user_id:
        user = User.get_by_id(auth.user_id)
    
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
    response.view = "default/invitation_to_review.html"

    form = invitation_to_review_form(request, auth, db, article, user, review, more_delay)

    if form.process().accepted:
        if request.vars.no_conflict_of_interest == 'yes' and request.vars.anonymous_agreement == 'yes' and request.vars.ethics_approved == 'true' and (request.vars.cgu_checkbox == 'yes' or user.ethical_code_approved):
            url_vars = dict(articleId=article.id, key=user.reset_password_key, reviewId=review.id)
            
            if more_delay and request.vars.review_duration and review.review_duration != request.vars.review_duration:
                Review.set_review_duration(review, article, request.vars.review_duration)
                url_vars['more_delay'] = 'true'
            
            action_form_url = cast(str, URL("default", "invitation_to_review_acceptation", vars=url_vars))
            redirect(action_form_url)

    if review.acceptation_timestamp:
        url_vars = dict(articleId=article.id, key=user.reset_password_key, reviewId=review.id)
        
        if review.review_state == ReviewState.AWAITING_REVIEW.value:
            action_form_url = cast(str, URL("default", "invitation_to_review_acceptation", vars=url_vars))
            redirect(action_form_url)
        elif review.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value or more_delay:
            url_vars['more_delay'] = 'true'
            action_form_url = cast(str, URL("default", "invitation_to_review_acceptation", vars=url_vars))
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
                form=form,
                more_delay=more_delay)


def invitation_to_review_preprint(): # legacy
    return invitation_to_review()


def invitation_to_review_acceptation():
    article_id = get_article_id(request)
    review_id = get_review_id(request)
    more_delay = cast(bool, request.vars['more_delay'] == 'true')

    reset_password_key = get_reset_password_key(request)
    user: Optional[User] = None
    if reset_password_key and not auth.user_id:
        user = User.get_by_reset_password_key(reset_password_key)
    elif auth.user_id:
        user = User.get_by_id(auth.user_id)

    if user and not user.ethical_code_approved:
        user.ethical_code_approved = True
        user.update_record()

    if article_id and review_id:
        url_vars = dict(reviewId=review_id, _next=URL(c="user", f="recommendations", vars=dict(articleId=article_id)))
        session._reset_password_redirect = URL(c="user_actions", f="accept_review_confirmed", vars=url_vars)

        review = Review.get_by_id(review_id)
        article = Article.get_by_id(article_id)
        if review and article:
            if review.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value:
                url_vars = dict(reviewId=review_id, _next=URL(c="user_actions", f="suggestion_sent_page"))
                session._reset_password_redirect = URL(c="user_actions", f="accept_review_confirmed", vars=url_vars)

            if not review.acceptation_timestamp:
                if more_delay:
                    Review.accept_review(review, article, True, ReviewState.NEED_EXTRA_REVIEW_TIME)
                    send_conditional_acceptation_review_mail(session, auth, db, review)
                else:
                    Review.accept_review(review, article, True)

            if user and not review.suggested_reviewers_send and not auth.user_id:
                url_vars = dict(_next=URL("default", "invitation_to_review_acceptation", vars=request.vars), reviewId=review_id)
                redirect(URL(c="user_actions", f="send_suggestion_page", vars=url_vars))

    if user and auth.user_id:
        redirect(session._reset_password_redirect)

    form = auth.reset_password(session._reset_password_redirect)
    
    titleIcon = "user"
    pageTitle = cast(str, T("Create account"))
    customText = CENTER(
        P(T("Please create an account right now by defining a password below (your login is your email address)"), _style="font-weight: bold; width: 800px"),
    )
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
    table_file_data_field = table_file_field + "_data"
    try:
        file_data_bytes = row[table_file_data_field]
    except:
        raise HTTP(404, "404: " + T("Unavailable"))

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
