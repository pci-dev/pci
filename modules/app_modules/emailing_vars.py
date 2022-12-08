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

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

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
def getAdminsMails(db):
    return getMails(db, "administrator")


def getManagersMails(db):
    return getMails(db, "manager")


def getMails(db, role):
    managers = db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == role)).select(db.auth_user.ALL)

    result = []
    for manager in managers:
        result.append(manager.email)

    return result


######################################################################################################################################################################
# PCI RR vars
######################################################################################################################################################################
def getPCiRRinvitationTexts(article):
    report_survey = article.t_report_survey.select().last()

    programmaticRR_invitation_text = ""
    signedreview_invitation_text = ""
    if report_survey is not None:
        if report_survey.q2 == "PROGRAMMATIC RR":
            # Gab: As it is editable template, I found no other way to display the link than hardcoding it.
            programmaticRR_invitation_text = SPAN(
                current.T("Please note that this submission is being submitted via the "),
                '<a href="https://rr.peercommunityin.org/help/guide_for_authors#h_52492857233251613309610581" >programmatic RR track</a>',
                current.T(
                    " in which one Stage 1 manuscript can propose a sufficient volume of work to justify multiple Stage 2 articles. A Stage 1 programmatic RR must prespecify which parts of the protocol will eventually produce separate Stage 2 articles, and as part of the Stage 1 review process, we ask reviewers to evaluate the validity and substantive contribution of each component. These prespecified boundaries are effectively treated as design elements; therefore, like any other design element, Stage 1 IPA will be conditional on authors adhering to the prespecified and approved article boundaries at Stage 2."
                ),
            )
        if report_survey.q22 == "YES - ACCEPT SIGNED REVIEWS ONLY":
            signedreview_invitation_text = SPAN(
                current.T("The current submission is being submitted via a route in which PCI RR considers evaluations only from reviewers who sign their reviews. "),
                "<b>Therefore, please accept this review request only if you are willing to sign your review.</b>",
                current.T(
                    " Signing your review means the authors will learn your identity, regardless of whether your review is positive or negative. In the event of a final positive recommendation from PCI RR, your signed review will be published on the PCI RR website, but in the event of a negative recommendation (rejection), your signed review will not be published."
                ),
            )

    return dict(programmaticRR_invitation_text=programmaticRR_invitation_text, signedreview_invitation_text=signedreview_invitation_text,)


######################################################################################################################################################################
def getPCiRRScheduledSubmissionsVars(article):
    scheduledSubmissionDate = ""
    scheduledSubmissionLatestReviewStartDate = ""
    scheduledReviewDueDate = ""
    snapshotUrl = ""

    report_survey = article.t_report_survey.select().last()

    if report_survey and report_survey.q10:
        submission_date = report_survey.q10 # article.scheduled_submission_date
        review_start_date = submission_date + timedelta(days=7)
        dow = review_start_date.weekday()
        five_working_days = 7 if dow < 5 else (7 + (7-dow))
        review_due_date = review_start_date + timedelta(days=five_working_days)

        scheduledSubmissionDate = submission_date.strftime(DEFAULT_DATE_FORMAT)
        scheduledSubmissionLatestReviewStartDate = review_start_date.strftime(DEFAULT_DATE_FORMAT)
        scheduledReviewDueDate = review_due_date.strftime(DEFAULT_DATE_FORMAT)

    if report_survey:
        snapshotUrl = report_survey.q1_1

    return dict(
        scheduledSubmissionDate=scheduledSubmissionDate,
        scheduledSubmissionLatestReviewStartDate=scheduledSubmissionLatestReviewStartDate,
        scheduledReviewDueDate=scheduledReviewDueDate,
        snapshotUrl=snapshotUrl,
    )


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
