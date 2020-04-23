# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import re
import copy

from gluon.contrib.markdown import WIKI

from app_modules.helper import *
from gluon.utils import web2py_uuid

# -------------------------------------------------------------------------
# This is a sample controller
# - index is the default action of any application
# - user is required for authentication and authorization
# - download is for downloading files uploaded in the db (does streaming)
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# app configuration made easy. Look inside private/appconfig.ini
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)


def loading():
    return DIV(IMG(_alt="Loading...", _src=URL(c="static", f="images/loading.gif")), _id="loading", _style="text-align:center;")


# Home page (public)
def index():
    response.view = "default/index.html"

    # NOTE: do not delete: kept for later use
    # thematics = db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword)
    # options = [OPTION('--- All thematic fields ---', _value='')]
    # for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
    # options.append(OPTION(thema.keyword, _value=thema.keyword))

    myPanel = []
    tweeterAcc = myconf.get("social.tweeter")
    tweetHash = myconf.get("social.tweethash")
    tweeterId = myconf.get("social.tweeter_id")
    if tweeterAcc:
        myPanel.append(
            XML(
                """<a class="twitter-timeline" href="https://twitter.com/%(tweeterAcc)s" style="margin:10px">Tweets by %(tweeterAcc)s</a> 
			<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
			"""
                % locals()
            )
        )
    # if tweetHash and tweeterId:
    # myPanel.append(DIV(XML('<a class="twitter-timeline"  href="https://twitter.com/hashtag/%(tweetHash)s" data-widget-id="%(tweeterId)s">Tweets about #%(tweeterAcc)s</a><script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?\'http\':\'https\'; if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+"://platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);} }(document,"script","twitter-wjs");</script>' % locals() ), _class='tweeterPanel'))

    nbMax = db(
        (db.t_articles.status == "Recommended") & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommendation_state == "Recommended")
    ).count()
    myVars = copy.deepcopy(request.vars)
    myVars["maxArticles"] = myVars["maxArticles"] or 10
    myVarsNext = copy.deepcopy(myVars)
    myVarsNext["maxArticles"] = myVarsNext["maxArticles"] + 10

    form = FORM(
        H3(
            T("Latest recommendations"),
            A(
                SPAN(IMG(_alt="rss", _src=URL(c="static", f="images/rss.png"), _style="margin-right:8px;"),),
                _href=URL("about", "rss_info"),
                _class="btn btn-default pci-rss-btn",
                _style="float:right;",
            ),
        ),
        DIV(loading(), _id="lastRecommendations",),
    )
    myScript = SCRIPT(
        """window.onload=function() {
	ajax('%s', ['qyThemaSelect', 'maxArticles'], 'lastRecommendations');
	if ($.cookie('PCiHideHelp') == 'On') $('DIV.pci-helptext').hide(); else $('DIV.pci-helptext').show();
}"""
        % (URL("articles", "last_recomms", vars=myVars, user_signature=True)),
        _type="text/javascript",
    )

    # if auth.user_id:
    # theUser = db.auth_user[auth.user_id]
    # if theUser.ethical_code_approved is False:
    # redirect(URL('about','ethics'))

    if request.user_agent().is_mobile:
        return dict(
            pageTitle=getTitle(request, auth, db, "#HomeTitle"),
            customText=getText(request, auth, db, "#HomeInfo"),
            pageHelp=getHelp(request, auth, db, "#Home"),
            form=form,
            myBottomPanel=DIV(DIV(myPanel, _style="overflow-y:auto; max-height: 95vh;"), _class="tweeterBottomPanel pci2-hide-under-tablet", _style="overflow: hidden; padding: 0"),
            shareable=True,
            script=myScript,
        )
    else:
        return dict(
            pageTitle=getTitle(request, auth, db, "#HomeTitle"),
            customText=getText(request, auth, db, "#HomeInfo"),
            pageHelp=getHelp(request, auth, db, "#Home"),
            form=form,
            panel=DIV(DIV(myPanel, _style="overflow-y:auto; max-height: 95vh;"), _class="tweeterPanel pci2-hide-under-tablet", _style="overflow: hidden; padding: 0"),
            shareable=True,
            script=myScript,
        )


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
        suite = request.vars["_next"]
        if len(suite) < 4:
            suite = None
    else:
        suite = None
    if isinstance(suite, list):
        suite = suite[1]

    if "key" in request.vars:
        vkey = request.vars["key"]
    else:
        vkey = None
    if isinstance(vkey, list):
        vkey = vkey[1]
    if vkey == "":
        vkey = None

    if "_formkey" in request.vars:
        fkey = request.vars["_formkey"]
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
    myScript = ""

    form = auth()
    db.auth_user.registration_key.writable = False
    db.auth_user.registration_key.readable = False
    if request.args and len(request.args) > 0:

        if request.args[0] == "login":
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
            titleIcon = "edit"
            pageTitle = getTitle(request, auth, db, "#CreateAccountTitle")
            pageHelp = getHelp(request, auth, db, "#CreateAccount")
            customText = getText(request, auth, db, "#ProfileText")
            myBottomText = getText(request, auth, db, "#ProfileBottomText")
            db.auth_user.ethical_code_approved.requires = IS_IN_SET(["on"])
            form.element(_type="submit")["_class"] = "btn btn-success"
            if suite:
                auth.settings.register_next = suite

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
            if (fkey is not None) and (user is not None):
                reset_password_key = str(int(time.time())) + "-" + web2py_uuid()
                user.update_record(reset_password_key=reset_password_key)
                do_send_email_to_reset_password(session, auth, db, user.id)
                if suite:
                    redirect(URL("default", "index", vars=dict(_next=suite)))  # squeeze normal functions
                else:
                    redirect(URL("default", "index"))  # squeeze normal functions
            if suite:
                auth.settings.request_reset_password_next = suite

        elif request.args[0] == "reset_password":
            titleIcon = "lock"
            pageTitle = getTitle(request, auth, db, "#ResetPasswordTitle")
            pageHelp = getHelp(request, auth, db, "#ResetPassword")
            customText = getText(request, auth, db, "#ResetPasswordText")
            user = db(db.auth_user.reset_password_key == vkey).select().last()
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


# (gab) is this used ?
@cache.action()
def download():
    """
	allows downloading of uploaded files
	http://..../[app]/default/download/[filename]
	"""
    return response.download(request, db)


# (gab) is this used ?
def call():
    """
	exposes services. for example:
	http://..../[app]/default/call/jsonrpc
	decorate with @services.jsonrpc the functions to expose
	supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
	"""
    return service()

