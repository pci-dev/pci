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
scheme = myconf.take("alerts.scheme")
host = myconf.take("alerts.host")
port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))


parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

######################################################################################################################################################################
# Mailing parts
######################################################################################################################################################################


def getReviewHTML(rewiewId):
    db, auth = current.db, current.auth
    review = db.t_reviews[rewiewId]

    reviewAuthorAndDate = SPAN(
        current.T("Reviewed by"),
        " ",
        common_small_html.mkUser(review.reviewer_id, linked=False),
        (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review.last_change else ""),
    )

    pdfLink = ""
    if review.review_pdf:
        pdfLink = A(
            current.T("Download the review (PDF file)"),
            _href=URL("default", "download", args=review.review_pdf, scheme=scheme, host=host, port=port),
            _style="font-weight: bold; margin-bottom: 5px; display:block",
        )

    return DIV(
        H4(reviewAuthorAndDate, _style="margin-top: 10px; font-weight: bold; color: #555; margin-bottom: 10px"),
        DIV(
            WIKI((review.review if review.review else ""), safe_mode=False),
            pdfLink,
            _style="border-left: 1px solid #e0e0e0; padding: 5px 15px; margin-bottom: 10px;"
        )
    )


def getAuthorsReplyLinks(recommId):
    db, auth = current.db, current.auth
    recomm = db.t_recommendations[recommId]
    
    authorsReplyPdfLink = ""
    if recomm.reply_pdf:
        authorsReplyPdfLink = A(
            current.T("Download author's reply (PDF file)"),
            _href=URL("default", "download", args=recomm.reply_pdf, scheme=scheme, host=host, port=port),
            _style="font-weight: bold; margin-bottom: 5px; display:block",
        )

    authorsReplyTrackChangeFileLink = ""
    if recomm.track_change:
        authorsReplyTrackChangeFileLink = A(
            current.T("Download tracked changes file"),
            _href=URL("default", "download", args=recomm.track_change, scheme=scheme, host=host, port=port),
            _style="font-weight: bold; margin-bottom: 5px; display:block",
        )

    return authorsReplyPdfLink, authorsReplyTrackChangeFileLink


def getAuthorsReplyHTML(recommId):
    db, auth = current.db, current.auth
    authorsReplyPdfLink, authorsReplyTrackChangeFileLink = getAuthorsReplyLinks(recommId)
    recomm = db.t_recommendations[recommId]

    return DIV(
        H4(current.T("Author's Reply"), _style="margin-top: 10px; font-weight: bold; color: #555; margin-bottom: 10px"),
        DIV(
            WIKI(recomm.reply or "", safe_mode=False),
            authorsReplyPdfLink,
            authorsReplyTrackChangeFileLink,
            _style="border-left: 1px solid #e0e0e0; padding: 5px 15px; margin-bottom: 10px;"
        )
    )