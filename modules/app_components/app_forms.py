from re import match
from typing import Optional
from gluon import *
from gluon.globals import Session
from gluon.html import *
from gluon.sqlhtml import SQLFORM
from gluon.contrib.appconfig import AppConfig
from gluon import current
from app_modules import emailing
from gluon.validators import *
from app_modules.helper import *
from datetime import date

from models.article import Article
from models.report_survey import ReportSurvey

myconf = AppConfig(reload=True)
applongname = myconf.take("app.longname")

######################################################################################################################################################################
# New common modules
def searchByThematic(auth, db, myVars, allowBlank=True,redirectSearchArticle=False):
    keywords = None
    if "qyKeywords" in myVars:
        keywords = myVars["qyKeywords"]
        if isinstance(keywords, list):
            keywords = keywords[1]

    # count requested thematic fields
    if myVars is None:
        myVars = dict()
    searchedThematics = 0
    for myVar in myVars:
        if match("^qy_", myVar):
            searchedThematics += 1

    thematics = db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword)
    thematicsList = []
    for thematic in thematics:
        if searchedThematics == 0:
            checkbox = INPUT(_name="qy_" + thematic.keyword, _type="checkbox", value=True, keepvalues=True)
        else:
            checkbox = INPUT(_name="qy_" + thematic.keyword, _type="checkbox", value=("qy_" + thematic.keyword in myVars), keepvalues=True)
        thematicsList.append(DIV(LABEL(checkbox, thematic.keyword, _style="font-weight: normal;")))

    if searchedThematics >= 1 and searchedThematics < len(thematics):
        iconPanelCLass = "glyphicon-rotate-reversed"
        panelCLass = ""
    else:
        iconPanelCLass = "glyphicon-rotate"
        panelCLass = "pci2-panel-closed"

    actionForm = ""
    placeholderText = current.T("Search")
    if redirectSearchArticle == True:
        actionForm = URL('default','index')
        placeholderText = current.T("Search articles")

    return FORM(
        DIV(
            DIV(
                INPUT(_placeholder=placeholderText, _name="qyKeywords", value=keywords, keepvalues=True, _class="form-control pci2-search-input"),
                _class="pci2-search-input-div",
            ),
            BUTTON(current.T("Search"), _type="submit", _class="btn btn-success pci2-search-button"),
            _class="pci2-search-div",
        ),
        DIV(
            A(
                SPAN(current.T("Filter by thematic fields"), _class="pci2-flex-grow"),
                I("", _class="glyphicon glyphicon-chevron-up pci2-icon-rotating " + iconPanelCLass),
                _class="pci2-thematic-link",
                _onclick="""
					if( jQuery(".pci2-thematics-div" ).hasClass("pci2-panel-closed")) { 
						jQuery(".pci2-thematics-div").removeClass("pci2-panel-closed") 						
						jQuery(".pci2-icon-rotating").removeClass("glyphicon-rotate") 
						jQuery(".pci2-icon-rotating").addClass("glyphicon-rotate-reversed") 
					} else {
						jQuery(".pci2-thematics-div").addClass("pci2-panel-closed") 						
						jQuery(".pci2-icon-rotating").removeClass("glyphicon-rotate-reversed") 
						jQuery(".pci2-icon-rotating").addClass("glyphicon-rotate") 
					} 
				""",
            ),
            _class="pci2-thematic-link-div",
        ),
        DIV(
            DIV(thematicsList, _class="pci2-thematics-list"),
            DIV(
                BUTTON(
                    current.T("Check all thematic fields"),
                    _type="button",
                    _class="btn btn-default pci2-thematics-button",
                    _onclick='jQuery("input[type=checkbox]").each(function(k){if (this.name.match("^qy_")) {jQuery(this).prop("checked", true);} });',
                ),
                BUTTON(
                    current.T("Toggle thematic fields"),
                    _type="button",
                    _class="btn btn-default pci2-thematics-button",
                    _onclick='jQuery("input[type=checkbox]").each(function(k){if (this.name.match("^qy_")) {jQuery(this).prop("checked", !jQuery(this).prop("checked"));} });',
                ),
            ),
            _class="pci2-thematics-div " + panelCLass,
        ),
        _class="pci2-search-form search-form-front",
        _action=actionForm
    )


######################################################################################################################################################################
def getSendMessageForm(declineKey, response):
    if response == 'accept': text = ' also '
    else: text = ' '

    return FORM(
        DIV(
            H4("We welcome your suggestions on who might%sbe a suitable reviewer for this article. Please enter the names and email of suggested reviewers here (one line per reviewer):"%text, _class="decline-review-title")
        ),
        DIV(
            TEXTAREA(_name="suggested_reviewers_text", keepvalues=True, _class="form-control", _id="suggestion-textbox", _style="resize: none")
        ),
        DIV(
            BUTTON(current.T("Send these suggestions to the recommender"), _type="submit", _id="suggestion-submission", _class="btn btn-success"),
            BUTTON(current.T("I have no suggestions"), _type="submit", _name="noluck", _value="1", _class="btn btn-default"),
            _class="pci2-flex-center",
        ),
        hidden={"declineKey":declineKey},
        _action=URL("send_suggested_reviewers"),
        _style="max-width: 800px; display: inline-block",
    )


from gluon import IS_EMPTY_OR, IS_LIST_OF_EMAILS

def cc_widget(field, value):
    field.requires = IS_EMPTY_OR(IS_LIST_OF_EMAILS(error_message="invalid (list of) e-mail(s): %s"))

    return SQLFORM.widgets.string.widget(field, ('' if value is None else ', '.join(value)))


#########################################################################
# reminders emails form validation
#########################################################################

from app_modules import emailing_tools

def update_mail_content_keep_editing_form(form, db, request, response):

    mail = db.mail_queue[request.vars.id]
    content_saved = process_mail_content(mail, form)

    if content_saved:
        request.args[0] = "view"
        response.flash = current.T("Reminder saved")
    else:
        response.flash = current.T("Error saving reminder: ") + form.error_msg

    form.errors = True  # force validation failure to keep editing form
    form.content_saved = content_saved


def process_mail_content(mail, form):
    try:
        content_begin = mail.mail_content.rindex("<!-- CONTENT START -->") + 22
        content_end = mail.mail_content.rindex("<!-- CONTENT END -->")

        new_content = mail.mail_content[0:content_begin]
        new_content += form.vars.mail_content
        new_content += mail.mail_content[content_end:-1]

        mail.mail_content = new_content
        mail.mail_subject = form.vars.mail_subject
        mail.sending_date = form.vars.sending_date
        mail.cc_mail_addresses = emailing_tools.list_addresses(form.vars.cc_mail_addresses)
        mail.replyto_addresses = emailing_tools.list_addresses(form.vars.replyto_addresses)
        mail.bcc_mail_addresses = emailing_tools.list_addresses(form.vars.bcc_mail_addresses)
        mail.update_record()

        content_saved = True
    except Exception as e:
        content_saved = False
        form.error_msg = str(e)

    return content_saved


#########################################################################
from pydal import Field

def article_add_mandatory_checkboxes(form, pciRRactivated):
    checkboxes_min = {
        "i_am_an_author":
        "I am an author of the article and I am acting on behalf of all authors",

        "is_not_reviewed_elsewhere":
        current.T(
        "This preprint has not been published or sent for review elsewhere. I agree not to submit this preprint to a journal before the end of the %s evaluation process (i.e. before its rejection or recommendation by %s), if it is sent out for review."
        ) % (applongname, applongname),
    }
    checkboxes_std = {
        "guide_read":
        "I read the guide for authors",

        "approvals_obtained":
        "If applicable, all the necessary approvals have been obtained before submission (or not applicable)",

        "human_subject_consent_obtained":
        "If applicable, a statement that informed consent was obtained, for experimentation with human subjects, is in the manuscript (or not applicable)",

        "lines_numbered":
        "Lines are numbered (unless your preprint is deposited in arXiv or in any other archive not accepting line numbering)",

        "conflicts_of_interest_indicated":
        "Non-financial conflicts of interest are indicated in the “Conflict of interest disclosure” section or in the cover letter",

        "no_financial_conflict_of_interest":
        "The authors declare that they have no financial conflict of interest with the content of the manuscript",
    }
    checkboxes = dict(checkboxes_min)
    checkboxes.update(checkboxes_std)

    if pciRRactivated:
        checkboxes = checkboxes_min

    fields = [
        Field(
            name,
            type="boolean",
            label=current.T(label),
            requires=IS_NOT_EMPTY(),
        )
        for name, label in checkboxes.items()
    ]
    extra = SQLFORM.factory(
        *fields,
        table_name="t_articles",
    )

    for field in extra.elements('.form-group')[:-1]: # discard submit button
        form[0].insert(-1, field)

#######################################################################################
def report_survey(auth: Auth, session: Session, article: Article, db: DAL, survey: Optional[ReportSurvey] = None, controller: Optional[str] = None, do_validate: bool = True):
    db.t_report_survey._id.readable = False
    db.t_report_survey._id.writable = False

    if article.report_stage == "STAGE 1":
        fields = get_from_fields_report_survey_stage1(db)
    else:
        fields = get_from_fields_report_survey_stage2(db, auth, article)

    form = SQLFORM(db.t_report_survey, survey.id if survey else "", fields=fields, keepvalues=True,)
    form.append(STYLE(".calendar tbody td.weekend { pointer-events:none; }"))

    if controller == "user_fill":
        form.element(_type="submit")["_value"] = current.T("Complete your submission")
        form.element(_type="submit")["_class"] = "btn btn-success"


    if form.process(onvalidation=report_survey_on_validation(form, article, do_validate)).accepted:
        doUpdateArticle = False
        prepareReminders = False
        if form.vars.q10 is not None:
            if article.scheduled_submission_date or controller == "user_fill":
                # /!\ used as a _flag_ and reset to None in user.py
                #     do not set it back to non-None accidently
                article.scheduled_submission_date = form.vars.q10
                doUpdateArticle = True
            prepareReminders = True

        if form.vars.temp_art_stage_1_id is not None:
            article.art_stage_1_id = form.vars.temp_art_stage_1_id
            doUpdateArticle = True

        if controller == "user_edit" and article.status in ["Pending-survey", "Pre-submission"]:
            article.status = "Pending"
            article.request_submission_change = False
            doUpdateArticle = True

        if controller == "user_fill" and True:
            article.status = "Pending"
            doUpdateArticle = True

        if doUpdateArticle == True:
            article.update_record()

        if prepareReminders == True:
            emailing.create_reminders_for_submitter_scheduled_submission(session, auth, db, article)

        myVars = dict(articleId=article.id)
        session.flash = current.T("Article submitted", lazy=False)

        if controller == "user_fill":
            emailing.send_to_submitter_acknowledgement_submission(session, auth, db, article.id)
            emailing.create_reminder_for_submitter_suggested_recommender_needed(session, auth, db, article.id)
            redirect(URL(c="user", f="add_suggested_recommender", vars=myVars, user_signature=True))

        if controller == "manager_edit":
            controller = "manager" if auth.has_membership(role="manager") else "recommender"
            redirect(URL(c=controller, f="recommendations", vars=myVars, user_signature=True))

        if controller == "user_edit":
            redirect(URL(c="user", f="recommendations", vars=myVars, user_signature=True))

    elif form.errors:
        session.flash = current.T("Form has errors", lazy=False)

    return form


def report_survey_validate_due_date(form: FORM):
    due_date = form.vars.q10
    is_snapshot = form.vars.q1 == "RR SNAPSHOT FOR SCHEDULED REVIEW"

    if not is_snapshot:
        return

    if not due_date:
        return "Please provide a date"

    if due_date.weekday() >= 5:
        return "selected date must be a week day"

    if due_date < date.today():
        return "Please select a date in the future"


def report_survey_on_validation(form: FORM, article: Article, do_validate: bool):
    form.vars.article_id = article.id
    if form.vars.q16 == "UNDER PRIVATE EMBARGO" and form.vars.q17 is None:
        form.errors.q17 = "Please provide a duration"

    error = report_survey_validate_due_date(form)
    if error and do_validate:
        form.errors.q10 = error
    
    if form.vars.q10 is not None and form.vars.q4 is None:
        form.errors.q4 = "This box needs to be ticked"


def get_from_fields_report_survey_stage1(db: DAL):
    db.t_report_survey.q1.requires = IS_IN_SET(("COMPLETE STAGE 1 REPORT FOR REGULAR REVIEW", "RR SNAPSHOT FOR SCHEDULED REVIEW"))
    db.t_report_survey.q2.requires = IS_IN_SET(("REGULAR RR", "PROGRAMMATIC RR"))
    db.t_report_survey.q3.requires = IS_IN_SET(("FULLY PUBLIC", "PRIVATE"))
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
    db.t_report_survey.q15.requires = [IS_NOT_EMPTY(), IS_LENGTH(2000, 0)]
    db.t_report_survey.q16.requires = IS_IN_SET(("MAKE PUBLIC IMMEDIATELY", "UNDER PRIVATE EMBARGO",))
    db.t_report_survey.q17.requires = IS_EMPTY_OR(IS_LENGTH(128, 0))
    db.t_report_survey.q20.requires = IS_IN_SET(("YES - please alert PCI RR-interested journals in the event of IPA, as described above", "NO",))
    db.t_report_survey.q21.requires = IS_IN_SET(("PUBLISH STAGE 1 REVIEWS AT POINT OF IPA", "PUBLISH STAGE 1 AND 2 REVIEWS TOGETHER FOLLOWING STAGE 2 ACCEPTANCE",))
    db.t_report_survey.q22.requires = IS_IN_SET(("YES - ACCEPT SIGNED REVIEWS ONLY", "NO - ACCEPT SIGNED AND ANONYMOUS REVIEWS",))
    db.t_report_survey.q23.requires = [IS_NOT_EMPTY(), IS_LENGTH(128, 0)]
    db.t_report_survey.q24.requires = IS_DATE(format=current.T('%Y-%m-%d'), error_message='must be a valid date: YYYY-MM-DD')
    db.t_report_survey.q24_1.requires = [IS_NOT_EMPTY(), IS_LENGTH(128, 0)]

    return [
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


def get_from_fields_report_survey_stage2(db: DAL, auth: Auth, article: Article):
    if auth.has_membership(role="manager") or auth.has_membership(role="recommender"):
        dbset = db((db.t_articles.user_id == article.user_id) & (db.t_articles.art_stage_1_id == None) & (db.t_articles.status.belongs("Recommended", "Recommended-private")) | (db.t_articles.id == article.art_stage_1_id))
    else:
        dbset = db((db.t_articles.user_id == auth.user_id) & (db.t_articles.user_id == article.user_id) & (db.t_articles.art_stage_1_id == None) & (db.t_articles.status.belongs("Recommended", "Recommended-private")) | (db.t_articles.id == article.art_stage_1_id))

    db.t_report_survey.temp_art_stage_1_id.requires = IS_IN_DB(
            dbset, "t_articles.id", 'Stage 2 of "%(title)s"'
        )
    db.t_report_survey.tracked_changes_url.requires = IS_URL(mode='generic',allowed_schemes=['http', 'https'],prepend_scheme='https')

    # TODO: remove the following constraints, they are copy/pasted from db.py
    db.t_report_survey.q26.requires = IS_IN_SET(
        (
            "YES - All data are contained in manuscript",
            "YES - Enter URL of the repository containing the data, ensuring that it contains sufficient README documentation to explain file definitions, file structures, and variable names (e.g. using a codebook)",
            "NO - Please state the ethical or legal reasons why study data are not publicly archived and explain how the data supporting the reported results can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement.",
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
    db.t_report_survey.q30.requires = IS_URL(mode='generic',allowed_schemes=['http', 'https'],prepend_scheme='https')
    db.t_report_survey.q30_details.requires = [IS_NOT_EMPTY(), IS_LENGTH(256, 0)]
    db.t_report_survey.q31.requires = IS_IN_SET(("N/A - NOT A PROGRAMMATIC RR", "CONFIRM",))

    return [
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

########################################################################################################################
def checklist_validation(form):
    if form.vars.results_based_on_data == "All or part of the results presented in this preprint are based on data" and form.vars.data_doi == []:
        form.errors.data_doi = "Provide the web address(es) to the data used"
    if form.vars.scripts_used_for_result == "Scripts were used to obtain or analyze the results" and form.vars.scripts_doi == []:
        form.errors.scripts_doi = "Provide the web address(es) to the scripts used"
    if form.vars.codes_used_in_study == "Codes have been used in this study" and form.vars.codes_doi == []:
        form.errors.codes_doi = "Provide the web address(es) to the code used"
        
