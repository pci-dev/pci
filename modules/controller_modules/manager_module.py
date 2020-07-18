# -*- coding: utf-8 -*-

import re
import copy
import tempfile
from datetime import datetime, timedelta
import glob
import os

from gluon import current

from app_modules import common_small_html

# sudo pip install tweepy
# import tweepy

import codecs

# import html2text
from gluon.contrib.markdown import WIKI

from app_modules.helper import *

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)

# frequently used constants
from app_modules.emailing import MAIL_HTML_LAYOUT, MAIL_DELAY

csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get("config.trgm_limit") or 0.4
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
not_considered_delay_in_days = myconf.get("config.unconsider_limit_days", default=20)


######################################################################################################################################################################
## Manager Modules
######################################################################################################################################################################
def mkRecommenderButton(row, auth, db):
    last_recomm = db(db.t_recommendations.article_id == row.id).select(orderby=db.t_recommendations.id).last()
    if last_recomm:
        resu = SPAN(common_small_html.mkUserWithMail(auth, db, last_recomm.recommender_id))
        corecommenders = db(db.t_press_reviews.recommendation_id == last_recomm.id).select(db.t_press_reviews.contributor_id)
        if len(corecommenders) > 0:
            resu.append(BR())
            resu.append(B(current.T("Co-recommenders:")))
            resu.append(BR())
            for corecommender in corecommenders:
                resu.append(SPAN(common_small_html.mkUserWithMail(auth, db, corecommender.contributor_id)) + BR())
        return DIV(resu, _class="pci-w200Cell")
    else:
        return ""


def mkSuggestedRecommendersManagerButton(row, whatNext, auth, db):
    if row.already_published:
        return ""

    exclude = [str(auth.user_id)]
    # sr = db.v_suggested_recommenders[row.id].suggested_recommenders
    suggRecomms = db(db.t_suggested_recommenders.article_id == row.id).select()
    for sr in suggRecomms:
        exclude.append(str(sr.suggested_recommender_id))
        
    myVars = dict(articleId=row.id, whatNext=whatNext)
    if len(exclude) > 0:
        myVars["exclude"] = ",".join(exclude)
    
    button = None
    if row.status in ("Awaiting consideration", "Pending"):
        button = A(
            I(_class="glyphicon glyphicon-user"),
            current.T("Manage recommenders"),
            _class="pci2-flex-row pci2-align-items-center pci2-tool-link pci2-yellow-link",
            _href=URL(c="manager", f="suggested_recommenders", vars=myVars),
        )

    return button


######################################################################################################################################################################
# From common.py
######################################################################################################################################################################
def mkLastRecommendation(auth, db, articleId):
    lastRecomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.id).last()
    if lastRecomm:
        return DIV(lastRecomm.recommendation_title or "", _class="pci-w200Cell")
    else:
        return ""


######################################################################################################################################################################
def mkViewEditRecommendationsManagerButton(auth, db, row):
    return A(
        SPAN(current.T("Check & Edit"), _class="buttontext btn btn-default pci-button"),
        _href=URL(c="manager", f="recommendations", vars=dict(articleId=row.article_id)),
        _class="button",
        _title=current.T("View and/or edit article"),
    )
