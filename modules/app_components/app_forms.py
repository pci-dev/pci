from re import match
from copy import deepcopy

from gluon.html import *
from gluon.sqlhtml import SQLFORM
from gluon import current

from app_modules import common_small_html

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
        actionForm = URL(c="articles", f="recommended_articles")
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
def getSendMessageForm(declineKey):
    return FORM(
        DIV(
            P("We welcome your suggestions on who might be a suitable reviewer for this article. Please enter the names and email of suggested reviewers here (one line per reviewer):")
        ),
        DIV(
            TEXTAREA(_name="suggested_reviewers_text", keepvalues=True, _class="form-control", _style="resize: none")
        ),
        DIV(
            BUTTON(current.T("Send these suggestions to the recommender"), _type="submit", _class="btn btn-success"),
            BUTTON(current.T("Sorry I have no suggestions"), _type="submit", _name="noluck", _value="1", _class="btn btn-default"),
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
        mail.update_record()

        content_saved = True
    except Exception as e:
        content_saved = False
        form.error_msg = str(e)

    return content_saved


#########################################################################
from pydal import Field
from gluon.validators import IS_NOT_EMPTY

def article_add_mandatory_checkboxes(form):
    checkboxes = {
        "guide_read":
        "I read the guide for authors.",

        "approvals_obtained":
        "If applicable, all the necessary approvals have been obtained before submission. (or not applicable)",

        "human_subject_consent_obtained":
        "If applicable, a statement that informed consent was obtained, for experimentation with human subjects, is in the manuscript. (or not applicable)",

        "lines_numbered":
        "Lines are numbered.",

        "funding_sources_listed":
        "All sources of funding are listed (or absence of funding is indicated) in a separate funding section or in the cover letter.",

        "conflicts_of_interest_indicated":
        "Non-financial conflicts of interest are indicated in the “Conflict of interest disclosure” section or in the cover letter.",

        "no_financial_conflict_of_interest":
        "The authors declare that they have no financial conflict of interest with the content of the manuscript.",
    }
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
