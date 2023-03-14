# -*- coding: utf-8 -*-

import re
import copy
import datetime

from gluon.contrib.markdown import WIKI

from app_modules.helper import *

from app_modules import common_small_html
pciRRactivated = myconf.get("config.registered_reports", default=False)
######################################################################################################################################################################
def mkSuggestedRecommendersUserButton(auth, db, row):
    butts = []
    suggRecomsTxt = []
    # exclude = [str(auth.user_id)]
    excludeList = [auth.user_id]
    suggRecomms = db(db.t_suggested_recommenders.article_id == row["t_articles.id"]).select()
    for sr in suggRecomms:
        # excludeList.append(str(sr.suggested_recommender_id))
        excludeList.append(sr.suggested_recommender_id)
        if sr.declined:
            suggRecomsTxt.append(common_small_html.mkUser(auth, db, sr.suggested_recommender_id) + I(XML("&nbsp;declined")) + BR())
        else:
            suggRecomsTxt.append(common_small_html.mkUser(auth, db, sr.suggested_recommender_id) + BR())
    if len(suggRecomsTxt) > 0:
        butts += suggRecomsTxt
    if row["t_articles.status"] in ("Pending", "Awaiting consideration"):
        myVars = dict(articleId=row["t_articles.id"], exclude=excludeList)
        butts.append(A(current.T("Add / Remove"), _class="btn btn-default pci-submitter", _href=URL(c="user", f="add_suggested_recommender", vars=myVars, user_signature=True)))
    return DIV(butts, _class="pci-w200Cell")


######################################################################################################################################################################
# From common.py
######################################################################################################################################################################
def mkSuggestUserArticleToButton(auth, db, row, articleId, excludeList, vars):
    vars["recommenderId"] = row.auth_user["id"]
    _class = "buttontext btn btn-default pci-submitter"
    if pciRRactivated:
        _class = "buttontext btn btn-success pci-submitter"
    anchor = A(
        SPAN(current.T("Suggest as recommender"), _class=_class),
        _href=URL(
            c="user_actions",
            f="suggest_article_to",
            vars=vars,
            user_signature=True,
        ),
        _class="button",
    )
    return anchor

######################################################################################################################################################################
def mkExcludeRecommenderButton(auth, db, row, articleId, excludeList, vars):
    vars["recommenderId"] = row.auth_user["id"]
    anchor = A(
        SPAN(current.T("Exclude recommender"), _class="buttontext btn btn-default pci-submitter"),
        _href=URL(
            c="user_actions",
            f="exclude_article_from",
            vars=vars,
            user_signature=True,
        ),
        _class="button",
    )
    return anchor

######################################################################################################################################################################
def mkRecommendation4ReviewFormat(auth, db, row):
    recomm = db(db.t_recommendations.id == row.recommendation_id).select(db.t_recommendations.id, db.t_recommendations.recommender_id).last()
    anchor = SPAN(common_small_html.mkUserWithMail(auth, db, recomm.recommender_id))
    return anchor


######################################################################################################################################################################
def do_suggest_article_to(auth, db, articleId, recommenderId):
    db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)

######################################################################################################################################################################
def do_exclude_article_from(auth, db, articleId, recommenderId):
    db.t_excluded_recommenders.update_or_insert(excluded_recommender_id=recommenderId, article_id=articleId)

######################################################################################################################################################################
def getRecommender(auth, db, row):
    recomm = (
        db(db.t_recommendations.article_id == row["t_articles.id"]).select(db.t_recommendations.id, db.t_recommendations.recommender_id, orderby=db.t_recommendations.id).last()
    )
    if recomm and recomm.recommender_id:
        resu = SPAN(common_small_html.mkUser(auth, db, recomm.recommender_id))
        corecommenders = db(db.t_press_reviews.recommendation_id == recomm.id).select(db.t_press_reviews.contributor_id)
        if len(corecommenders) > 0:
            resu.append(BR())
            resu.append(B(current.T("Co-recommenders:")))
            resu.append(BR())
            for corecommender in corecommenders:
                resu.append(SPAN(common_small_html.mkUser(auth, db, corecommender.contributor_id)) + BR())
        return DIV(resu, _class="pci-w200Cell")
    else:
        return ""

######################################################################################################################################################################
def getReviewers(recomm, db):
    revList = []
    latestRound = db((db.t_recommendations.article_id == recomm.article_id)).select(
            db.t_recommendations.id, orderby=db.t_recommendations.id).last()
    reviewersList = db((db.t_reviews.recommendation_id == latestRound.id)).select(db.t_reviews.reviewer_id)
    for i in reviewersList:
        revList.append(i.reviewer_id)
    return revList

######################################################################################################################################################################
def getAllRecommenders(db):
    recommList = []
    recomm_query = db((db.auth_membership.group_id == 1)).select(db.auth_membership.user_id)
    for i in recomm_query:
        recommList.append(i.user_id)
    return recommList
