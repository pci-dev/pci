from re import match

from gluon.html import *
from gluon.sqlhtml import SQLFORM
from gluon import current

from copy import deepcopy

######################################################################################################################################################################
# New common modules
def searchByThematic(auth, db, myVars, allowBlank=True):
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

    return FORM(
        DIV(
            DIV(
                INPUT(_placeholder=current.T("Search"), _name="qyKeywords", value=keywords, keepvalues=True, _class="form-control pci2-search-input"),
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
        _class="pci2-search-form",
    )
