# -*- coding: utf-8 -*-

import os
import time
from re import sub, match

from datetime import datetime, timedelta

# from copy import deepcopy
from dateutil.relativedelta import *
import traceback
from pprint import pprint

from gluon import current
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail

from gluon.custom_import import track_changes

track_changes(True)
import socket

from uuid import uuid4
from contextlib import closing
import shutil

from app_modules import common_tools
from app_modules import common_small_html

myconf = AppConfig(reload=True)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
scheme = myconf.take("alerts.scheme")
host = myconf.take("alerts.host")
port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

######################################################################################################################################################################
# Mailing parts
######################################################################################################################################################################

######################################################################################################################################################################
def getCoRecommendersMails(db, recommId):
    contribsQy = db(db.t_press_reviews.recommendation_id == recommId).select()

    result = []
    for contrib in contribsQy:
        result.append(db.auth_user[contrib.contributor_id]["email"])

    return result


######################################################################################################################################################################
def getManagersMails(db):
    managers = db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "manager")).select(db.auth_user.ALL)

    result = []
    for manager in managers:
        result.append(manager.email)

    return result


# def getArticleVars(db, articleId=None, article=None, anonymousAuthors=False):
#     art = None
#     if article is not None:
#         art = article
#     if (art is None) and (articleId is not None):
#         art = db.t_articles[articleId]

#     if art is not None:
#         if article.anonymous_submission and anonymousAuthors:
#             articleAuthors = current.T("[undisclosed]")
#         else:
#             articleAuthors = article.authors

#         mail_vars = dict(
#             articleTitle=art.title,
#             articleAuthors=articleAuthors,
#             articleDoi=common_small_html.mkDOI(article.doi),
#             articlePrePost="postprint" if art.already_published else "preprint",
#         )

#         return mail_vars
    

