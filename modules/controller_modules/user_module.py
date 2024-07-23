# -*- coding: utf-8 -*-
from typing import Any, List
from app_modules import common_tools

from gluon import current

from app_modules.helper import *

from app_modules import common_small_html
from models.article import ArticleStatus
from models.suggested_recommender import SuggestedRecommender

from app_modules.common_tools import URL

pciRRactivated = myconf.get("config.registered_reports", default=False)
######################################################################################################################################################################
def mk_suggested_recommenders_user_button(row: Any):
    auth = current.auth
    butts: List[Any] = []
    suggested_recommender_txt: List[Any] = []
    # exclude = [str(auth.user_id)]
    exclude_list: List[int] = [auth.user_id]
    suggested_recommenders = SuggestedRecommender.get_suggested_recommender_by_article(row["t_articles.id"])
    if suggested_recommenders:
        for suggested_recommender in suggested_recommenders:
            if not suggested_recommender.suggested_recommender_id:
                continue

            exclude_list.append(suggested_recommender.suggested_recommender_id)
            if suggested_recommender.declined:
                suggested_recommender_txt.append(common_small_html.mkUser(suggested_recommender.suggested_recommender_id) + I(XML("&nbsp;declined")) + BR())
            else:
                suggested_recommender_txt.append(common_small_html.mkUser(suggested_recommender.suggested_recommender_id) + BR())
    if len(suggested_recommender_txt) > 0:
        butts += suggested_recommender_txt
    if row["t_articles.status"] in (ArticleStatus.PENDING.value, ArticleStatus.AWAITING_CONSIDERATION.value):
        vars = dict(articleId=row["t_articles.id"], exclude=exclude_list)
        butts.append(A(current.T("Add / Remove"), _class="btn btn-default pci-submitter", _href=common_tools.URL(c="user", f="add_suggested_recommender", vars=vars, user_signature=True)))
    return DIV(butts, _class="pci-w200Cell")


######################################################################################################################################################################
# From common.py
######################################################################################################################################################################
def mk_suggest_user_article_to_button(row: ..., articleId: int, excludeList: List[int], vars: ...):
    db = current.db
    # if this recommender is a coauthor, then return empty
    art = db(db.t_articles.id == articleId).select().last()
    if art.manager_authors:
        m_ids = art.manager_authors.split(',')
        if str(row['auth_user']['id']) in m_ids:
            return ''

    vars["recommenderId"] = row.auth_user["id"]
    _class = "buttontext btn btn-default pci-submitter"
    _btn_label = "Suggest as Recommender"
    if pciRRactivated:
        _class = "buttontext btn btn-success pci-submitter"
        _btn_label = "Suggest"

    anchor = A(
        SPAN(current.T(_btn_label), _class=_class),
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
def mk_exclude_recommender_button(row: ..., articleId :int, excludeList: List[int], vars: ...):
    vars["recommenderId"] = row.auth_user["id"]
    anchor = A(
        SPAN(current.T("Exclude"), _class="buttontext btn btn-warning pci-submitter"),
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
def mkRecommendation4ReviewFormat(row):
    db = current.db
    recomm = db(db.t_recommendations.id == row.recommendation_id).select(db.t_recommendations.id, db.t_recommendations.recommender_id).last()
    anchor = SPAN(common_small_html.mkUserWithMail(recomm.recommender_id))
    return anchor


######################################################################################################################################################################
def do_suggest_article_to(articleId, recommenderId):
    db = current.db
    db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)

######################################################################################################################################################################
def do_exclude_article_from(articleId, recommenderId):
    db = current.db
    db.t_excluded_recommenders.update_or_insert(excluded_recommender_id=recommenderId, article_id=articleId)

######################################################################################################################################################################
def getRecommender(row):
    db = current.db
    recomm = (
        db(db.t_recommendations.article_id == row["t_articles.id"]).select(db.t_recommendations.id, db.t_recommendations.recommender_id, orderby=db.t_recommendations.id).last()
    )
    if recomm and recomm.recommender_id:
        resu = SPAN(common_small_html.mkUser(recomm.recommender_id))
        corecommenders = db(db.t_press_reviews.recommendation_id == recomm.id).select(db.t_press_reviews.contributor_id)
        if len(corecommenders) > 0:
            resu.append(BR())
            resu.append(B(current.T("Co-recommenders:")))
            resu.append(BR())
            for corecommender in corecommenders:
                resu.append(SPAN(common_small_html.mkUser(corecommender.contributor_id)) + BR())
        return DIV(resu, _class="pci-w200Cell")
    else:
        return ""

######################################################################################################################################################################
def getReviewers(recomm):
    db = current.db
    revList = []
    latestRound = db((db.t_recommendations.article_id == recomm.article_id)).select(
            db.t_recommendations.id, orderby=db.t_recommendations.id).last()
    reviewersList = db((db.t_reviews.recommendation_id == latestRound.id)).select(db.t_reviews.reviewer_id)
    for i in reviewersList:
        revList.append(i.reviewer_id)
    return revList

######################################################################################################################################################################
def getAllRecommenders():
    db = current.db
    recommList = []
    recomm_query = db((db.auth_membership.group_id == 1)).select(db.auth_membership.user_id)
    for i in recomm_query:
        recommList.append(i.user_id)
    return recommList
