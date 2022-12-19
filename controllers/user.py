# -*- coding: utf-8 -*-

import os
import re
import copy
from datetime import date

from gluon.contrib.markdown import WIKI

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


# frequently used constants
myconf = AppConfig(reload=True)
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

######################################################################################################################################################################
def index():
    return my_reviews()

# Recommendations of my articles
@auth.requires_login()
def recommendations():

    printable = "printable" in request.vars and request.vars["printable"] == "True"
    myScript = ""

    articleId = request.vars["articleId"]
    if not articleId:
        return my_articles()

    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
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
            stage1Link = common_small_html.mkRepresentArticleLightLinkedWithStatus(auth, db, art.art_stage_1_id, urlArticle)

        # Create related stage 2 list
        elif pciRRactivated and not isStage2:
            stage2Articles = db(db.t_articles.art_stage_1_id == articleId).select()
            stage2List = []
            for art_st_2 in stage2Articles:
                urlArticle = URL(c="user", f="recommendations", vars=dict(articleId=art_st_2.id))
                stage2List.append(common_small_html.mkRepresentArticleLightLinkedWithStatus(auth, db, art_st_2.id, urlArticle))

        # Scheduled Submission form (doi + manuscript version)
        isScheduledSubmission = False
        scheduledSubmissionRemaningDays = None
        scheduledSubmissionForm = None
        if scheduledSubmissionActivated and art.status != "Cancelled" and art.user_id == auth.user_id:
            db.t_articles.doi.requires = IS_NOT_EMPTY(error_message=T("Cannot be empty"))
            scheduledSubmissionForm = SQLFORM(db.t_articles, articleId, fields=["doi", "ms_version"], keepvalues=True, showid=False)

            # Show form and get remaining days
            if  art.scheduled_submission_date is not None:
                isScheduledSubmission = True
                scheduledSubmissionRemaningDays = (art.scheduled_submission_date - date.today()).days

            showFullSubmissionUploadScreen = (
                art.scheduled_submission_date and
                (art.scheduled_submission_date - date.today()).days <= 7
            )
            if not showFullSubmissionUploadScreen:
                scheduledSubmissionForm = None
            else:
            # Remove scheduled submission date when doi is updated
              if scheduledSubmissionForm.process().accepted:
                art.scheduled_submission_date = None
                art.doi = scheduledSubmissionForm.vars.doi
                art.ms_version = scheduledSubmissionForm.vars.ms_version
                art.status = "Scheduled submission pending"
                art.update_record()

                session.flash = T("Article submitted successfully")
                redirect(URL(c="user", f="recommendations", vars=dict(articleId=articleId)))

        # Build recommendation
        response.title = art.title or myconf.take("app.longname")

        finalRecomm = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()

        if pciRRactivated and art.user_id != auth.user_id:
            recommHeaderHtml = article_components.getArticleInfosCard(auth, db, response, art, printable, False)
        else:
            recommHeaderHtml = article_components.getArticleInfosCard(auth, db, response, art, printable, True)

        recommStatusHeader = ongoing_recommendation.getRecommStatusHeader(auth, db, response, art, "user", request, True, printable, quiet=False)
        recommTopButtons = ongoing_recommendation.getRecommendationTopButtons(auth, db, art, printable, quiet=False)

        recommendationProgression = ongoing_recommendation.getRecommendationProcessForSubmitter(auth, db, response, art, printable)
        myContents = ongoing_recommendation.getRecommendationProcess(auth, db, response, art, printable)

        if printable:
            printableClass = "printable"
            response.view = "default/wrapper_printable.html"
        else:
            printableClass = ""
            response.view = "default/wrapper_normal.html"

        viewToRender = "default/recommended_articles.html"

        return dict(
            printable=printable,
            isSubmitter=(art.user_id == auth.user_id),
            viewToRender=viewToRender,
            recommHeaderHtml=recommHeaderHtml,
            recommStatusHeader=recommStatusHeader,
            recommTopButtons=recommTopButtons or "",
            pageHelp=getHelp(request, auth, db, "#UserRecommendations"),
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
        )


######################################################################################################################################################################
@auth.requires_login()
def search_recommenders():
    myVars = request.vars
    qyKw = ""
    qyTF = []
    excludeList = []
    articleId = None
    for myVar in myVars:
        if myVar == "exclude":
            myValue = myVars[myVar]
            myValue = myValue.split(",") if type(myValue) is str else myValue
            excludeList = list(map(int, myValue))
        elif isinstance(myVars[myVar], list):
            myValue = (myVars[myVar])[1]
        else:
            myValue = myVars[myVar]
        if myVar == "qyKeywords":
            qyKw = myValue
        elif re.match("^qy_", myVar) and myValue == "on":
            qyTF.append(re.sub(r"^qy_", "", myVar))
        elif myVar == "articleId":
            articleId = myValue

    if articleId is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    art = db.t_articles[articleId]
    if art is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if art.user_id != auth.user_id:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        # We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
        temp_db = DAL("sqlite:memory")
        qy_recomm = temp_db.define_table(
            "qy_recomm",
            Field("id", type="integer"),
            Field("num", type="integer"),
            Field("roles", type="string"),
            Field("score", type="double", label=T("Score"), default=0),
            Field("first_name", type="string", length=128, label=T("First name")),
            Field("last_name", type="string", length=128, label=T("Last name")),
            Field("email", type="string", length=512, label=T("e-mail")),
            Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
            Field("city", type="string", label=T("City"), represent=lambda t, r: t if t else ""),
            Field("country", type="string", label=T("Country"), represent=lambda t, r: t if t else ""),
            Field("laboratory", type="string", label=T("Department"), represent=lambda t, r: t if t else ""),
            Field("institution", type="string", label=T("Institution"), represent=lambda t, r: t if t else ""),
            Field("thematics", type="string", label=T("Thematic fields")),
            Field("keywords", type="string", label=T("Keywords")),
            Field("expertise", type="string", label=T("Areas of expertise")),
            Field("excluded", type="boolean", label=T("Excluded")),
            Field("any", type="string", label=T("All fields")),
        )
        qyKwArr = qyKw.split(" ")
        searchForm = app_forms.searchByThematic(auth, db, myVars)
        if searchForm.process(keepvalues=True).accepted:
            response.flash = None
        else:
            qyTF = []
            for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
                qyTF.append(thema.keyword)
        filtered = db.executesql("SELECT * FROM search_recommenders(%s, %s, %s) WHERE country is not null;", placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)

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

        users_ids = [ fr['id'] for fr in filtered ]
        keywords = { user.id: user.keywords for user in db(db.auth_user.id.belongs(users_ids)).select() }
        expertise = { user.id: user.cv for user in db(db.auth_user.id.belongs(users_ids)).select() }
        for fr in filtered:
            fr['keywords'] = keywords[fr['id']] or ""
            fr['expertise'] = expertise[fr['id']] or ""
            qy_recomm.insert(**fr, any=" ".join([str(fr[k]) if k in full_text_search_fields else "" for k in fr]))

        links = [
            dict(header=T(""), body=lambda row: "" if row.excluded else user_module.mkSuggestUserArticleToButton(auth, db, row, art.id, excludeList, myVars)),
        ]
        if pciRRactivated:
            links.append(dict(header=T(""), body=lambda row: "" if row.excluded else user_module.mkExcludeRecommenderButton(auth, db, row, art.id, excludeList, myVars)))
        selectable = None
        temp_db.qy_recomm.uploaded_picture.readable = False
        temp_db.qy_recomm.num.readable = False
        temp_db.qy_recomm.score.readable = False
        temp_db.qy_recomm.excluded.readable = False

        original_grid = SQLFORM.smartgrid(
                        qy_recomm,
                        editable=False,
                        deletable=False,
                        create=False,
                        details=False,
                        searchable=dict(auth_user=True, auth_membership=False),
                        selectable=selectable,
                        maxtextlength=250,
                        paginate=1000,
                        csv=csv,
                        exportclasses=expClass,
                        fields=[
                            temp_db.qy_recomm._id,
                            temp_db.qy_recomm.num,
                            temp_db.qy_recomm.score,
                            temp_db.qy_recomm.uploaded_picture,
                            temp_db.qy_recomm.first_name,
                            temp_db.qy_recomm.last_name,
                            temp_db.qy_recomm.laboratory,
                            temp_db.qy_recomm.institution,
                            temp_db.qy_recomm.city,
                            temp_db.qy_recomm.country,
                            temp_db.qy_recomm.thematics,
                            temp_db.qy_recomm.excluded,
                        ],
                        links=links,
                        orderby=temp_db.qy_recomm.num,
                        _class="web2py_grid action-button-absolute",
                    )

        # options to be removed from the search dropdown:
        remove_options = ['qy_recomm.id']

        # the grid is adjusted after creation to adhere to our requirements
        grid = adjust_grid.adjust_grid_basic(original_grid, 'recommenders', remove_options)

        if len(excludeList) > 1:
            btnTxt = current.T("Done")
        else:
            btnTxt = current.T("I don't wish to suggest recommenders now")
        myAcceptBtn = DIV(
            A(
                SPAN(btnTxt, _class="buttontext btn btn-info"),
                _href=URL(c="user", f="add_suggested_recommender", vars=dict(articleId=articleId, exclude=excludeList)),
                _class="button",
            ),
            _style="text-align:center; margin-top:16px;",
        )

        myUpperBtn = ""
        if len(grid) >= 10:
            myUpperBtn = myAcceptBtn

        response.view = "default/gab_list_layout.html"
        return dict(
            pageHelp=getHelp(request, auth, db, "#UserSearchRecommenders"),
            customText=getText(request, auth, db, "#UserSearchRecommendersText"),
            titleIcon="search",
            pageTitle=getTitle(request, auth, db, "#UserSearchRecommendersTitle"),
            myUpperBtn=myUpperBtn,
            myAcceptBtn=myAcceptBtn,
            grid=grid,
            absoluteButtonScript=common_tools.absoluteButtonScript,
        )


######################################################################################################################################################################
def new_submission():
    form = None
    state = None
    loginLink = None
    registerLink = None
    submitPreprintLink = None


    pageTitle=getTitle(request, auth, db, "#UserBeforeSubmissionTitle")
    customText=getText(request, auth, db, "#SubmissionOnHoldInfo")

    db.submissions.allow_submissions.writable = True
    db.submissions.allow_submissions.readable = True

    status = db.submissions[1]
    fields = ["allow_submissions"]
    
    if auth.has_membership(role="manager"):
        form = SQLFORM(db.submissions, 1, fields=fields)
        form.element(_type="checkbox")["_id"] = "toggle"
        if request.vars["allow_submissions"]:
            state = request.vars["allow_submissions"]
        else:
            state = "off"
        state = True if state == "on" else False
        if request.vars["update"]:
            status.update_record(allow_submissions=state)
    

    if status['allow_submissions']:
        pageTitle=getTitle(request, auth, db, "#UserBeforeSubmissionTitle")
        customText=getText(request, auth, db, "#NewRecommendationRequestInfo")
        
        if auth.user:
            submitPreprintLink = URL("user", "fill_new_article", user_signature=True)
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
def fill_new_article():
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
        db.t_articles.report_stage.readable = True
        db.t_articles.report_stage.writable = True
        db.t_articles.sub_thematics.readable = True
        db.t_articles.sub_thematics.writable = True

        db.t_articles.record_url_version.readable = True
        db.t_articles.record_url_version.writable = True
        db.t_articles.record_id_version.readable = True
        db.t_articles.record_id_version.writable = True

        db.t_articles.report_stage.requires = IS_IN_SET(("STAGE 1", "STAGE 2"))
        db.t_articles.ms_version.requires = [IS_NOT_EMPTY(), IS_LENGTH(1024, 0)]
        db.t_articles.doi.requires = [IS_NOT_EMPTY(), IS_LENGTH(512, 0)]
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
    ]

    if not pciRRactivated:
        fields += ["preprint_server"]
    
    fields += ["ms_version"]

    if pciRRactivated:
        fields += ["record_url_version", "record_id_version"]

    fields += [
        "anonymous_submission",
        "title",
        "authors",
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
    ]

    fields += ["thematics"]

    if pciRRactivated:
        fields += ["sub_thematics"]

    fields += ["keywords"]

    if not pciRRactivated:
        fields += [
            "suggest_reviewers",
            "competitors" 
    ]
    
    fields += ["recomm_notice" , "cover_letter"]

    if parallelSubmissionAllowed:
        fields += ["parallel_submission"]

    form = SQLFORM(db.t_articles, fields=fields, keepvalues=True,

            extra_fields=[
                Field("recomm_notice", widget=widget(_type="hidden"),
                    label=T("On the next page you will have the possibility to suggest recommenders for your article"),
                ),
            ],
    )

    app_forms.article_add_mandatory_checkboxes(form, pciRRactivated)

    def fixup_radio_group(name):
        elements = form.elements(_name=name)
        elements[0].update(_id=name+"_group")
        elements[1].update(_id="t_articles_no_"+name)
        elements[2].update(_id="t_articles_"+name)

    if not pciRRactivated:
        fixup_radio_group("results_based_on_data")
        fixup_radio_group("scripts_used_for_result")
        fixup_radio_group("codes_used_in_study")

    if pciRRactivated:
        form.element(_type="submit")["_value"] = T("Continue your submission")
    else:
        form.element(_type="submit")["_value"] = T("Complete your submission")

    form.element(_type="submit")["_class"] = "btn btn-success"

    def onvalidation(form):
        if pciRRactivated:
            form.vars.status = "Pending-survey"
    if form.process(onvalidation=onvalidation).accepted:
        articleId = form.vars.id
        if pciRRactivated:
            pass
        else:
            session.flash = T("Article submitted", lazy=False)
        myVars = dict(articleId=articleId)
        # for thema in form.vars.thematics:
        # myVars['qy_'+thema] = 'on'
        # myVars['qyKeywords'] = form.vars.keywords
        if pciRRactivated:
            redirect(URL(c="user", f="fill_report_survey", vars=myVars, user_signature=True))
        else:
            redirect(URL(c="user", f="add_suggested_recommender", vars=myVars, user_signature=True))
    elif form.errors:
        response.flash = T("Form has errors", lazy=False)


    customText = getText(request, auth, db, "#UserSubmitNewArticleText", maxWidth="800")
    if pciRRactivated:
        customText = ""
    status = db.submissions[1]
    if status['allow_submissions'] is False:
        form = getText(request, auth, db, "#SubmissionOnHoldInfo")

    myScript = common_tools.get_template("script", "fill_new_article.js")
    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp(request, auth, db, "#UserSubmitNewArticle"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#UserSubmitNewArticleTitle"),
        customText=customText,
        form=form,
        myFinalScript=SCRIPT(myScript) or "",
    )


######################################################################################################################################################################
@auth.requires_login()
def edit_my_article():

    response.view = "default/myLayout.html"
    if not ("articleId" in request.vars):
        session.flash = T("Unavailable")
        redirect(URL("my_articles", user_signature=True))
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art == None:
        session.flash = T("Unavailable")
        redirect(URL("my_articles", user_signature=True))
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    elif art.status not in ("Pending", "Awaiting revision", "Pending-survey", "Pre-submission"):
        session.flash = T("Forbidden access")
        redirect(URL("my_articles", user_signature=True))
    # deletable = (art.status == 'Pending')
    deletable = False
    db.t_articles.status.readable = False
    db.t_articles.status.writable = False
    db.t_articles.cover_letter.readable = True
    db.t_articles.cover_letter.writable = True
    db.t_articles.request_submission_change.readable = False
    db.t_articles.request_submission_change.writable = False

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
                IS_IN_DB(db((db.t_articles.user_id == auth.user_id) & (db.t_articles.art_stage_1_id == None) & (db.t_articles.id != art.id)), "t_articles.id", "%(title)s")
            )
            pciRRjsScript = ""
        else:
            db.t_articles.art_stage_1_id.requires = IS_EMPTY_OR([])
            pciRRjsScript = SCRIPT(
                """
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

    if pciRRactivated:
        db.t_articles.report_stage.readable = True
        db.t_articles.report_stage.writable = True
        db.t_articles.sub_thematics.readable = True
        db.t_articles.sub_thematics.writable = True

        db.t_articles.record_url_version.readable = True
        db.t_articles.record_url_version.writable = True
        db.t_articles.record_id_version.readable = True
        db.t_articles.record_id_version.writable = True

        db.t_articles.report_stage.requires = IS_IN_SET(("STAGE 1", "STAGE 2"))
        db.t_articles.ms_version.requires = [IS_NOT_EMPTY(), IS_LENGTH(1024, 0)]
        db.t_articles.doi.requires = [IS_NOT_EMPTY(), IS_LENGTH(512, 0)]
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

    if parallelSubmissionAllowed and art.status == "Pending":
        db.t_articles.parallel_submission.label = T("This preprint is (or will be) also submitted to a journal")
        fields = []
        if pciRRactivated:
            fields = ["report_stage"]
            if art.report_stage == "STAGE 2":
                fields += ["art_stage_1_id"]
                db.t_articles.art_stage_1_id.readable = True
                db.t_articles.art_stage_1_id.writable = True

        fields += [
            "doi",
        ]

        if not pciRRactivated:
            fields += ["preprint_server"]
        
        fields += ["ms_version"]

        if pciRRactivated:
            fields += ["record_url_version", "record_id_version"]

        fields += [
            "title",
            "anonymous_submission",
            "parallel_submission",
            "authors",
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
        ]

        fields += ["thematics"]

        if pciRRactivated:
            fields += ["sub_thematics"]

        fields += ["keywords"]

        if not pciRRactivated:
            fields += [
                "suggest_reviewers",
                "competitors" 
            ]

        fields += ["cover_letter"]
        myScript = common_tools.get_template("script", "edit_my_article.js")

    else:
        fields = []
        if pciRRactivated:
            fields = ["report_stage"]
            if art.report_stage == "STAGE 2":
                fields += ["art_stage_1_id"]
                db.t_articles.art_stage_1_id.readable = True
                db.t_articles.art_stage_1_id.writable = True

        fields += [
            "doi",
        ]

        if not pciRRactivated:
            fields += ["preprint_server"]
        
        fields += ["ms_version"]

        if pciRRactivated:
            fields += ["record_url_version", "record_id_version"]

        fields += [
            "title",
            "abstract",
            "anonymous_submission",
            "authors",
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
            ]

        fields += ["thematics"]

        if pciRRactivated:
            fields += ["sub_thematics"]

        fields += ["keywords"]

        if not pciRRactivated:
            fields += [
                "suggest_reviewers",
                "competitors" 
            ]

        fields += ["cover_letter"]
        if not pciRRactivated:
            myScript = common_tools.get_template("script", "new_field_responsiveness.js")

    buttons = [
        A("Cancel", _class="btn btn-default", _href=URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True)),
        INPUT(_type="Submit", _name="save", _class="btn btn-success", _value="Save"),
    ]

    form = SQLFORM(db.t_articles, articleId, fields=fields, upload=URL("static", "uploads"), deletable=deletable, buttons=buttons, showid=False)
    try:
        article_version = int(art.ms_version)
    except:
        article_version = art.ms_version

    prev_picture = art.uploaded_picture

    if type(db.t_articles.uploaded_picture.requires) == list: # non-RR see db.py
        not_empty = db.t_articles.uploaded_picture.requires.pop()

    # form.element(_type="submit")["_value"] = T("Save")
    def onvalidation(form):
        if not pciRRactivated:
            if isinstance(article_version, int):
                if int(art.ms_version) > int(form.vars.ms_version):
                    form.errors.ms_version = "New version number must be greater than or same as previous version number"
            if not prev_picture and form.vars.uploaded_picture == b"":
                form.errors.uploaded_picture = not_empty.error_message

    if form.process(onvalidation=onvalidation).accepted:
        if prev_picture and form.vars.uploaded_picture:
            try: os.unlink(os.path.join(request.folder, "uploads", prev_picture))
            except: pass

        response.flash = T("Article saved", lazy=False)
        article = db.t_articles[articleId]
        if article.status == "Pre-submission":
            article.status = "Pending"
        if form.vars.report_stage == "STAGE 1":
            article.art_stage_1_id = None
        article.request_submission_change = False
        article.update_record()
        if art.status == "Pending":
            redirect(URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True))
        else:
            redirect(URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True, anchor="author-reply"))

    elif form.errors:
        response.flash = T("Form has errors", lazy=False)
    status = db.submissions[1]

    if pciRRactivated and status['allow_submissions'] is False:
        form = getText(request, auth, db, "#SubmissionOnHoldInfo")

    return dict(
        pageHelp=getHelp(request, auth, db, "#UserEditArticle"),
        customText=getText(request, auth, db, "#UserEditArticleText"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#UserEditArticleTitle"),
        form=form,
        myFinalScript=SCRIPT(myScript),
        pciRRjsScript=pciRRjsScript,
    )


######################################################################################################################################################################
@auth.requires_login()
def fill_report_survey():
    response.view = "default/myLayout.html"

    if not ("articleId" in request.vars):
        session.flash = T("Unavailable")
        redirect(URL("my_articles", user_signature=True))
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art == None:
        session.flash = T("Unavailable")
        redirect(URL("my_articles", user_signature=True))
    if art.status not in ("Pending-survey", "Pending", "Awaiting revision"):
        session.flash = T("Forbidden access")
        redirect(URL("my_articles", user_signature=True))
    if art.user_id != auth.user_id:
        session.flash = T("Forbidden access")
        redirect(URL("my_articles", user_signature=True))

    if art.report_stage == "STAGE 1":
        db.t_report_survey.q1.requires = IS_IN_SET(("COMPLETE STAGE 1 REPORT FOR REGULAR REVIEW", "RR SNAPSHOT FOR SCHEDULED REVIEW"))
        db.t_report_survey.q2.requires = IS_IN_SET(("REGULAR RR", "PROGRAMMATIC RR"))
        db.t_report_survey.q3.requires = IS_IN_SET(("FULLY PUBLIC", "PRIVATE"))
        # db.t_report_survey.q4.requires = IS_NOT_EMPTY()
        # db.t_report_survey.q5.requires = IS_NOT_EMPTY()
        db.t_report_survey.q6.requires = IS_IN_SET(
            (
                "YES - THE RESEARCH INVOLVES AT LEAST SOME QUANTITATIVE HYPOTHESIS-TESTING AND THE REPORT INCLUDES A STUDY DESIGN TEMPLATE",
                "YES - EVEN THOUGH THE RESEARCH DOESN’T INVOLVE ANY QUANTITATIVE HYPOTHESIS-TESTING, THE REPORT NEVERTHELESS INCLUDES A STUDY DESIGN TEMPLATE",
                "NO - THE REPORT DOES NOT INCLUDE ANY QUANTITATIVE STUDIES THAT TEST HYPOTHESES OR PREDICTIONS. NO STUDY DESIGN TEMPLATE IS INCLUDED.",
                "N/A - THE SUBMISSION IS A STAGE 1 SNAPSHOT, NOT A STAGE 1 REPORT",
            )
        )
        db.t_report_survey.q7.requires = IS_IN_SET(
            (
                "No part of the data or evidence that will be used to answer the research question yet exists and no part will be generated until after IPA [Level 6]",
                "ALL of the data or evidence that will be used to answer the research question already exist, but are currently inaccessible to the authors and thus unobservable prior to IPA (e.g. held by a gatekeeper) [Level 5]",
                "At least some of the data/evidence that will be used to answer the research question already exists AND is accessible in principle to the authors (e.g. residing in a public database or with a colleague), BUT the authors certify that they have not yet accessed any part of that data/evidence [Level 4]",
                "At least some data/evidence that will be used to the answer the research question has been previously accessed by the authors (e.g. downloaded or otherwise received), but the authors certify that they have not yet observed ANY part of the data/evidence [Level 3]",
                "At least some data/evidence that will be used to answer the research question has been accessed and partially observed by the authors, but the authors certify that they have not yet observed the key variables within the data that will be used to answer the research question AND they have taken additional steps to maximise bias control and rigour (e.g. conservative statistical threshold; recruitment of a blinded analyst; robustness testing, multiverse/specification analysis, or other approach) [Level 2]",
                "At least some of the data/evidence that will be used to the answer the research question has been accessed and observed by the authors, including key variables, but the authors certify that they have not yet performed ANY of their preregistered analyses, and in addition they have taken stringent steps to reduce the risk of bias [Level 1]",
                "At least some of the data/evidence that will be used to the answer the research question has been accessed and observed by the authors, including key variables, AND the authors have already conducted (and know the outcome of) at least some of their preregistered analyses [Level 0]",
            )
        )
        db.t_report_survey.q8.requires = [IS_NOT_EMPTY(), IS_LENGTH(1024, 0)]
        db.t_report_survey.q9.requires = [IS_NOT_EMPTY(), IS_LENGTH(1024, 0)]
        db.t_report_survey.q11.requires = IS_IN_SET(("YES", "NO - PROVIDE DETAILS"))
        db.t_report_survey.q12.requires = IS_IN_SET(("YES", "NO - PROVIDE DETAILS"))
        db.t_report_survey.q13.requires = IS_IN_SET(db.TOP_guidelines_choices)
        # db.t_report_survey.q14.requires = IS_NOT_EMPTY()
        db.t_report_survey.q15.requires = [IS_NOT_EMPTY(), IS_LENGTH(2000, 0)]
        db.t_report_survey.q16.requires = IS_IN_SET(("MAKE PUBLIC IMMEDIATELY", "UNDER PRIVATE EMBARGO",))
        db.t_report_survey.q17.requires = [IS_NOT_EMPTY(), IS_LENGTH(128, 0)]
        # db.t_report_survey.q18.requires = IS_NOT_EMPTY()
        # db.t_report_survey.q19.requires = IS_NOT_EMPTY()
        db.t_report_survey.q20.requires = IS_IN_SET(("YES - please alert PCI RR-interested journals in the event of IPA, as described above", "NO",))
        db.t_report_survey.q21.requires = IS_IN_SET(("PUBLISH STAGE 1 REVIEWS AT POINT OF IPA", "PUBLISH STAGE 1 AND 2 REVIEWS TOGETHER FOLLOWING STAGE 2 ACCEPTANCE",))
        db.t_report_survey.q22.requires = IS_IN_SET(("YES - ACCEPT SIGNED REVIEWS ONLY", "NO - ACCEPT SIGNED AND ANONYMOUS REVIEWS",))
        db.t_report_survey.q23.requires = [IS_NOT_EMPTY(), IS_LENGTH(128, 0)]
        db.t_report_survey.q24.requires = IS_DATE(format=T('%Y-%m-%d'), error_message='must be a valid date: YYYY-MM-DD')
        db.t_report_survey.q24_1.requires = [IS_NOT_EMPTY(), IS_LENGTH(128, 0)]

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
            db((db.t_articles.user_id == auth.user_id) & (db.t_articles.art_stage_1_id == None)), "t_articles.id", 'Stage 2 of "%(title)s"'
        )

        # db.t_report_survey.q25.requires = IS_NOT_EMPTY()
        db.t_report_survey.q26.requires = IS_IN_SET(
            (
                T("YES - All data are contained in manuscript"),
                T(
                    "YES - Enter URL of the repository containing the data, ensuring that it contains sufficient README documentation to explain file definitions, file structures, and variable names (e.g. using a codebook)"
                ),
                T(
                    "NO - Please state the ethical or legal reasons why study data are not publicly archived and explain how the data supporting the reported results can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement."
                ),
            )
        )
        db.t_report_survey.q27.requires = IS_IN_SET(
            (
                "YES - All digital materials are contained in manuscript",
                "YES - Enter URL of the repository containing the digital materials, ensuring that it contains sufficient README documentation to explain file definitions, file structures, and variable names (e.g. using a codebook)",
                "NO - Please state the ethical or legal reasons why digital study materials are not publicly archived and explain how the materials can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement.",
                "N/A - There are no digital study materials of any kind",
            )
        )
        db.t_report_survey.q28.requires = IS_IN_SET(
            (
                "YES - All code is contained in manuscript",
                "YES - Enter URL of the repository containing the analysis code/scripts",
                "NO - Please state the ethical or legal reasons why analysis code is not publicly archived and explain how the materials can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement.",
                "N/A - No analysis code/scripts were used in any part of the data analysis",
            )
        )
        # db.t_report_survey.q29.requires = IS_NOT_EMPTY()
        db.t_report_survey.q30.requires = [IS_NOT_EMPTY(), IS_LENGTH(256, 0)]
        db.t_report_survey.q31.requires = IS_IN_SET(("N/A - NOT A PROGRAMMATIC RR", "CONFIRM",))

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

    form = SQLFORM(db.t_report_survey, fields=fields, keepvalues=True,)
    form.element(_type="submit")["_value"] = T("Complete your submission")
    form.element(_type="submit")["_class"] = "btn btn-success"

    form.append(STYLE(".calendar tbody td.weekend { pointer-events:none; }"))

    def onvalidation(form):
        if form.vars.q10 and form.vars.q10.weekday() >= 5:
            form.errors.q10 = "selected date must be a week day"

    if form.process(onvalidation=onvalidation).accepted:
        surveyId = form.vars.id
        survey = db.t_report_survey[surveyId]
        survey.article_id = articleId
        survey.update_record()

        doUpdateArticle = False
        prepareReminders = False
        if form.vars.q10 is not None:
            art.scheduled_submission_date = form.vars.q10
            # art.doi = None
            doUpdateArticle = True
            prepareReminders = True

        if form.vars.temp_art_stage_1_id is not None:
            art.art_stage_1_id = form.vars.temp_art_stage_1_id
            doUpdateArticle = True

        if True:
            art.status = "Pending"
            doUpdateArticle = True

        if doUpdateArticle == True:
            art.update_record()

        if prepareReminders == True:
            emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterScheduledSubmissionSoonDue", articleId)
            emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterScheduledSubmissionDue", articleId)
            emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterScheduledSubmissionOverDue", articleId)
            emailing.create_reminder_for_submitter_scheduled_submission_soon_due(session, auth, db, articleId)
            emailing.create_reminder_for_submitter_scheduled_submission_due(session, auth, db, articleId)
            emailing.create_reminder_for_submitter_scheduled_submission_over_due(session, auth, db, articleId)

        emailing.send_to_submitter_acknowledgement_submission(session, auth, db, articleId)
        emailing.create_reminder_for_submitter_suggested_recommender_needed(session, auth, db, articleId)

        session.flash = T("Article submitted", lazy=False)
        myVars = dict(articleId=articleId)
        # for thema in form.vars.thematics:
        # myVars['qy_'+thema] = 'on'
        # myVars['qyKeywords'] = form.vars.keywords
        redirect(URL(c="user", f="add_suggested_recommender", vars=myVars, user_signature=True))
    elif form.errors:
        response.flash = T("Form has errors", lazy=False)

    myScript = common_tools.get_template("script", "fill_report_survey.js")
    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp(request, auth, db, "#FillReportSurvey"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#FillReportSurveyTitle"),
        customText=getText(request, auth, db, "#FillReportSurveyText", maxWidth="800"),
        form=form,
        myFinalScript=SCRIPT(myScript),
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

    db.t_report_survey._id.readable = False
    db.t_report_survey._id.writable = False

    if art.report_stage == "STAGE 1":  # STAGE 1 survey
        db.t_report_survey.q1.requires = IS_IN_SET(("COMPLETE STAGE 1 REPORT FOR REGULAR REVIEW", "RR SNAPSHOT FOR SCHEDULED REVIEW"))
        db.t_report_survey.q2.requires = IS_IN_SET(("REGULAR RR", "PROGRAMMATIC RR"))
        db.t_report_survey.q3.requires = IS_IN_SET(("FULLY PUBLIC", "PRIVATE"))
        # db.t_report_survey.q4.requires = IS_NOT_EMPTY()
        # db.t_report_survey.q5.requires = IS_NOT_EMPTY()
        db.t_report_survey.q6.requires = IS_IN_SET(
            (
                "YES - THE RESEARCH INVOLVES AT LEAST SOME QUANTITATIVE HYPOTHESIS-TESTING AND THE REPORT INCLUDES A STUDY DESIGN TEMPLATE",
                "YES - EVEN THOUGH THE RESEARCH DOESN’T INVOLVE ANY QUANTITATIVE HYPOTHESIS-TESTING, THE REPORT NEVERTHELESS INCLUDES A STUDY DESIGN TEMPLATE",
                "NO - THE REPORT DOES NOT INCLUDE ANY QUANTITATIVE STUDIES THAT TEST HYPOTHESES OR PREDICTIONS. NO STUDY DESIGN TEMPLATE IS INCLUDED.",
                "N/A - THE SUBMISSION IS A STAGE 1 SNAPSHOT, NOT A STAGE 1 REPORT",
            )
        )
        db.t_report_survey.q7.requires = IS_IN_SET(
            (
                "No part of the data or evidence that will be used to answer the research question yet exists and no part will be generated until after IPA [Level 6]",
                "ALL of the data or evidence that will be used to answer the research question already exist, but are currently inaccessible to the authors and thus unobservable prior to IPA (e.g. held by a gatekeeper) [Level 5]",
                "At least some of the data/evidence that will be used to answer the research question already exists AND is accessible in principle to the authors (e.g. residing in a public database or with a colleague), BUT the authors certify that they have not yet accessed any part of that data/evidence [Level 4]",
                "At least some data/evidence that will be used to the answer the research question has been previously accessed by the authors (e.g. downloaded or otherwise received), but the authors certify that they have not yet observed ANY part of the data/evidence [Level 3]",
                "At least some data/evidence that will be used to answer the research question has been accessed and partially observed by the authors, but the authors certify that they have not yet observed the key variables within the data that will be used to answer the research question AND they have taken additional steps to maximise bias control and rigour (e.g. conservative statistical threshold; recruitment of a blinded analyst; robustness testing, multiverse/specification analysis, or other approach) [Level 2]",
                "At least some of the data/evidence that will be used to the answer the research question has been accessed and observed by the authors, including key variables, but the authors certify that they have not yet performed ANY of their preregistered analyses, and in addition they have taken stringent steps to reduce the risk of bias [Level 1]",
                "At least some of the data/evidence that will be used to the answer the research question has been accessed and observed by the authors, including key variables, AND the authors have already conducted (and know the outcome of) at least some of their preregistered analyses [Level 0]",
            )
        )
        db.t_report_survey.q8.requires = [IS_NOT_EMPTY(), IS_LENGTH(1024, 0)]
        db.t_report_survey.q9.requires = [IS_NOT_EMPTY(), IS_LENGTH(1024, 0)]
        db.t_report_survey.q11.requires = IS_IN_SET(("YES", "NO - PROVIDE DETAILS"))
        db.t_report_survey.q12.requires = IS_IN_SET(("YES", "NO - PROVIDE DETAILS"))
        db.t_report_survey.q13.requires = IS_IN_SET(db.TOP_guidelines_choices)
        # db.t_report_survey.q14.requires = IS_NOT_EMPTY()
        db.t_report_survey.q15.requires = [IS_NOT_EMPTY(), IS_LENGTH(2000, 0)]
        db.t_report_survey.q16.requires = IS_IN_SET(("MAKE PUBLIC IMMEDIATELY", "UNDER PRIVATE EMBARGO",))
        db.t_report_survey.q17.requires = [IS_NOT_EMPTY(), IS_LENGTH(128, 0)]
        # db.t_report_survey.q18.requires = IS_NOT_EMPTY()
        # db.t_report_survey.q19.requires = IS_NOT_EMPTY()
        db.t_report_survey.q20.requires = IS_IN_SET(("YES - please alert PCI RR-interested journals in the event of IPA, as described above", "NO",))
        db.t_report_survey.q21.requires = IS_IN_SET(("PUBLISH STAGE 1 REVIEWS AT POINT OF IPA", "PUBLISH STAGE 1 AND 2 REVIEWS TOGETHER FOLLOWING STAGE 2 ACCEPTANCE",))
        db.t_report_survey.q22.requires = IS_IN_SET(("YES - ACCEPT SIGNED REVIEWS ONLY", "NO - ACCEPT SIGNED AND ANONYMOUS REVIEWS",))
        db.t_report_survey.q23.requires = [IS_NOT_EMPTY(), IS_LENGTH(128, 0)]
        db.t_report_survey.q24.requires = IS_DATE(format=T('%Y-%m-%d'), error_message='must be a valid date: YYYY-MM-DD')
        db.t_report_survey.q24_1.requires = [IS_NOT_EMPTY(), IS_LENGTH(128, 0)]
        
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
            db((db.t_articles.user_id == auth.user_id) & (db.t_articles.art_stage_1_id == None)), "t_articles.id", 'Stage 2 of "%(title)s"'
        )

        # db.t_report_survey.q25.requires = IS_NOT_EMPTY()
        db.t_report_survey.q26.requires = IS_IN_SET(
            (
                T("YES - All data are contained in manuscript"),
                T(
                    "YES - Enter URL of the repository containing the data, ensuring that it contains sufficient README documentation to explain file definitions, file structures, and variable names (e.g. using a codebook)"
                ),
                T(
                    "NO - Please state the ethical or legal reasons why study data are not publicly archived and explain how the data supporting the reported results can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement."
                ),
            )
        )
        db.t_report_survey.q27.requires = IS_IN_SET(
            (
                "YES - All digital materials are contained in manuscript",
                "YES - Enter URL of the repository containing the digital materials, ensuring that it contains sufficient README documentation to explain file definitions, file structures, and variable names (e.g. using a codebook)",
                "NO - Please state the ethical or legal reasons why digital study materials are not publicly archived and explain how the materials can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement.",
                "N/A - There are no digital study materials of any kind",
            )
        )
        db.t_report_survey.q28.requires = IS_IN_SET(
            (
                "YES - All code is contained in manuscript",
                "YES - Enter URL of the repository containing the analysis code/scripts",
                "NO - Please state the ethical or legal reasons why analysis code is not publicly archived and explain how the materials can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement.",
                "N/A - No analysis code/scripts were used in any part of the data analysis",
            )
        )
        # db.t_report_survey.q29.requires = IS_NOT_EMPTY()
        db.t_report_survey.q30.requires = [IS_NOT_EMPTY(), IS_LENGTH(256, 0)]
        db.t_report_survey.q31.requires = IS_IN_SET(("N/A - NOT A PROGRAMMATIC RR", "CONFIRM",))

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

    form = SQLFORM(db.t_report_survey, survey.id, fields=fields, keepvalues=True,)

    form.append(STYLE(".calendar tbody td.weekend { pointer-events:none; }"))

    def onvalidation(form):
        if form.vars.q10 and form.vars.q10.weekday() >= 5:
            form.errors.q10 = "selected date must be a week day"

    if form.process(onvalidation=onvalidation).accepted:
        doUpdateArticle = False
        prepareReminders = False
        if form.vars.q10 is not None:
            art.scheduled_submission_date = form.vars.q10
            # art.doi = None
            doUpdateArticle = True
            prepareReminders = True

        if form.vars.temp_art_stage_1_id is not None:
            art.art_stage_1_id = form.vars.temp_art_stage_1_id
            doUpdateArticle = True

        if art.status in ["Pending-survey", "Pre-submission"]:
            art.status = "Pending"
            art.request_submission_change = False
            doUpdateArticle = True

        if doUpdateArticle == True:
            art.update_record()

        if prepareReminders == True:
            emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterScheduledSubmissionSoonDue", articleId)
            emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterScheduledSubmissionDue", articleId)
            emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterScheduledSubmissionOverDue", articleId)
            emailing.create_reminder_for_submitter_scheduled_submission_soon_due(session, auth, db, articleId)
            emailing.create_reminder_for_submitter_scheduled_submission_due(session, auth, db, articleId)
            emailing.create_reminder_for_submitter_scheduled_submission_over_due(session, auth, db, articleId)

        session.flash = T("Article submitted", lazy=False)
        myVars = dict(articleId=articleId)
        # for thema in form.vars.thematics:
        # myVars['qy_'+thema] = 'on'
        # myVars['qyKeywords'] = form.vars.keywords
        redirect(URL(c="user", f="recommendations", vars=myVars, user_signature=True))
    elif form.errors:
        response.flash = T("Form has errors", lazy=False)

    status = db.submissions[1]
    if pciRRactivated and status['allow_submissions'] is False:
        form = getText(request, auth, db, "#SubmissionOnHoldInfo")

    myScript = common_tools.get_template("script", "fill_report_survey.js")
    response.view = "default/gab_form_layout.html"
    return dict(
        pageHelp=getHelp(request, auth, db, "#EditReportSurvey"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#EditReportSurveyTitle"),
        customText=getText(request, auth, db, "#EditReportSurveyText", maxWidth="800"),
        form=form,
        myFinalScript=SCRIPT(myScript),
    )


######################################################################################################################################################################
# Display suggested recommenders for a submitted article
# Logged users only (submission)
@auth.requires_login()
def suggested_recommenders():
    response.view = "default/myLayout.html"
    write_auth = auth.has_membership("administrator") or auth.has_membership("developer")
    query = db.t_suggested_recommenders.article_id == request.vars["articleId"]
    db.t_suggested_recommenders._id.readable = False
    grid = SQLFORM.grid(
        query,
        details=False,
        editable=False,
        deletable=write_auth,
        create=False,
        searchable=False,
        maxtextlength=250,
        paginate=100,
        csv=csv,
        exportclasses=expClass,
        fields=[db.t_suggested_recommenders.suggested_recommender_id],
    )
    return dict(
        myBackButton=common_small_html.mkBackButton(),
        titleIcon="education",
        pageTitle=getTitle(request, auth, db, "#SuggestedRecommendersTitle"),
        customText=getText(request, auth, db, "#SuggestedRecommendersText"),
        pageHelp=getHelp(request, auth, db, "#SuggestedRecommenders"),
        grid=grid,
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
        db.t_suggested_recommenders.suggested_recommender_id.represent = lambda userId, row: common_small_html.mkUser(auth, db, userId)
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
            pageHelp=getHelp(request, auth, db, "#UserSuggestedRecommenders"),
            customText=getText(request, auth, db, "#UserSuggestedRecommendersText"),
            titleIcon="education",
            pageTitle=getTitle(request, auth, db, "#UserSuggestedRecommendersTitle"),
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
        auth, db, text, showStage=pciRRactivated, stage1Id=row.t_articles.art_stage_1_id, reportStage=row.t_articles.report_stage
    )
    db.t_articles.status.writable = False
    db.t_articles._id.represent = lambda text, row: common_small_html.mkArticleCellNoRecomm(auth, db, row)
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
    # db.t_articles.anonymous_submission.represent = lambda anon, r: common_small_html.mkAnonymousMask(auth, db, anon)
    links = [
        dict(header=T("Suggested recommenders"), body=lambda row: user_module.mkSuggestedRecommendersUserButton(auth, db, row)),
        dict(header=T("Recommender(s)"), body=lambda row: user_module.getRecommender(auth, db, row)),
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
        # myBackButton=common_small_html.mkBackButton(),
        pageHelp=getHelp(request, auth, db, "#UserMyArticles"),
        customText=getText(request, auth, db, "#UserMyArticlesText"),
        titleIcon="duplicate",
        pageTitle=getTitle(request, auth, db, "#UserMyArticlesTitle"),
        #grid=DIV(grid, _style="max-width:100%; overflow-x:auto;"),
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
            & (db.t_reviews.review_state == "Awaiting response")
            & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration")))
        )
        pageTitle = getTitle(request, auth, db, "#UserMyReviewsRequestsTitle")
        customText = getText(request, auth, db, "#UserMyReviewsRequestsText")
        btnTxt = current.T("Accept or decline")
    else:
        query = (query
            & (db.t_reviews.review_state != "Awaiting response")
        )
        pageTitle = getTitle(request, auth, db, "#UserMyReviewsTitle")
        customText = getText(request, auth, db, "#UserMyReviewsText")
        btnTxt = current.T("View / Edit")

    # db.t_articles._id.readable = False
    db.t_articles._id.represent = lambda aId, row: common_small_html.mkRepresentArticleLight(auth, db, aId)
    db.t_articles._id.label = T("Article")
    db.t_recommendations._id.represent = lambda rId, row: common_small_html.mkArticleCellNoRecommFromId(auth, db, rId)
    db.t_recommendations._id.label = T("Recommendation")

    db.t_articles.art_stage_1_id.writable = False
    db.t_articles.art_stage_1_id.readable = False
    db.t_articles.report_stage.writable = False
    db.t_articles.report_stage.readable = False
    db.t_articles.status.represent = lambda text, row: common_small_html.mkStatusDivUser(
        auth, db, text, showStage=pciRRactivated, stage1Id=row.t_articles.art_stage_1_id, reportStage=row.t_articles.report_stage
    )

    db.t_reviews.last_change.label = T("Days elapsed")
    db.t_reviews.last_change.represent = lambda text, row: DIV(common_small_html.mkElapsed(text), _style="min-width: 100px; text-align: center")
    db.t_reviews.reviewer_id.writable = False
    # db.t_reviews.recommendation_id.writable = False
    # db.t_reviews.recommendation_id.label = T('Member in charge of the recommendation process')
    db.t_reviews.recommendation_id.label = T("Recommender")
    db.t_reviews.recommendation_id.represent = lambda text, row: user_module.mkRecommendation4ReviewFormat(auth, db, row.t_reviews)

    db.t_articles.scheduled_submission_date.readable = False
    db.t_articles.scheduled_submission_date.writable = False

    db.t_articles.doi.readable = False
    db.t_articles.doi.writable = False

    db.t_reviews._id.readable = False
    db.t_reviews.review_state.readable = False
    db.t_reviews.anonymously.readable = False
    db.t_reviews.review.readable = False

    if pendingOnly:
        db.t_reviews.review.readable = False
        db.t_reviews.review_pdf.readable = False
    else:
        db.t_reviews.recommendation_id.readable = False
    # db.t_reviews.review.label = T('Your review')
    # links = [dict(header='toto', body=lambda row: row.t_articles.id),]
    links = [
        dict(
            header=T("Review as text"),
            body=lambda row: DIV(
                DIV(
                    DIV(B("Review status : ", _style="margin-top: -2px; font-size: 14px"), common_small_html.mkReviewStateDiv(auth, db, row.t_reviews["review_state"])),
                    _style="border-bottom: 1px solid #ddd",
                    _class="pci2-flex-row pci2-align-items-center",
                ),
                DIV(
                    WIKI(
                        row.t_reviews.review
                        or DIV(
                            DIV(
                                A(
                                    SPAN(current.T("Write, edit or upload your review")),
                                    _href=URL(c="user", f="edit_review", vars=dict(reviewId=row.t_reviews.id)),
                                    _class="btn btn-default disabled"
                                    if ((scheduledSubmissionActivated)  and (row.t_articles.scheduled_submission_date is not None or (row.t_articles.status.startswith("Scheduled submission"))))
                                    else "btn btn-default",
                                    _style="margin: 20px 10px 5px",
                                ),
                                I(current.T("You will be able to upload your review as soon as the author submit his preprint."),)
                                if ((scheduledSubmissionActivated) and (row.t_articles.scheduled_submission_date is not None or (row.t_articles.status.startswith("Scheduled submission"))))
                                else "",
                                _style="margin-bottom: 20px",
                                _class="text-center pci2-flex-center pci2-flex-column",
                            )
                            if row.t_reviews["review_state"] == "Awaiting review"
                            else ""
                        )
                        or "",
                        safe_mode=False,
                    ),
                    _style="color: #888",
                    _class="pci-div4wiki-large",
                ),
            ),
        ),
        dict(
            header=T(""),
            body=lambda row: A(
                SPAN(btnTxt, _class="buttontext btn btn-default pci-reviewer pci-button"),
                _href=URL(c="user", f="recommendations", vars=dict(articleId=row.t_articles.id), user_signature=True),
                _class="",
                _title=current.T("View and/or edit review"),
            )
            if row.t_reviews.review_state in ("Awaiting response", "Awaiting review", "Review completed", "Willing to review")
            else "",
        ),
    ]
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
        links=links,
        orderby=~db.t_reviews.last_change | ~db.t_reviews.review_state,
        _class="web2py_grid action-button-absolute",
        upload=URL("default", "download"),
    )
    if pendingOnly:
        titleIcon = "envelope"
    else:
        titleIcon = "eye-open"

    return dict(
        pageHelp=getHelp(request, auth, db, "#UserMyReviews"),
        titleIcon=titleIcon,
        pageTitle=pageTitle,
        customText=customText,
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )


######################################################################################################################################################################
@auth.requires_login()
def accept_new_review():

    if not ("reviewId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    reviewId = request.vars["reviewId"]
    if reviewId is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    rev = db.t_reviews[reviewId]
    if rev is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    if rev["reviewer_id"] != auth.user_id:
        raise HTTP(403, "403: " + T("Forbidden"))

    if rev["review_state"] in ["Declined", "Declined manually", "Review completed", "Cancelled"]:
        recomm = db((db.t_recommendations.id == rev["recommendation_id"])).select(db.t_recommendations.ALL).last()
        session.flash = T("Review state has been changed")
        redirect(URL(c="user", f="recommendations", vars=dict(articleId=recomm["article_id"])))

    isParallel = db((db.t_recommendations.id == rev["recommendation_id"]) & (db.t_recommendations.article_id == db.t_articles.id)).select(db.t_articles.parallel_submission).last()

    _next = None
    if "_next" in request.vars:
        _next = request.vars["_next"]

    disclaimerText = None
    actionFormUrl = None
    dueTime = None
    ethics_not_signed = not (db.auth_user[auth.user_id].ethical_code_approved)
    if ethics_not_signed:
        redirect(URL(c="about", f="ethics", vars=dict(_next=URL("user", "accept_new_review", vars=dict(reviewId=reviewId) if reviewId else ""))))
    else:
        disclaimerText = DIV(getText(request, auth, db, "#ConflictsForReviewers"))
        actionFormUrl = URL("user_actions", "do_accept_new_review", vars=dict(reviewId=reviewId) if reviewId else "")
        dueTime = rev.review_duration.lower()

    pageTitle = getTitle(request, auth, db, "#AcceptReviewInfoTitle")
    customText = getText(request, auth, db, "#AcceptReviewInfoText")

    response.view = "controller/user/accept_new_review.html"
    return dict(titleIcon="eye-open", pageTitle=pageTitle, disclaimerText=disclaimerText, actionFormUrl=actionFormUrl, dueTime=dueTime, customText=customText, reviewId=reviewId)


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

    disclaimerText = DIV(getText(request, auth, db, "#ConflictsForReviewers"))
    actionFormUrl = URL("user_actions", "do_ask_to_review")
    amISubmitter = article.user_id == auth.user_id
    recomm = db(db.t_recommendations.article_id == articleId).select().last()
    amIReviewer = auth.user_id in user_module.getReviewers(recomm, db)
    amIRecommender = recomm.recommender_id == auth.user_id

    rev = db(db.t_reviews.recommendation_id == recomm.id).select().last()
    dueTime = rev.review_duration.lower() if rev else 'three weeks'
    # FIXME: set parallel reviews default = three weeks (hardcoded) in user select form

    recommHeaderHtml = article_components.getArticleInfosCard(auth, db, response, article, False, True)

    pageTitle = getTitle(request, auth, db, "#AskForReviewTitle")
    customText = getText(request, auth, db, "#AskForReviewText")

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
        raise HTTP(404, "404: " + T("ID Unavailable"))
    reviewId = request.vars["reviewId"]

    review = db.t_reviews[reviewId]
    if review is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    recomm = db.t_recommendations[review.recommendation_id]
    if recomm is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    art = db.t_articles[recomm.article_id]
    if pciRRactivated: \
    survey = db(db.t_report_survey.article_id == recomm.article_id).select().last()
    # survey.article_id = articleId
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
            INPUT(_type="Submit", _name="save", _class="btn btn-info", _value="Save"),
            INPUT(_type="Submit", _name="terminate", _class="btn btn-success", _value="Save & Submit Your Review"),
        ]
        db.t_reviews.no_conflict_of_interest.writable = not (review.no_conflict_of_interest)
        db.t_reviews.review_pdf.label = T("AND/OR Upload review as PDF")
        db.t_reviews.review_pdf.comment = T('Upload your PDF with the button or download it from the "file" link.')
        if art.has_manager_in_authors:
            review.anonymously = False
            db.t_reviews.anonymously.writable = False
            db.t_reviews.anonymously.label = T("You cannot be anonymous because there is a manager in the authors")
        elif pciRRactivated and survey.q22 == "YES - ACCEPT SIGNED REVIEWS ONLY":
            db.t_reviews.anonymously.writable = False
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

        if form.process().accepted:
            if form.vars.save:
                session.flash = T("Review saved", lazy=False)
                redirect(URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True))
            elif form.vars.terminate:
                redirect(URL(c="user_actions", f="review_completed", vars=dict(reviewId=review.id), user_signature=True))
        elif form.errors:
            response.flash = T("Form has errors", lazy=False)

    myScript = common_tools.get_template("script", "edit_review.js")

    return dict(
        pageHelp=getHelp(request, auth, db, "#UserEditReview"),
        myBackButton=common_small_html.mkBackButton(),
        customText=getText(request, auth, db, "#UserEditReviewText"),
        titleIcon="edit",
        pageTitle=getTitle(request, auth, db, "#UserEditReviewTitle"),
        form=form,
        myFinalScript=SCRIPT(myScript),
        deleteFileButtonsScript=SCRIPT(common_tools.get_template("script", "add_delete_review_file_buttons_user.js"), _type="text/javascript"),
    )


######################################################################################################################################################################
@auth.requires_login()
def add_suggested_recommender():
    response.view = "default/myLayout.html"

    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if (art.user_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        recommendersListSel = db((db.t_suggested_recommenders.article_id == articleId) & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)).select()
        excluded_recommenders = db(db.t_excluded_recommenders.article_id == articleId).select()
        recommendersList, excludedRecommenders = [], []
        reviewersIds = [auth.user_id]
        for con in recommendersListSel:
            reviewersIds.append(con.auth_user.id)
            if con.t_suggested_recommenders.declined:
                recommendersList.append(LI(common_small_html.mkUser(auth, db, con.auth_user.id), I(T("(declined)"))))
            else:
                recommendersList.append(
                    LI(
                        common_small_html.mkUser(auth, db, con.auth_user.id),
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
                        common_small_html.mkUser(auth, db, user_id),
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
        myContents = DIV()
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
        return dict(
            titleIcon="education",
            pageTitle=getTitle(request, auth, db, "#UserAddSuggestedRecommenderTitle"),
            customText=getText(request, auth, db, "#UserAddSuggestedRecommenderText"),
            pageHelp=getHelp(request, auth, db, "#UserAddSuggestedRecommender"),
            myUpperBtn=myUpperBtn,
            content=myContents,
            form="",
            myAcceptBtn=myAcceptBtn,
            # myFinalScript=myScript,
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
        # if request.vars.completed:
        #     session.flash = T("Reply completed", lazy=False)
        #     redirect(URL(c="user_actions", f="article_revised", vars=dict(articleId=art.id), user_signature=True))
        # else:
        session.flash = T("Reply saved", lazy=False)
        redirect(URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True, anchor="author-reply"))
    elif form.errors:
        response.flash = T("Form has errors", lazy=False)
    return dict(
        pageHelp=getHelp(request, auth, db, "#UserEditReply"),
        # myBackButton = common_small_html.mkBackButton(),
        titleIcon="edit",
        customText=getText(request, auth, db, "#UserEditReplyText"),
        pageTitle=getTitle(request, auth, db, "#UserEditReplyTitle"),
        form=form,
        deleteFileButtonsScript=SCRIPT(common_tools.get_template("script", "add_delete_recommendation_file_buttons_user.js"), _type="text/javascript"),
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

    query = (db.t_articles.is_searching_reviewers == True) & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration")))

    qy_art = DAL("sqlite:memory").define_table(
        "qy_art",

        # displayed full-text searchable synthetic field
        Field("text", type="string", label="Article"),

        # displayed fields
        Field("thematics", type="string", label=T("Thematic fields")),
        Field("auto_nb_recommendations", type="integer", label=T("Rounds of reviews")),

        # additional advanced search fields (if not filtered in adjust_grid)
        Field("abstract", type="text"),
        Field("keywords", type="text"),

        Field("last_status_change", type="date", readable=False), # sort key
    )

    art_html = {}
    qy_art.text.represent = lambda text, row: art_html[row.id]
    qy_art.thematics.requires = IS_IN_DB(db, db.t_thematics.keyword, zero=None)

    for row in db(query).select():
        html = common_small_html.mkArticleCellNoRecomm(auth, db, row)
        art_html[row.id] = html
        row.text = html.flatten()
        row.thematics = ", ".join(row.thematics)
        row = {f: row[f] for f in [str(f).replace("qy_art.", "") for f in qy_art]}
        qy_art.insert(**row)

    links = [
        dict(
            header="",
            body=lambda row: A(
                SPAN(current.T("Willing to review"), _class="buttontext btn btn-default pci-button pci-submitter"),
                _href=URL(c="user", f="ask_to_review", vars=dict(articleId=row.id)),
                _class="",
                _title=current.T("View and/or edit article"),
            ),
        ),
    ]

    fields = [
            qy_art.text,
            qy_art.thematics,
            qy_art.auto_nb_recommendations,
        ]

    original_grid = SQLFORM.grid(
        qy_art,
        searchable=True,
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
        orderby=~qy_art.last_status_change,
        _class="web2py_grid action-button-absolute",
    )

    # options to be removed from the search dropdown:
    remove_options = ['qy_art.doi', 'qy_art.abstract', 'qy_art.status', 'qy_art.id', 
                      'qy_art.parallel_submission', 'qy_art.last_status_change', 
                      'qy_art.already_published']

    # the grid is adjusted after creation to adhere to our requirements
    grid = adjust_grid.adjust_grid_basic(original_grid, 'articles2', remove_options)

    return dict(
        pageHelp=getHelp(request, auth, db, "#ArticlesAwaitingReviewers"),
        customText=getText(request, auth, db, "#ArticlesAwaitingReviewersText"),
        titleIcon="inbox",
        pageTitle=getTitle(request, auth, db, "#ArticlesAwaitingReviewersTitle"),
        grid=grid,
        absoluteButtonScript=common_tools.absoluteButtonScript,
    )
