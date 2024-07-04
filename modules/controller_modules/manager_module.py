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
from models.article import Article

myconf = AppConfig(reload=True)


csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
not_considered_delay_in_days = myconf.get("config.unconsider_limit_days", default=20)

######################################################################################################################################################################
## Manager Modules
######################################################################################################################################################################
def mkSuggestedRecommendersManagerButton(row: Article, whatNext: str):
    db, auth = current.db, current.auth

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
def mkLastRecommendation(articleId):
    db = current.db
    lastRecomm = db.get_last_recomm(articleId)
    if lastRecomm:
        return DIV(common_small_html.md_to_html(lastRecomm.recommendation_title) or "", _class="pci-w200Cell")
    else:
        return ""


######################################################################################################################################################################
def mkViewEditRecommendationsManagerButton(row):
    return A(
        SPAN(current.T("View / Edit"), _class="buttontext btn btn-default pci-button"),
        _href=URL(c="manager", f="recommendations", vars=dict(articleId=row.article_id)),
        _class="button",
        _title=current.T("View and/or edit article"),
    )
