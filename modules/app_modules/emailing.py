# -*- coding: utf-8 -*-

import os
import datetime
import time
from re import sub, match

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
from app_modules import old_common
from app_modules import emailing_tools
from app_modules import newsletter_module


myconf = AppConfig(reload=True)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)

MAIL_DELAY = 1.5  # in seconds

# common view for all emails
MAIL_HTML_LAYOUT = os.path.join(os.path.dirname(__file__), "../../views/mail", "mail.html")

######################################################################################################################################################################
# Mailing functions
######################################################################################################################################################################

######################################################################################################################################################################
# TEST MAIL (or "How to properly create an emailing function")
def send_test_mail(session, auth, db, userId):
    print("send_test_mail")
    # Get common variables :
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    # Set custom variables :
    mail_vars["destAddress"] = db.auth_user[userId]["email"]
    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, userId)
    mail_vars["linkTarget"] = URL(c="default", f="index", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

    # Insert mail in mail_queue :
    hashtag_template = "#TestMail"
    emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars)

    # Create report for session flash alerts :
    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    # Build reports :
    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Send email to the requester (if any)
def send_to_submitter(session, auth, db, articleId, newStatus):
    print("send_to_submitter")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    mail_vars["unconsider_limit_days"] = myconf.get("config.unconsider_limit_days", default=20)
    mail_vars["recomm_limit_days"] = myconf.get("config.recomm_limit_days", default=50)

    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        mail_vars["articleTitle"] = article.title

        recomm = db((db.t_recommendations.article_id == article.id)).select().last()
        recomm_id = None
        if recomm:
            recomm_id = recomm.id

        recommendation = None
        mail_vars["linkTarget"] = URL(c="user", f="my_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        # Define template depending on the article status changed
        if article.status == "Pending" and newStatus == "Awaiting consideration":
            if article.parallel_submission:
                hashtag_template = "#SubmitterParallelPreprintSubmitted"
            else:
                mail_vars["parallelText"] = ""
                if parallelSubmissionAllowed:
                    mail_vars["parallelText"] += (
                        """Please note that if you abandon the process with %(appName)s after reviewers have contributed their time toward evaluation and before the end of the evaluation, we will post the reviewers' reports on the %(appName)s website as recognition of their work and in order to enable critical discussion.<p>"""
                        % mail_vars
                    )
                hashtag_template = "#SubmitterPreprintSubmitted"

        elif article.status == "Awaiting consideration" and newStatus == "Under consideration":
            if article.parallel_submission:
                hashtag_template = "#SubmitterParallelPreprintUnderConsideration"
            else:
                hashtag_template = "#SubmitterPreprintUnderConsideration"

        elif article.status != newStatus and newStatus == "Cancelled":
            hashtag_template = "#SubmitterCancelledSubmission"

        elif article.status != newStatus and newStatus == "Rejected":
            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["recommTarget"] = URL(
                c="user", f="recommendations", vars=dict(articleId=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )

            hashtag_template = "#SubmitterRejectedSubmission"

        elif article.status != newStatus and newStatus == "Not considered":
            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["recommTarget"] = URL(
                c="user", f="recommendations", vars=dict(articleId=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )

            hashtag_template = "#SubmitterNotConsideredSubmission"

        elif article.status != newStatus and newStatus == "Awaiting revision":
            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["recommTarget"] = URL(
                c="user", f="recommendations", vars=dict(articleId=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )

            hashtag_template = "#SubmitterAwaitingSubmission"

        elif article.status != newStatus and newStatus == "Pre-recommended":
            return  # patience!

        elif article.status != newStatus and newStatus == "Recommended":
            lastRecomm = db((db.t_recommendations.article_id == article.id) & (db.t_recommendations.recommendation_state == "Recommended")).select().last()
            mail_vars["linkTarget"] = URL(c="articles", f="rec", vars=dict(id=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["doiRecomm"] = XML(common_small_html.mkLinkDOI(lastRecomm.recommendation_doi))
            mail_vars["recommVersion"] = lastRecomm.ms_version
            mail_vars["recommsList"] = SPAN(common_small_html.getRecommAndReviewAuthors(auth, db, recomm=lastRecomm, with_reviewers=False, linked=False)).flatten()

            hashtag_template = "#SubmitterRecommendedPreprint"

        elif article.status != newStatus:
            mail_vars["tOldStatus"] = current.T(article.status)
            mail_vars["tNewStatus"] = current.T(newStatus)

            hashtag_template = "#SubmitterPreprintStatusChanged"
        else:
            return

        # Fill define template with mail_vars :
        emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm_id, recommendation)

        reports = emailing_tools.createMailReport(True, "submitter " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Send email to the recommenders (if any) for postprints
def send_to_recommender_postprint_status_changed(session, auth, db, articleId, newStatus):
    print("send_to_recommender_postprint_status_changed")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    if article:
        mail_vars["linkTarget"] = URL(
            c="recommender", f="my_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(pressReviews=True)
        )
        for myRecomm in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, distinct=True):
            mail_vars["recommender_id"] = myRecomm["recommender_id"]
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, mail_vars["recommender_id"])
            mail_vars["destAddress"] = db.auth_user[myRecomm.recommender_id]["email"]
            mail_vars["articleAuthors"] = article.authors
            mail_vars["articleTitle"] = article.title
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["tOldStatus"] = current.T(article.status)
            mail_vars["tNewStatus"] = current.T(newStatus)

            hashtag_template = "#RecommenderPostprintStatusChanged"
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, myRecomm.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Send email to the recommenders (if any)
def send_to_recommender_status_changed(session, auth, db, articleId, newStatus):
    print("send_to_recommender_status_changed")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    mail_vars["recomm_limit_days"] = myconf.get("config.recomm_limit_days", default=50)

    article = db.t_articles[articleId]
    if article is not None:
        mail_vars["linkTarget"] = URL(
            c="recommender", f="my_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(pressReviews=article.already_published)
        )

        for recommender in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, distinct=True):
            recommender_id = recommender.recommender_id
            myRecomm = db((db.t_recommendations.article_id == articleId) & (db.t_recommendations.recommender_id == recommender_id)).select(orderby=db.t_recommendations.id).last()

            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recommender_id)
            mail_vars["destAddress"] = db.auth_user[myRecomm.recommender_id]["email"]
            mail_vars["articleAuthors"] = article.authors
            mail_vars["articleTitle"] = article.title
            mail_vars["articleDoi"] = XML(common_small_html.mkSimpleDOI(article.doi))
            mail_vars["tOldStatus"] = current.T(article.status)
            mail_vars["tNewStatus"] = current.T(newStatus)

            if article.status == "Awaiting revision" and newStatus == "Under consideration":
                mail_vars["deadline"] = (datetime.date.today() + datetime.timedelta(weeks=1)).strftime("%a %b %d")

                hashtag_template = "#RecommenderStatusChangedToUnderConsideration"

            elif newStatus == "Recommended":
                mail_vars["linkRecomm"] = URL(c="articles", f="rec", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(id=article.id))
                mail_vars["doiRecomm"] = common_small_html.mkLinkDOI(myRecomm.recommendation_doi)

                hashtag_template = "#RecommenderStatusChangedUnderToRecommended"

            else:
                hashtag_template = "#RecommenderArticleStatusChanged"

            # Fill define template with mail_vars :
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, myRecomm.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Do send email to suggested recommenders for a given NO MORE available article
def send_to_suggested_recommenders_not_needed_anymore(session, auth, db, articleId):
    print("send_to_suggested_recommenders_not_needed_anymore")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    if article:
        recomm = db((db.t_recommendations.article_id == article.id)).select().last()
        recomm_id = None
        if recomm:
            recomm_id = recomm.id

        mail_vars["articleTitle"] = article.title
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)

        if article.anonymous_submission:
            mail_vars["articleAuthors"] = current.T("[undisclosed]")
        else:
            mail_vars["articleAuthors"] = article.authors

        # TODO: removing auth.user_id is not the best solution... Should transmit recommender_id
        suggested_recommenders = db(
            (db.t_suggested_recommenders.article_id == articleId)
            & (db.t_suggested_recommenders.suggested_recommender_id != auth.user_id)
            & (db.t_suggested_recommenders.declined == False)
            & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)
        ).select(db.t_suggested_recommenders.ALL, db.auth_user.ALL)
        for sugg_recommender in suggested_recommenders:
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, sugg_recommender["auth_user.id"])
            mail_vars["destAddress"] = db.auth_user[sugg_recommender["auth_user.id"]]["auth_user.email"]

            # TODO: parallel submission
            hashtag_template = "#RecommenderSuggestionNotNeededAnymore"
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm_id)

            reports = emailing_tools.createMailReport(True, "suggested recommender" + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Do send email to suggested recommenders for a given available article
def send_to_suggested_recommenders(session, auth, db, articleId):
    print("send_to_suggested_recommenders")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    if article:

        mail_vars["articleTitle"] = article.title
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)

        if article.anonymous_submission:
            mail_vars["articleAuthors"] = current.T("[undisclosed]")
        else:
            mail_vars["articleAuthors"] = article.authors

        recomm = db((db.t_recommendations.article_id == article.id)).select().last()
        recomm_id = None
        if recomm:
            recomm_id = recomm.id

        suggested_recommenders = db.executesql(
            "SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND sr.declined IS FALSE AND article_id=%s;",
            placeholders=[article.id],
            as_dict=True,
        )
        for sugg_recommender in suggested_recommenders:
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, sugg_recommender["id"])
            mail_vars["destAddress"] = db.auth_user[sugg_recommender["id"]]["email"]
            mail_vars["linkTarget"] = URL(
                c="recommender", f="article_details", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )
            mail_vars["helpurl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["ethicsurl"] = URL(c="about", f="ethics", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            if article.parallel_submission:
                mail_vars["addNote"] = (
                    "<b>Note:</b> The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appName)s, and hope you will agree to manage this preprint. If the authors abandon the process at %(appName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appName)s website as recognition of the reviewers' work and in order to enable critical discussion."
                    % mail_vars
                )
            else:
                mail_vars["addNote"] = ""

            hashtag_template = "#RecommenderSuggestedArticle"
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm_id)

            delete_reminder_for_submitter(db, "#ReminderSubmitterSuggestedRecommenderNeeded", articleId)

            reports = emailing_tools.createMailReport(True, "suggested recommender" + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Individual reminder for previous message
def send_reminder_to_suggested_recommender(session, auth, db, suggRecommId):
    print("send_reminder_to_suggested_recommenders")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    suggRecomm = db.t_suggested_recommenders[suggRecommId]
    if suggRecomm:
        article = db.t_articles[suggRecomm.article_id]
        if article:
            recomm = db((db.t_recommendations.article_id == article.id)).select().last()
            recomm_id = None
            if recomm:
                recomm_id = recomm.id

            mail_vars["articleTitle"] = article.title
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["linkTarget"] = URL(
                c="recommender", f="article_details", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )
            mail_vars["helpurl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            if article.anonymous_submission:
                mail_vars["articleAuthors"] = current.T("[undisclosed]")
            else:
                mail_vars["articleAuthors"] = article.authors

            suggested_recommender = db.auth_user[suggRecomm.suggested_recommender_id]
            if suggested_recommender:
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, suggested_recommender["id"])
                mail_vars["destAddress"] = suggested_recommender["email"]

                hashtag_template = "#RecommenderSuggestedArticleReminder"
                emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm_id)

                reports = emailing_tools.createMailReport(True, "suggested recommender" + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Do send email to recommender when a review is re-opened
def send_to_reviewer_review_reopened(session, auth, db, reviewId, newForm):
    print("send_to_reviewer_review_reopened")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["linkTarget"] = URL(c="user", f="my_reviews", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["articleTitle"] = B(article.title)
            if article.anonymous_submission:
                mail_vars["articleAuthors"] = current.T("[undisclosed]")
            else:
                mail_vars["articleAuthors"] = article.authors
            reviewer = db.auth_user[rev.reviewer_id]
            if reviewer:
                mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id) or ""
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.reviewer_id)
                mail_vars["destAddress"] = db.auth_user[rev.reviewer_id]["email"]

                hashtag_template = "#ReviewerReviewReopened"
                emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Do send email to recommender when a review is closed
def send_to_recommenders_review_completed(session, auth, db, reviewId):
    print("send_to_recommenders_review_completed")
    mail_vars = emailing_tools.getMailCommonVars()

    reports = []

    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = article.title
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )

            recommender = db.auth_user[recomm.recommender_id]
            if recommender:
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
                mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
                mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(auth, db, rev.reviewer_id)

                hashtag_template = "#ReviewerReviewCompleted"
                emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Do send email to recommender when a co correcommender accepted recommendation
def send_to_recommender_co_recommender_considerated(session, auth, db, pressId):
    print("send_to_recommender_co_recommender_considerated")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    press = db.t_press_reviews[pressId]
    recomm = db.t_recommendations[press.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
            mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
            mail_vars["contributorPerson"] = common_small_html.mkUserWithMail(auth, db, press.contributor_id)

            hashtag_template = "#RecommenderCoRecommenderConsiderated"
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_recommenders_co_recommender_declined(session, auth, db, pressId):
    print("send_to_recommenders_co_recommender_declined")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    press = db.t_press_reviews[pressId]
    recomm = db.t_recommendations[press.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = article.title
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
            mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
            mail_vars["contributorPerson"] = common_small_html.mkUserWithMail(auth, db, press.contributor_id)

            hashtag_template = "#RecommenderCoRecommenderDeclined"
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_recommenders_co_recommender_agreement(session, auth, db, pressId):
    print("send_to_recommenders_co_recommender_agreement")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    press = db.t_press_reviews[pressId]
    recomm = db.t_recommendations[press.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = article.title
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
            mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
            mail_vars["contributorPerson"] = common_small_html.mkUserWithMail(auth, db, press.contributor_id)

            hashtag_template = "#RecommenderCoRecommenderAgreement"
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Do send email to recommender when a review is accepted for consideration
def send_to_recommenders_review_considered(session, auth, db, reviewId):
    print("send_to_recommenders_review_considered")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = article.title
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
            mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
            mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(auth, db, rev.reviewer_id)
            mail_vars["expectedDuration"] = datetime.timedelta(days=21)  # three weeks
            mail_vars["dueTime"] = str((datetime.datetime.now() + mail_vars["expectedDuration"]).date())

            if article.anonymous_submission:
                mail_vars["articleAuthors"] = current.T("[undisclosed]")
            else:
                mail_vars["articleAuthors"] = article.authors

            hashtag_template = "#RecommenderReviewConsidered"
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_recommenders_review_declined(session, auth, db, reviewId):
    print("send_to_recommenders_review_declined")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = article.title
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
            mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
            mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(auth, db, rev.reviewer_id)

            if article.anonymous_submission:
                mail_vars["articleAuthors"] = current.T("[undisclosed]")
            else:
                mail_vars["articleAuthors"] = article.authors

            hashtag_template = "#RecommenderReviewDeclined"
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_reviewer_review_invitation(session, auth, db, reviewsList):
    print("send_to_reviewer_review_invitation")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    for rev in db((db.t_reviews.id.belongs(reviewsList)) & (db.t_reviews.review_state == None)).select():
        if rev and rev.review_state is None:
            recomm = db.t_recommendations[rev.recommendation_id]
            if recomm:
                if recomm.recommender_id != rev.reviewer_id:
                    article = db.t_articles[recomm["article_id"]]
                    if article:
                        mail_vars["articleTitle"] = article.title
                        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                        mail_vars["linkTarget"] = URL(
                            c="user", f="my_reviews", vars=dict(pendingOnly=True), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
                        )
                        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.reviewer_id)
                        mail_vars["destAddress"] = db.auth_user[rev.reviewer_id]["email"]
                        mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id)
                        if article.anonymous_submission:
                            mail_vars["articleAuthors"] = current.T("[undisclosed]")
                        else:
                            mail_vars["articleAuthors"] = article.authors

                        hashtag_template = "#ReviewerReviewInvitation"
                        emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                        rev.review_state = "Pending"
                        rev.update_record()

                        reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)
                    else:
                        print("send_to_reviewer_review_invitation: Article not found")
                else:
                    print("send_to_reviewer_review_invitation: recommender = reviewer")
            else:
                print("send_to_reviewer_review_invitation: Recommendation not found")
        else:
            print("send_to_reviewer_review_invitation: Review not found")

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_reviewers_article_cancellation(session, auth, db, articleId, newStatus):
    print("send_to_reviewers_article_cancellation")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    if article:
        mail_vars["articleTitle"] = article.title
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
        mail_vars["linkTarget"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=True), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        if article.anonymous_submission:
            mail_vars["articleAuthors"] = current.T("[undisclosed]")
        else:
            mail_vars["articleAuthors"] = article.authors

        lastRecomm = db(db.t_recommendations.article_id == article.id).select(orderby=db.t_recommendations.id).last()
        if lastRecomm:
            reviewers = db((db.t_reviews.recommendation_id == lastRecomm.id) & (db.t_reviews.review_state in ("Pending", "Under consideration", "Completed"))).select()
            for rev in reviewers:
                if rev is not None and rev.reviewer_id is not None:
                    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.reviewer_id)
                    mail_vars["destAddress"] = db.auth_user[rev.reviewer_id]["email"]
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, lastRecomm.recommender_id)

                    hashtag_template = "#ReviewersArticleCancellation"
                    emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, lastRecomm.id)

                    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)
        else:
            print("send_to_reviewers_article_cancellation: Recommendation not found")
    else:
        print("send_to_reviewers_article_cancellation: Article not found")

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_admin_new_user(session, auth, db, userId):
    print("send_admin_new_user")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    admins = db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "administrator")).select(
        db.auth_user.ALL
    )
    dest = []

    user = db.auth_user[userId]
    if user:
        mail_vars["userTxt"] = common_small_html.mkUser(auth, db, userId)
        mail_vars["userMail"] = user.email

        for admin in admins:
            mail_vars["destAddress"] = admin.email

            hashtag_template = "#AdminNewUser"
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars)

    reports = emailing_tools.createMailReport(True, "administrators", reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_new_user(session, auth, db, userId):
    print("send_new_user")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    # get thematics and alerts
    user = db.auth_user[userId]
    if type(user.thematics) is list:
        thema = user.thematics
    else:
        thema = [user.thematics]
    if type(user.alerts) is list:
        alerts = user.alerts
    else:
        if user.alerts:
            alerts = [user.alerts]
        else:
            alerts = ["[no alerts]"]

    if user:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, userId)
        mail_vars["destAddress"] = db.auth_user[userId]["email"]
        mail_vars["baseurl"] = URL(c="about", f="about", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["infourl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["recommurl"] = URL(c="about", f="recommenders", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["thematics"] = ", ".join(thema)
        mail_vars["days"] = ", ".join(alerts)

        parallel_submission_allowed = myconf.get("config.parallel_submission", default=False)
        if parallel_submission_allowed:
            hashtag_template = "#NewUserParallelSubmissionAllowed"
        else:
            hashtag_template = "#NewUser"

        emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars)

        reports = emailing_tools.createMailReport(True, "new user " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_new_membreship(session, auth, db, membershipId):
    print("send_new_membreship")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    user = db.auth_user[db.auth_membership[membershipId].user_id]
    group = db.auth_group[db.auth_membership[membershipId].group_id]
    if user and group:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, user.id)
        mail_vars["destAddress"] = db.auth_user[user.id]["email"]

        if group.role == "recommender":
            mail_vars["days"] = ", ".join(user.alerts)
            mail_vars["baseurl"] = URL(c="default", f="index", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["helpurl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["ethicsurl"] = URL(c="about", f="ethics", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            hashtag_template = "#NewMembreshipRecommender"
            new_role_report = "new recommender "

        elif group.role == "manager":
            hashtag_template = "#NewMembreshipManager"
            new_role_report = "new manager "

        else:
            return

        emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars)

        reports = emailing_tools.createMailReport(True, new_role_report + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_managers(session, auth, db, articleId, newStatus):
    print("send_to_managers")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    managers = db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "manager")).select(db.auth_user.ALL)
    article = db.t_articles[articleId]
    if article:
        recomm = db((db.t_recommendations.article_id == articleId)).select(orderby=db.t_recommendations.id).last()
        recomm_id = None
        if recomm:
            recomm_id = recomm.id

        recommendation = None

        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)

        if article.user_id:
            mail_vars["submitterPerson"] = common_small_html.mkUser(auth, db, article.user_id)  # submitter
        else:
            mail_vars["submitterPerson"] = "?"

        if newStatus == "Pending":
            mail_vars["linkTarget"] = URL(c="manager", f="pending_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            hashtag_template = "#ManagersPreprintSubmission"

        elif newStatus.startswith("Pre-"):
            if recomm is not None:
                mail_vars["recommenderPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id) or ""  # recommender
            else:
                mail_vars["recommenderPerson"] = "?"
            mail_vars["linkTarget"] = URL(c="manager", f="pending_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            hashtag_template = "#ManagersRecommendationOrDecision"

        elif newStatus == "Under consideration":
            recomm = db((db.t_recommendations.article_id == articleId)).select(orderby=db.t_recommendations.id).last()
            if recomm is not None:
                mail_vars["recommenderPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id) or ""  # recommender
            else:
                mail_vars["recommenderPerson"] = "?"

            mail_vars["linkTarget"] = URL(c="manager", f="ongoing_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            if article.status == "Awaiting revision":
                hashtag_template = "#ManagersArticleResubmited"
            else:
                hashtag_template = "#ManagersArticleConsideredForRecommendation"

        elif newStatus == "Cancelled":
            mail_vars["linkTarget"] = URL(c="manager", f="completed_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            hashtag_template = "#ManagersArticleCancelled"

        else:
            mail_vars["linkTarget"] = URL(c="manager", f="all_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["tOldStatus"] = current.T(article.status)
            mail_vars["tNewStatus"] = current.T(newStatus)

            hashtag_template = "#ManagersArticleStatusChanged"

        for manager in managers:
            mail_vars["destAddress"] = manager.email
            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm_id, recommendation)

            reports = emailing_tools.createMailReport(True, "manager " + (manager.email or ""), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_thank_recommender_postprint(session, auth, db, recommId):
    print("send_to_thank_recommender_postprint")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    recomm = db.t_recommendations[recommId]
    if recomm:
        article = db.t_articles[recomm.article_id]
        if article:
            mail_vars["articleTitle"] = article.title
            mail_vars["articleAuthors"] = article.authors
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )

            recommender = db.auth_user[recomm.recommender_id]
            if recommender:
                # recommender = common_small_html.mkUser(auth, db, recomm.recommender_id)
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
                mail_vars["destAddress"] = recommender["email"]

                hashtag_template = "#RecommenderThankForPostprint"
                emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_thank_recommender_preprint(session, auth, db, articleId):
    print("send_to_thank_recommender_preprint")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    if articleId:
        article = db.t_articles[articleId]
        if article:
            mail_vars["articleTitle"] = article.title
            mail_vars["articleAuthors"] = article.authors
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["linkTarget"] = URL(
                c="recommender", f="my_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(pressReviews=False)
            )

            recomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.id).last()
            recommender = db.auth_user[recomm.recommender_id]
            if recommender:
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recommender.id)
                mail_vars["destAddress"] = recommender["email"]

                if article.parallel_submission:
                    hashtag_template = "#RecommenderThankForPreprintParallelSubmission"
                else:
                    hashtag_template = "#RecommenderThankForPreprint"

                emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_thank_reviewer_acceptation(session, auth, db, reviewId, newForm):
    print("send_to_thank_reviewer_acceptation")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    if rev:
        recomm = db.t_recommendations[rev.recommendation_id]
        if recomm:
            article = db.t_articles[recomm["article_id"]]
            if article:
                mail_vars["articleTitle"] = article.title
                mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                mail_vars["linkTarget"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=False), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                if article.anonymous_submission:
                    mail_vars["articleAuthors"] = current.T("[undisclosed]")
                else:
                    mail_vars["articleAuthors"] = article.authors

                reviewer = db.auth_user[rev.reviewer_id]
                if reviewer:
                    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.reviewer_id)
                    mail_vars["destAddress"] = reviewer["email"]

                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id) or ""
                    mail_vars["expectedDuration"] = datetime.timedelta(days=21)  # three weeks
                    mail_vars["dueTime"] = str((datetime.datetime.now() + mail_vars["expectedDuration"]).date())

                    hashtag_template = "#ReviewerThankForReviewAcceptation"
                    emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_thank_reviewer_done(session, auth, db, reviewId, newForm):
    print("send_to_thank_reviewer_done")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    if rev:
        recomm = db.t_recommendations[rev.recommendation_id]
        if recomm:
            article = db.t_articles[recomm["article_id"]]
            if article:
                mail_vars["articleTitle"] = article.title
                mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                mail_vars["linkTarget"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=False), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                if article.anonymous_submission:
                    mail_vars["articleAuthors"] = current.T("[undisclosed]")
                else:
                    mail_vars["articleAuthors"] = article.authors

                mail_vars["parallelText"] = ""
                if parallelSubmissionAllowed:
                    mail_vars[
                        "parallelText"
                    ] += """Note that if the authors abandon the process at %(longname)s after reviewers have written their reports, we will post the reviewers' reports on the %(longname)s website as recognition of their work and in order to enable critical discussion."""
                    if article.parallel_submission:
                        mail_vars[
                            "parallelText"
                        ] += """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(longname)s, and hope you will agree to review this preprint."""

                reviewer = db.auth_user[rev.reviewer_id]
                if reviewer:
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id) or ""
                    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.reviewer_id)
                    mail_vars["destAddress"] = reviewer["email"]

                    hashtag_template = "#ReviewerThankForReviewDone"
                    emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_delete_one_corecommender(session, auth, db, contribId):
    print("send_to_delete_one_corecommender")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    if contribId:
        contrib = db.t_press_reviews[contribId]
        if contrib:
            recomm = db.t_recommendations[contrib.recommendation_id]
            if recomm:
                article = db.t_articles[recomm.article_id]
                if article:
                    mail_vars["articleTitle"] = article.title
                    mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                    mail_vars["articlePrePost"] = "postprint" if article.already_published else "preprint"
                    mail_vars["linkTarget"] = URL(c="recommender", f="my_co_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, contrib.contributor_id)
                    mail_vars["destAddress"] = db.auth_user[contrib.contributor_id]["email"]
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id) or ""
                    if article.anonymous_submission:
                        mail_vars["articleAuthors"] = current.T("[undisclosed]")
                    else:
                        mail_vars["articleAuthors"] = article.authors

                    hashtag_template = "#CoRecommenderRemovedFromArticle"
                    emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                    reports = emailing_tools.createMailReport(True, "contributor " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_one_corecommender(session, auth, db, contribId):
    print("send_to_one_corecommender")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    if contribId:
        contrib = db.t_press_reviews[contribId]
        if contrib:
            recomm = db.t_recommendations[contrib.recommendation_id]
            if recomm:
                article = db.t_articles[recomm.article_id]
                if article:
                    mail_vars["articleTitle"] = article.title
                    mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                    mail_vars["articlePrePost"] = "postprint" if article.already_published else "preprint"
                    mail_vars["linkTarget"] = URL(c="recommender", f="my_co_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, contrib.contributor_id)
                    mail_vars["destAddress"] = db.auth_user[contrib.contributor_id]["email"]
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id) or ""
                    mail_vars["ethicsLink"] = URL("about", "ethics", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                    if article.anonymous_submission:
                        mail_vars["articleAuthors"] = current.T("[undisclosed]")
                    else:
                        mail_vars["articleAuthors"] = article.authors

                    if article.status in ("Under consideration", "Pre-recommended"):
                        if article.already_published:
                            hashtag_template = "#CoRecommenderAddedOnArticleAlreadyPublished"
                        else:
                            hashtag_template = "#CoRecommenderAddedOnArticle"

                        emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                        reports = emailing_tools.createMailReport(True, "contributor " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_to_corecommenders(session, auth, db, articleId, newStatus):
    print("send_to_corecommenders")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    recomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.id).last()
    if recomm:
        mail_vars["articleTitle"] = article.title
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
        mail_vars["articlePrePost"] = "postprint" if article.already_published else "preprint"
        mail_vars["tOldStatus"] = current.T(article.status)
        mail_vars["tNewStatus"] = current.T(newStatus)
        mail_vars["linkTarget"] = URL(c="recommender", f="my_co_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id) or ""
        if article.anonymous_submission:
            mail_vars["articleAuthors"] = current.T("[undisclosed]")
        else:
            mail_vars["articleAuthors"] = article.authors

        contribs = db(db.t_press_reviews.recommendation_id == recomm.id).select()
        for contrib in contribs:
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, contrib.contributor_id)
            dest = db.auth_user[contrib.contributor_id]
            if dest:
                mail_vars["destAddress"] = dest["email"]
            else:
                mail_vars["destAddress"] = ""

            if newStatus == "Recommended":
                mail_vars["recommDOI"] = common_small_html.mkLinkDOI(recomm.recommendation_doi)
                mail_vars["linkRecomm"] = URL(c="articles", f="rec", vars=dict(id=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                hashtag_template = "#CoRecommendersArticleRecommended"
            else:
                hashtag_template = "#CoRecommendersArticleStatusChanged"

            emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

            reports = emailing_tools.createMailReport(true, "contributor " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_decision_to_reviewers(session, auth, db, articleId, newStatus):
    print("send_decision_to_reviewers")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    recomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.id).last()
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = article.title
            mail_vars["articleStatus"] = current.T(newStatus)
            mail_vars["linkTarget"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=False), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["myRefArticle"] = common_small_html.mkArticleCitation(auth, db, recomm)
            mail_vars["myRefRecomm"] = common_small_html.mkRecommCitation(auth, db, recomm)

            if newStatus == "Recommended":
                reviewers = db(
                    (db.auth_user.id == db.t_reviews.reviewer_id)
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    & (db.t_recommendations.article_id == article.id)
                    & (db.t_reviews.review_state == "Completed")
                ).select(db.t_reviews.id, db.auth_user.ALL, distinct=db.auth_user.email)
            else:
                reviewers = db((db.auth_user.id == db.t_reviews.reviewer_id) & (db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Completed")).select(
                    db.t_reviews.id, db.auth_user.ALL, distinct=db.auth_user.email
                )

            for rev in reviewers:
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.auth_user.id)
                mail_vars["destAddress"] = rev.auth_user.email

                if newStatus == "Recommended":
                    mail_vars["recommDOI"] = common_small_html.mkLinkDOI(recomm.recommendation_doi)
                    mail_vars["linkRecomm"] = URL(c="articles", f="rec", vars=dict(id=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                    hashtag_template = "#ReviewersArticleRecommended"
                else:
                    hashtag_template = "#ReviewersArticleStatusChanged"

                emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars, recomm.id)

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
# Mail with templates
######################################################################################################################################################################
def send_reviewer_invitation(session, auth, db, reviewId, replyto, cc, hashtag_template, subject, message, reset_password_key=None, linkTarget=None, declineLinkTarget=None):
    print("send_reviewer_invitation")
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    review = db.t_reviews[reviewId]
    if review:
        recomm = db.t_recommendations[review.recommendation_id]
        if recomm:
            rev = db.auth_user[review["reviewer_id"]]
            if rev:
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, review.reviewer_id)
                mail_vars["destAddress"] = rev["email"]
                content = DIV(WIKI(message, safe_mode=False))

                if reset_password_key:
                    if linkTarget:
                        link = URL(
                            a=None,
                            c="default",
                            f="user",
                            args="reset_password",
                            vars=dict(key=reset_password_key, _next=linkTarget),
                            scheme=mail_vars["scheme"],
                            host=mail_vars["host"],
                            port=mail_vars["port"],
                        )
                    else:
                        link = URL(
                            a=None,
                            c="default",
                            f="user",
                            args="reset_password",
                            vars=dict(key=reset_password_key),
                            scheme=mail_vars["scheme"],
                            host=mail_vars["host"],
                            port=mail_vars["port"],
                        )

                    declineLinkTarget = URL(
                        a=None, c="user", f="delete_temp_user", vars=dict(key=reset_password_key), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
                    )

                    content.append(P(B(current.T("TO ACCEPT OR DECLINE CLICK ON THE FOLLOWING BUTTON:"))))
                    content.append(
                        DIV(
                            A(
                                SPAN(
                                    current.T("Validate your account"),
                                    _style="margin: 10px; font-size: 14px; background: #93c54b; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px",
                                ),
                                _href=link,
                                _style="text-decoration: none;",
                            ),
                            _style="width: 100%; text-align: center; margin-bottom: 25px;",
                        )
                    )

                    content.append(P(B(current.T('THEN GO TO "Contribute —> invitations to review a preprint" IN THE TOP MENU'))))
                    content.append(HR())
                    content.append(P(current.T("You can also delete the created account by clicking on this button :")))
                    content.append(
                        DIV(
                            A(
                                SPAN(
                                    current.T("Delete the temporary account"),
                                    _style="margin: 10px; font-size: 14px; background: #f47c3c; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px",
                                ),
                                _href=declineLinkTarget,
                                _style="text-decoration: none;",
                            ),
                            _style="width: 100%; text-align: center; margin-bottom: 25px;",
                        )
                    )

                elif linkTarget:
                    content.append(P())

                    if review.review_state is None or review.review_state == "Pending" or review.review_state == "":
                        content.append(P(B(current.T("TO ACCEPT OR DECLINE CLICK ON THE FOLLOWING BUTTONS:"))))

                        if declineLinkTarget:
                            content.append(
                                DIV(
                                    A(
                                        SPAN(
                                            current.T("Yes, I agree to review this preprint"),
                                            _style="margin: 10px; font-size: 14px; background: #93c54b; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px",
                                        ),
                                        _href=linkTarget,
                                        _style="text-decoration: none;",
                                    ),
                                    A(
                                        SPAN(
                                            current.T("No thanks, I'd rather not"),
                                            _style="margin: 10px; font-size: 14px; background: #f47c3c; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px",
                                        ),
                                        _href=declineLinkTarget,
                                        _style="text-decoration: none;",
                                    ),
                                    _style="width: 100%; text-align: center; margin-bottom: 25px;",
                                )
                            )

                    elif review.review_state == "Under consideration":
                        content.append(P(B(current.T("TO WRITE, EDIT OR UPLOAD YOUR REVIEW CLICK ON THE FOLLOWING LINK:"))))
                        content.append(A(linkTarget, _href=linkTarget))

                subject_without_appname = subject.replace("%s: " % mail_vars["appName"], "")
                applogo = URL("static", "images/small-background.png", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                message = render(
                    filename=MAIL_HTML_LAYOUT,
                    context=dict(subject=subject_without_appname, applogo=applogo, appname=mail_vars["appName"], content=XML(content), footer=emailing_tools.mkFooter()),
                )

                db.mail_queue.insert(
                    dest_mail_address=mail_vars["destAddress"],
                    mail_subject=subject,
                    mail_content=message,
                    user_id=auth.user_id,
                    recommendation_id=recomm.id,
                    mail_template_hashtag=hashtag_template,
                )

                if review.review_state is None:
                    review.review_state = "Pending"
                    review.update_record()

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_change_mail(session, auth, db, userId, dest_mail, key):
    print("send_change_mail")
    mail = emailing_tools.getMailer(auth)
    mail_vars = emailing_tools.getMailCommonVars()

    mail_resu = False
    reports = []

    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, userId)
    mail_vars["destAddress"] = dest_mail
    mail_vars["verifyMailUrl"] = URL(c="default", f="user", args=["verify_email", key], scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

    hashtag_template = "#UserChangeMail"
    emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars)

    reports = emailing_tools.createMailReport(True, mail_vars["destAddress"], reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
def send_recover_mail(session, auth, db, userId, dest_mail, key):
    print("send_recover_mail")
    mail = emailing_tools.getMailer(auth)
    mail_vars = emailing_tools.getMailCommonVars()

    mail_resu = False
    reports = []

    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, userId)
    mail_vars["destAddress"] = dest_mail
    mail_vars["recoverMailUrl"] = URL(c="default", f="recover_mail", vars=dict(key=key), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

    hashtag_template = "#UserRecoverMail"
    emailing_tools.insertMailInQueue(auth, db, hashtag_template, mail_vars)

    reports = emailing_tools.createMailReport(True, mail_vars["destAddress"], reports)

    emailing_tools.getFlashMessage(session, reports)


######################################################################################################################################################################
## News letter
######################################################################################################################################################################
def send_newsletter_mail(session, auth, db, userId):
    mail_vars = emailing_tools.getMailCommonVars()

    user = db.auth_user[userId]

    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, userId)
    mail_vars["destAddress"] = user["email"]

    hashtag_template = "#NewsLetter"

    # New recommended articles
    new_recommended_articles = db(
        (
            (db.t_articles.last_status_change >= (datetime.datetime.now() - datetime.timedelta(days=7)).date())
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.recommendation_state == "Recommended")
            & (db.t_articles.status == "Recommended")
        )
    ).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)

    i = 0
    newRecommendations = DIV()
    newRecommendationsCount = len(new_recommended_articles)
    for article in new_recommended_articles:
        i += 1
        if i <= 5:
            newRecommendations.append(newsletter_module.makeArticleWithRecommRow(auth, db, article))

    # New preprint searching for reviewers
    new_searching_for_reviewers_preprint = db(
        (
            (db.t_articles.last_status_change >= (datetime.datetime.now() - datetime.timedelta(days=7)).date())
            & (db.t_articles.is_searching_reviewers == True)
            & (db.t_articles.status == "Under consideration")
        )
    ).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)

    j = 0
    newPreprintSearchingForReviewers = DIV()
    newPreprintSearchingForReviewersCount = len(new_searching_for_reviewers_preprint)
    for article in new_searching_for_reviewers_preprint:
        j += 1
        if j <= 5:
            newPreprintSearchingForReviewers.append(newsletter_module.makeArticleRow(article, "review"))

    # New preprint requiring recommender 
    group = db((db.auth_user.id == userId) & (db.auth_membership.user_id == db.auth_user.id) & (db.auth_membership.group_id == 2)).count()
    
    newPreprintRequiringRecommender = None
    newPreprintRequiringRecommenderCount = 0
    if group > 0:
        new_searching_for_recommender_preprint = db(
            ((db.t_articles.last_status_change >= (datetime.datetime.now() - datetime.timedelta(days=7)).date()) & (db.t_articles.status == "Awaiting consideration"))
        ).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)

        k = 0
        newPreprintRequiringRecommender = DIV()
        newPreprintRequiringRecommenderCount = len(new_searching_for_recommender_preprint)
        for article in new_searching_for_recommender_preprint:
            k += 1
            if k <= 5:
                newPreprintRequiringRecommender.append(newsletter_module.makeArticleRow(article, "recommendation"))

    emailing_tools.insertNewsLetterMailInQueue(
        auth,
        db,
        mail_vars,
        hashtag_template,
        newRecommendations=newRecommendations,
        newRecommendationsCount=newRecommendationsCount,
        newPreprintSearchingForReviewers=newPreprintSearchingForReviewers,
        newPreprintSearchingForReviewersCount=newPreprintSearchingForReviewersCount,
        newPreprintRequiringRecommender=newPreprintRequiringRecommender,
        newPreprintRequiringRecommenderCount=newPreprintRequiringRecommenderCount,
    )


######################################################################################################################################################################
## Reminders
######################################################################################################################################################################
def create_reminder_for_submitter_suggested_recommender_needed(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    sugg_recommenders = db(db.t_suggested_recommenders.article_id == articleId).select()

    if article and article.user_id is not None and len(sugg_recommenders) == 0:

        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        hashtag_template = "#ReminderSubmitterSuggestedRecommenderNeeded"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 2, None, None, articleId)


######################################################################################################################################################################
def create_reminder_for_submitter_new_suggested_recommender_needed(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        hashtag_template = "#ReminderSubmitterNewSuggestedRecommenderNeeded"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 10, None, None, articleId)


######################################################################################################################################################################
def create_reminder_for_submitter_cancel_submission(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        hashtag_template = "#ReminderSubmitterCancelSubmission"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 20, None, None, articleId)


######################################################################################################################################################################
def create_reminder_for_submitter_revised_version_warning(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = db((db.t_recommendations.article_id == article.id)).select().last()

    if article and recomm:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderSubmitterRevisedVersionWarning"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 7, recomm.id, None, articleId)


######################################################################################################################################################################
def create_reminder_for_submitter_revised_version_needed(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = db((db.t_recommendations.article_id == article.id)).select().last()

    if article and recomm:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderSubmitterRevisedVersionNeeded"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 30, recomm.id, None, articleId)


######################################################################################################################################################################
def delete_reminder_for_submitter(db, hashtag_template, articleId):
    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        submitter_mail = db.auth_user[article.user_id]["email"]

        db((db.mail_queue.dest_mail_address == submitter_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.article_id == articleId)).delete()


######################################################################################################################################################################
def create_reminder_for_suggested_recommenders_invitation(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        hashtag_template = "#ReminderSuggestedRecommenderInvitation"

        suggested_recommenders = db(
            (db.t_suggested_recommenders.article_id == articleId)
            & (db.t_suggested_recommenders.declined == False)
            & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)
        ).select(db.t_suggested_recommenders.ALL, db.auth_user.ALL)

        for sugg_recommender in suggested_recommenders:
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, sugg_recommender["auth_user.id"])
            mail_vars["destAddress"] = db.auth_user[sugg_recommender["auth_user.id"]]["auth_user.email"]

            emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 5, None, None, articleId)


######################################################################################################################################################################
def delete_reminder_for_suggested_recommenders(db, hashtag_template, articleId):
    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        suggested_recommenders = db(
            (db.t_suggested_recommenders.article_id == articleId)
            & (db.t_suggested_recommenders.declined == False)
            & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)
        ).select(db.t_suggested_recommenders.ALL, db.auth_user.ALL)

        for sugg_recommender in suggested_recommenders:
            db(
                (db.mail_queue.dest_mail_address == sugg_recommender["auth_user.email"])
                & (db.mail_queue.mail_template_hashtag == hashtag_template)
                & (db.mail_queue.article_id == articleId)
            ).delete()


######################################################################################################################################################################
def create_reminder_for_reviewer_review_invitation(session, auth, db, reviewId):
    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    article = db.t_articles[recomm.article_id]

    if review and recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, review.reviewer_id)
        mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]

        mail_vars["articleDoi"] = article.doi
        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["myReviewsLink"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=True), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderReviewerReviewInvitation"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 5, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_reviewer_review_soon_due(session, auth, db, reviewId):
    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    article = db.t_articles[recomm.article_id]

    if review and recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, review.reviewer_id)
        mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]

        mail_vars["articleDoi"] = article.doi
        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["myReviewsLink"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=True), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["reviewDueDate"] = str((datetime.datetime.now() + datetime.timedelta(days=10)).date())
        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderReviewerReviewSoonDue"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 14, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_reviewer_review_due(session, auth, db, reviewId):
    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    article = db.t_articles[recomm.article_id]

    if review and recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, review.reviewer_id)
        mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]

        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderReviewerReviewDue"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 21, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_reviewer_review_over_due(session, auth, db, reviewId):
    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    article = db.t_articles[recomm.article_id]

    if review and recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, review.reviewer_id)
        mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]

        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderReviewerReviewOverDue"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 25, recomm.id, None, article.id)


######################################################################################################################################################################
def delete_reminder_for_reviewer(db, hashtag_template, reviewId):
    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]

    if review and recomm:
        review_mail = db.auth_user[review.reviewer_id]["email"]

        db((db.mail_queue.dest_mail_address == review_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.recommendation_id == recomm.id)).delete()


######################################################################################################################################################################
def create_reminder_for_recommender_reviewers_needed(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = db((db.t_recommendations.article_id == article.id)).select().last()

    if recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderRecommenderReviewersNeeded"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 1, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_recommender_new_reviewers_needed(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = db((db.t_recommendations.article_id == article.id)).select().last()

    if recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderRecommenderNewReviewersNeeded"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 7, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_recommender_decision_soon_due(session, auth, db, reviewId):
    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]

    count_reviews_under_consideration = 0
    if recomm:
        count_reviews_under_consideration = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Completed")).count()

    if recomm and count_reviews_under_consideration >= 1:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        hashtag_template = "#ReminderRecommenderDecisionSoonDue"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 8, recomm.id, None, recomm.article_id)


######################################################################################################################################################################
def create_reminder_for_recommender_decision_due(session, auth, db, reviewId):
    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]

    count_reviews_under_consideration = 0
    if recomm:
        count_reviews_under_consideration = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Completed")).count()

    if recomm and count_reviews_under_consideration >= 1:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        hashtag_template = "#ReminderRecommenderDecisionDue"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 10, recomm.id, None, recomm.article_id)


######################################################################################################################################################################
def create_reminder_for_recommender_decision_over_due(session, auth, db, reviewId):
    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]

    count_reviews_under_consideration = 0
    if recomm:
        count_reviews_under_consideration = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Completed")).count()

    if recomm and count_reviews_under_consideration >= 1:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        hashtag_template = "#ReminderRecommenderDecisionOverDue"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 14, recomm.id, None, recomm.article_id)


######################################################################################################################################################################
def create_reminder_for_recommender_revised_decision_soon_due(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = db((db.t_recommendations.article_id == article.id)).select().last()

    if recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderRecommenderRevisedDecisionSoonDue"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 7, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_recommender_revised_decision_due(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = db((db.t_recommendations.article_id == article.id)).select().last()

    if recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderRecommenderRevisedDecisionDue"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 10, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_recommender_revised_decision_over_due(session, auth, db, articleId):
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = db((db.t_recommendations.article_id == article.id)).select().last()

    if recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        mail_vars["articleTitle"] = article.title
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

        hashtag_template = "#ReminderRecommenderRevisedDecisionOverDue"

        emailing_tools.insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, 14, recomm.id, None, article.id)


######################################################################################################################################################################
def delete_reminder_for_recommender(db, hashtag_template, recommendationId):
    recomm = db.t_recommendations[recommendationId]

    if recomm:
        recomm_mail = db.auth_user[recomm.recommender_id]["email"]

        if hashtag_template == "#ReminderRecommenderNewReviewersNeeded":
            count_reviews_under_consideration = db(
                (db.t_reviews.recommendation_id == recommendationId) & ((db.t_reviews.review_state == "Under consideration") | (db.t_reviews.review_state == "Completed"))
            ).count()
            if count_reviews_under_consideration >= 1:
                db(
                    (db.mail_queue.dest_mail_address == recomm_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.recommendation_id == recomm.id)
                ).delete()

        elif hashtag_template in ("#ReminderRecommenderRevisedDecisionSoonDue", "#ReminderRecommenderRevisedDecisionDue", "#ReminderRecommenderRevisedDecisionOverDue"):
            article = db.t_articles[recomm.article_id]
            db(
                (db.mail_queue.dest_mail_address == recomm_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.article_id == recomm.article_id)
            ).delete()

        else:
            db(
                (db.mail_queue.dest_mail_address == recomm_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.recommendation_id == recomm.id)
            ).delete()


######################################################################################################################################################################
def delete_reminder_for_recommender_from_article_id(db, hashtag_template, articleId):
    article = db.t_articles[articleId]
    recomm = db((db.t_recommendations.article_id == article.id)).select().last()

    if recomm:
        recomm_mail = db.auth_user[recomm.recommender_id]["email"]
        db((db.mail_queue.dest_mail_address == recomm_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.article_id == articleId)).delete()


######################################################################################################################################################################
def delete_all_reminders_from_article_id(db, articleId):
    article = db.t_articles[articleId]
    if article:
        db((db.mail_queue.article_id == articleId) & (db.mail_queue.mail_template_hashtag.startswith("#Reminder"))).delete()


#####################################################################################################################################################################
def delete_all_reminders_from_recommendation_id(db, recommendationId):
    recomm = db.t_recommendations[recommendationId]
    if recomm:
        db((db.mail_queue.recommendation_id == recommendationId) & (db.mail_queue.mail_template_hashtag.startswith("#Reminder"))).delete()


######################################################################################################################################################################
# RESET PASSWORD EMAIL
def send_to_reset_password(session, auth, db, userId):
    print("send_reset_password")
    mail = emailing_tools.getMailer(auth)
    mail_vars = emailing_tools.getMailCommonVars()

    mail_resu = False
    reports = []

    fkey = db.auth_user[userId]["reset_password_key"]
    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, userId)
    mail_vars["destAddress"] = db.auth_user[userId]["email"]
    mail_vars["siteName"] = mail_vars["appName"]
    mail_vars["linkTarget"] = URL(
        c="default", f="user", args=["reset_password"], scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(key=fkey)
    )  # default/user/reset_password?key=1561727068-2946ea7b-54fe-4caa-87af-9c5e459b3487.
    mail_vars["linkTargetA"] = A(mail_vars["linkTarget"], _href=mail_vars["linkTarget"])

    mail = emailing_tools.buildMail(db, "#UserResetPassword", mail_vars)

    try:
        mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=mail["subject"], message=mail["content"])
    except:
        pass

    reports = emailing_tools.createMailReport(mail_resu, mail_vars["destPerson"].flatten(), reports)
    time.sleep(MAIL_DELAY)

    emailing_tools.getFlashMessage(session, reports)
