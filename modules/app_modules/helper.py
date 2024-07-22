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
def _get_author_ids(data: Dict[str, str]) -> List[Dict[str, Any]]:
        """Function to get author IDs from Semantic Scholar API"""
        name = data["name"]
        url = f'https://api.semanticscholar.org/graph/v1/author/search?query={name.replace(" ", "+")}&fields=name,papers.authors,papers.year'
        http_client = HttpClient()
        response = http_client.get(url)
        current_year = datetime.datetime.now().year
        if response.ok:
            result = response.json() # type: ignore
            if result.get("data"):
                return [
                            {"authorId": author["authorId"],
                            "group": data["group"],
                            "name": author["name"],
                            "papers": [paper for paper in author["papers"] if paper.get("year") is not None and current_year - paper["year"] <= 4]
                            }
                            for author in result['data']
                        ]   
        return []

def query_semantic_api(authors: List[Dict[str, str]], recommenders: List[Dict[str, str]]):
    grid: List[Any] = []
    all_data: Dict[str, List[Any]] = {
        "author" : [],
        "invited reviewer": [],
        "recommender" : [],
        "suggested recommender" : [],
        "accepted reviewer": [],
        "suggested reviewer": [],
        "co-recommender": []
    }

    # Get  datas of authors and recommenders
    recommender_to_print = dict(group="None", name="None")
    for recommender in recommenders:
        recommender_to_print = recommender
        user_data = _get_author_ids(recommender)
        if len(user_data) > 0:
            all_data[recommender["group"]] += user_data
        else:
            grid.append(DIV(SPAN(f'Analysis not possible for {recommender["group"]} {recommender["name"]} (not found in semantic scholar database)')))

    recommender_data = all_data["accepted reviewer"] + all_data["invited reviewer"] + all_data["recommender"] + all_data["suggested recommender"] + all_data["co-recommender"]
    if len(recommender_data) == 0:
        return grid
    
    # Check if any of the authors have co-published with the suggested recommenders
    for author in authors:
        grid.append(BR())
        grid.append(DIV(SPAN(B(f'Author {author["name"]}'))))
        author_data: List[Dict[str, Any]] = []
        author_data.extend(_get_author_ids(author))
        found = False
        if len(author_data) == 0:
            grid.append(DIV(SPAN(f'Analysis not possible for {recommender_to_print["group"]} {recommender_to_print["name"]} (not found in semantic scholar database)')))
            continue

        author_id_to_print = dict(name="None")
        for data in recommender_data:
            co_authors = [(co_author["authorId"], paper) for paper in data["papers"] for co_author in paper["authors"]]
            for author_id in author_data:
                author_id_to_print = author_id
                for co_author_id, paper in co_authors:
                    if author_id ["authorId"] == co_author_id:
                        found = True
                        matched_paper = paper
                        author_url = A(author_id["name"], _href=f'https://www.semanticscholar.org/author/{author_id["authorId"]}', _target="_blank")
                        co_author_url = A(data["name"], _href=f'https://www.semanticscholar.org/author/{data["authorId"]}', _target="_blank")
                        paper_url = A('paper', _href=f'https://api.semanticscholar.org/{matched_paper["paperId"]}', _target="_blank")
                        grid.append(DIV(SPAN(author_url, f" has co-published with {data['group']} ", co_author_url, " on this ", paper_url, f" published in {matched_paper['year']}.")))
        if not found:
            grid.append(DIV(SPAN(f'{author_id_to_print["name"]} has no co-publication with anyone assigned to this article.')))

    return grid

######################################################################################################################################################################
def format_keywords_for_google_scholar(input_string: str):
    # Split the string by commas, semicolons, or 'and'
    keywords = re.split(r',|;| and ', input_string)
    
    formatted_keywords = ['"' + keyword.strip().replace(' ', '+') + '"' for keyword in keywords]
    return '+AND+'.join(formatted_keywords)
