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
def getPCiRRinvitationTexts(article, new_stage=False):
    report_survey = article.t_report_survey.select().last()

    stage1_art = current.db.t_articles[article.art_stage_1_id]
    if stage1_art and new_stage:
        article = stage1_art

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
            ) if not new_stage else current.T("The original Stage 1 manuscript was submitted via the programmatic track, in which one Stage 1 protocol is expected to lead to multiple Stage 2 outputs. The current Stage 2 submission is one such expected output. For this reason, the tracked-changes version of the Stage 2 manuscript documents changes in text for this expected output only. Sections of text reserved for other expected outputs are likely to be omitted without track changes because these will (or have already) appeared within at least one other Stage 2 output.")
        if report_survey.q22 == "YES - ACCEPT SIGNED REVIEWS ONLY":
            signedreview_invitation_text = SPAN(
                current.T("The current submission is being submitted via a route in which PCI RR considers evaluations only from reviewers who sign their reviews. "),
                "<b>Therefore, please accept this review request only if you are willing to sign your review.</b>",
                current.T(
                    " Signing your review means the authors will learn your identity, regardless of whether your review is positive or negative. In the event of a final positive recommendation from PCI RR, your signed review will be published on the PCI RR website, but in the event of a negative recommendation (rejection), your signed review will not be published."
                ),
            ) if not new_stage else current.T("As at Stage 1, the authors have submitted via a track in which PCI RR considers evaluations only from reviewers who sign their reviews, so please only accept the review assignment if you have happy to sign your Stage 2 review. Signing your review means the authors will learn your identity, regardless of whether your review is positive or negative. In the event of a final positive recommendation from PCI RR, your signed review will be published on the PCI RR website, but in the event of a negative recommendation (rejection), your signed Stage 2 review will not be published.")

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
        review_due_date = review_start_date + timedelta(days=7)

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
#         mail_vars = dict(
#             articleTitle=art.title,
#             articleAuthors=mkAuthors(article),
#             articleDoi=common_small_html.mkDOI(article.doi),
#             articlePrePost="postprint" if art.already_published else "preprint",
#         )

#         return mail_vars
def getPCiRRrecommendationText(db, article):
    recommendation_text = ""
    if article.status == "Recommended":
        href=URL(c="articles", f="rec", vars=dict(id=article.id), scheme=scheme, host=host, port=port)
        recommendation_text = SPAN (
            current.T("You can also find the complete, public review history of the Stage 1 manuscript "), f'<a href="{href}" ><b>here on the PCI RR website.</b></a>', 
        )
    return recommendation_text


def getPCiRRstageVars(article):
    if article.art_stage_1_id is None:
        return {}

    stage1_art = current.db.t_articles[article.art_stage_1_id]
    report_survey = article.t_report_survey.select().last()

    mail_vars = {}
    mail_vars["Stage1_registeredURL"] = report_survey.q30
    mail_vars["Stage2_Stage1recommendationtext"] = getPCiRRrecommendationText(current.db, stage1_art)
    mail_vars["Stage2vsStage1_trackedchangesURL"] = report_survey.tracked_changes_url

    return mail_vars


def getRRInvitiationVars(db, article, new_stage):
    rr_vars = dict()
    rr_vars.update(getPCiRRstageVars(article))

    pci_rr_vars = getPCiRRinvitationTexts(article, new_stage)
    programmaticRR_invitation_text = pci_rr_vars["programmaticRR_invitation_text"]
    signedreview_invitation_text = pci_rr_vars["signedreview_invitation_text"]

    sched_sub_vars = getPCiRRScheduledSubmissionsVars(article)
    scheduledSubmissionDate = sched_sub_vars["scheduledSubmissionDate"]
    scheduledSubmissionLatestReviewStartDate = sched_sub_vars["scheduledSubmissionLatestReviewStartDate"]
    scheduledReviewDueDate = sched_sub_vars["scheduledReviewDueDate"]
    snapshotUrl = sched_sub_vars["snapshotUrl"]

    rr_vars["programmaticRR_invitation_text"] = programmaticRR_invitation_text
    rr_vars["signedreview_invitation_text"] = signedreview_invitation_text
    rr_vars["scheduledSubmissionDate"] = scheduledSubmissionDate
    rr_vars["scheduledSubmissionLatestReviewStartDate"] = scheduledSubmissionLatestReviewStartDate
    rr_vars["scheduledReviewDueDate"] = scheduledReviewDueDate
    rr_vars["snapshotUrl"] = snapshotUrl

    return rr_vars
