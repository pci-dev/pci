# -*- coding: utf-8 -*-

import os
from datetime import date
from typing import Any, Callable, List, Optional, Union, cast

from gluon import Field
from gluon.contrib.markdown import WIKI # type: ignore

from app_modules.helper import *

# App modules
from controller_modules import user_module
from controller_modules import adjust_grid

from app_components import app_forms

from app_components import article_components
from app_components import ongoing_recommendation

from app_modules import emailing
from app_modules import common_tools
from app_modules import common_small_html
from app_modules.orcid import OrcidTools
from app_modules.article_translator import ArticleTranslator
from gluon.http import HTTP, redirect # type: ignore
from app_components.custom_validator import VALID_LIST_NAMES_MAIL

from gluon.sqlhtml import SQLFORM
from gluon.storage import Storage
from models.group import Role
from models.review import Review, ReviewState
from models.article import Article, clean_vars_doi, clean_vars_doi_list, ArticleStatus
from models.report_survey import ReportSurvey
from models.recommendation import Recommendation
from models.user import User
from pydal.validators import IS_EMPTY_OR, IS_IN_DB, IS_IN_SET, IS_LENGTH, IS_NOT_EMPTY, IS_URL
from app_components.article_components import fix_web2py_list_str_bug_article_form

from app_modules.common_tools import URL

request = current.request
session = current.session
db = current.db
auth = current.auth
response = current.response
T = current.T

# frequently used constants
myconf = AppConfig(reload=True)
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
status = db.config[1]

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)
contact = myconf.get("contacts.contact")

######################################################################################################################################################################
def index():
    return my_reviews()

# Recommendations of my articles
@auth.requires_login()
def recommendations():

    printable = "printable" in request.vars and request.vars["printable"] == "True"

    articleId = request.vars["articleId"]
    manager_authors = request.vars["manager_authors"]
    if not articleId:
        return my_articles()

    art = Article.get_by_id(articleId)
    if art is None:
        session.flash = auth.not_authorized()
        return redirect(request.env.http_referer)
    
    if manager_authors != None:
        art.update_record(manager_authors=manager_authors)

    
    # NOTE: security hole possible by changing manually articleId value
    revCpt = 0
    if art.user_id == auth.user_id:
        revCpt += 1  # NOTE: checkings owner rights.
    # NOTE: checking reviewer rights
    revCpt += db((db.t_recommendations.article_id == articleId) & (db.t_recommendations.id == db.t_reviews.recommendation_id) & (db.t_reviews.reviewer_id == auth.user_id)).count()

    # PCI RR
    if pciRRactivated and art.art_stage_1_id is None:
        revCpt += db(
            (db.t_articles.art_stage_1_id == articleId)
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.id == db.t_reviews.recommendation_id)
            & (db.t_reviews.reviewer_id == auth.user_id)
            & (db.t_reviews.review_state != "Willing to review")
        ).count()
        revCpt += db(
            (db.t_articles.art_stage_1_id == articleId) & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommender_id == auth.user_id)
        ).count()

    if pciRRactivated and art.status == "Recommended":
        revCpt += 1

    if revCpt == 0:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:

        # PCI Registered Reports
        isStage2 = art.art_stage_1_id is not None
        stage1Link = None
        stage2List = None

        # Create related stage 1 link
        if pciRRactivated and isStage2:
            urlArticle = URL(c="user", f="recommendations", vars=dict(articleId=art.art_stage_1_id))
            stage1Link = common_small_html.mkRepresentArticleLightLinkedWithStatus(art.art_stage_1_id, urlArticle)

        # Create related stage 2 list
        elif pciRRactivated and not isStage2:
            stage2Articles = db(db.t_articles.art_stage_1_id == articleId).select()
            stage2List = []
            for art_st_2 in stage2Articles:
                urlArticle = URL(c="user", f="recommendations", vars=dict(articleId=art_st_2.id))
                stage2List.append(common_small_html.mkRepresentArticleLightLinkedWithStatus(art_st_2.id, urlArticle))

        # Scheduled Submission form (doi + manuscript version)
        isScheduledSubmission = False
        scheduledSubmissionRemaningDays = None
        scheduledSubmissionForm = None
        if scheduledSubmissionActivated and art.status != "Cancelled" and art.user_id == auth.user_id:
            db.t_articles.doi.requires = IS_URL(mode='generic',allowed_schemes=['http', 'https'],
                    prepend_scheme='https',
                    error_message=T("Cannot be empty"))
            scheduledSubmissionForm = SQLFORM(db.t_articles, articleId, fields=["doi", "ms_version"], keepvalues=True, showid=False)

            # Show form and get remaining days
            if  art.scheduled_submission_date is not None:
                isScheduledSubmission = True
                scheduledSubmissionRemaningDays = (art.scheduled_submission_date - date.today()).days

            showFullSubmissionUploadScreen = (
                art.scheduled_submission_date and
                scheduledSubmissionRemaningDays <= db.full_upload_opening_offset.days
            )
            if not showFullSubmissionUploadScreen:
                scheduledSubmissionForm = None
            else:
            # Remove scheduled submission date when doi is updated
              if scheduledSubmissionForm.process().accepted:
                art.scheduled_submission_date = None
                art.is_scheduled = True
                art.doi = scheduledSubmissionForm.vars.doi
                art.ms_version = scheduledSubmissionForm.vars.ms_version
                art.status = "Scheduled submission pending"
                art.update_record()

                emailing.delete_reminder_for_submitter("#SubmitterScheduledSubmissionOpen", art.id)

                session.flash = T("Article submitted successfully")
                redirect(URL(c="user", f="recommendations", vars=dict(articleId=articleId)))

        # Build recommendation
        response.title = art.title or myconf.take("app.longname")


        if pciRRactivated and art.user_id != auth.user_id:
            recommHeaderHtml = article_components.get_article_infos_card(art, printable, False)
        else:
            recommHeaderHtml = article_components.get_article_infos_card(art, printable, True)

        recommStatusHeader = ongoing_recommendation.getRecommStatusHeader(art, True, printable, quiet=False)
        recommTopButtons = ongoing_recommendation.getRecommendationTopButtons(art, printable, quiet=False)

        recommendationProgression = ongoing_recommendation.getRecommendationProcessForSubmitter(art, printable)
        myContents = ongoing_recommendation.get_recommendation_process(art, printable)

        reviews = Review.get_all_active_reviews(db.get_last_recomm(art.id), auth.user_id)
        for review in reviews:
            if review.review_state == ReviewState.AWAITING_REVIEW.value:
                response.flash = common_small_html.write_edit_upload_review_button(review.id)

        if printable:
            response.view = "default/wrapper_printable.html"
        else:
            response.view = "default/wrapper_normal.html"

        viewToRender = "default/recommended_articles.html"

        return dict(
            printable=printable,
            isSubmitter=(art.user_id == auth.user_id),
            isManager=current.auth.has_membership(role=Role.MANAGER.value),
            isRecommender=user_is_in_recommender_team(art.id),
            viewToRender=viewToRender,
            recommHeaderHtml=recommHeaderHtml,
            recommStatusHeader=recommStatusHeader,
            recommTopButtons=recommTopButtons or "",
            pageHelp=getHelp("#UserRecommendations"),
            myContents=myContents,
            recommendationProgression=recommendationProgression["content"],
            roundNumber=recommendationProgression["roundNumber"],
            isRecommAvalaibleToSubmitter=recommendationProgression["isRecommAvalaibleToSubmitter"],
            myBackButton=common_small_html.mkBackButton(),
            pciRRactivated=pciRRactivated,
            isStage2=isStage2,
            stage1Link=stage1Link,
            stage2List=stage2List,
            scheduledSubmissionActivated=scheduledSubmissionActivated,
            isScheduledSubmission=isScheduledSubmission,
            scheduledSubmissionForm=scheduledSubmissionForm,
            scheduledSubmissionRemaningDays=scheduledSubmissionRemaningDays,
            confirmationScript = common_small_html.confirmationDialog('Are you sure?'),
            myFinalScript=common_tools.get_script("user_recommendations.js")
        )


######################################################################################################################################################################
@auth.requires_login() # type: ignore
def search_recommenders():
    request, T, auth, session, db = current.request, current.T, current.auth, current.session, current.db
    
    what_next: Optional[str] = request.vars["whatNext"]
    article_id: Optional[int] = request.vars.articleId
    exclude_list = common_tools.get_exclude_list()
    random = True

    if 'random' in request.vars:
        random = str(request.vars['radom']).lower() == 'false'

    if exclude_list is None:
        return "invalid parameter: exclude"

    if article_id is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    article = Article.get_by_id(article_id)
    if article is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if article.user_id != auth.user_id:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        users = db.auth_user
        full_text_search_fields = [
            'id',
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

        def limit_to_width_list(value: Optional[str], row: ...):
            if value == None: return SPAN(_class="m300w")
            return SPAN(current.T("%s" %', '.join(value)), _class="m300w"),

        def limit_to_width_str(value: Optional[str], row: ...):
            if value == None: return SPAN(_class="m300w")
            return SPAN(current.T("%s" %value), _class="m300w"),

        users.thematics.label = "Thematics fields"
        users.thematics.type = "string"
        users.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, zero="")
        users.thematics.represent = limit_to_width_list

        users.keywords.represent = limit_to_width_str

        users.id.label = "Name"
        users.id.readable = True
        users.id.represent = lambda uid, row: DIV( # type: ignore
                common_small_html.mk_reviewer_info(db.auth_user[uid]),
                _class="pci-w300Cell")

        for f in users.fields:
            if not f in full_text_search_fields:
                users[f].readable = False

        def mk_button(func: Callable[[Any, int, List[int], Any], Union[DIV, str]], modus: str):
            funct: Callable[[Any], Union[DIV, str]] = lambda row: "" if row.auth_user.id in exclude_list else (
                    "" if str(row.auth_user.id) in (article.manager_authors or "").split(',')
                    else DIV( func(row, article.id, exclude_list, request.vars),
                              INPUT(_type="checkbox", _id='checkbox_%s_%s'%(modus, str(row.auth_user.id)), _class="multiple-choice-checks %s"%modus, _onclick='update_parameter_for_selection(this)'),
                              _class="min15w"))
            return funct

        links = [
            dict(header="", body=mk_button(user_module.mk_suggest_user_article_to_button, 'suggest')),
        ]

        btn_label = "CLICK HERE TO SUGGEST ALL SELECTED RECOMMENDERS"
        btn_style = "btn-success"
        if pciRRactivated:
            btn_label = "CLICK HERE TO SUGGEST/EXCLUDE ALL SELECTED RECOMMENDERS"

        select_all_btn = DIV(A(
                            SPAN(current.T(btn_label), _class="btn %s"%btn_style),
                            _href=URL(c="user_actions", f="suggest_all_selected", vars=dict(articleId=article_id, whatNext=what_next, recommenderIds='', exclusionIds='', exclude=exclude_list)),
                            _class="button select-all-btn",
                            _id="select-all-btn",
                            )
                            )

        if pciRRactivated:
            links.append(dict(header="", body=mk_button(user_module.mk_exclude_recommender_button, 'exclude')))

        query = (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "recommender")
        first_name_represent_fct: Callable[[str, Any], SPAN] = lambda text, row: OrcidTools.build_name_with_orcid(text, '000', before=True)

        db.auth_group.role.searchable = False
        db.auth_user.first_name.represent = first_name_represent_fct

        original_grid = cast(SQLFORM, SQLFORM.grid( # type: ignore
                        query,
                        editable=False,
                        deletable=False,
                        create=False,
                        details=False,
                        searchable=dict(auth_user=True, auth_membership=False), # type: ignore
                        selectable=None,
                        maxtextlength=250,
                        paginate=1000,
                        csv=csv,
                        exportclasses=expClass,
                        fields=[
                            users.id,
                            users.thematics,
                            users.keywords,
                            users.orcid
                        ],
                        links=links,
                        orderby='<random>' if random else (users.last_name, users.first_name),
                        _class="web2py_grid action-button-absolute",
                    ))

        # options to be removed from the search dropdown:
        remove_options = ['auth_membership.id', 'auth_membership.user_id', 'auth_membership.group_id',
                          'auth_group.id', 'auth_group.role', 'auth_group.description']
        
        # the grid is adjusted after creation to adhere to our requirements
        grid = adjust_grid.adjust_grid_basic(original_grid, 'recommenders', remove_options)

        if len(exclude_list) > 1:
            btn_txt = current.T("Done")
        else:
            btn_txt = current.T("I don't wish to suggest recommenders now")

        alphabetical_order_vars = request.vars.copy()
        alphabetical_order_vars['random'] = 'false'
        my_accept_btn = DIV(
            A(
                SPAN(btn_txt, _class="buttontext btn btn-info"),
                _href=URL(c="user", f="add_suggested_recommender", vars=dict(articleId=article_id, exclude=exclude_list)),
                _class="button",
            ),
            A("Recommenders' names order is random, click here to get an alphabetical order",
              _href=URL("user", "search_recommenders", vars=alphabetical_order_vars, args=request.args, user_signature=True),
              _class="button") if random else '',
            _style="text-align:center; margin-top:16px;",
            _class="done-btn",
        )

        my_upper_btn = ""
        if len(grid) >= 10:
            my_upper_btn = my_accept_btn
        select_all_script = common_tools.get_script("select_all.js")
        current.response.view = "default/gab_list_layout.html"

        return dict(
            pageHelp=getHelp("#UserSearchRecommenders"),
            customText=getText("#UserSearchRecommendersText"),
            titleIcon="search",
            pageTitle=getTitle("#UserSearchRecommendersTitle"),
            myUpperBtn=my_upper_btn,
            myAcceptBtn=my_accept_btn,
            myFinalScript=common_tools.get_script("popover.js"),
            grid=grid,
            selectAllBtn = select_all_btn,
            selectAllScript = select_all_script,
            absoluteButtonScript=common_tools.absoluteButtonScript,
        )


######################################################################################################################################################################
def new_submission():
    form = None
    state = None
    loginLink = None
    registerLink = None
    submitPreprintLink = None


    pageTitle=getTitle("#UserBeforeSubmissionTitle")
    customText=getText("#SubmissionOnHoldInfo")

    db.config.allow_submissions.writable = True
    db.config.allow_submissions.readable = True

    fields = ["allow_submissions"]
    
    if auth.has_membership(role="manager"):
        form = SQLFORM(db.config, 1, fields=fields)
        form.element(_type="checkbox")["_id"] = "toggle"
        if request.vars["allow_submissions"]:
            state = request.vars["allow_submissions"]
        else:
            state = "off"
        state = True if state == "on" else False
        if request.vars["update"]:
            status.update_record(allow_submissions=state)
    

    if status['allow_submissions']:
        pageTitle=getTitle("#UserBeforeSubmissionTitle")
        customText=getText("#NewRecommendationRequestInfo")
        
        if auth.user:
            submitPreprintLink = URL("user", "check_title" if pciRRactivated else "fill_new_article", user_signature=True)
        else:
            loginLink = URL(c="default", f="user", args=["login"], vars=dict(_next=URL(c="user", f="new_submission")))
            registerLink = URL(c="default", f="user", args=["register"], vars=dict(_next=URL(c="user", f="new_submission")))

    response.view = "controller/user/new_submission.html"
    return dict(
        titleIcon="edit",
        pageTitle=pageTitle,
        customText=customText,
        submitPreprintLink=submitPreprintLink,
        loginLink=loginLink,
        registerLink=registerLink,
        form=form
    )

######################################################################################################################################################################
@auth.requires_login()
def check_title():
    form = SQLFORM.factory(
        Field("report_stage", type="string", label=T("Is this a Stage 1 or Stage 2 submission?"), requires=IS_IN_SET(("STAGE 1", "STAGE 2"))),
        Field("title", label=T("Title"), type="string", length=250),
    )
    form.element(_type="submit")["_value"] = T("Continue")
    def onvalidation(form):
        if form.vars.report_stage == "STAGE 1":
            if form.vars.title is None:
                form.errors.title = T("Title cannot be empty, please provide a title")
            else:
                title_already_submitted = db((db.t_articles.user_id == auth.user_id) & (db.t_articles.title.lower() == form.vars.title.lower()) & (db.t_articles.report_stage == "STAGE 1") & (db.t_articles.scheduled_submission_date != None)).select().last()
                if title_already_submitted:
                    form.errors.title =  SPAN(T("Title error message"), A(contact, _href="mailto:%s" % contact, _target="_blank"))

    if form.process(onvalidation=onvalidation).accepted:
        myVars = dict(title=form.vars.title or "", report_stage=form.vars.report_stage)
        redirect(URL(c="user", f="fill_new_article", vars=myVars, user_signature=True))

    myScript = common_tools.get_script("check_title.js")
    response.view = "default/myLayout.html"
    return dict(
        pageHelp=getHelp("#UserSubmitNewArticle"),
        customText=getText("#UserEditArticleText"),
        titleIcon="edit",
        pageTitle=getTitle("#UserSubmitNewArticleTitle"),
        myFinalScript=myScript,
        form=form
    )


    
######################################################################################################################################################################
@auth.requires_login()
def fill_new_article():
    current_user = User.get_by_id(current.auth.user_id)

    title = request.vars.title
    report_stage = request.vars.report_stage
    db.t_articles.article_source.writable = False
    db.t_articles.ms_version.writable = True
    db.t_articles.upload_timestamp.readable = False
    db.t_articles.status.readable = False
    db.t_articles.status.writable = False
    db.t_articles.user_id.default = auth.user_id
    db.t_articles.user_id.writable = False
    db.t_articles.user_id.readable = False
    db.t_articles.last_status_change.readable = False
    db.t_articles.auto_nb_recommendations.readable = False
    db.t_articles.already_published.default = False
    db.t_articles.already_published.readable = False
    db.t_articles.already_published.writable = False
    db.t_articles.request_submission_change.readable = False
    db.t_articles.request_submission_change.writable = False
    db.t_articles.manager_authors.readable = False
    db.t_articles.cover_letter.readable = True
    db.t_articles.cover_letter.writable = True
    db.t_articles.suggest_reviewers.readable = True
    db.t_articles.suggest_reviewers.writable = True
    db.t_articles.competitors.readable = True
    db.t_articles.competitors.writable = True

    db.t_articles.results_based_on_data.requires(db.data_choices)
    db.t_articles.scripts_used_for_result.requires(db.script_choices)
    db.t_articles.codes_used_in_study.requires(db.code_choices)

    if parallelSubmissionAllowed:
        db.t_articles.parallel_submission.label = T("This preprint is (or will be) also submitted to a journal")

    if pciRRactivated:
        if title is None and report_stage is None:
            redirect(URL(c="user", f="check_title",user_signature=True))
        db.t_articles.report_stage.readable = True
        db.t_articles.report_stage.writable = True
        db.t_articles.sub_thematics.readable = True
        db.t_articles.sub_thematics.writable = True

        db.t_articles.record_url_version.readable = True
        db.t_articles.record_url_version.writable = True
        db.t_articles.record_id_version.readable = True
        db.t_articles.record_id_version.writable = True

        db.t_articles.title.default = title  if type(title) is str else title[0]
        db.t_articles.report_stage.default = report_stage if type(report_stage) is str else report_stage[0]

        db.t_articles.report_stage.writable = False
        db.t_articles.ms_version.requires = [IS_NOT_EMPTY(), IS_LENGTH(1024, 0)]
        db.t_articles.sub_thematics.requires = [IS_NOT_EMPTY(), IS_LENGTH(512, 0)]
        db.t_articles.cover_letter.requires = IS_NOT_EMPTY()
        db.t_articles.keywords.requires = [IS_NOT_EMPTY(), IS_LENGTH(4096, 0)]
    else:
        db.t_articles.report_stage.readable = False
        db.t_articles.report_stage.writable = False

    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.art_stage_1_id.writable = False
    db.t_articles.scheduled_submission_date.readable = False
    db.t_articles.scheduled_submission_date.writable = False

    fields = []
    if pciRRactivated:
        fields += ["report_stage"]

    fields += [
        "doi",
        "preprint_server",
        "ms_version",
    ]

    if pciRRactivated:
        fields += ["record_url_version", "record_id_version"]

    fields += [
        "anonymous_submission",
        "title",
        "authors",
        "article_year",
        "picture_rights_ok",
        "uploaded_picture",
        "abstract",
    ]

    if not pciRRactivated:
        fields += [
        "results_based_on_data",
        "data_doi",
        "scripts_used_for_result", 
        "scripts_doi", 
        "codes_used_in_study", 
        "codes_doi", 
        "funding",
    ]

    fields += ["thematics"]

    if pciRRactivated:
        fields += ["sub_thematics"]

    fields += ["keywords"]

    if not pciRRactivated:
        fields += [
            "methods_require_specific_expertise",
            "suggest_reviewers",
            "competitors" 
    ]
    
    fields += ["recomm_notice" , "cover_letter"]

    if parallelSubmissionAllowed:
        fields += ["parallel_submission"]

    managers = common_tools.get_managers()
    manager_ids = [m[0] for m in managers]
    manager_label = [Field('manager_label', 'string', label='Tick the box in front of the following names (who are members of the managing board) if they are co-authors of the article')]
    manager_fields = [Field('chk_%s'%m[0], 'boolean', default=False, label=m[1], widget=lambda field, value: SQLFORM.widgets.boolean.widget(field, value, _class='manager_checks', _onclick="check_checkboxes()")) for i,m in enumerate(managers)]

    form = SQLFORM(db.t_articles, fields=fields, keepvalues=True,
            extra_fields=[
                Field("recomm_notice", widget=widget(_type="hidden"),
                    label=T("On the next page you will have the possibility to suggest recommenders for your article"),
                ),
            ] + manager_label + manager_fields,
    )

    app_forms.article_add_mandatory_checkboxes(form, pciRRactivated)

    data_doi_form = form.elements(_id="t_articles_results_based_on_data__row")
    if data_doi_form:
        data_code_script_label = LABEL("Data, code and scripts", SPAN(" * ", _style="color:red;"), _class="control-label col-sm-3")
        data_doi_form[0].insert(0, data_code_script_label)

    def fixup_radio_group(name: str):
        """
        Just for test.
        """
        elements = form.elements(_name=name)
        elements[0].update(_id=name + "_group")

        elements[1].update(_id="t_articles_no_" + name)
        elements[1].parent.components[1].update(_for="t_articles_no_" + name)

        elements[2].update(_id="t_articles_" + name)
        elements[2].parent.components[1].update(_for="t_articles_" + name)

    if not pciRRactivated:
        fixup_radio_group("results_based_on_data")
        fixup_radio_group("scripts_used_for_result")
        fixup_radio_group("codes_used_in_study")

    if pciRRactivated:
        form.element(_type="submit")["_value"] = T("Continue your submission")
    else:
        form.element(_type="submit")["_value"] = "Save & Complete your submission"

    form.element(_type="submit")["_class"] = "btn btn-success"
    form.element(_type="submit")["_name"] = "submit"
    form.element(_type="submit")["_id"] = "submit-article-btn"

    if not pciRRactivated:
        has_saved_new_article = current_user and current_user.new_article_cache

        form.element(_type="submit").parent.components.insert(0, BUTTON('Save', _id="save-article-form-button", _name="save", _class="btn btn-primary"))
        form.element(_type="submit").parent.components.insert(0, BUTTON('Reset', _id="clean-save-article-form-button", _name="clean_save", _class="btn btn-danger", _style="" if has_saved_new_article else "display: none"))


    def onvalidation(form):
        _save_article_form(form)
        if not pciRRactivated:
            app_forms.checklist_validation(form)
        if pciRRactivated:
            form.vars.status = "Pending-survey"

        check_suggested_and_opposed_reviewers(form)
        check_duplicate_submission(form)

        form.vars.doi = clean_vars_doi(form.vars.doi)
        form.vars.data_doi = clean_vars_doi_list(form.vars.data_doi)
        form.vars.codes_doi = clean_vars_doi_list(form.vars.codes_doi)
        form.vars.scripts_doi = clean_vars_doi_list(form.vars.scripts_doi)

    final_scripts = _load_article_form_saved(form)
    
    if form.process(onvalidation=onvalidation).accepted:
        articleId = form.vars.id
        if pciRRactivated:
            pass
        else:
            session.flash = T("Article submitted", lazy=False)

        manager_ids = common_tools.extract_manager_ids(form, manager_ids)
        myVars = dict(articleId=articleId, manager_authors=manager_ids, clean_form_saved=request.env.path_info)
        # for thema in form.vars.thematics:
        # myVars['qy_'+thema] = 'on'
        # myVars['qyKeywords'] = form.vars.keywords
        _clean_article_form_saved(False)
        
        if pciRRactivated:
            redirect(URL(c="user", f="fill_report_survey", vars=myVars, user_signature=True))
        else:
            redirect(URL(c="user", f="add_suggested_recommender", vars=myVars, user_signature=True))
    elif form.errors:
        fix_web2py_list_str_bug_article_form(form)
        _save_article_form(form)
        _clean_article_form_saved(True)

        if form.errors.duplicate:
            redirect(URL(c="user", f="duplicate_submission", vars=form.errors.duplicate))

        response.flash = T("Form has errors", lazy=False)


    customText = getText("#UserSubmitNewArticleText", maxWidth="800")
    if pciRRactivated:
        customText = ""

    if status['allow_submissions'] is False:
        form = getText("#SubmissionOnHoldInfo")

    myScript = common_tools.get_script("fill_new_article.js")
    article_form_clean_script = common_tools.get_script('clean_saved_article_form.js')
    article_form_common_script = common_tools.get_script("article_form_common.js")
    response.view = "default/gab_form_layout.html"

    response.cookies['user_id'] = current.auth.user_id
    response.cookies['user_id']['expires'] = 24 * 3600
    response.cookies['user_id']['path'] = '/'
    response.cookies['user_id']['samesite'] = 'Strict'

    final_scripts.extend([myScript or "", article_form_clean_script, article_form_common_script])

    return dict(
        pageHelp=getHelp("#UserSubmitNewArticle"),
        titleIcon="edit",
        pageTitle=getTitle("#UserSubmitNewArticleTitle"),
        customText=customText,
        form=form,
        myFinalScript=final_scripts
    )


def check_suggested_and_opposed_reviewers(form: ...):
    suggest_reviewers, suggested_reviewers_error = VALID_LIST_NAMES_MAIL(True, optional_email=True)(form.vars.suggest_reviewers)
    if suggested_reviewers_error:
        form.errors.suggest_reviewers = suggested_reviewers_error

    opposed_reviewers, opposed_reviewers_reviewers_error = VALID_LIST_NAMES_MAIL(True, optional_email=True)(form.vars.competitors)
    if opposed_reviewers_reviewers_error:
        form.errors.competitors = opposed_reviewers_reviewers_error

    form.vars.suggest_reviewers = suggest_reviewers
    form.vars.competitors = opposed_reviewers

    return suggest_reviewers, opposed_reviewers


def check_duplicate_submission(form):
    dup_info = Article.check_duplicate_submission(
            form.vars.doi,
            form.vars.title,
    )
    if dup_info:
        form.errors.duplicate = dict(
            title=form.vars.title,
            url=form.vars.doi,
            dup_info=dup_info,
        )


def duplicate_submission():
    text = XML(f"""
        An article with the same {request.vars.dup_info}
        is already being evaluated in this PCI.
        <div style="margin: 1em 0; line-height: 1.5em">
        <u>Title:</u> {request.vars.title}<br>
        <u>URL:</u> {request.vars.url}<br>
        </div>
        Therefore, your submission has not been registered.
        <br>
        Please contact the Managing Board at {myconf.get("contacts.contact")}
        for further assistance.
    """)
    response.view = "default/myLayoutBot.html"
    return dict(
        #pageHelp=getHelp("#UserSubmitNewArticle"),
        #pageTitle=getTitle("#UserSubmitNewArticleTitle"),
        titleIcon="warning",
        pageTitle="Duplicate submission",
        customText=text,
    )


def _save_article_form(form: SQLFORM):
    if request.post_vars.save:
        form.vars.pop('uploaded_picture')
        current_user = User.get_by_id(current.auth.user_id)
        if current_user:
            form_values = dict(form=form.vars, list_str=current.request.vars.list_str, saved_picture=current.request.vars.saved_picture)
            User.set_in_new_article_cache(current_user, form_values)
            session.flash = 'Your incomplete submission has been saved. You can resume the submission now or later by choosing the menu "For contributors > Your incomplete submission"'
        redirect(URL(args=request.args, vars=request.get_vars))


def _load_article_form_saved(form: SQLFORM):
    saved_var: List[str] = []
    if not request.post_vars.save and not request.post_vars.submit:
        current_user = User.get_by_id(current.auth.user_id)
        if current_user and current_user.new_article_cache:
            form_values = Storage(current_user.new_article_cache['form'])
            form.vars = form_values
            if 'list_str' in current_user.new_article_cache and current_user.new_article_cache['list_str']:
                saved_var.append(SCRIPT(f"var savedListStr = {current_user.new_article_cache['list_str']};"))
            if 'saved_picture' in current_user.new_article_cache and current_user.new_article_cache['saved_picture']:
                saved_var.append(SCRIPT(f"var savedPicture = {current_user.new_article_cache['saved_picture']};"))
                
            if not response.flash and not session.flash:
                response.flash = 'Saved form data have been loaded.'
    return saved_var

    
def _clean_article_form_saved(form_with_error: bool):
    if request.post_vars.submit and not form_with_error:
        current_user = User.get_by_id(current.auth.user_id)
        if current_user:
            User.clear_new_article_cache(current_user)

    if request.post_vars.clean_save:
        current_user = User.get_by_id(current.auth.user_id)
        if current_user:
            User.clear_new_article_cache(current_user)
            
        redirect(URL(args=request.args, vars=request.get_vars))

######################################################################################################################################################################
@auth.requires_login()
def edit_my_article():

    response.view = "default/myLayout.html"
    if not ("articleId" in request.vars):
        session.flash = T("Unavailable")
        return redirect(URL("my_articles", user_signature=True))
    articleId = request.vars["articleId"]
    article = Article.get_by_id(articleId)
    if article == None:
        session.flash = T("Unavailable")
        return redirect(URL("my_articles", user_signature=True))
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    elif article.status not in ("Pending", "Awaiting revision", "Pending-survey", "Pre-submission", "Scheduled submission revision"):
        session.flash = T("Forbidden access")
        return redirect(URL("my_articles", user_signature=True))

    user = db.auth_user[auth.user_id]
    if not user.ethical_code_approved:
        user.ethical_code_approved = True
        user.update_record()

    from models.user import User
    if not User.is_profile_completed(user):
        redirect(URL("default", "user/profile",
            vars={"_next": URL(request.controller, request.function, vars=request.vars)}))


    # deletable = (art.status == 'Pending')
    deletable = False
    db.t_articles.status.readable = False
    db.t_articles.status.writable = False
    db.t_articles.cover_letter.readable = True
    db.t_articles.cover_letter.writable = True
    db.t_articles.request_submission_change.readable = False
    db.t_articles.request_submission_change.writable = False
    db.t_articles.manager_authors.readable = False

    db.t_articles.results_based_on_data.requires(db.data_choices)
    db.t_articles.scripts_used_for_result.requires(db.script_choices)
    db.t_articles.codes_used_in_study.requires(db.code_choices)

    db.t_articles.data_doi.writable = True
    db.t_articles.scripts_doi.writable = True
    db.t_articles.codes_doi.writable = True

    pciRRjsScript = ""
    myScript = ""
    if pciRRactivated:
        havingStage2Articles = db(db.t_articles.art_stage_1_id == articleId).count() > 0
        db.t_articles.cover_letter.readable = True
        db.t_articles.cover_letter.writable = True

        if not havingStage2Articles:
            db.t_articles.art_stage_1_id.requires = IS_EMPTY_OR(
                IS_IN_DB(db((db.t_articles.user_id == auth.user_id) & (db.t_articles.art_stage_1_id == None) & (db.t_articles.id != article.id)), "t_articles.id", "%(title)s")
            )
            pciRRjsScript = ""
        else:
            db.t_articles.art_stage_1_id.requires = IS_EMPTY_OR([])
            pciRRjsScript = common_tools.get_script("disable_stage1_article.js")

    if pciRRactivated:
        db.t_articles.report_stage.readable = True
        db.t_articles.report_stage.writable = True
        db.t_articles.sub_thematics.readable = True
        db.t_articles.sub_thematics.writable = True

        db.t_articles.cover_letter.label = "Cover letter"
        
        db.t_articles.record_url_version.readable = True
        db.t_articles.record_url_version.writable = True
        db.t_articles.record_id_version.readable = True
        db.t_articles.record_id_version.writable = True

        db.t_articles.report_stage.requires = IS_IN_SET(("STAGE 1", "STAGE 2"))
        db.t_articles.ms_version.requires = [IS_NOT_EMPTY(), IS_LENGTH(1024, 0)]
        db.t_articles.sub_thematics.requires = [IS_NOT_EMPTY(), IS_LENGTH(512, 0)]
        db.t_articles.cover_letter.requires = IS_NOT_EMPTY()
        db.t_articles.keywords.requires = [IS_NOT_EMPTY(), IS_LENGTH(4096, 0)]
    else:
        db.t_articles.report_stage.readable = False
        db.t_articles.report_stage.writable = False

    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.art_stage_1_id.writable = False
    db.t_articles.scheduled_submission_date.readable = False
    db.t_articles.scheduled_submission_date.writable = False

    if parallelSubmissionAllowed and article.status == "Pending":
        db.t_articles.parallel_submission.label = T("This preprint is (or will be) also submitted to a journal")
        fields = []
        if pciRRactivated:
            fields = ["report_stage"]
            if article.report_stage == "STAGE 2":
                fields += ["art_stage_1_id"]
                db.t_articles.art_stage_1_id.readable = True
                db.t_articles.art_stage_1_id.writable = True

        fields += [
            "doi",
            "preprint_server",
            "ms_version",
        ]

        if pciRRactivated:
            fields += ["record_url_version", "record_id_version"]

        fields += [
            "title",
            "anonymous_submission",
            "parallel_submission",
            "authors",
            "article_year",
            "picture_rights_ok",
            "uploaded_picture",
            "abstract",
        ]
        if not pciRRactivated:
            fields += [
            "results_based_on_data",
            "data_doi",
            "scripts_used_for_result", 
            "scripts_doi", 
            "codes_used_in_study", 
            "codes_doi", 
            "funding",
        ]

        fields += ["thematics"]

        if pciRRactivated:
            fields += ["sub_thematics"]

        fields += ["keywords"]

        if not pciRRactivated:
            fields += [
                "methods_require_specific_expertise",
                "suggest_reviewers",
                "competitors" 
            ]

        fields += ["cover_letter"]
        myScript = common_tools.get_script("edit_my_article.js")

    else:
        fields = []
        if pciRRactivated:
            fields = ["report_stage"]
            if article.report_stage == "STAGE 2":
                fields += ["art_stage_1_id"]
                db.t_articles.art_stage_1_id.readable = True
                db.t_articles.art_stage_1_id.writable = True

        fields += [
            "doi",
            "preprint_server",
            "ms_version",
        ]

        if pciRRactivated:
            fields += ["record_url_version", "record_id_version"]

        fields += [
            "title",
            "abstract",
            "anonymous_submission",
            "authors",
            "article_year",
            "picture_rights_ok",
            "uploaded_picture",
        ]

        if not pciRRactivated:
            fields += [
                "results_based_on_data",
                "data_doi",
                "scripts_used_for_result", 
                "scripts_doi", 
                "codes_used_in_study", 
                "codes_doi", 
                "funding",
            ]

        fields += ["thematics"]

        if pciRRactivated:
            fields += ["sub_thematics"]

        fields += ["keywords"]
        fields += ["methods_require_specific_expertise"]

        if not pciRRactivated:
            fields += [
                "suggest_reviewers",
                "competitors" 
            ]

        fields += ["cover_letter"]
        if not pciRRactivated:
            myScript = common_tools.get_script("new_field_responsiveness.js")

    buttons: List[Union[A, INPUT]] = [
        A("Cancel", _class="btn btn-default", _href=URL(c="user", f="recommendations", vars=dict(articleId=article.id), user_signature=True)),
        INPUT(_id="submit-article-btn", _type="Submit", _name="save", _class="btn btn-success", _value="Save"),
    ]

    def manager_check(field: ..., value: ...) -> ...:
        return SQLFORM.widgets.boolean.widget(field, value, _class='manager_checks', _onclick="check_checkboxes()") # type: ignore

    try: article_manager_coauthors = article.manager_authors
    except: article_manager_coauthors = False
    managers = common_tools.get_managers()
    manager_checks: Dict[str, bool] = {}
    for m in managers:
        manager_checks[m[0]] = False
    if article_manager_coauthors:
        for amc in article_manager_coauthors.split(','):
            manager_checks[amc] = True
    manager_ids = [m[0] for m in managers]
    manager_label = [Field('manager_label', 'string', label='Tick the box in front of the following names (who are members of the managing board) if they are co-authors of the article')]
    manager_fields = [Field('chk_%s'%m[0], 'boolean', default=manager_checks[m[0]], label=m[1], widget=manager_check) for _,m in enumerate(managers)]

    form: ... = SQLFORM(db.t_articles, articleId, upload=URL("static", "uploads"), deletable=deletable, showid=False, fields = fields, extra_fields = manager_label + manager_fields, buttons=buttons)
    ArticleTranslator.add_edit_translation_buttons(article, form)
    _hide_suggested_reviewer_for_user(article, form)

    article_version: Union[int, str, None] = None

    try:
        if article.ms_version is not None:
            article_version = int(article.ms_version)
        else:
            article.ms_version = None
    except:
        article_version = article.ms_version

    prev_picture = article.uploaded_picture

    if type(db.t_articles.uploaded_picture.requires) == list: # non-RR see db.py
        not_empty = current.db.t_articles.uploaded_picture.requires.pop()
    else:
        not_empty = None

    # form.element(_type="submit")["_value"] = T("Save")
    def onvalidation(form: ...):        
        if not pciRRactivated:
            if isinstance(article_version, int):
                if article_version > int(form.vars.ms_version):
                    form.errors.ms_version = "New version number must be greater than or same as previous version number"
            if not prev_picture and form.vars.uploaded_picture == b"" and not_empty:
                form.errors.uploaded_picture = not_empty.error_message
            app_forms.checklist_validation(form)
            check_suggested_and_opposed_reviewers(form)

    if form.process(onvalidation=onvalidation).accepted: # type: ignore
        article = Article.get_by_id(articleId)
        if article == None:
            session.flash = T("Unavailable")
            return redirect(URL("my_articles", user_signature=True))
        if prev_picture and form.vars.uploaded_picture:
            try: os.unlink(os.path.join(request.folder, "uploads", prev_picture))
            except: pass

        suggested_reviewers_value, opposed_reviewers_reviewers_value = check_suggested_and_opposed_reviewers(form)
        article.suggest_reviewers = [suggested_reviewers_value] if isinstance(suggested_reviewers_value, str) else suggested_reviewers_value
        article.competitors = [opposed_reviewers_reviewers_value] if isinstance(opposed_reviewers_reviewers_value, str) else opposed_reviewers_reviewers_value

        response.flash = T("Article saved", lazy=False)
        if article.status == "Pre-submission":
            article.status = "Pending"
        if form.vars.report_stage == "STAGE 1":
            article.art_stage_1_id = None
        article.request_submission_change = False
        article.update_record() # type: ignore

        manager_ids = common_tools.extract_manager_ids(form, manager_ids)
        page_vars = dict(articleId=article.id, manager_authors=manager_ids)

        target_page = "recommendations"
        anchor = "author-reply"

        if article.status in ["Pending", "Pre-submission"] :
            anchor = None

            if article.coar_notification_id or article.pre_submission_token:
                # alternative: if request.vars.key: # coar first time only
                target_page = (
                        "fill_report_survey" if pciRRactivated else
                        "add_suggested_recommender"
                )

                Article.remove_pre_submission_token(article)

        _get_hidden_suggested_reviewer_for_user(article)
        
        redirect(URL(c="user", f=target_page, vars=page_vars, anchor=anchor))

    elif form.errors:
        response.flash = T("Form has errors", lazy=False)

    if pciRRactivated and status['allow_submissions'] is False:
        form = getText("#SubmissionOnHoldInfo")

    _get_hidden_suggested_reviewer_for_user(article)

    manager_script = common_tools.get_script("manager_selection.js")
    article_form_common_script = common_tools.get_script("article_form_common.js")
    return dict(
        pageHelp=getHelp("#UserEditArticle"),
        customText=getText("#UserEditArticleText"),
        titleIcon="edit",
        pageTitle=getTitle("#UserEditArticleTitle"),
        form=form,
        myFinalScript=[myScript, article_form_common_script],
        managerScript = manager_script,
        pciRRjsScript=pciRRjsScript,
    )


def _hide_suggested_reviewer_for_user(article: Article, form: ...):
    if article.user_id != current.auth.user_id:
        return
    
    li_els = form.components[0].components[20].components[1].components[0].components
    session.hidden_suggested_reviewer = []

    li = None
    for li in li_els.copy():
        if type(li.components[0]) is str: continue
        value: str = str(li.components[0].attributes['value'])
        if "suggested:" in value:
            if value not in current.session.hidden_suggested_reviewer:
                current.session.hidden_suggested_reviewer.append(value)
            li_els.remove(li)

    if len(li_els) == 0 and li:
        li.components[0].attributes['_value'] = ""
        li_els.append(li)


def _get_hidden_suggested_reviewer_for_user(article: Article):
    if article.user_id != current.auth.user_id:
        return
    
    hidden_susggested_reviewer: List[str] = session.hidden_suggested_reviewer
    if article.suggest_reviewers is None:
        article.suggest_reviewers = []

    reviewer_added = False

    for suggested_reviewer in hidden_susggested_reviewer:
        if suggested_reviewer not in article.suggest_reviewers:
            article.suggest_reviewers.append(suggested_reviewer)
            reviewer_added = True

    if reviewer_added:
        article.update_record() # type: ignore


######################################################################################################################################################################
@auth.requires_login()
def fill_report_survey():
    response.view = "default/myLayout.html"

    if not ("articleId" in request.vars):
        session.flash = T("Unavailable")
        redirect(URL("my_articles", user_signature=True))
    manager_authors = request.vars["manager_authors"]
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]

    if manager_authors != None:
        art.update_record(manager_authors=manager_authors)

    if art == None:
        session.flash = T("Unavailable")
        redirect(URL("my_articles", user_signature=True))
    if art.status not in ("Pending-survey", "Pending", "Awaiting revision"):
        session.flash = T("Forbidden access")
        redirect(URL("my_articles", user_signature=True))
    if art.user_id != auth.user_id:
        session.flash = T("Forbidden access")
        redirect(URL("my_articles", user_signature=True))

    form = app_forms.report_survey(art, controller="user_fill")

    article_form_clean_script = common_tools.get_script('clean_saved_article_form.js')
    myScript = common_tools.get_script("fill_report_survey.js")
    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp("#FillReportSurvey"),
        titleIcon="edit",
        pageTitle=getTitle("#FillReportSurveyTitle"),
        customText=getText("#FillReportSurveyText", maxWidth="800"),
        form=form,
        myFinalScript=[myScript, article_form_clean_script],
    )


######################################################################################################################################################################
@auth.requires_login()
def edit_report_survey():
    response.view = "default/myLayout.html"

    if not ("articleId" in request.vars):
        session.flash = T("Unavailable")
        redirect(URL("my_articles", user_signature=True))
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art == None:
        session.flash = T("Unavailable")
        redirect(URL("my_articles", user_signature=True))
    if art.status not in ("Pending", "Awaiting revision", "Pending-survey", "Pre-submission") and not scheduledSubmissionActivated:
        session.flash = T("Forbidden access")
        redirect(URL("my_articles", user_signature=True))
    if art.status in ("Under consideration", "Awaiting consideration") and scheduledSubmissionActivated and art.scheduled_submission_date is None:
        session.flash = T("Forbidden access")
        redirect(URL("my_articles", user_signature=True))
    if art.user_id != auth.user_id:
        session.flash = T("Forbidden access")
        redirect(URL("my_articles", user_signature=True))

    survey = db(db.t_report_survey.article_id == articleId).select().last()
    if survey is None:
        session.flash = T("No survey yet, please fill this form.")
        survey = db.t_report_survey.insert(article_id=articleId, temp_art_stage_1_id=art.art_stage_1_id)

    # condition copy/pasted from showFullSubmissionUploadScreen
    fullSubmissionOpened = (
            art.scheduled_submission_date and
            (art.scheduled_submission_date - date.today()).days
                <= db.full_upload_opening_offset.days
    )

    form = app_forms.report_survey(art, survey, "user_edit",
                                    do_validate=not fullSubmissionOpened)

    if fullSubmissionOpened:
        form.element("#t_report_survey_q10")["_disabled"] = 1

    if pciRRactivated and status['allow_submissions'] is False:
        form = getText("#SubmissionOnHoldInfo")

    myScript = common_tools.get_script("fill_report_survey.js")
    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp("#EditReportSurvey"),
        titleIcon="edit",
        pageTitle=getTitle("#EditReportSurveyTitle"),
        customText=getText("#EditReportSurveyText", maxWidth="800"),
        form=form,
        myFinalScript=myScript,
    )


######################################################################################################################################################################
# Display suggested recommenders for a submitted article
# Logged users only (submission)
@auth.requires_login()
def suggested_recommenders():
    response.view = "default/myLayout.html"
    articleId = request.vars["articleId"]

    if articleId is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    art = db.t_articles[articleId]
    if art is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if art.user_id != auth.user_id or art.status not in ("Pending"):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        query = (db.t_suggested_recommenders.article_id == articleId) & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)
        db.t_suggested_recommenders._id.readable = False
        db.t_suggested_recommenders.suggested_recommender_id.represent = lambda userId, row: common_small_html.mkUser(userId)
        grid = SQLFORM.grid(
            query,
            details=False,
            editable=False,
            deletable=True,
            searchable=False,
            create=False,
            maxtextlength=250,
            paginate=100,
            csv=csv,
            exportclasses=expClass,
            fields=[db.t_suggested_recommenders.id, db.t_suggested_recommenders.suggested_recommender_id, db.auth_user.thematics],
            field_id=db.t_suggested_recommenders.id,
        )
        return dict(
            # myBackButton=common_small_html.mkBackButton(),
            pageHelp=getHelp("#UserSuggestedRecommenders"),
            customText=getText("#UserSuggestedRecommendersText"),
            titleIcon="education",
            pageTitle=getTitle("#UserSuggestedRecommendersTitle"),
            grid=grid,
        )


######################################################################################################################################################################
# Show my submissions
@auth.requires_login()
def my_articles():

    response.view = "default/myLayout.html"

    query = db.t_articles.user_id == auth.user_id
    db.t_articles.user_id.default = auth.user_id
    db.t_articles.user_id.writable = False
    db.t_articles.auto_nb_recommendations.writable = False
    db.t_articles.art_stage_1_id.writable = False
    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.report_stage.writable = False
    db.t_articles.report_stage.readable = False
    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDivUser(
        text, showStage=pciRRactivated, stage1Id=row.t_articles.art_stage_1_id
    )
    db.t_articles.status.writable = False
    db.t_articles._id.represent = lambda text, row: common_small_html.mkArticleCellNoRecomm(row)
    db.t_articles._id.label = T("Article")
    db.t_articles.doi.readable = False
    db.t_articles.title.readable = False
    db.t_articles.authors.readable = False
    db.t_articles.ms_version.readable = False
    db.t_articles.article_source.readable = False
    db.t_articles.parallel_submission.readable = False
    db.t_articles.anonymous_submission.readable = False

    db.t_articles.scheduled_submission_date.readable = False
    db.t_articles.scheduled_submission_date.writable = False

    # db.t_articles.anonymous_submission.label = T("Anonymous submission")
    # db.t_articles.anonymous_submission.represent = lambda anon, r: common_small_html.mkAnonymousMask(anon)
    links = [
        dict(header=T("Suggested recommenders"), body=lambda row: user_module.mk_suggested_recommenders_user_button(row)),
        dict(header=T("Recommender(s)"), body=lambda row: user_module.getRecommender(row)),
        dict(
            header="",
            body=lambda row: A(
                SPAN(current.T("View / Edit"), _class="buttontext btn btn-default pci-button pci-submitter"),
                _href=URL(c="user", f="recommendations", vars=dict(articleId=row["t_articles.id"]), user_signature=True),
                _class="",
                _title=current.T("View and/or edit article"),
            ),
        ),
    ]
    if len(request.args) == 0:  # in grid
        db.t_articles.abstract.readable = False
        db.t_articles.keywords.readable = False
        db.t_articles.methods_require_specific_expertise.readable = False
        db.t_articles.thematics.readable = False
        db.t_articles.upload_timestamp.readable = False
        db.t_articles.upload_timestamp.represent = lambda text, row: common_small_html.mkLastChange(text)
        db.t_articles.upload_timestamp.label = T("Submitted")
        db.t_articles.last_status_change.represent = lambda text, row: common_small_html.mkLastChange(text)
        db.t_articles.auto_nb_recommendations.readable = True
    else:
        db.t_articles.doi.represent = lambda text, row: common_small_html.mkDOI(text)

    fields = [
            db.t_articles.scheduled_submission_date,
            db.t_articles.art_stage_1_id,
            db.t_articles.report_stage,
            db.t_articles.last_status_change,
            db.t_articles.status,
            # db.t_articles.uploaded_picture,
            db.t_articles._id,
            db.t_articles.upload_timestamp,
            db.t_articles.title,
            db.t_articles.anonymous_submission,
            db.t_articles.authors,
            db.t_articles.article_source,
            db.t_articles.abstract,
            db.t_articles.doi,
            db.t_articles.ms_version,
            db.t_articles.thematics,
            db.t_articles.keywords,
            db.t_articles.methods_require_specific_expertise,
            db.t_articles.auto_nb_recommendations,
        ]
    grid = SQLFORM.grid(
        query,
        searchable=False,
        details=False,
        editable=False,
        deletable=False,
        create=False,
        csv=csv,
        exportclasses=expClass,
        maxtextlength=250,
        paginate=20,
        fields=fields,
        links=links,
        left=db.t_status_article.on(db.t_status_article.status == db.t_articles.status),
        orderby=~db.t_articles.last_status_change,
        _class="web2py_grid action-button-absolute",
    )
    return dict(
        pageHelp=getHelp("#UserMyArticles"),
        customText=getText("#UserMyArticlesText"),
        titleIcon="duplicate",
        pageTitle=getTitle("#UserMyArticlesTitle"),
        grid=DIV(grid, _style=""),
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


######################################################################################################################################################################
@auth.requires_login()
def my_reviews():

    response.view = "default/myLayout.html"

    query = (
            (db.t_reviews.reviewer_id == auth.user_id)
            & (db.t_reviews.recommendation_id == db.t_recommendations._id)
            & (db.t_recommendations.article_id == db.t_articles._id)
    )
    pendingOnly = ("pendingOnly" in request.vars) and (request.vars["pendingOnly"] == "True")
    if pendingOnly:
        query = (query
            & (db.t_reviews.review_state == ReviewState.AWAITING_RESPONSE.value)
            & (db.t_articles.status.belongs((ArticleStatus.UNDER_CONSIDERATION.value, ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value)))
        )
        pageTitle = getTitle("#UserMyReviewsRequestsTitle")
        customText = getText("#UserMyReviewsRequestsText")
        btnTxt = current.T("Accept or decline")
    else:
        query = (query
            & (db.t_reviews.review_state != ReviewState.AWAITING_RESPONSE.value)
        )
        pageTitle = getTitle("#UserMyReviewsTitle")
        customText = getText("#UserMyReviewsText")
        btnTxt = current.T("View")

    def represent_article(article_id: int, row: ...):
        return common_small_html.represent_article_with_recommendation_info(row.t_reviews.recommendation_id)

    def represent_recommendation(recommendation_id: int, row: ...):
        return common_small_html.mkArticleCellNoRecommFromId(recommendation_id)

    def represent_article_status(status: str, row: ...):
        return common_small_html.mkStatusDivUser(status,
                                                 showStage=pciRRactivated,
                                                 stage1Id=row.t_articles.art_stage_1_id)
    
    def represent_article_last_change(last_change: datetime.datetime, row: Article):
        return DIV(common_small_html.mkElapsed(last_change), _style="min-width: 100px; text-align: center")

    def represent_review(recommendation_id: int, row: ...):
        return user_module.mkRecommendation4ReviewFormat(row.t_reviews)

    db.t_articles._id.represent = represent_article
    db.t_articles._id.label = T("Article")
    db.t_recommendations._id.represent = represent_recommendation
    db.t_recommendations._id.label = T("Recommendation")

    db.t_articles.art_stage_1_id.writable = False
    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.report_stage.writable = False
    db.t_articles.report_stage.readable = False
    db.t_articles.status.represent = represent_article_status

    db.t_reviews.last_change.label = T("Days elapsed")
    db.t_reviews.last_change.represent = represent_article_last_change
    db.t_reviews.reviewer_id.writable = False

    db.t_reviews.recommendation_id.label = T("Recommender")
    db.t_reviews.recommendation_id.represent = represent_review

    db.t_articles.scheduled_submission_date.readable = False
    db.t_articles.scheduled_submission_date.writable = False

    db.t_articles.doi.readable = False
    db.t_articles.doi.writable = False

    db.t_reviews._id.readable = False
    db.t_reviews.review_state.readable = False
    db.t_reviews.anonymously.readable = False
    db.t_reviews.review.readable = False
    db.t_reviews.review_pdf.readable = False

    if pendingOnly:
        db.t_reviews.review.readable = False
    else:
        db.t_reviews.recommendation_id.readable = False

    def download_review_link(row: ...):
        return A(T("file"), _href=URL(c="default", f='download', args=row.t_reviews.review_pdf)) if row.t_reviews.review_pdf else ""
    
    def review_as_text(row: ...):
        return DIV(
                DIV(
                    DIV(B("Review status : ", _style="margin-top: -2px; font-size: 14px"), common_small_html.mkReviewStateDiv(row.t_reviews["review_state"])),
                    _style="border-bottom: 1px solid #ddd",
                    _class="pci2-flex-row pci2-align-items-center",
                ),
                DIV(
                    WIKI(row.t_reviews.review or ""),
                         DIV(
                            DIV(
                                A(
                                    SPAN(current.T("Write, edit or upload your review")),
                                    _href=URL(c="user", f="edit_review", vars=dict(reviewId=row.t_reviews.id)),
                                    _class="btn btn-default" + (" disabled"
                                        if is_scheduled_review_open(db.t_articles[row.t_articles.id])
                                        else ""),
                                    _style="margin: 20px 10px 5px",
                                ),
                                I(current.T("You will be able to upload your review as soon as the author submit his preprint."),)
                                if is_scheduled_review_open(db.t_articles[row.t_articles.id])
                                else "",
                                _style="margin-bottom: 20px",
                                _class="text-center pci2-flex-center pci2-flex-column",
                            )
                            if row.t_reviews["review_state"] == ReviewState.AWAITING_REVIEW.value
                            else ""
                        ),
                    _style="color: #888",
                    _class="pci-div4wiki-large",
                ),
            )

    def view_edit_button(row: ...):
        return A(
            SPAN(btnTxt, _class="buttontext btn btn-default pci-reviewer pci-button"),
            _href=URL(c="user", f="recommendations", vars=dict(articleId=row.t_articles.id), user_signature=True),
            _class="",
            _title=current.T("View and/or edit review"),
        ) if row.t_reviews.review_state in (ReviewState.AWAITING_RESPONSE.value,
                                            ReviewState.AWAITING_REVIEW.value,
                                            ReviewState.REVIEW_COMPLETED.value,
                                            ReviewState.WILLING_TO_REVIEW.value) else ""

    links = [
        dict(
            header=T("Review uploaded as file") if not pciRRactivated else T("Review files"),
            body=download_review_link
        ),
        dict(
            header=T("Review as text"),
            body=review_as_text
        ),
        dict(
            header=T(""),
            body=view_edit_button
        ),
    ]
    grid: ... = SQLFORM.grid( # type: ignore
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
            db.t_articles.report_stage,
            db.t_articles.doi,
            db.t_articles.status,
            db.t_articles._id,
            db.t_reviews._id,
            db.t_reviews.anonymously,
            db.t_reviews.recommendation_id,
            db.t_reviews.last_change,
            db.t_reviews.review_state,
            db.t_reviews.review,
            db.t_reviews.review_pdf,
        ],
        links=links[1:] if pendingOnly else links,
        orderby=~db.t_reviews.last_change | ~db.t_reviews.review_state,
        _class="web2py_grid action-button-absolute",
        upload=URL("default", "download"),
    )
    if pendingOnly:
        titleIcon = "envelope"
    else:
        titleIcon = "eye-open"

    return dict(
        pageHelp=getHelp("#UserMyReviews"),
        titleIcon=titleIcon,
        pageTitle=pageTitle,
        customText=customText,
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


from app_components.ongoing_recommendation import is_scheduled_review_open


######################################################################################################################################################################
@auth.requires_login()
def ask_to_review():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    if articleId is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    article = db.t_articles[articleId]
    if article is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    if not (article.is_searching_reviewers):
        raise HTTP(403, "403: " + T("ERROR: The recommender is not searching for reviewers"))

    isParallel = db((db.t_articles.id == articleId)).select(db.t_articles.parallel_submission).last()

    _next = None
    if "_next" in request.vars:
        _next = request.vars["_next"]

    disclaimerText = None
    actionFormUrl = None
    dueTime = None
    ethics_not_signed = not (db.auth_user[auth.user_id].ethical_code_approved)
    if ethics_not_signed:
        redirect(URL(c="about", f="ethics", vars=dict(_next=URL("user", "ask_to_review", vars=dict(articleId=articleId) if articleId else ""))))

    disclaimerText = DIV(getText("#ConflictsForReviewers"))
    actionFormUrl = URL("user_actions", "do_ask_to_review")
    amISubmitter = article.user_id == auth.user_id
    recomm = db(db.t_recommendations.article_id == articleId).select().last()
    amIReviewer = auth.user_id in user_module.getReviewers(recomm)
    amIRecommender = recomm.recommender_id == auth.user_id

    rev = db(db.t_reviews.recommendation_id == recomm.id).select().last()
    dueTime = rev.review_duration.lower() if rev else 'three weeks'
    # FIXME: set parallel reviews default = three weeks (hardcoded) in user select form

    recommHeaderHtml = article_components.get_article_infos_card(article, False, True)

    pageTitle = getTitle("#AskForReviewTitle")
    customText = getText("#AskForReviewText")

    response.view = "controller/user/ask_to_review.html"
    return dict(
        titleIcon="envelope",
        pageTitle=pageTitle,
        disclaimerText=disclaimerText,
        actionFormUrl=actionFormUrl,
        dueTime=dueTime,
        customText=customText,
        articleId=articleId,
        isAlreadyReviewer=amIReviewer,
        isRecommender=amIRecommender,
        isSubmitter=amISubmitter,
        recommHeaderHtml=recommHeaderHtml,
        myBackButton=common_small_html.mkBackButton(),
    )


######################################################################################################################################################################
@auth.requires_login()
def edit_review():
    response.view = "default/myLayout.html"

    if "reviewId" not in request.vars:
        session.flash = "404: " + T("ID Unavailable")
        redirect(URL('default','index'))
    reviewId = int(request.vars["reviewId"])

    review = Review.get_by_id(reviewId)
    if review is None:
        session.flash = "404: " + T("Unavailable")
        redirect(URL('default','index'))

    recomm = Recommendation.get_by_id(review.recommendation_id)
    if recomm is None:
        session.flash = "404: " + T("Unavailable")
        redirect(URL('default','index'))

    art = Article.get_by_id(recomm.article_id)

    survey: Optional[ReportSurvey] = None
    if pciRRactivated:
        survey = ReportSurvey.get_merged_report_survey(recomm.article_id)

    # Check if article have correct status
    if review.reviewer_id != auth.user_id or review.review_state != "Awaiting review" or art.status != "Under consideration":
        session.flash = T("Unauthorized", lazy=False)
        redirect(URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True))
    # Check if article is Scheduled submission without doi
    elif scheduledSubmissionActivated and ((art.scheduled_submission_date is not None) or (art.status.startswith("Scheduled submission"))):
        session.flash = T("Unauthorized", lazy=False)
        redirect(URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True))
    else:
        buttons = [
            INPUT(_type="Submit", _name="save", _id="save-btn", _class="btn btn-info", _value="Save"),
            INPUT(_type="Submit", _name="terminate", _id="submit-btn", _class="btn btn-success", _value="Save & Submit Your Review"),
        ]
        db.t_reviews.no_conflict_of_interest.writable = not (review.no_conflict_of_interest)
        db.t_reviews.review_pdf.comment = T('Upload your PDF with the button or download it from the "file" link.')

        if pciRRactivated:
            common_tools.divert_review_pdf_to_multi_upload()

        if art.has_manager_in_authors:
            review.anonymously = False
            db.t_reviews.anonymously.writable = False
            db.t_reviews.anonymously.label = T("You cannot be anonymous because there is a manager in the authors")
        elif pciRRactivated and survey and survey.q22 == "YES - ACCEPT SIGNED REVIEWS ONLY":
            db.t_reviews.anonymously.widget = widget(_type="hidden")
            db.t_reviews.anonymously.label = T("Please note that reviews of this submission must be signed")
        else:
            db.t_reviews.anonymously.label = T("I wish to remain anonymous")

        fields = [
            "anonymously",
            "review",
            "review_pdf",
            "no_conflict_of_interest",
        ]
        if pciRRactivated: fields += [
            "anonymous_agreement",
        ]
        form = SQLFORM(
            db.t_reviews, record=review,
            fields=fields,
            showid=False, buttons=buttons, keepvalues=True, upload=URL("default", "download")
        )

        anonymous_dialog_input = INPUT(_name='anonymous_dialog_input', _id='anonymous-dialog-input', value='', _type='hidden')
        form[0].insert(0, anonymous_dialog_input)

        if form.process().accepted:
            files = form.vars.review_pdf
            if type(files) == list:
                common_tools.handle_multiple_uploads(review, files)

            if form.vars.save or form.vars.anonymous_dialog_input == 'save':
                session.flash = T("Review saved", lazy=False)
                redirect(URL(c="user", f="edit_review", vars=dict(reviewId=reviewId), user_signature=True))
            elif form.vars.terminate or form.vars.anonymous_dialog_input == 'terminate':
                redirect(URL(c="user_actions", f="review_completed", vars=dict(reviewId=review.id), user_signature=True))
        elif form.errors:
            response.flash = T("Form has errors", lazy=False)

    myScript = common_tools.get_script("edit_review.js")
    anonymousDialog = common_small_html.confirmationDialog("anonymousReviewerConfirmDialogMessage")

    return dict(
        pageHelp=getHelp("#UserEditReview"),
        myBackButton=common_small_html.mkBackButton(),
        anonymousReviewerConfirmDialog=anonymousDialog,
        customText=getText("#UserEditReviewText"),
        titleIcon="edit",
        pageTitle=getTitle("#UserEditReviewTitle"),
        form=form,
        myFinalScript=myScript,
        deleteFileButtonsScript=common_tools.get_script("add_delete_review_file_buttons_user.js"),
    )

######################################################################################################################################################################
@auth.requires_login()
def add_suggested_recommender():
    response.view = "default/myLayout.html"

    articleId = request.vars["articleId"]
    manager_authors = request.vars["manager_authors"]
    art = db.t_articles[articleId]

    if manager_authors != None:
        art.update_record(manager_authors=manager_authors)

    if (art.user_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        recommendersListSel = db((db.t_suggested_recommenders.article_id == articleId) & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)).select()
        excluded_recommenders = db(db.t_excluded_recommenders.article_id == articleId).select()
        recommendersList: List[LI] = []
        excludedRecommenders: List[LI] = []
        reviewersIds = [auth.user_id]
        for con in recommendersListSel:
            reviewersIds.append(con.auth_user.id)
            if con.t_suggested_recommenders.declined:
                recommendersList.append(LI(common_small_html.mkUser(con.auth_user.id), I(f' {T("(Declined by the recommender)")}')))
            elif con.t_suggested_recommenders.recommender_validated is False:
                recommendersList.append(LI(common_small_html.mkUser(con.auth_user.id), I(f' {T("(Cancelled by the managing board)")}')))
            elif con.t_suggested_recommenders.recommender_validated is True:
                recommendersList.append(LI(common_small_html.mkUser(con.auth_user.id), I(f' {T("(Validated by the managing board)")}')))
            else:
                recommendersList.append(
                    LI(
                        common_small_html.mkUser(con.auth_user.id),
                        I(" (Awaiting validation by the manager)") if (con.t_suggested_recommenders.recommender_validated is None) else "",
                        A(
                            "Remove",
                            _class="btn btn-warning",
                            _href=URL(c="user_actions", f="del_suggested_recommender", vars=dict(suggId=con.t_suggested_recommenders.id)),
                            _title=T("Delete"),
                            _style="margin-left:8px;",
                        )
                        if (art.status == "Pending" or art.status == "Awaiting consideration")
                        else "",
                    )
                )
        for row in excluded_recommenders:
            user_id = row.excluded_recommender_id
            reviewersIds.append(user_id)
            excludedRecommenders.append(
                    LI(
                        common_small_html.mkUser(user_id),
                        A(
                            "Remove",
                            _class="btn btn-warning",
                            _href=URL(c="user_actions", f="del_excluded_recommender", vars=dict(exclId=user_id)),
                            _title=T("Delete"),
                            _style="margin-left:8px;",
                        )
                        if (art.status == "Pending" or art.status == "Awaiting consideration")
                        else "",
                    )
                )
        excludeList = ','.join(map(str,reviewersIds))
        myContents: ... = DIV()
        txtbtn = current.T("Suggest recommenders")
        if len(recommendersList) > 0:
            myContents.append(DIV(LABEL(T("Suggested recommenders:")), UL(recommendersList, _class="pci-li-spacy")))
            txtbtn = current.T("Suggest another recommender?")

        if len(excludedRecommenders) > 0:
            myContents.append(DIV(LABEL(T("Excluded recommenders:")), UL(excludedRecommenders, _class="pci-li-spacy")))
            txtbtn = current.T("Suggest another recommender?")

        myUpperBtn = DIV(
            A(
                SPAN(txtbtn, _class="buttontext btn btn-info"),
                _href=URL(c="user", f="search_recommenders", vars=dict(articleId=articleId, exclude=excludeList), user_signature=True),
            ),
            _style="margin-top:16px; text-align:center;",
        )
        myAcceptBtn = DIV(
            A(SPAN(T("Complete your submission"), _class="buttontext btn btn-success"), _href=URL(c="user", f="my_articles", user_signature=True)),
            _style="margin-top:16px; text-align:left;",
            _class="pci2-complete-ur-submission",
        )

        article_form_clean_script = common_tools.get_script('clean_saved_article_form.js')

        return dict(
            titleIcon="education",
            pageTitle=getTitle("#UserAddSuggestedRecommenderTitle"),
            customText=getText("#UserAddSuggestedRecommenderText"),
            pageHelp=getHelp("#UserAddSuggestedRecommender"),
            myUpperBtn=myUpperBtn,
            content=myContents,
            form="",
            myAcceptBtn=myAcceptBtn,
            myFinalScript=article_form_clean_script,
        )


######################################################################################################################################################################
@auth.requires_login()
def edit_reply():
    response.view = "default/myLayout.html"
    if "recommId" not in request.vars:
        raise HTTP(404, "404: " + T("Unavailable"))
    recommId = request.vars["recommId"]

    recomm = db.t_recommendations[recommId]
    if recomm is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    art = db.t_articles[recomm.article_id]
    if not ((art.user_id == auth.user_id or auth.has_membership(role="manager")) and (art.status == "Awaiting revision")):
        session.flash = T("Unauthorized", lazy=False)
        redirect(URL(c="user", f="my_articles"))
    db.t_recommendations.reply_pdf.label = T("OR Upload your reply as PDF file")

    buttons = [
        A("Cancel", _class="btn btn-default", _href=URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True)),
        INPUT(_type="Submit", _name="save", _class="btn btn-success", _value="Save"),
    ]

    form = SQLFORM(db.t_recommendations, record=recommId, fields=["id", "reply", "reply_pdf", "track_change"], buttons=buttons, upload=URL("default", "download"), showid=False)

    if form.process().accepted:
        session.flash = T("Reply saved", lazy=False)
        redirect(URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True, anchor="author-reply"))
    elif form.errors:
        response.flash = T("Form has errors", lazy=False)
    if pciRRactivated and status['allow_submissions'] is False:
        form = getText("#SubmissionOnHoldInfo")
    return dict(
        pageHelp=getHelp("#UserEditReply"),
        titleIcon="edit",
        customText=getText("#UserEditReplyText"),
        pageTitle=getTitle("#UserEditReplyTitle"),
        form=form,
        deleteFileButtonsScript=common_tools.get_script("add_delete_recommendation_file_buttons_user.js"),
    )


def delete_temp_user():
    if "key" in request.vars:
        vkey = request.vars["key"]
    else:
        vkey = None
    if isinstance(vkey, list):
        vkey = vkey[1]
    if vkey == "":
        vkey = None

    user = db(db.auth_user.reset_password_key == vkey).select().last()

    reviews = db(db.t_reviews.reviewer_id == user.id).select()

    for rev in reviews:
        rev.review_state = "Declined"
        rev.update_record()

    if vkey is not None and user is not None:
        db(db.auth_user.reset_password_key == vkey).delete()
        session.flash = T("Account successfully deleted")
        redirect(URL(c="default", f="index"))
    else:
        session.flash = T("Account deletion failed")
        redirect(URL(c="default", f="index"))


######################################################################################################################################################################
# Show my submissions
@auth.requires_login()
def articles_awaiting_reviewers():
    response.view = "default/myLayout.html"

    articles = db.t_articles
    full_text_search_fields = [
        'id',
        'title',
        'authors',
        'thematics',
        'auto_nb_recommendations'
    ]

    def article_html(art_id):
        return common_small_html.mkRepresentArticleLight(art_id)

    articles.id.readable = True
    articles.id.represent = lambda text, row: article_html(row.id)
    articles.thematics.label = "Thematics fields"
    articles.thematics.type = "string"
    articles.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, zero=None)
    articles.auto_nb_recommendations.readable = True

    for a_field in articles.fields:
        if not a_field in full_text_search_fields:
            articles[a_field].readable = False

    articles.id.label = "Article"

    links = []
    links.append(dict(header="", body=lambda row: A(
        SPAN(current.T("Willing to review"), _class="buttontext btn btn-default pci-button pci-submitter"),
                _href=URL(c="user", f="ask_to_review", vars=dict(articleId=row.id)),
                _class="",
                _title=current.T("View and/or edit article"),),),)

    query = (db.t_articles.is_searching_reviewers == True) & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration")))
        
    original_grid = SQLFORM.grid(
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
            articles.id,
            articles.thematics,
            articles.auto_nb_recommendations,
        ],
        links=links,
        orderby=~articles.last_status_change,
        _class="web2py_grid action-button-absolute",
    )

    # options to be removed from the search dropdown:
    remove_options = []

    # fields that are integer and need to be treated differently
    integer_fields = ['t_articles.id', 't_articles.auto_nb_recommendations']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'articles_temp', remove_options, integer_fields)

    return dict(
        pageHelp=getHelp("#ArticlesAwaitingReviewers"),
        customText=getText("#ArticlesAwaitingReviewersText"),
        titleIcon="inbox",
        pageTitle=getTitle("#ArticlesAwaitingReviewersTitle"),
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )
