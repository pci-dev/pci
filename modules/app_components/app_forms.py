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

    return SQLFORM.widgets.string.widget(field, ('' if value is None else ','.join(value)))
