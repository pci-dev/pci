# -*- coding: utf-8 -*-

from gluon import current
from gluon.tools import Auth
from gluon.html import *
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
import requests
import datetime

myconf = AppConfig(reload=True)
description = myconf.take("app.description")
appname = myconf.take("app.name")
shortname = myconf.take("app.name")
longname = myconf.take("app.longname")
contact = myconf.take("contacts.managers")
siteUrl = URL(c="default", f="index", scheme=myconf.take("alerts.scheme"), host=myconf.take("alerts.host"), port=myconf.take("alerts.port"))
issn = "set in models/db.py"

######################################################################################################################################################################
def getHelp(request, auth, db, myHashtag, myLanguage="default"):
    r0 = []
    c = ""
    query = (db.help_texts.hashtag == myHashtag) & (db.help_texts.lang == myLanguage)
    h = db(query).select().first()
    if h:
        i = h.id
        c = replaceMailVars(h.contents or "", globals())
        # try:
        #     c = (h.contents or "") % globals()
        #     c = (h.contents or "") % globals()
        # except:
        #     c = h.contents or ""
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

    return DIV(DIV(r0, _class="pci-help-buttons"), DIV(WIKI(c, safe_mode=False), _class="pci-helptext", _style="display:none;",), _class="pci-helper",)


######################################################################################################################################################################
def getText(request, auth, db, myHashtag, myLanguage="default", maxWidth="1200"):
    r0 = ""
    c = ""
    if not isinstance(db, str):
        query = (db.help_texts.hashtag == myHashtag) & (db.help_texts.lang == myLanguage)
        h = db(query).select().first()
        if h:
            i = h.id
            c = replaceMailVars(h.contents or "", globals())
            # try:
            #     c = (h.contents or "") % globals()
            #     c = (h.contents or "") % globals()
            # except:
            #     c = h.contents or ""
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
            DIV(WIKI(c, safe_mode=False), _class="pci-infotext", _style="max-width:" + maxWidth + "px"),
            _class="pci-infotextbox",
        )


######################################################################################################################################################################
def getTitle(request, auth, db, myHashtag, myLanguage="default"):
    r0 = ""
    c = ""
    query = (db.help_texts.hashtag == myHashtag) & (db.help_texts.lang == myLanguage)
    h = db(query).select().first()
    if h:
        i = h.id
        c = replaceMailVars(h.contents or "", globals())
        # try:
        #     c = (h.contents or "") % globals()
        #     c = (h.contents or "") % globals()
        # except:
        #     c = h.contents or ""
    else:
        i = db.help_texts.insert(hashtag=myHashtag, lang=myLanguage)

    if auth.has_membership(role="administrator") or auth.has_membership(role="developer"):
        r0 = A(
            current.T("edit title"), _href=URL(c="custom_help_text", f="help_texts", args=["edit", "help_texts", i], user_signature=True), _class="pci-text-button-edit pci-admin"
        )

    if c != "" and (auth.has_membership(role="administrator") or auth.has_membership(role="developer")):
        return DIV(DIV(r0, _class="pci-text-buttons"), DIV(WIKI(c, safe_mode=False), _class="pci-text-title"), _class="pci-infotextbox",)
    else:
        return DIV(DIV(r0, _class="pci-text-buttons"), DIV(WIKI(c, safe_mode=False), _class="pci-text-title pci-text-buttons-no-margin"), _class="pci-infotextbox",)


######################################################################################################################################################################
def replaceMailVars(text, mail_vars):
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


def is_recommender(auth, request):
    return (
        auth.has_membership(role="recommender") and
        str(auth.user_id) == request.vars["recommender"]
    )

def is_co_recommender(auth, db, recommId):
    return db((db.t_press_reviews.recommendation_id == recommId) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0


def query_semantic_api(authors: list, recommenders: list):
    grid = []
    

    def get_author_ids(name):
        """Function to get author IDs from Semantic Scholar API"""
        url = f'https://api.semanticscholar.org/graph/v1/author/search?query={name.replace(" ", "+")}'
        response = requests.get(url)
        if response.ok:
            result = response.json()
            if result.get("data"):
                return [{"authorId": author["authorId"], "name": author["name"]} for author in result["data"]]
        return []

    def get_author_papers(author_id):
        """Function to get papers of an author from Semantic Scholar API"""
        url = f'https://api.semanticscholar.org/graph/v1/author/{author_id}?fields=papers.year,papers.authors'
        response = requests.get(url)
        if response.ok:
            result = response.json()
            papers = result.get("papers")
            if papers:
                current_year = datetime.datetime.now().year
                return [paper for paper in papers if paper.get("year") is not None and current_year - paper["year"] <= 4]
        return []

# Get author IDs of suggested recommenders
    recommender_ids = []
    for recommender in recommenders:
        ids = get_author_ids(recommender)
        recommender_ids.extend(ids)

    # Get papers of suggested recommenders published in the last 4 years
    recommender_papers = {}
    for recommender_id in recommender_ids:
        papers = get_author_papers(recommender_id["authorId"])
        if papers:
            recommender_papers[recommender_id["authorId"]] = papers

    # Check if any of the authors have co-published with the suggested recommenders
    for author in authors:
        nome = f'Author {author}'
        author_ids = []
        ids = get_author_ids(author)
        author_ids.extend(ids)
        found = False
        for recommender_id in recommender_ids:
            for paper in recommender_papers.get(recommender_id["authorId"], []):
                co_authors = [co_author["authorId"] for co_author in paper["authors"]]
                for author_id in author_ids:
                    for co_author_id in co_authors:
                        if author_id["authorId"] == co_author_id:
                            found = True
                            paper_url = f'https://api.semanticscholar.org/{paper["paperId"]}'
                            grid.append(DIV(SPAN(f'{author_id["name"]} has co-published with suggested recommender {recommender_id["name"]} on this ', A('paper', _href=paper_url), f' published in {paper["year"]}')))
                            grid.append(BR())
                            break
        if not found:
            grid.append(DIV(SPAN(nome, BR(), f'{author_id["name"]} has not co-published with any suggested recommenders')))
            grid.append(BR())
    return grid

