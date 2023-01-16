# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations
import time
import re
import copy
import os
import io

from gluon.contrib.markdown import WIKI

from app_modules.helper import *
from gluon.utils import web2py_uuid
from gluon.storage import Storage # for db.get_last_recomms()

from app_components import app_forms
from app_modules import common_tools
from controller_modules import adjust_grid

trgmLimit = myconf.get("config.trgm_limit") or 0.4

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

    def articleRow(row):
        if "maxArticles" in request.vars:
            maxArticles = int(request.vars["maxArticles"])
        else:
            maxArticles = 10
        myVars = copy.deepcopy(request.vars)
        myVars["maxArticles"] = myVars["maxArticles"] or 10
        myVarsNext = copy.deepcopy(myVars)
        myVarsNext["maxArticles"] = int(myVarsNext["maxArticles"]) + 10

        queryRecommendedArticles = None

        if queryRecommendedArticles is None:
            queryRecommendedArticles = db(
                (db.t_articles.status == "Recommended") & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommendation_state == "Recommended")
            ).iterselect(
                db.t_articles.art_stage_1_id,
                db.t_articles.id,
                db.t_articles.title,
                db.t_articles.authors,
                db.t_articles.article_source,
                db.t_articles.doi,
                db.t_articles.picture_rights_ok,
                db.t_articles.uploaded_picture,
                db.t_articles.abstract,
                db.t_articles.upload_timestamp,
                db.t_articles.user_id,
                db.t_articles.status,
                db.t_articles.last_status_change,
                db.t_articles.thematics,
                db.t_articles.keywords,
                db.t_articles.already_published,
                db.t_articles.auto_nb_recommendations,
                db.t_articles.scheduled_submission_date,
                limitby=(0, maxArticles),
                orderby=~db.t_articles.last_status_change,
            )

        recomms = db.get_last_recomms()
        recommendedArticlesList = []
        for prow in queryRecommendedArticles:
            r = article_components.getRecommArticleRowCard(auth, db, response, prow, recomms.get(prow.id), withDate=True)
            if r:
                recommendedArticlesList.append(r)

        if len(recommendedArticlesList) == 0:
            return DIV(I(T("Coming soon...")))

        resu = DIV(_class="pci2-articles-list")
        single_row = DIV(_class="pci2-flex-row pci2-article-row pci2-flex-column-mobile")

        # generate left column (date + image)
        left_column = DIV(_class="pci2-flex-column pci2-article-left-div")
        date = I(SPAN(row.submission))
        image_container = DIV(_class="pci2-flex-center pci2-flex-grow pci2-article-image-div", _onclick="window.open('/pci/articles/rec?id=" + str(row.id) + "')")
        if row.uploaded_picture == '': image = IMG(_src="/pci/static/images/small-background.png")
        else: image = IMG(_src=row.uploaded_picture)
        image_container.append(image)
        left_column.append(date)
        left_column.append(image_container)
        single_row.append(left_column)

        # generate right column (rest of article content)
        right_column = DIV(_class="pci2-flex-column")
        top_container = DIV(_class="pci2-flex-column")
        headline = H3(row.title)
        authors = SPAN(row.authors, _class="pci2-article-infos")
        doi = SPAN(_class="pci2-article-infos")
        doi_link = A(_class="doi_url", _target="_blank", _href=row.article_source)
        doi_b = B(row.article_source)
        doi.append(doi_link)
        doi.append(doi_b)
        top_container.append(headline)
        top_container.append(authors)
        top_container.append(doi)
        right_column.append(top_container)
        bottom_container = DIV(_class="pci2-flex-column pci2-article-recommendation-div")
        small_head = H4('small header')
        recommend_container = I("Recommended by ")
        recommend_sub = SPAN()
        recommend_link = A(B(row.recommender), _class="cyp-user-profile-link")
        recommend_sub.append(recommend_link)
        recommend_sub.append(" based on reviews by")
        '''for reviewer in row.reviewers:
            rev_span = SPAN(reviewer)
            recommend_sub.append(rev_span)'''
        recommend_container.append(recommend_sub)
        abstract_fader = SPAN(DIV(_class="fade-transparent-text"))

        more_link = DIV(A("MORE", _class="btn btn-success pci-public pci-smallBtn", _href="/pci/articles/rec?id=" + str(row.id)))
        bottom_container.append(small_head)
        bottom_container.append(recommend_container)
        bottom_container.append(abstract_fader)
        bottom_container.append(more_link)

        right_column.append(bottom_container)

        single_row.append(right_column)
        resu.append(single_row)

        return resu

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    
    response.view = "default/index.html"

    # NOTE: do not delete: kept for later use
    # thematics = db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword)
    # options = [OPTION('--- All thematic fields ---', _value='')]
    # for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
    # options.append(OPTION(thema.keyword, _value=thema.keyword))

    tweeterAcc = myconf.get("social.tweeter")

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

    # We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
    temp_db = DAL("sqlite:memory")
    qy_articles = temp_db.define_table(
        "qy_articles",
        Field("id", type="integer"),
        Field("num", type="integer"),
        Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
        Field("title", type="string", label=T("Title")),
        Field("authors", type="string", label=T("Authors")),
        Field("article_source", type="string", label=T("Source")),
        Field("abstract", type="string", label=T("Abstract")),
        Field("thematics", type="string", label=T("Thematic Fields"), requires=IS_IN_DB(db, db.t_thematics.keyword, zero=None)),
        Field("keywords", type="string", label=T("Keywords")),
        Field("submission", type="datetime", label=T("Submission Date")),
        Field("reviewers", type="string", label=T("Reviewers")),
        Field("recommender", type="string", label=T("Recommender")),
        Field("any", type="string", label=T("All fields")),
    )

    qyTF = []
    for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
        qyTF.append(thema.keyword)

    #filtered = db.executesql("SELECT * FROM search_articles_new(%s, %s, %s, %s, %s);", placeholders=[qyTF, qyKwArr, excludeList, trgmLimit, True], as_dict=True)

    filtered = db.executesql("SELECT * FROM search_articles_new(%s, %s, %s, %s, %s);", placeholders=[[".*"], None, "Recommended", trgmLimit, True], as_dict=True)

    temp_db.qy_articles.num.readable = False
    temp_db.qy_articles.id.readable = False
    temp_db.qy_articles.uploaded_picture.readable = False

    temp_db.qy_articles.title.represent = lambda text, row: articleRow(row)

    full_text_search_fields = [
            'title',
            'authors',
            'article_source',
            'abstract',
            'thematics',
            'keywords',
            'reviewers',
            'recommender',
    ]

    for fr in filtered:
       qy_articles.insert(**fr, any=" ".join([str(fr[k]) if k in full_text_search_fields else "" for k in fr]))

    original_grid = SQLFORM.smartgrid(
        qy_articles,
        editable=False,
        deletable=False,
        create=False,
        details=False,
        searchable=dict(auth_user=True, auth_membership=False),
        selectable=None,
        maxtextlength=250,
        paginate=1000,
        csv=False,
        exportclasses=None,
        fields=[
            temp_db.qy_articles.id,
            temp_db.qy_articles.num,
            temp_db.qy_articles.uploaded_picture,
            temp_db.qy_articles.title,
            temp_db.qy_articles.authors,
            temp_db.qy_articles.article_source,
            temp_db.qy_articles.abstract,
            temp_db.qy_articles.thematics,
            temp_db.qy_articles.keywords,
            temp_db.qy_articles.reviewers,
            temp_db.qy_articles.recommender,
            temp_db.qy_articles.submission,
        ],
        links=[],
        orderby=temp_db.qy_articles.num,
        _class="web2py_grid action-button-absolute",
    )

    # options to be removed from the search dropdown:
    remove_options = ['qy_articles._id']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'main_articles', remove_options)

    if request.user_agent().is_mobile:
        return dict(
            pageTitle=getTitle(request, auth, db, "#HomeTitle"),
            customText=getText(request, auth, db, "#HomeInfo"),
            pageHelp=getHelp(request, auth, db, "#Home"),
            searchForm=False,#searchForm,
            lastRecommTitle=False,#lastRecommTitle,
            lastRecomms=False,#lastRecomms,
            grid=grid,
            shareable=True,
            currentUrl=URL(c="default", f="index", host=host, scheme=scheme, port=port),
            pciRRactivated=pciRRactivated,
            tweeterAcc=tweeterAcc,
            panel=None,
            absoluteButtonScript=common_tools.absoluteButtonScript,
        )
    else:
        return dict(
            pageTitle=getTitle(request, auth, db, "#HomeTitle"),
            customText=getText(request, auth, db, "#HomeInfo"),
            pageHelp=getHelp(request, auth, db, "#Home"),
            searchForm=False,#searchForm,
            lastRecommTitle=False,#lastRecommTitle,
            lastRecomms=False,#lastRecomms,
            grid=grid,
            panel=None,
            shareable=True,
            currentUrl=URL(c="default", f="index", host=host, scheme=scheme, port=port),
            pciRRactivated=pciRRactivated,
            tweeterAcc=tweeterAcc,
            absoluteButtonScript=common_tools.absoluteButtonScript,
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


def check_already_registered(form):
    existing_user = db(db.auth_user.email.lower() == str(form.vars.email).lower()).select().last()
    if existing_user:
        form.errors.email = SPAN(
                T("This email is already registered"),
                T("; you may wish to "),
                A(T("reset your password"), _href=URL("user/request_reset_password", vars={"email":form.vars.email})),
        )


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
    table_name = match_regex.group(1)
    table_file_field = match_regex.group(2)

    row = db(db[table_name][table_file_field] == filename).select().first()

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
