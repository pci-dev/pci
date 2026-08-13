# -*- coding: utf-8 -*-

import re
from typing import Any, Dict, List, Optional
from gluon import current
from gluon.html import *
from gluon.contrib.markdown import WIKI # type: ignore
from gluon.contrib.appconfig import AppConfig # type: ignore
from models.recommendation import Recommendation
from models.group import Role
from app_modules.httpClient import HttpClient
import datetime

from app_modules.common_tools import URL

myconf = AppConfig(reload=True)
description = myconf.take("app.description")
appname = myconf.take("app.name")
shortname = myconf.take("app.name")
longname = myconf.take("app.longname")
contact = myconf.take("contacts.managers")
siteUrl = URL(c="default", f="index", scheme=myconf.take("alerts.scheme"), host=myconf.take("alerts.host"), port=myconf.take("alerts.port"))
issn = "set in models/db.py"

######################################################################################################################################################################
def getHelp(myHashtag: str, myLanguage: str = "default"):
    auth, db = current.auth, current.db
    r0: List[A] = []
    c = ""
    query = (db.help_texts.hashtag == myHashtag) & (db.help_texts.lang == myLanguage)
    h = db(query).select().first()
    if h:
        i = h.id
        c = replaceMailVars(h.contents or "", globals())
    else:
        i = db.help_texts.insert(hashtag=myHashtag, lang=myLanguage)

    r0 += [
        A(
            SPAN(current.T("show/hide help")),
            _onclick="""jQuery(function(){ if ($.cookie('PCiHideHelp') == 'On') {
												$('DIV.pci-helptext').show(); 
												$.cookie('PCiHideHelp', 'Off', {expires:365, path:'/'});
											} else {
												$('DIV.pci-helptext').hide(); 
												$.cookie('PCiHideHelp', 'On', {expires:365, path:'/'});
											}
									})""",
            _class="pci-help-button",
        ),
    ]

    if auth.has_membership(role="administrator") or auth.has_membership(role="developer"):
        r0 += [A(SPAN(current.T("edit help")), _href=URL(c="custom_help_text", f="help_texts", args=["edit", "help_texts", i], user_signature=True), _class="pci-help-button-edit")]

    return DIV(DIV(r0, _class="pci-help-buttons"), DIV(WIKI(c, safe_mode=""), _class="pci-helptext", _style="display:none;",), _class="pci-helper",)


######################################################################################################################################################################
def getText(myHashtag: str, myLanguage: str = "default", maxWidth: str = "1200"):
    auth, db = current.auth, current.db
    r0 = ""
    c = ""
    if not isinstance(db, str):
        query = (db.help_texts.hashtag == myHashtag) & (db.help_texts.lang == myLanguage)
        h = db(query).select().first()
        if h:
            i = h.id
            c = replaceMailVars(h.contents or "", globals())
        else:
            i = db.help_texts.insert(hashtag=myHashtag, lang=myLanguage)

        if auth.has_membership(role="administrator") or auth.has_membership(role="developer"):
            r0 = A(
                current.T("edit text"),
                _href=URL(c="custom_help_text", f="help_texts", args=["edit", "help_texts", i], user_signature=True),
                _class="pci-text-button-edit pci-admin",
            )

        return DIV(
            DIV(r0, _class="pci-text-buttons", _style="max-width:" + maxWidth + "px"),
            DIV(WIKI(c, safe_mode=""), _class="pci-infotext", _style="max-width:" + maxWidth + "px"),
            _class="pci-infotextbox",
        )


######################################################################################################################################################################
def getTitle(myHashtag: str, myLanguage: str = "default"):
    auth, db = current.auth, current.db

    r0 = ""
    c = ""
    query = (db.help_texts.hashtag == myHashtag) & (db.help_texts.lang == myLanguage)
    h = db(query).select().first()
    if h:
        i = h.id
        c = replaceMailVars(h.contents or "", globals())
    else:
        i = db.help_texts.insert(hashtag=myHashtag, lang=myLanguage)

    if auth.has_membership(role="administrator") or auth.has_membership(role="developer"):
        r0 = A(
            current.T("edit title"), _href=URL(c="custom_help_text", f="help_texts", args=["edit", "help_texts", i], user_signature=True), _class="pci-text-button-edit pci-admin"
        )

    if c != "" and (auth.has_membership(role="administrator") or auth.has_membership(role="developer")):
        return DIV(DIV(r0, _class="pci-text-buttons"), DIV(WIKI(c, safe_mode=""), _class="pci-text-title"), _class="pci-infotextbox",)
    else:
        return DIV(DIV(r0, _class="pci-text-buttons"), DIV(WIKI(c, safe_mode=""), _class="pci-text-title pci-text-buttons-no-margin"), _class="pci-infotextbox",)


######################################################################################################################################################################
def replaceMailVars(text: str, mail_vars: Dict[str, Any]):
    mail_vars_list = mail_vars.keys()

    for var in mail_vars_list:
        if text.find("{{" + var + "}}") > -1:
            if isinstance(mail_vars[var], str):
                replacement_var = mail_vars[var]
            elif isinstance(mail_vars[var], int):
                replacement_var = str(mail_vars[var])
            else:
                try:
                    replacement_var = mail_vars[var].flatten()
                except:
                    replacement_var = str(mail_vars[var])

            text = text.replace("{{" + var + "}}", replacement_var)

    return text

######################################################################################################################################################################
def is_recommender():
    auth, request = current.auth, current.request
    
    return (
        auth.has_membership(role="recommender") and
        str(auth.user_id) == request.vars["recommender"]
    )

######################################################################################################################################################################
def is_co_recommender(recommendation_id: int, user_id: Optional[int] = None):
    db = current.db
    if user_id is None:
        user_id = current.auth.user_id

    return bool(db((db.t_press_reviews.recommendation_id == recommendation_id) & (db.t_press_reviews.contributor_id == user_id)).count() > 0)


def user_is_in_recommender_team(article_id: int, user_id: Optional[int] = None):
    if user_id is None:
        user_id = current.auth.user_id
        
    if not current.auth.has_membership(Role.RECOMMENDER.value, user_id=user_id):
        return False
    
    recommendations = Recommendation.get_by_article_id(article_id)
    for recommendation in recommendations:
        if recommendation.recommender_id == user_id or is_co_recommender(recommendation.id, user_id):
            return True
    
    return False


######################################################################################################################################################################
def extract_name_from_author(s: str):
    # Split pattern to handle most cases
    split_pattern = re.compile(r'\b\s*and\s*\b|;\s*|,\s*(?=[A-Z])|,\s+and\s+|&')
    # Check and handle "John, Doe and Jane, Doe and Unknown, User" format
    if re.match(r'(\w+), (\w+) and', s):
        s = re.sub(r'(\w+), (\w+)', r'\1 \2', s)
    # Check and handle "John, D"  format
    elif re.match(r'(\w+),\s(\w)\b', s):
        s = re.sub(r'(\w+),\s(\w)\b', r'\1 \2', s)
        # Check and handle "John, Doe" format
    elif re.match(r'(\w+),\s(\w+)(?:;\s)?', s):
        s = re.sub(r'(\w+),\s(\w+)', r'\1 \2', s)

    return [str(part.strip()) for part in split_pattern.split(s) if part.strip()]


def extract_name_without_email(s: str):
    s = s.strip()
    if re.match(r'(([\w\-\.]+ )*[\w\-]+)+', s):
        match = re.search(r'([\w_\-\.]+ (\w\. )*[\w_\-\.]+)+', s)
        if match:
            s = match.group()
    return s


######################################################################################################################################################################
def format_keywords_for_google_scholar(input_string: str):
    # Split the string by commas, semicolons, or 'and'
    keywords = re.split(r',|;| and ', input_string)
    
    formatted_keywords = ['"' + keyword.strip().replace(' ', '+') + '"' for keyword in keywords]
    return '+AND+'.join(formatted_keywords)
