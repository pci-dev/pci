# -*- coding: utf-8 -*-

import html
import os
import datetime
import time
from re import sub, match
from typing import List, Optional, cast, Any, Dict, Union

# from copy import deepcopy
from dateutil.relativedelta import *
import traceback
from pprint import pprint

from gluon import current
from gluon.globals import Session
from gluon.sqlhtml import SQLFORM
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render # type: ignore
from gluon.contrib.markdown import WIKI # type: ignore
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon.tools import Mail
from gluon.storage import Storage
import models.article

from gluon.custom_import import track_changes
from models.suggested_recommender import SuggestedRecommender, SuggestedBy

track_changes(True)
import socket

from uuid import uuid4
from contextlib import closing
import shutil

from app_modules import common_tools
from app_modules import common_small_html
from app_modules import old_common
from app_modules import emailing_tools
from app_modules import emailing_parts
from app_modules import emailing_vars
from app_modules import newsletter
from app_modules import reminders
from app_components import ongoing_recommendation
from app_modules.common_small_html import md_to_html, mkUser, mkUser_U
from app_modules.emailing_vars import getPCiRRinvitationTexts
from app_modules.emailing_vars import getPCiRRScheduledSubmissionsVars
from app_modules.emailing_vars import getPCiRRstageVars
from app_modules.emailing_tools import mkAuthors, replaceMailVars
from app_modules.emailing_tools import getMailCommonVars
from app_modules.emailing_tools import replace_mail_vars_set_not_considered_mail
from app_modules.emailing_tools import exempt_addresses
from models.article import Article, ArticleStatus
from models.review import Review, ReviewState
from models.recommendation import Recommendation
from models.user import User
from models.mail_queue import MailQueue, SendingStatus
from app_modules.common_tools import URL

myconf = AppConfig(reload=True)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

default_review_duration = "Two weeks" if pciRRactivated else "Three weeks"

MAIL_DELAY = 1.5  # in seconds

# common view for all emails
MAIL_HTML_LAYOUT = os.path.join(os.path.dirname(__file__), "../../views/mail", "mail.html")
RESEND_MAIL_HTML_LAYOUT = os.path.join(os.path.dirname(__file__), "../../views/mail", "resend_mail.html")

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

######################################################################################################################################################################
# Mailing functions
######################################################################################################################################################################

email_subject_header = emailing_tools.email_subject_header
patch_email_subject = emailing_tools.patch_email_subject
get_review_days = Review.get_review_days_from_due_date

######################################################################################################################################################################
# TEST MAIL (or "How to properly create an emailing function")
def send_test_mail(userId):
    db = current.db

    # Get common variables :
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    # Set custom variables :
    mail_vars["destAddress"] = db.auth_user[userId]["email"]
    mail_vars["destPerson"] = common_small_html.mkUser(userId)
    mail_vars["linkTarget"] = URL(c="default", f="index", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

    # Insert mail in mail_queue :
    hashtag_template = "#TestMail"
    emailing_tools.insertMailInQueue(hashtag_template, mail_vars)

    # Create report for session flash alerts :
    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    # Build reports :
    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
# Send email to the requester (if any)
def send_to_submitter(articleId: int, newStatus: str):
    session, auth, db, response = current.session, current.auth, current.db, current.response

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    mail_vars["unconsider_limit_days"] = myconf.get("config.unconsider_limit_days", default=20)
    mail_vars["recomm_limit_days"] = myconf.get("config.recomm_limit_days", default=50)

    article = Article.get_by_id(articleId)
    if article and article.user_id is not None:
        mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["editTranslationLink"] = URL(c="article_translations", f="edit_all_article_translations", vars=dict(article_id=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        recomm = Article.get_last_recommendation(articleId)
        recomm_id = None
        if recomm:
            recomm_id = recomm.id

        recommendation = None
        mail_vars["linkTarget"] = URL(c="user", f="my_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        # Define template depending on the article status changed
        if article.status == "Pending" and newStatus == "Awaiting consideration":
            if article.parallel_submission:
                hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterParallelPreprintSubmitted", article)
            else:
                mail_vars["parallelText"] = ""
                if parallelSubmissionAllowed:
                    mail_vars["parallelText"] += (
                        """Please note that if you abandon the process with %(appName)s after reviewers have contributed their time toward evaluation and before the end of the evaluation, we will post the reviewers' reports on the %(appName)s website as recognition of their work and in order to enable critical discussion."""
                        % mail_vars
                    )
                hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterPreprintSubmitted", article)

        elif article.status == "Awaiting consideration" and newStatus == "Under consideration":
            if article.parallel_submission:
                hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterParallelPreprintUnderConsideration", article)
            else:
                hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterPreprintUnderConsideration", article)
                current.coar.send_acknowledge_and_tentative_accept(article)

            if pciRRactivated:
                mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        elif article.status != newStatus and newStatus == "Cancelled":
            mail_vars["parallelText"] = ""
            if parallelSubmissionAllowed and article.parallel_submission:
                mail_vars[
                    "parallelText"
                ] += """If your manuscript was sent to reviewers and evaluated, we will add a link to the reports on our progress log page. This is because you chose the parallel submission option and we do not wish to waste the effort that went into evaluating your work. This provides reviewers a possibility to claim credit for their evaluation work and, in addition to being useful to your team, we hope the reports are useful discussion points for other researchers in the field."""
            hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterCancelledSubmission", article)
            current.coar.send_acknowledge_and_reject(article)

        elif article.status != newStatus and newStatus == "Rejected":
            mail_vars["recommTarget"] = URL(
                c="user", f="recommendations", vars=dict(articleId=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )

            if recomm:
                mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(recomm.id)
            mail_vars["recommendationProcess"] = ongoing_recommendation.get_recommendation_process(article, True)

            hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterRejectedSubmission", article)
            current.coar.send_acknowledge_and_reject(article)

        elif article.status != newStatus and newStatus == "Not considered":
            current.coar.send_acknowledge_and_reject(article)
            return

        elif article.status != newStatus and newStatus == "Awaiting revision":
            mail_vars["recommTarget"] = URL(
                c="user", f="recommendations", vars=dict(articleId=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )

            if recomm:
                mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(recomm.id)
            mail_vars["recommendationProcess"] = ongoing_recommendation.get_recommendation_process(article, True)

            hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterAwaitingSubmission", article)
            if article.coar_notification_id: hashtag_template = "#SubmitterAwaitingSubmissionCOAR"

            current.coar.send_acknowledge_and_reject(article, resubmit=True)

        elif article.status != newStatus and newStatus == "Pre-recommended":
            return  # patience!

        elif article.status != newStatus and newStatus == "Recommended":
            lastRecomm = db((db.t_recommendations.article_id == article.id) & (db.t_recommendations.recommendation_state == "Recommended")).select().last()
            mail_vars["linkTarget"] = URL(c="articles", f="rec", vars=dict(id=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            if lastRecomm:
                mail_vars["doiRecomm"] = XML(common_small_html.mkLinkDOI(lastRecomm.recommendation_doi))
                mail_vars["recommVersion"] = lastRecomm.ms_version
                mail_vars["recommsList"] = SPAN(common_small_html.getRecommAndReviewAuthors(recomm=lastRecomm, with_reviewers=False, linked=False)).flatten()

                mail_vars["ccAddresses"] = [db.auth_user[lastRecomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(lastRecomm.id)
                mail_vars["recommendationProcess"] = ongoing_recommendation.get_recommendation_process(article, True)

            hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterRecommendedPreprint", article)

        elif article.status != newStatus and newStatus == "Recommended-private":
            lastRecomm = db((db.t_recommendations.article_id == article.id) & (db.t_recommendations.recommendation_state == "Recommended")).select().last()

            if lastRecomm:
                mail_vars["doiRecomm"] = XML(common_small_html.mkLinkDOI(lastRecomm.recommendation_doi))
                mail_vars["recommVersion"] = lastRecomm.ms_version
                mail_vars["recommsList"] = SPAN(common_small_html.getRecommAndReviewAuthors(recomm=lastRecomm, with_reviewers=False, linked=False)).flatten()

                mail_vars["ccAddresses"] = [db.auth_user[lastRecomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(lastRecomm.id)
                mail_vars["recommendationProcess"] = ongoing_recommendation.get_recommendation_process(article, True)

            hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterRecommendedPreprintPrivate", article)

        elif article.status != newStatus:
            mail_vars["tOldStatus"] = current.T(article.status)
            mail_vars["tNewStatus"] = current.T(newStatus)

            hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterPreprintStatusChanged", article)
        else:
            return

        # Fill define template with mail_vars :
        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm_id, article_id=articleId)

        reports = emailing_tools.createMailReport(True, "submitter " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
# Send email to the requester (if any)
def send_to_submitter_acknowledgement_submission(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        mail_vars["articleTitle"] = md_to_html(article.title)

        hashtag_template = emailing_tools.get_correct_hashtag("#SubmitterAcknowledgementSubmission", article)

        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, None, None, articleId)


##############################################################################
def send_to_submitter_scheduled_submission_open(article: Article):
    db, auth = current.db, current.auth
    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
    mail_vars["destAddress"] = db.auth_user[article.user_id].email
    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["recommenderPerson"] = mk_recommender(article)
    mail_vars["linkTarget"] = mk_submitter_my_articles_url(mail_vars)
    mail_vars["ccAddresses"] = [
            mail_vars["appContactMail"], # i.e. contacts.managers
    ] + get_recomm_and_co_recomm_emails(article)

    mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

    hashtag_template = "#SubmitterScheduledSubmissionOpen"
    full_upload_opening_offset: datetime.datetime = db.full_upload_opening_offset
    scheduled_submission_date = get_scheduled_submission_date(article)
    sending_date: Optional[datetime.date] = None

    if scheduled_submission_date:
        sending_date = scheduled_submission_date - full_upload_opening_offset

    if not sending_date or sending_date < datetime.date.today():
        return

    emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, None, None, article.id, sending_date_forced=sending_date)


def mk_recommender(article):
    db, auth = current.db, current.auth
    recomm = db.get_last_recomm(article.id)
    return common_small_html.mkUserWithMail(recomm.recommender_id)


def get_recomm_and_co_recomm_emails(article):
    db = current.db
    recomm = db.get_last_recomm(article.id)
    return [
            db.auth_user[recomm.recommender_id]["email"],
    ] + emailing_vars.get_co_recommenders_mails(recomm.id)


######################################################################################################################################################################
# Send email to the recommenders (if any) for postprints
def send_to_recommender_postprint_status_changed(articleId, newStatus):
    session, auth, db = current.session, current.auth, current.db
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    if article:
        mail_vars["linkTarget"] = URL(
            c="recommender", f="my_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(pressReviews=True)
        )
        for myRecomm in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, db.t_recommendations.id, distinct=True):
            mail_vars["recommender_id"] = myRecomm["recommender_id"]
            mail_vars["destPerson"] = common_small_html.mkUser(mail_vars["recommender_id"])
            mail_vars["destAddress"] = db.auth_user[myRecomm.recommender_id]["email"]
            mail_vars["articleAuthors"] = article.authors
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["tOldStatus"] = current.T(article.status)
            mail_vars["tNewStatus"] = current.T(newStatus)

            # mail_vars["ccAddresses"] = emailing_vars.getCoRecommendersMails(myRecomm.id)

            hashtag_template = "#RecommenderPostprintStatusChanged"
            emailing_tools.insertMailInQueue(hashtag_template, mail_vars, myRecomm.id, None, articleId)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
# Send email to the recommenders (if any)
def send_to_recommender_status_changed(articleId: int, newStatus: str):
    session, auth, db = current.session, current.auth, current.db

    mail_vars: Dict[str, Any] = emailing_tools.getMailCommonVars()
    reports: List[Dict[str, Union[bool, str]]] = []

    mail_vars["recomm_limit_days"] = myconf.get("config.recomm_limit_days", default=50)

    article = db.t_articles[articleId]
    recommendation = Article.get_last_recommendation(articleId)

    if article is not None and recommendation is not None:
        mail_vars["linkTarget"] = URL(
            c="recommender", f="my_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(pressReviews=article.already_published)
        )

        recommender_id = recommendation.recommender_id

        mail_vars["destPerson"] = common_small_html.mkUser(recommender_id)
        mail_vars["destAddress"] = db.auth_user[recommender_id]["email"]
        mail_vars["articleAuthors"] = article.authors
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleDoi"] = XML(common_small_html.mkSimpleDOI(article.doi))
        mail_vars["tOldStatus"] = current.T(article.status)
        mail_vars["tNewStatus"] = current.T(newStatus)

        myRecomm = db(
            (db.t_recommendations.article_id == articleId) &
            (db.t_recommendations.recommender_id == recommender_id)
        ).select(orderby=db.t_recommendations.id).last()

        authors_reply = None
        if article.status == "Awaiting revision" and newStatus == "Under consideration":
            mail_vars["linkTarget"] = URL(
                c="recommender", f="recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(articleId=article.id)
            )
            mail_vars["deadline"] = (datetime.date.today() + datetime.timedelta(weeks=1)).strftime(DEFAULT_DATE_FORMAT)

            mail_vars["ccAddresses"] = emailing_vars.get_co_recommenders_mails(myRecomm.id)

            hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderStatusChangedToUnderConsideration", article)
            authors_reply = emailing_parts.getAuthorsReplyHTML(myRecomm.id)

        elif newStatus == "Recommended":
            mail_vars["linkRecomm"] = URL(c="articles", f="rec", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(id=article.id))
            mail_vars["doiRecomm"] = common_small_html.mkLinkDOI(myRecomm.recommendation_doi)
            mail_vars["bccAddresses"] = emailing_vars.getManagersMails()

            hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderStatusChangedUnderToRecommended", article)

        elif newStatus == "Recommended-private":
            mail_vars["doiRecomm"] = common_small_html.mkLinkDOI(myRecomm.recommendation_doi)

            hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderStatusChangedUnderToRecommendedPrivate", article)

        else:
            hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderArticleStatusChanged", article)

        # Fill define template with mail_vars :
        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, myRecomm.id, None, articleId, authors_reply=authors_reply)

        dest_person_str = str(mail_vars["destPerson"].flatten()) # type: ignore
        reports = emailing_tools.createMailReport(True, dest_person_str, reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_recommender_decision_sent_back(form, articleId, lastRecomm, hashtag):
    if common_tools.is_silent_mode():
        return

    session, auth, db = current.session, current.auth, current.db

    clean_cc_addresses, cc_errors = emailing_tools.clean_addresses(form.vars.cc_mail_addresses)
    cc_addresses = emailing_tools.list_addresses(clean_cc_addresses)

    clean_replyto_adresses, replyto_errors = emailing_tools.clean_addresses(form.vars.replyto)
    replyto_addresses = emailing_tools.list_addresses(clean_replyto_adresses)

    mail_content = mk_mail(form.vars.subject, form.vars.message, resend=True)

    db.mail_queue.insert(
        user_id = auth.user_id,
        dest_mail_address = form.vars.dest_mail_address,
        replyto_addresses = replyto_addresses,
        cc_mail_addresses = cc_addresses,
        mail_subject = form.vars.subject,
        mail_content = mail_content,
        article_id = articleId,
        recommendation_id = lastRecomm,
        mail_template_hashtag = hashtag,
    )

    reports = emailing_tools.createMailReport(True, replyto_addresses, reports=[])
    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
# Do send email to suggested recommenders for a given NO MORE available article
def send_to_suggested_recommenders_not_needed_anymore(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    if article:
        recomm = Article.get_last_recommendation(articleId)
        recomm_id = None
        if recomm:
            recomm_id = recomm.id

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
        mail_vars["articleAuthors"] = mkAuthors(article)

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        # TODO: removing auth.user_id is not the best solution... Should transmit recommender_id
        suggested_recommenders = db(
            (db.t_suggested_recommenders.article_id == articleId)
            & (db.t_suggested_recommenders.suggested_recommender_id != auth.user_id)
            & (db.t_suggested_recommenders.declined == False)
            & (db.t_suggested_recommenders.recommender_validated == True)
            & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)
        ).select(db.t_suggested_recommenders.ALL, db.auth_user.ALL)

        for sugg_recommender in suggested_recommenders:
            mail_vars["destPerson"] = common_small_html.mkUser(sugg_recommender["auth_user.id"])
            mail_vars["destAddress"] = db.auth_user[sugg_recommender["auth_user.id"]]["auth_user.email"]

            # TODO: parallel submission
            hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderSuggestionNotNeededAnymore", article)
            emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm_id, None, articleId)

            reports = emailing_tools.createMailReport(True, "suggested recommender" + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


def mkUnanonymizedAuthors(article):
    return SPAN(article.authors, (" [this is an anonymous submission]"))


######################################################################################################################################################################
# Do send email to suggested recommenders for a given available article
def send_to_suggested_recommenders(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    if article:

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
        mail_vars["articleAuthors"] = mkAuthors(article)

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

            if article.anonymous_submission:
                mail_vars["articleAuthors"] = mkUnanonymizedAuthors(article)

        recomm = Article.get_last_recommendation(articleId)
        recomm_id = None
        if recomm:
            recomm_id = recomm.id

        query = "SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND sr.declined IS FALSE AND sr.recommender_validated IS TRUE AND article_id=%s;"

        suggested_recommenders = db.executesql(
            query,
            placeholders=[article.id],
            as_dict=True,
        )
        for sugg_recommender in suggested_recommenders:
            mail_vars["destPerson"] = common_small_html.mkUser(sugg_recommender["id"])
            mail_vars["destAddress"] = db.auth_user[sugg_recommender["id"]]["email"]
            mail_vars["linkTarget"] = URL(
                c="recommender", f="article_details", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )
            mail_vars["helpurl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            if article.parallel_submission:
                mail_vars["addNote"] = (
                    "<b>Note:</b> The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appName)s, and hope you will agree to manage this preprint. If the authors abandon the process at %(appName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appName)s website as recognition of the reviewers' work and in order to enable critical discussion."
                    % mail_vars
                )
            else:
                mail_vars["addNote"] = ""

            hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderSuggestedArticle", article)
            sugg_recommender_buttons = build_sugg_recommender_buttons(mail_vars["linkTarget"], articleId, sugg_recommender["id"])

            emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm_id, None, articleId, sugg_recommender_buttons=sugg_recommender_buttons)

            delete_reminder_for_submitter("#ReminderSubmitterSuggestedRecommenderNeeded", articleId)

            reports = emailing_tools.createMailReport(True, "suggested recommender" + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


def build_sugg_recommender_buttons(link_target: str, article_id: int, suggested_recommender_id: int):
    common_mail_vars = emailing_tools.getMailCommonVars()
    suggested_recommender = SuggestedRecommender.get_by_article_and_user_id(article_id, suggested_recommender_id)
    if not suggested_recommender:
        return

    declineLinkTarget = URL(
                c="recommender_actions",
                f="decline_new_article_to_recommend",
                vars=dict(articleId=article_id, quick_decline_key=suggested_recommender.quick_decline_key),
                scheme=common_mail_vars["scheme"],
                host=common_mail_vars["host"],
                port=common_mail_vars["port"],
            )

    sugg_recommender_buttons = DIV(
                A(
                    SPAN(
                        current.T("Yes, I would like to handle the evaluation process"),
                        _style="margin: 10px; font-size: 14px; background: #93c54b; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px; display: block",
                    ),
                    _href=link_target,
                    _style="text-decoration: none; display: block",
                ),
                B(current.T("OR")),
                A(
                    SPAN(
                        current.T("No, I would rather not"),
                        _style="margin: 10px; font-size: 14px; background: #f47c3c; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px; display: block",
                    ),
                    _href=declineLinkTarget,
                    _style="text-decoration: none; display: block",
                ),
                _style="width: 100%; text-align: center; margin-bottom: 25px;",
            )

    return sugg_recommender_buttons


######################################################################################################################################################################
# Do send email to suggested recommenders for a given available article
def send_to_suggested_recommender(article: Article, recommender_id: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    suggested_recommender = User.get_by_id(recommender_id)
    if suggested_recommender and suggested_recommender.email:

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
        mail_vars["articleAuthors"] = mkAuthors(article)

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

            if article.anonymous_submission:
                mail_vars["articleAuthors"] = mkUnanonymizedAuthors(article)

        recomm = Article.get_last_recommendation(article.id)
        recomm_id = None
        if recomm:
            recomm_id = recomm.id

        mail_vars["destPerson"] = common_small_html.mkUser(recommender_id)
        mail_vars["destAddress"] = suggested_recommender.email
        mail_vars["linkTarget"] = URL(
            c="recommender", f="article_details", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
        )
        mail_vars["helpurl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        if article.parallel_submission:
            mail_vars["addNote"] = (
                "<b>Note:</b> The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appName)s, and hope you will agree to manage this preprint. If the authors abandon the process at %(appName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appName)s website as recognition of the reviewers' work and in order to enable critical discussion."
                % mail_vars
            )
        else:
            mail_vars["addNote"] = ""

        hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderSuggestedArticle", article)
        sugg_recommender_buttons = build_sugg_recommender_buttons(mail_vars["linkTarget"], article.id, recommender_id)

        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm_id, None, article.id, sugg_recommender_buttons=sugg_recommender_buttons)

        delete_reminder_for_submitter("#ReminderSubmitterSuggestedRecommenderNeeded", article.id)

        reports = emailing_tools.createMailReport(True, "suggested recommender" + mail_vars["destPerson"].flatten(), reports) # type: ignore

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
# Do send email to recommender when a review is closed
def send_to_recommenders_review_completed(reviewId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    reports = []

    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = md_to_html(article.title)
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
                mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
                mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
                mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(rev.reviewer_id)

                hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderReviewerReviewCompleted", article)

                reviewHTML = emailing_parts.getReviewHTML(rev.id)

                emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id, review=reviewHTML)

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
# Do send email to recommender when a review is accepted for consideration
def send_to_recommenders_review_considered(reviewId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["articleAuthors"] = mkAuthors(article)
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )
            mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
            mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
            mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(rev.reviewer_id)
            mail_vars["expectedDuration"] = datetime.timedelta(days=get_review_days(rev))
            mail_vars["dueTime"] = str((datetime.datetime.now() + mail_vars["expectedDuration"]).strftime(DEFAULT_DATE_FORMAT))

            if pciRRactivated:
                mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

            hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderReviewConsidered", article)

            emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_recommenders_review_declined(reviewId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["articleAuthors"] = mkAuthors(article)
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )
            mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
            recommender = db.auth_user[recomm.recommender_id]
            if recommender is not None:
                mail_vars["destAddress"] = recommender["email"]
                mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(rev.reviewer_id)

                hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderReviewDeclined", article)

                emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_recommenders_pending_review_request(reviewId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["articleAuthors"] = mkAuthors(article)
            mail_vars["linkTarget"] = URL(
                c="recommender", f="recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(articleId=article.id),
            )
            mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
            mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
            mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(rev.reviewer_id)

            hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderPendingReviewRequest", article)

            emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
# Do send email to recommender when a review is re-opened
def send_to_reviewer_review_reopened(reviewId, newForm):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["linkTarget"] = URL(c="user", f="my_reviews", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["articleTitle"] = B(md_to_html(article.title))
            mail_vars["articleAuthors"] = mkAuthors(article)

            reviewer = db.auth_user[rev.reviewer_id]
            if reviewer:
                mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(recomm.recommender_id) or ""
                mail_vars["destPerson"] = common_small_html.mkUser(rev.reviewer_id)
                mail_vars["destAddress"] = db.auth_user[rev.reviewer_id]["email"]

                mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(recomm.id)

                hashtag_template = emailing_tools.get_correct_hashtag("#ReviewerReviewReopened", article)

                emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_reviewers_article_cancellation(articleId, newStatus):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    if article:
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
        mail_vars["articleAuthors"] = mkAuthors(article)
        mail_vars["linkTarget"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=True), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        lastRecomm = db.get_last_recomm(article.id)
        if lastRecomm:
            reviewers = db((db.t_reviews.recommendation_id == lastRecomm.id) & (db.t_reviews.review_state in ("Awaiting response", "Awaiting review", "Review completed"))).select()
            for rev in reviewers:
                if rev is not None and rev.reviewer_id is not None:
                    mail_vars["destPerson"] = common_small_html.mkUser(rev.reviewer_id)
                    mail_vars["destAddress"] = db.auth_user[rev.reviewer_id]["email"]
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(lastRecomm.recommender_id)

                    mail_vars["ccAddresses"] = [db.auth_user[lastRecomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(lastRecomm.id)

                    hashtag_template = emailing_tools.get_correct_hashtag("#ReviewersArticleCancellation", article)

                    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, lastRecomm.id, None, article.id)

                    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)
        else:
            pass #("send_to_reviewers_article_cancellation: Recommendation not found")
    else:
        pass #("send_to_reviewers_article_cancellation: Article not found")

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_reviewer_review_request_accepted(reviewId, newForm):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    if rev:
        recomm = db.t_recommendations[rev.recommendation_id]
        if recomm:
            article = db.t_articles[recomm["article_id"]]
            if article:
                mail_vars["articleTitle"] = md_to_html(article.title)
                mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                mail_vars["articleAuthors"] = mkAuthors(article)
                mail_vars["linkTarget"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=False), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

                reviewer = db.auth_user[rev.reviewer_id]
                if reviewer:
                    mail_vars["destPerson"] = common_small_html.mkUser(rev.reviewer_id)
                    mail_vars["destAddress"] = reviewer["email"]

                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(recomm.recommender_id) or ""
                    mail_vars["expectedDuration"] = datetime.timedelta(days=get_review_days(rev))
                    mail_vars["dueTime"] = str((datetime.datetime.now() + mail_vars["expectedDuration"]).strftime(DEFAULT_DATE_FORMAT))

                    mail_vars["reviewDuration"] = (rev.review_duration).lower()

                    hashtag_template = emailing_tools.get_correct_hashtag("#ReviewerReviewRequestAccepted", article)

                    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

                    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_reviewer_review_request_declined(reviewId, newForm):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    if rev:
        recomm = db.t_recommendations[rev.recommendation_id]
        if recomm:
            article = db.t_articles[recomm["article_id"]]
            if article:
                mail_vars["articleTitle"] = md_to_html(article.title)
                mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                mail_vars["articleAuthors"] = mkAuthors(article)
                mail_vars["linkTarget"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=False), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

                reviewer = db.auth_user[rev.reviewer_id]
                if reviewer:
                    mail_vars["destPerson"] = common_small_html.mkUser(rev.reviewer_id)
                    mail_vars["destAddress"] = reviewer["email"]

                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(recomm.recommender_id) or ""
                    mail_vars["expectedDuration"] = datetime.timedelta(days=get_review_days(rev))
                    mail_vars["dueTime"] = str((datetime.datetime.now() + mail_vars["expectedDuration"]).strftime(DEFAULT_DATE_FORMAT))

                    hashtag_template = emailing_tools.get_correct_hashtag("#ReviewerReviewRequestDeclined", article)

                    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

                    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_thank_reviewer_acceptation(reviewId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    review = Review.get_by_id(reviewId)
    if not review:
        emailing_tools.getFlashMessage(reports)
        return

    recommendation = Recommendation.get_by_id(review.recommendation_id)
    if not recommendation:
        emailing_tools.getFlashMessage(reports)
        return

    article = Article.get_by_id(recommendation.article_id)
    if not article:
        emailing_tools.getFlashMessage(reports)
        return

    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
    mail_vars["articleAuthors"] = mkAuthors(article)

    if pciRRactivated:
        mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

    reviewer = User.get_by_id(review.reviewer_id)
    if reviewer:
        mail_vars["linkTarget"] = URL(c="default", f="invitation_to_review", vars=dict(reviewId=review.id, key=reviewer.reset_password_key), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]) #URL(c="user", f="my_reviews", vars=dict(pendingOnly=False), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
        mail_vars["destAddress"] = reviewer["email"]

        mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(recommendation.recommender_id) or ""
        mail_vars["expectedDuration"] = datetime.timedelta(days=get_review_days(review))
        mail_vars["dueTime"] = Review.get_due_date(review).strftime(DEFAULT_DATE_FORMAT)
        mail_vars["reviewDuration"] = (review.review_duration).lower()

        mail_vars["ccAddresses"] = [db.auth_user[recommendation.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(recommendation.id)

        hashtag_template = emailing_tools.get_correct_hashtag("#ReviewerThankForReviewAcceptation", article)

        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recommendation.id, None, article.id)

        reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_thank_reviewer_done(reviewId, newForm):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    rev = db.t_reviews[reviewId]
    if rev:
        recomm = db.t_recommendations[rev.recommendation_id]
        if recomm:
            article = db.t_articles[recomm["article_id"]]
            if article:
                mail_vars["articleTitle"] = md_to_html(article.title)
                mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                mail_vars["articleAuthors"] = mkAuthors(article)
                mail_vars["linkTarget"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=False), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

                mail_vars["parallelText"] = ""
                if parallelSubmissionAllowed:
                    mail_vars[
                        "parallelText"
                    ] += """Note that if the authors abandon the process at %(appLongName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appLongName)s website as recognition of their work and in order to enable critical discussion.""" % mail_vars
                    if article.parallel_submission:
                        mail_vars[
                            "parallelText"
                        ] += """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appLongName)s, and hope you will agree to review this preprint.""" % mail_vars

                reviewer = db.auth_user[rev.reviewer_id]
                if reviewer:
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(recomm.recommender_id) or ""
                    mail_vars["destPerson"] = common_small_html.mkUser(rev.reviewer_id)
                    mail_vars["destAddress"] = reviewer["email"]

                    hashtag_template = emailing_tools.get_correct_hashtag("#ReviewerThankForReviewDone", article)

                    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

                    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_admin_2_reviews_under_consideration(reviewId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    article = db((db.t_articles.id == recomm.article_id)).select().last()

    count_reviews_under_consideration = 0
    if recomm:
        count_reviews_under_consideration = db(
            (db.t_reviews.recommendation_id == recomm.id) & ((db.t_reviews.review_state == "Awaiting review") | (db.t_reviews.review_state == "Review completed"))
        ).count()

    if recomm and article and count_reviews_under_consideration == 2:
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["linkTarget"] = URL(c="manager", f="recommendations", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        hashtag_template = emailing_tools.get_correct_hashtag("#AdminTwoReviewersIn", article)

        admins = db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "administrator")).select(
            db.auth_user.ALL
        )

        dest_emails = []
        for admin in admins:
            dest_emails.append(admin.email)

        if dest_emails != []:
            merge_mails(hashtag_template, mail_vars, recomm.id, None, article.id, dest_emails, dest_role=None)


######################################################################################################################################################################
def send_to_admin_all_reviews_completed(reviewId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    article = db((db.t_articles.id == recomm.article_id)).select().last()

    count_reviews_completed = 0
    count_reviews_under_consideration = 0
    if recomm:
        count_reviews_completed = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Review completed")).count()
        count_reviews_under_consideration = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Awaiting review")).count()

    if recomm and article and count_reviews_completed >= 2 and count_reviews_under_consideration == 0:
        delete_reminder_for_recommender("#ReminderRecommender2ReviewsReceivedCouldMakeDecision", recomm.id)

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["linkTarget"] = URL(c="manager", f="recommendations", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        hashtag_template = emailing_tools.get_correct_hashtag("#AdminAllReviewsCompleted", article)

        admins = db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "administrator")).select(
            db.auth_user.ALL
        )

        dest_emails = []
        for admin in admins:
            dest_emails.append(admin.email)

        if dest_emails != []:
            merge_mails(hashtag_template, mail_vars, recomm.id, None, article.id, dest_emails, dest_role=None)


######################################################################################################################################################################
def send_admin_new_user(userId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    admins = db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "administrator")).select(
        db.auth_user.ALL
    )

    user = db.auth_user[userId]
    if user:
        mail_vars["userTxt"] = common_small_html.mkUser(userId)
        mail_vars["userMail"] = user.email
        hashtag_template = "#AdminNewUser"

        dest_emails = []
        for admin in admins:
            dest_emails.append(admin.email)

        if dest_emails != []:
            reports = merge_mails(hashtag_template, mail_vars, recomm_id=None, recommendation=None, article_id=None, dest_emails=dest_emails, dest_role="administrators")

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_new_user(userId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    # get thematics and alerts
    user = db.auth_user[userId]
    if type(user.thematics) is list:
        thema = user.thematics
    else:
        thema = list(user.thematics or '')
    if type(user.alerts) is list:
        alerts = user.alerts
    else:
        alerts = list(user.alerts or "[no alerts]")

    if user:
        mail_vars["destPerson"] = common_small_html.mkUser(userId)
        mail_vars["destAddress"] = db.auth_user[userId]["email"]
        mail_vars["baseurl"] = URL(c="about", f="about", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["infourl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["recommurl"] = URL(c="about", f="recommenders", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["thematics"] = ", ".join(thema)
        mail_vars["days"] = ", ".join(alerts)

        if parallelSubmissionAllowed:
            hashtag_template = "#NewUserParallelSubmissionAllowed"
        else:
            hashtag_template = "#NewUser"

        emailing_tools.insertMailInQueue(hashtag_template, mail_vars)

        reports = emailing_tools.createMailReport(True, "new user " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_new_membreship(membershipId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    user = db.auth_user[db.auth_membership[membershipId].user_id]
    group = db.auth_group[db.auth_membership[membershipId].group_id]
    if user and group:
        mail_vars["destPerson"] = common_small_html.mkUser(user.id)
        mail_vars["destAddress"] = db.auth_user[user.id]["email"]

        if group.role == "recommender":
            mail_vars["days"] = ", ".join(user.alerts)
            mail_vars["baseurl"] = URL(c="default", f="index", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["helpurl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            mail_vars["bccAddresses"] = emailing_vars.getManagersMails()

            hashtag_template = "#NewMembreshipRecommender"
            new_role_report = "new recommender "

        elif group.role == "manager":
            mail_vars["bccAddresses"] = emailing_vars.getAdminsMails()

            hashtag_template = "#NewMembreshipManager"
            new_role_report = "new manager "

        else:
            return

        emailing_tools.insertMailInQueue(hashtag_template, mail_vars)

        reports = emailing_tools.createMailReport(True, new_role_report + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_managers(articleId: int, newStatus: str):
    session, auth, db, response = current.session, current.auth, current.db, current.response

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    if article:
        recomm = db((db.t_recommendations.article_id == articleId)).select(orderby=db.t_recommendations.id).last()
        recomm_id = None
        if recomm:
            recomm_id = recomm.id

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = article.authors
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)

        if article.user_id:
            mail_vars["submitterPerson"] = common_small_html.mkUser(article.user_id)  # submitter
        else:
            mail_vars["submitterPerson"] = "?"

        if newStatus == "Pending":
            mail_vars["linkTarget"] = URL(c="manager", f="pending_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            hashtag_template = emailing_tools.get_correct_hashtag("#ManagersPreprintSubmission", article)

        elif newStatus == "Resubmission":
            mail_vars["linkTarget"] = URL(c="manager", f="recommendations", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            hashtag_template = emailing_tools.get_correct_hashtag("#ManagersPreprintResubmission", article)

        elif newStatus.startswith("Pre-"):
            if recomm is not None:
                mail_vars["recommenderPerson"] = common_small_html.mkUser(recomm.recommender_id) or ""  # recommender
            else:
                mail_vars["recommenderPerson"] = "?"
            mail_vars["linkTarget"] = URL(c="manager", f="pending_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            mail_vars["recommendationProcess"] = ongoing_recommendation.get_recommendation_process(article, True)
            hashtag_template = emailing_tools.get_correct_hashtag("#ManagersRecommendationOrDecision", article)

        elif newStatus == "Under consideration":
            recomm = db((db.t_recommendations.article_id == articleId)).select(orderby=db.t_recommendations.id).last()
            if recomm is not None:
                mail_vars["recommenderPerson"] = common_small_html.mkUser(recomm.recommender_id) or ""  # recommender
            else:
                mail_vars["recommenderPerson"] = "?"

            mail_vars["linkTarget"] = URL(c="manager", f="ongoing_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["recommendationProcess"] = ongoing_recommendation.get_recommendation_process(article, True)

            if article.status == "Awaiting revision":
                hashtag_template = emailing_tools.get_correct_hashtag("#AdminArticleResubmited", article)
            else:
                hashtag_template = emailing_tools.get_correct_hashtag("#ManagersArticleConsideredForRecommendation", article)

        elif newStatus == "Cancelled":
            mail_vars["linkTarget"] = URL(c="manager", f="completed_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            hashtag_template = emailing_tools.get_correct_hashtag("#ManagersArticleCancelled", article)
            current.coar.send_acknowledge_and_reject(article)

        else:
            mail_vars["linkTarget"] = URL(c="manager", f="all_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["tOldStatus"] = current.T(article.status)
            mail_vars["tNewStatus"] = current.T(newStatus)

            hashtag_template = emailing_tools.get_correct_hashtag("#ManagersArticleStatusChanged", article)

        for_admins = [
            "#AdminArticleResubmited",
            "#ManagersArticleConsideredForRecommendation",
            "#ManagersArticleStatusChanged",
        ]
        if hashtag_template in listCorrectHashtags(for_admins, article):
            dest_emails = emailing_vars.getAdminsMails()
            dest_role = "admin"
        else:
            dest_emails = emailing_vars.getManagersMails()
            dest_role = "manager"
        reports = merge_mails(hashtag_template, mail_vars, recomm_id, None, article.id, dest_emails, dest_role)

    emailing_tools.getFlashMessage(reports)


def merge_mails(hashtag_template, mail_vars, recomm_id, recommendation, article_id, dest_emails, dest_role=None, sugg_recommender_buttons=None):
    db, auth = current.db, current.auth
    email_destinations = ','.join(dest_emails)
    mail_vars["destAddress"] = email_destinations

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm_id, recommendation, article_id, sugg_recommender_buttons=sugg_recommender_buttons)
    if dest_role:
        report = emailing_tools.createMailReport(True, dest_role + ' ' + (email_destinations or ''), [])
        return report


def listCorrectHashtags(hashtags, article):
    return [ emailing_tools.get_correct_hashtag(hashtag, article) for hashtag in hashtags ]


######################################################################################################################################################################
def send_to_thank_recommender_postprint(recommId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    recomm = db.t_recommendations[recommId]
    if recomm:
        article = db.t_articles[recomm.article_id]
        if article:
            mail_vars["articleTitle"] = md_to_html(article.title)
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
                # recommender = common_small_html.mkUser(recomm.recommender_id)
                mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
                mail_vars["destAddress"] = recommender["email"]

                hashtag_template = "#RecommenderThankForPostprint"
                emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_thank_recommender_preprint(articleId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    if articleId:
        article = db.t_articles[articleId]
        if article:
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleAuthors"] = article.authors
            mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
            mail_vars["linkTarget"] = URL(
                c="recommender", f="my_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(pressReviews=False)
            )

            if pciRRactivated:
                mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

            recomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.id).last()
            if recomm:
                recommender = db.auth_user[recomm.recommender_id]
                if recommender:
                    mail_vars["destPerson"] = common_small_html.mkUser(recommender.id)
                    mail_vars["destAddress"] = recommender["email"]
                    mail_vars["reviewDuration"] = default_review_duration.lower()

                    if article.parallel_submission:

                        hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderThankForPreprintParallelSubmission", article)
                    else:

                        hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderThankForPreprint", article)

                    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

                    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_delete_one_corecommender(contribId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    if contribId:
        contrib = db.t_press_reviews[contribId]
        if contrib:
            recomm = db.t_recommendations[contrib.recommendation_id]
            if recomm:
                article = db.t_articles[recomm.article_id]
                if article:
                    if not (contrib.contributor_id and db.auth_user[contrib.contributor_id].email):
                        return
                    if not (recomm.recommender_id and db.auth_user[recomm.recommender_id].email):
                        return
                    mail_vars["articleTitle"] = md_to_html(article.title)
                    mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                    mail_vars["articleAuthors"] = mkAuthors(article)
                    mail_vars["articlePrePost"] = "postprint" if article.already_published else "preprint"
                    mail_vars["linkTarget"] = URL(c="recommender", f="my_co_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                    mail_vars["destPerson"] = common_small_html.mkUser(contrib.contributor_id)
                    mail_vars["destAddress"] = db.auth_user[contrib.contributor_id]["email"]
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(recomm.recommender_id) or ""
                    mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]]
                    mail_vars["bccAddresses"] = emailing_vars.getManagersMails()

                    hashtag_template = emailing_tools.get_correct_hashtag("#CoRecommenderRemovedFromArticle", article)

                    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

                    reports = emailing_tools.createMailReport(True, "contributor " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_one_corecommender(contribId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    if contribId:
        contrib = db.t_press_reviews[contribId]
        if contrib:
            recomm = db.t_recommendations[contrib.recommendation_id]
            if recomm:
                article = db.t_articles[recomm.article_id]
                if article:
                    mail_vars["articleTitle"] = md_to_html(article.title)
                    mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
                    mail_vars["articleAuthors"] = mkAuthors(article)
                    mail_vars["articlePrePost"] = "postprint" if article.already_published else "preprint"
                    mail_vars["linkTarget"] = URL(c="recommender", f="my_co_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                    mail_vars["destPerson"] = common_small_html.mkUser(contrib.contributor_id)
                    mail_vars["destAddress"] = db.auth_user[contrib.contributor_id]["email"]
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(recomm.recommender_id) or ""

                    if article.status in ("Under consideration", "Pre-recommended", "Pre-recommended-private"):
                        mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]]
                        mail_vars["bccAddresses"] = emailing_vars.getManagersMails()

                        if article.already_published:
                            hashtag_template = emailing_tools.get_correct_hashtag("#CoRecommenderAddedOnArticleAlreadyPublished", article)
                        else:
                            hashtag_template = emailing_tools.get_correct_hashtag("#CoRecommenderAddedOnArticle", article)

                        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

                        reports = emailing_tools.createMailReport(True, "contributor " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_corecommenders(articleId, newStatus):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    article = db.t_articles[articleId]
    recomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.id).last()
    if recomm:
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
        mail_vars["articleAuthors"] = mkAuthors(article)
        mail_vars["articlePrePost"] = "postprint" if article.already_published else "preprint"
        mail_vars["tOldStatus"] = current.T(article.status)
        mail_vars["tNewStatus"] = current.T(newStatus)
        mail_vars["linkTarget"] = URL(c="recommender", f="my_co_recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
        mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(recomm.recommender_id) or ""

        contribs = Recommendation.get_co_recommenders(recomm.id)
        for contrib in contribs:
            mail_vars["destPerson"] = common_small_html.mkUser(contrib.contributor_id)
            dest = db.auth_user[contrib.contributor_id]
            if dest:
                mail_vars["destAddress"] = dest["email"]
            else:
                mail_vars["destAddress"] = ""

            if newStatus == "Recommended":
                mail_vars["recommDOI"] = common_small_html.mkLinkDOI(recomm.recommendation_doi)
                mail_vars["linkRecomm"] = URL(c="articles", f="rec", vars=dict(id=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                hashtag_template = emailing_tools.get_correct_hashtag("#CoRecommendersArticleRecommended", article)
            elif newStatus == "Recommended-private":
                mail_vars["recommDOI"] = common_small_html.mkLinkDOI(recomm.recommendation_doi)
                hashtag_template = emailing_tools.get_correct_hashtag("#CoRecommendersArticleRecommendedPrivate", article)
            else:
                if newStatus == "Cancelled":
                    mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]]

                hashtag_template = emailing_tools.get_correct_hashtag("#CoRecommendersArticleStatusChanged", article)

            emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

            reports = emailing_tools.createMailReport(True, "contributor " + mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_decision_to_reviewers(articleId, newStatus):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    recomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.id).last()
    if recomm:
        article = db.t_articles[recomm["article_id"]]
        if article:
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleStatus"] = current.T(newStatus)
            mail_vars["linkTarget"] = URL(c="user", f="my_reviews", vars=dict(pendingOnly=False), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["myRefArticle"] = common_small_html.mkArticleCitation(recomm)
            mail_vars["myRefRecomm"] = common_small_html.mkRecommCitation(recomm)

            if newStatus == "Recommended":
                reviewers = db(
                    (db.auth_user.id == db.t_reviews.reviewer_id)
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    & (db.t_recommendations.article_id == article.id)
                    & (db.t_reviews.review_state == "Review completed")
                ).select(db.t_reviews.id, db.auth_user.ALL, distinct=db.auth_user.email)
            else:
                reviewers = db(
                    (db.auth_user.id == db.t_reviews.reviewer_id) & (db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Review completed")
                ).select(db.t_reviews.id, db.auth_user.ALL, distinct=db.auth_user.email)

            for rev in reviewers:
                mail_vars["destPerson"] = common_small_html.mkUser(rev.auth_user.id)
                mail_vars["destAddress"] = rev.auth_user.email

                if newStatus == "Recommended":
                    mail_vars["recommDOI"] = common_small_html.mkLinkDOI(recomm.recommendation_doi)
                    mail_vars["linkRecomm"] = URL(c="articles", f="rec", vars=dict(id=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                    hashtag_template = emailing_tools.get_correct_hashtag("#ReviewersArticleRecommended", article)
                elif newStatus == "Recommended-private":
                    mail_vars["recommDOI"] = common_small_html.mkLinkDOI(recomm.recommendation_doi)
                    hashtag_template = emailing_tools.get_correct_hashtag("#ReviewersArticleRecommendedPrivate", article)
                else:
                    hashtag_template = emailing_tools.get_correct_hashtag("#ReviewersArticleStatusChanged", article)

                recommender_email = [
                        db.auth_user[recomm.recommender_id]["email"]
                ] if db.auth_user[recomm.recommender_id] else []
                mail_vars["ccAddresses"] = recommender_email + emailing_vars.get_co_recommenders_mails(recomm.id) \

                emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, article.id)

                reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
# Mail for Scheduled submission
#
# The following two send_to are only ever called with pciRRactivated
#
######################################################################################################################################################################
def send_to_reviewers_preprint_submitted(articleId):
    session, auth, db = current.session, current.auth, current.db

    article = db.t_articles[articleId]
    finalRecomm = db(db.t_recommendations.article_id == articleId).select().last()

    if article and finalRecomm:

        reviews = db((db.t_reviews.recommendation_id == finalRecomm.id) & (db.t_reviews.review_state == "Awaiting review")).select()

        mail_vars = emailing_tools.getMailCommonVars()

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleDoi"] = article.doi

        mail_vars["sender"] = mkSender(finalRecomm)
        mail_vars["recommenderPerson"] = common_small_html.mkUser(finalRecomm.recommender_id)

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))
            mail_vars.update(getPCiRRinvitationTexts(article))
            mail_vars["ccAddresses"] = [db.auth_user[finalRecomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(finalRecomm.id)

        for review in reviews:
            # Get common variables :
            reports = []

            # Set custom variables :
            mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]
            mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
            mail_vars["linkTarget"] = URL(c="default", f="index", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            # Insert mail in mail_queue :
            hashtag_template = emailing_tools.get_correct_hashtag("#ReviewerFullPreprint", article, force_scheduled=True)
            emailing_tools.insertMailInQueue(hashtag_template, mail_vars, finalRecomm.id, None, article.id)

            # Create report for session flash alerts :
            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

            # Build reports :
            emailing_tools.getFlashMessage(reports)


def mkSender(recomm):
    db, auth = current.db, current.auth
    if auth.user_id == recomm.recommender_id:
        sender = common_small_html.mkUser(recomm.recommender_id).flatten()
    else:
        sender = "The Managing Board of " + myconf.get("app.longname") + " on behalf of " + common_small_html.mkUser(recomm.recommender_id).flatten()

    return sender

######################################################################################################################################################################
def send_to_recommender_preprint_submitted(articleId):
    session, auth, db = current.session, current.auth, current.db

    article = db.t_articles[articleId]
    finalRecomm = db(db.t_recommendations.article_id == articleId).select().last()

    if article and finalRecomm:
        # Get common variables :
        mail_vars = emailing_tools.getMailCommonVars()
        reports = []

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleDoi"] = article.doi
        mail_vars["articleAuthors"] = mkAuthors(article)

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))
            mail_vars.update(getPCiRRinvitationTexts(article))

        # Set custom variables :
        mail_vars["destAddress"] = db.auth_user[finalRecomm.recommender_id]["email"]
        mail_vars["destPerson"] = common_small_html.mkUser(finalRecomm.recommender_id)
        mail_vars["linkTarget"] = URL(c="default", f="index", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        # Insert mail in mail_queue :
        hashtag_template = "#RecommenderPreprintSubmittedScheduledSubmission"
        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, finalRecomm.id, None, article.id)

        # Create report for session flash alerts :
        reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

        # Build reports :
        emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
def send_to_recommender_preprint_validated(articleId):
    session, auth, db = current.session, current.auth, current.db

    article = db.t_articles[articleId]
    finalRecomm = db(db.t_recommendations.article_id == articleId).select().last()

    if article and finalRecomm:
        # Get common variables :
        mail_vars = emailing_tools.getMailCommonVars()
        reports = []

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleDoi"] = article.doi
        mail_vars["articleAuthors"] = mkAuthors(article)

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))
            mail_vars.update(getPCiRRinvitationTexts(article))
        # Set custom variables :
        mail_vars["destAddress"] = db.auth_user[finalRecomm.recommender_id]["email"]
        mail_vars["destPerson"] = common_small_html.mkUser(finalRecomm.recommender_id)
        # Insert mail in mail_queue :
        hashtag_template = "#RecommenderPreprintValidatedScheduledSubmission"
        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, finalRecomm.id, None, article.id)

        # Create report for session flash alerts :
        reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

        # Build reports :
        emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
# Mail with templates
######################################################################################################################################################################
def send_reviewer_invitation(reviewId: int,
                             replyto_addresses: str,
                             cc_addresses: List[str],
                             hashtag_template: str,
                             subject: str,
                             message: str,
                             reset_password_key: Optional[str] = None,
                             linkTarget: Optional[str] = None,
                             declineLinkTarget: Optional[str] = None,
                             new_round: bool = False,
                             new_stage: bool = False):
    session, auth, db = current.session, current.auth, current.db

    reg_user_reminder_template = None
    new_user_reminder_template = None

    reports: List[Dict[str, Union[bool, str]]] = []

    review = Review.get_by_id(reviewId)
    if not review:
        emailing_tools.getFlashMessage(reports)
        return

    recommendation = Recommendation.get_by_id(review.recommendation_id)
    if not recommendation:
        emailing_tools.getFlashMessage(reports)
        return

    article = Article.get_by_id(recommendation.article_id)
    if not article:
        emailing_tools.getFlashMessage(reports)
        return

    reviewer = User.get_by_id(review.reviewer_id)
    if not reviewer:
        emailing_tools.getFlashMessage(reports)
        return

    sender: Optional[User] = None
    if auth.has_membership(role="manager"):
        sender = User.get_by_id(recommendation.recommender_id)
    else:
        sender = cast(User, auth.user)

    if not sender:
        return

    mail_vars = emailing_tools.getMailForReviewerCommonVars(sender, article, recommendation, reviewer.last_name)
    mail_vars["LastName"] = reviewer.last_name
    mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
    mail_vars["destAddress"] = reviewer.email
    mail_vars["reviewDuration"] = (review.review_duration).lower() if review.review_duration else ''
    message = emailing_tools.replaceMailVars(message, mail_vars)

    content = DIV(WIKI(message, safe_mode=''))
    reviewer_invitation_buttons = None

    if reset_password_key:
        if linkTarget:
            linkVars = dict(key=reset_password_key, _next=linkTarget, reviewId=review.id)
        else:
            linkVars = dict(key=reset_password_key, reviewId=review.id)

        link = URL(
                c="default",
                f="invitation_to_review",
                vars=linkVars,
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
            )

        if declineLinkTarget and review.review_duration:
            reviewer_invitation_buttons = generate_reviewer_invitation_buttons(link, declineLinkTarget, review.review_duration, article)
        if hashtag_template == "#DefaultReviewInvitationNewUserStage2":
            new_user_reminder_template = emailing_tools.get_correct_hashtag("#ReminderReviewerReviewInvitationNewUser", article)

        create_reminder_for_reviewer_review_invitation_new_user(review.id, replyto_addresses, message, reviewer_invitation_buttons=reviewer_invitation_buttons, hashtag_template=new_user_reminder_template, new_stage=new_stage)

    elif linkTarget:
        if review.review_state is None or review.review_state == "Awaiting response" or review.review_state == "":
            if declineLinkTarget and review.review_duration:
                reviewer_invitation_buttons = generate_reviewer_invitation_buttons(linkTarget, declineLinkTarget, review.review_duration, article)

        elif review.review_state == "Awaiting review":
            reviewer_invitation_buttons = DIV(P(B(current.T("TO WRITE, EDIT OR UPLOAD YOUR REVIEW CLICK ON THE FOLLOWING LINK:"))), A(linkTarget, _href=linkTarget))

        if hashtag_template == "#DefaultReviewInvitationRegisteredUserNewReviewerStage2":
            reg_user_reminder_template = emailing_tools.get_correct_hashtag("#ReminderReviewInvitationRegisteredUserNewReviewer", article)
        if hashtag_template == "#DefaultReviewInvitationRegisteredUserReturningReviewerStage2":
            reg_user_reminder_template = emailing_tools.get_correct_hashtag("#ReminderReviewInvitationRegisteredUserReturningReviewer", article)

        create_reminder_for_reviewer_review_invitation_registered_user(review.id, replyto_addresses, message, reviewer_invitation_buttons=reviewer_invitation_buttons, new_round=new_round, hashtag_template=reg_user_reminder_template, new_stage=new_stage)

    subject_header = email_subject_header(recommendation.article_id)
    subject_without_appname = subject.replace("%s: " % subject_header, "")
    applogo = URL("static", "images/small-background.png", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
    authors_reply = None
    if new_round:
        prev_recomm = common_tools.get_prev_recomm(recommendation)
        authors_reply = emailing_parts.getAuthorsReplyHTML(prev_recomm.id)

    message: ... = render(
        filename=MAIL_HTML_LAYOUT,
        context=dict(
            subject=subject_without_appname,
            applogo=applogo,
            appname=mail_vars["appName"],
            content=XML(content),
            footer=emailing_tools.mkFooter(),
            reviewer_invitation_buttons=reviewer_invitation_buttons,
            authors_reply=authors_reply,
        ),
    )

    mail_vars["ccAddresses"] = cc_addresses + emailing_vars.get_co_recommenders_mails(recommendation.id)
    mail_vars["replytoAddresses"] = replyto_addresses

    sender_name = None
    if not pciRRactivated and sender:
        sender_name = f'{sender.first_name} {sender.last_name}'
    ccAddresses = exempt_addresses(mail_vars["ccAddresses"], hashtag_template)
    if not common_tools.is_silent_mode():
        db.mail_queue.insert(
            dest_mail_address=mail_vars["destAddress"],
            cc_mail_addresses=ccAddresses,
            replyto_addresses=mail_vars["replytoAddresses"],
            mail_subject=subject,
            mail_content=message,
            user_id=auth.user_id,
            recommendation_id=recommendation.id,
            mail_template_hashtag=hashtag_template,
            article_id=recommendation.article_id,
            sender_name=sender_name,
            review_id=reviewId
        )

    if review.review_state is None:
        review.review_state = "Awaiting response"
        review.update_record() # type: ignore

    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports) # type: ignore

    emailing_tools.getFlashMessage(reports)


def generate_reviewer_invitation_buttons(link: str, declineLinkTarget: str, review_duration: str, article: Article):
    button_style = "margin: 10px; font-size: 14px; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px; display: block; hyphens: none;"

    accept_button = A(
                        SPAN(
                            current.T("I accept to review this preprint within ") + review_duration.lower(),
                            _style=button_style + "background: #93c54b",
                        ),
                        _href=link,
                        _style="text-decoration: none; display: block",
                    )

    more_delay_button = A(
                            SPAN(
                                current.T("I accept to review this preprint, but I'll need more time to perform my review"),
                                _style=button_style + "background: #29abe0",
                            ),
                            _href=link + "&more_delay=true",
                            _style="text-decoration: none; display: block",
                        )

    decline_button = A(
                        SPAN(
                            current.T("Decline"),
                            _style=button_style + "background: #f47c3c",
                        ),
                        _href=declineLinkTarget,
                        _style="text-decoration: none; display: block",
                    )

    html = DIV(
                P(B(current.T("TO ACCEPT OR DECLINE CLICK ON ONE OF THE FOLLOWING BUTTONS:"))),
                DIV(accept_button, _style="width: 100%; text-align: center; margin-bottom: 25px;"),
            )

    if pciRRactivated and article.report_stage == "STAGE 1" and (article.is_scheduled or models.article.is_scheduled_submission(article)):
        pass
    else:
        html.components[1].components.append(B(current.T("OR"))) # type: ignore
        html.components[1].components.append(more_delay_button) # type: ignore

    html.components[1].components.append(B(current.T("OR"))) # type: ignore
    html.components[1].components.append(decline_button) # type: ignore

    return html


######################################################################################################################################################################
def send_to_recommender_reviewers_suggestions(review, suggested_reviewers_text):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    recomm = db.t_recommendations[review.recommendation_id]
    if recomm:
        article = db.t_articles[recomm.article_id]
        if article:
            mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
            mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
            reviewerPerson = common_small_html.mkUserWithMail(review.reviewer_id)
            mail_vars["reviewerPerson"] = reviewerPerson
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["linkTarget"] = URL(
                c="recommender",
                f="my_recommendations",
                scheme=mail_vars["scheme"],
                host=mail_vars["host"],
                port=mail_vars["port"],
                vars=dict(pressReviews=article.already_published),
            )

            mail_vars["suggestedReviewersText"] = suggested_reviewers_text.strip().replace('\n','<br>')

            if review.review_state in [ReviewState.NEED_EXTRA_REVIEW_TIME.value, ReviewState.AWAITING_RESPONSE.value, ReviewState.AWAITING_REVIEW.value, ReviewState.WILLING_TO_REVIEW.value, ReviewState.REVIEW_COMPLETED.value]:
                hashtag_template = "#RecommenderSuggestedReviewersAccepted"
            else:
                hashtag_template = emailing_tools.get_correct_hashtag("#RecommenderSuggestedReviewers", article)
            emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recomm.id, None, recomm.article_id)

            reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)

    emailing_tools.getFlashMessage(reports)

######################################################################################################################################################################
######################################################################################################################################################################
def send_change_mail(user_id: int, dest_mail: str, recover_email_key: str):
    auth, session = current.auth, current.session

    mail = emailing_tools.getMailer()
    mail_vars = emailing_tools.getMailCommonVars()

    mail_resu = False
    reports = []

    mail_vars["destPerson"] = common_small_html.mkUser(user_id)
    mail_vars["destAddress"] = dest_mail
    mail_vars["verifyMailUrl"] = URL(c="default", f="confirm_new_address", vars=dict(recover_email_key=recover_email_key), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

    hashtag_template = "#UserChangeMail"
    emailing_tools.insertMailInQueue(hashtag_template, mail_vars)

    reports = emailing_tools.createMailReport(True, mail_vars["destAddress"], reports)

    emailing_tools.getFlashMessage(reports)

######################################################################################################################################################################
def send_reviewer_generic_mail(reviewer_email, recomm, form):
    if common_tools.is_silent_mode():
        return

    session, auth, db = current.session, current.auth, current.db

    clean_cc_addresses, cc_errors = emailing_tools.clean_addresses(form.cc)
    cc_addresses = emailing_tools.list_addresses(clean_cc_addresses)

    clean_replyto_adresses, replyto_errors = emailing_tools.clean_addresses(form.replyto)
    replyto_addresses = emailing_tools.list_addresses(clean_replyto_adresses)

    hashtag_template = "#ReviewerGenericMail"
    mail_content = mk_mail(form.subject, form.message)
    ccAddresses = exempt_addresses(cc_addresses, hashtag_template)

    db.mail_queue.insert(
        user_id             = auth.user_id,
        dest_mail_address   = reviewer_email,
        replyto_addresses   = replyto_addresses,
        cc_mail_addresses   = ccAddresses,
        mail_subject        = form.subject,
        mail_content        = mail_content,

        article_id          = recomm.article_id,
        recommendation_id   = recomm.id,
        mail_template_hashtag = hashtag_template,
    )

    reports = emailing_tools.createMailReport(True, reviewer_email, reports=[])
    emailing_tools.getFlashMessage(reports)

######################################################################################################################################################################
def send_submitter_generic_mail(author_email: str, articleId: int, form: Union[SQLFORM, Storage], mail_template: str):
    db, auth, session = current.db, current.auth, current.session

    if common_tools.is_silent_mode():
        return

    cc_addresses = emailing_tools.list_addresses(form.cc)
    replyto_addresses = emailing_tools.list_addresses(form.replyto)
    form.subject
    form.message

    mail_content = mk_mail(form.subject, form.message)
    ccAddresses = exempt_addresses(cc_addresses, mail_template)
    mail_subject = patch_email_subject(form.subject, articleId)

    db.mail_queue.insert(
        user_id             = auth.user_id,
        dest_mail_address   = author_email,
        replyto_addresses   = replyto_addresses,
        cc_mail_addresses   = ccAddresses,
        mail_subject        = mail_subject,
        mail_content        = mail_content,

        article_id          = articleId,
        mail_template_hashtag = mail_template,
    )

    reports = emailing_tools.createMailReport(True, author_email, reports=[])
    emailing_tools.getFlashMessage(reports)


def send_submitter_generic_reminder(hashtag_template: str, subject: str, message: str, mail_vars: Dict[str, Any], article_id: int):
    if article_id:
        mail_subject = patch_email_subject(subject, article_id)
    else:
        mail_subject = subject

    mail_content = mk_mail(subject, message)

    emailing_tools.insert_generic_reminder_mail_in_queue(hashtag_template,
                                                         mail_subject,
                                                         mail_content,
                                                         mail_vars,
                                                         article_id=article_id)


def mk_mail(subject: str, message: str, resend: bool = False) -> str :
    mail_vars = emailing_tools.getMailCommonVars()
    applogo = URL("static", "images/small-background.png",
                    scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
    subject_without_appname = subject.replace("%s: " % mail_vars["appName"], "")

    if not resend: mail_template = MAIL_HTML_LAYOUT
    else: mail_template = RESEND_MAIL_HTML_LAYOUT

    return render( # type: ignore
        filename=mail_template,
        context=dict(
            applogo=applogo,
            appname=mail_vars["appName"],
            subject=subject_without_appname,
            content=XML(message),
        )
    )
######################################################################################################################################################################
def resend_mail(form, reviewId=None, recommId=None, articleId=None, hashtag=None):
    session, auth, db = current.session, current.auth, current.db

    clean_cc_addresses, cc_errors = emailing_tools.clean_addresses(form.vars.cc_mail_addresses)
    cc_addresses = emailing_tools.list_addresses(clean_cc_addresses)
    clean_replyto_adresses, replyto_errors = emailing_tools.clean_addresses(form.vars.replyto)
    replyto_addresses = emailing_tools.list_addresses(clean_replyto_adresses)
    dest_mail_address, dest_errors = emailing_tools.clean_addresses(form.vars.dest_mail_address)

    mail_content = mk_mail(form.vars.subject, form.vars.content, resend=True)
    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["destAddress"] = dest_mail_address
    mail_vars["ccAddresses"] = cc_addresses
    mail_vars["replytoAddresses"] = replyto_addresses

    if recommId != 'None' and reviewId != 'None' and articleId == 'None':
        emailing_tools.insertMailInQueue(hashtag, mail_vars, recommendation_id=recommId,
                                         review=reviewId, alternative_subject=form.vars.subject,
                                         alternative_content=mail_content)
    elif recommId != 'None' and reviewId != 'None' and articleId != 'None':
        emailing_tools.insertMailInQueue(hashtag, mail_vars, recommendation_id=recommId,
                                         article_id=articleId, review=reviewId, alternative_subject=form.vars.subject,
                                         alternative_content=mail_content)
    elif articleId != 'None':
        emailing_tools.insertMailInQueue(hashtag, mail_vars,
                                         article_id=articleId, alternative_subject=form.vars.subject,
                                         alternative_content=mail_content)
    else:
        emailing_tools.insertMailInQueue(hashtag, mail_vars,
                                         alternative_subject=form.vars.subject,
                                         alternative_content=mail_content)

    reports = emailing_tools.createMailReport(True, dest_mail_address, reports=[])
    emailing_tools.getFlashMessage(reports)


######################################################################################################################################################################
## News letter
######################################################################################################################################################################
def send_newsletter_mail(userId: int, newsletterType: str):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    user = db.auth_user[userId]

    mail_vars["destPerson"] = common_small_html.mkUser(userId)
    mail_vars["destAddress"] = user["email"]

    if newsletterType in ["Never", None]:
        hashtag_template = newsletter.template["Weekly"]
        newsletter_interval = 0
    else:
        hashtag_template = newsletter.template[newsletterType]
        newsletter_interval = newsletter.interval[newsletterType]

    new_articles_qy = (
            db.t_articles.last_status_change >=
            (datetime.datetime.now() - datetime.timedelta(days=newsletter_interval)).date()
    )

    newRecommendationsCount = 0
    newPreprintRequiringRecommenderCount = 0
    newPreprintSearchingForReviewersCount = 0
    if newsletter_interval is not None:
        # New recommended articles
        new_recommended_articles = db(
            (
                new_articles_qy
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
                newRecommendations.append(newsletter.makeArticleWithRecommRow(article))

        # New preprint searching for reviewers
        new_searching_for_reviewers_preprint = db(
            (
                (db.t_articles.is_searching_reviewers == True)
                & (new_articles_qy if pciRRactivated else True)
                & (db.t_articles.status.belongs(("Under consideration", "Scheduled submission under consideration")))
            )
        ).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)

        j = 0
        newPreprintSearchingForReviewers = DIV()
        newPreprintSearchingForReviewersCount = len(new_searching_for_reviewers_preprint)
        for article in new_searching_for_reviewers_preprint:
          if pciRRactivated:
            j += 1
            if j <= 5:
                newPreprintSearchingForReviewers.append(newsletter.makeArticleRow(article, "review"))
          else:
            newPreprintSearchingForReviewers.append(newsletter.makeArticleRow(article, "review"))

        # New preprint requiring recommender
        group = db((db.auth_user.id == userId) & (db.auth_membership.user_id == db.auth_user.id) & (db.auth_membership.group_id == 2)).count()

        newPreprintRequiringRecommender = None
        if group > 0:
            new_searching_for_recommender_preprint = db(
                (
                    (db.t_articles.status == "Awaiting consideration")
                    & (new_articles_qy if pciRRactivated else True)
                )
            ).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)

            k = 0
            newPreprintRequiringRecommender = DIV()
            newPreprintRequiringRecommenderCount = len(new_searching_for_recommender_preprint)
            for article in new_searching_for_recommender_preprint:
              if pciRRactivated:
                k += 1
                if k <= 5:
                    newPreprintRequiringRecommender.append(newsletter.makeArticleRow(article, "recommendation"))
              else:
                newPreprintRequiringRecommender.append(newsletter.makeArticleRow(article, "recommendation"))

    if (newRecommendationsCount > 0) or (newPreprintSearchingForReviewersCount > 0) or (newPreprintRequiringRecommenderCount > 0):
        emailing_tools.insert_newsletter_mail_in_queue(
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
def delete_newsletter_mail(userId: int):
    session, auth, db = current.session, current.auth, current.db

    user = db.auth_user[userId]

    if user is not None:
        db(
            (
                (db.mail_queue.dest_mail_address == user.email)
                & (
                    (db.mail_queue.mail_template_hashtag == "#NewsLetterWeekly")
                    | (db.mail_queue.mail_template_hashtag == "#NewsLetterEveryTwoWeeks")
                    | (db.mail_queue.mail_template_hashtag == "#NewsLetterMonthly")
                )
            )
        ).delete()


######################################################################################################################################################################
## Reminders
######################################################################################################################################################################
def create_reminder_for_submitter_suggested_recommender_needed(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    sugg_recommenders = db(db.t_suggested_recommenders.article_id == articleId).select()

    if article and article.user_id is not None and len(sugg_recommenders) == 0:

        mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderSubmitterSuggestedRecommenderNeeded", article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, None, None, articleId)


######################################################################################################################################################################
def create_reminder_for_submitter_new_suggested_recommender_needed(articleId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderSubmitterNewSuggestedRecommenderNeeded", article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, None, None, articleId)


######################################################################################################################################################################
def create_reminder_for_submitter_cancel_submission(articleId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderSubmitterCancelSubmission", article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, None, None, articleId)


######################################################################################################################################################################
def create_reminder_for_submitter_revised_version_warning(articleId):
    session, auth, db = current.session, current.auth, current.db
    _create_reminder_for_submitter_revised_version(articleId, "#ReminderSubmitterRevisedVersionWarning")

def create_reminder_for_submitter_revised_version_needed(articleId):
    session, auth, db = current.session, current.auth, current.db
    _create_reminder_for_submitter_revised_version(articleId, "#ReminderSubmitterRevisedVersionNeeded")

def _create_reminder_for_submitter_revised_version(articleId: int, email_template: str):
    db, auth = current.db, current.auth
    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = Article.get_last_recommendation(articleId)

    if article and recomm:
        mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]
        mail_vars["ccAddresses"] = db.auth_user[recomm.recommender_id]["email"]
        mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)

        hashtag_template = emailing_tools.get_correct_hashtag(email_template, article)
        if article.coar_notification_id:
            hashtag_template += "COAR" # i.e. #ReminderSubmitterRevisedVersionWarningCOAR / NeededCOAR
            mail_vars["message"] = get_original_submitter_awaiting_submission_email(article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, articleId)


def get_original_submitter_awaiting_submission_email(article):
    template = "#SubmitterAwaitingSubmissionCOAR"
    emails = MailQueue.get_by_article_and_template(article.id, template)
    if emails:
        return MailQueue.get_mail_content(emails.first())


######################################################################################################################################################################
def create_reminders_for_submitter_scheduled_submission(article: Article):
    session, auth, db = current.session, current.auth, current.db

    articleId = article.id

    delete_reminder_for_submitter("#ReminderSubmitterScheduledSubmissionSoonDue", articleId)
    delete_reminder_for_submitter("#ReminderSubmitterScheduledSubmissionDue", articleId)
    delete_reminder_for_submitter("#ReminderSubmitterScheduledSubmissionOverDue", articleId)

    if article.t_report_survey.select()[0].q1 == "COMPLETE STAGE 1 REPORT FOR REGULAR REVIEW":
        return # do not schedule reminders when report is already submitted

    create_reminder_for_submitter_scheduled_submission_soon_due(articleId)
    create_reminder_for_submitter_scheduled_submission_due(articleId)
    create_reminder_for_submitter_scheduled_submission_over_due(articleId)


def create_reminder_for_submitter_scheduled_submission_soon_due(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["linkTarget"] = mk_submitter_my_articles_url(mail_vars)

    article = db.t_articles[articleId]

    recommId = None
    recomm = Article.get_last_recommendation(articleId)
    if recomm:
        recommId = recomm.id
        mail_vars["recommenderPerson"] = common_small_html.mkUser(recomm.recommender_id)

    if article:
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        # do not user getCorrectHashtag here to avoid fake name
        hashtag_template = "#ReminderSubmitterScheduledSubmissionSoonDue"
        scheduled_submission_date = get_scheduled_submission_date(article)
        sending_date_forced: Optional[datetime.date] = None
        if scheduled_submission_date:
            sending_date_forced = scheduled_submission_date - datetime.timedelta(days=14)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recommId, None, articleId, sending_date_forced=sending_date_forced)

######################################################################################################################################################################
def create_reminder_for_submitter_scheduled_submission_due(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["linkTarget"] = mk_submitter_my_articles_url(mail_vars)

    article = db.t_articles[articleId]

    recommId = None
    recomm = Article.get_last_recommendation(articleId)
    if recomm:
        recommId = recomm.id
        mail_vars["recommenderPerson"] = common_small_html.mkUser(recomm.recommender_id)

    if article:
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        # do not user getCorrectHashtag here to avoid fake name
        hashtag_template = "#ReminderSubmitterScheduledSubmissionDue"
        scheduled_submission_date = get_scheduled_submission_date(article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recommId, None, articleId, sending_date_forced=scheduled_submission_date)

######################################################################################################################################################################
def create_reminder_for_submitter_scheduled_submission_over_due(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["linkTarget"] = mk_submitter_my_articles_url(mail_vars)

    article = db.t_articles[articleId]

    recommId = None
    recomm = Article.get_last_recommendation(articleId)
    if recomm:
        recommId = recomm.id
        mail_vars["recommenderPerson"] = common_small_html.mkUser(recomm.recommender_id)

    if article:
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        # do not user getCorrectHashtag here to avoid fake name
        hashtag_template = "#ReminderSubmitterScheduledSubmissionOverDue"
        scheduled_submission_date = get_scheduled_submission_date(article)
        sending_date_forced: Optional[datetime.date] = None
        if scheduled_submission_date:
            sending_date_forced = scheduled_submission_date + datetime.timedelta(days=1)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recommId, None, articleId, sending_date_forced=sending_date_forced)

######################################################################################################################################################################
def create_reminder_for_recommender_validated_scheduled_submission(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    article = db.t_articles[articleId]
    recomm = Article.get_last_recommendation(articleId)
    if article:
        mail_vars["articleDoi"] = article.doi
        mail_vars["articleAuthors"] = mkAuthors(article)
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
        mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["ccAddresses"] = mail_vars["appContactMail"] # contacts.managers

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))
            scheduled_review_start_date = mail_vars["scheduledSubmissionLatestReviewStartDate"]
            review_period = datetime.datetime.strptime(scheduled_review_start_date, DEFAULT_DATE_FORMAT).date()

        # do not use getCorrectHashtag here to avoid fake name
        hashtag_template = "#ReminderRecommenderPreprintValidatedScheduledSubmission"

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, articleId, sending_date_forced=(review_period - datetime.timedelta(days=1)))

######################################################################################################################################################################
def create_reminder_for_recommender_validated_scheduled_submission_late(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()
    article = db.t_articles[articleId]
    recomm = Article.get_last_recommendation(articleId)
    if article:
        mail_vars["articleDoi"] = article.doi
        mail_vars["articleAuthors"] = mkAuthors(article)
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
        mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["ccAddresses"] = mail_vars["appContactMail"] # contacts.managers

        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))
            scheduled_review_start_date = mail_vars["scheduledSubmissionLatestReviewStartDate"]
            review_period = datetime.datetime.strptime(scheduled_review_start_date, DEFAULT_DATE_FORMAT).date()

        # do not use getCorrectHashtag here to avoid fake name
        hashtag_template = "#ReminderRecommenderPreprintValidatedScheduledSubmissionLate"

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, articleId, sending_date_forced=(review_period + datetime.timedelta(days=1)))


def mk_submitter_my_articles_url(mail_vars):
    return URL(c="user", f="my_articles",
            scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])


######################################################################################################################################################################
def delete_reminder_for_submitter(hashtag_template: str, articleId: int):
    db = current.db
    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        submitter_mail = db.auth_user[article.user_id]["email"]

        if article.coar_notification_id and (
                "#ReminderSubmitterRevisedVersion" in hashtag_template):
            hashtag_template += "COAR"

        db((db.mail_queue.dest_mail_address == submitter_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.article_id == articleId)).delete()

        if pciRRactivated:
            hashtag_template_rr = hashtag_template + "Stage"
            db(
                (db.mail_queue.dest_mail_address == submitter_mail)
                & (db.mail_queue.mail_template_hashtag.startswith(hashtag_template_rr))
                & (db.mail_queue.article_id == articleId)
            ).delete()


######################################################################################################################################################################
def create_reminder_for_suggested_recommenders_invitation(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    if article:
        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        suggested_recommenders = db(
            (db.t_suggested_recommenders.article_id == articleId)
            & (db.t_suggested_recommenders.declined == False)
            & (db.t_suggested_recommenders.recommender_validated == True)
            & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)
        ).select(db.t_suggested_recommenders.ALL, db.auth_user.ALL)

        for sugg_recommender in suggested_recommenders:
            hashtag_template = emailing_tools.get_correct_hashtag("#ReminderSuggestedRecommenderInvitation", article)

            mail_vars["destPerson"] = common_small_html.mkUser(sugg_recommender["auth_user.id"])
            mail_vars["destAddress"] = db.auth_user[sugg_recommender["auth_user.id"]]["auth_user.email"]

            mail_vars["articleDoi"] = article.doi
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleAuthors"] = mkAuthors(article)
            mail_vars["linkTarget"] = URL(
                c="recommender", f="article_details", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )
            mail_vars["helpUrl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            sugg_recommender_buttons = build_sugg_recommender_buttons(mail_vars["linkTarget"], articleId, sugg_recommender["auth_user.id"])
            emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, None, None, articleId, sugg_recommender_buttons=sugg_recommender_buttons)


######################################################################################################################################################################
def create_reminder_for_suggested_recommender_invitation(article: Article, recommender_id: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    suggested_recommender = User.get_by_id(recommender_id)
    if suggested_recommender and suggested_recommender.email:
        if pciRRactivated:
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderSuggestedRecommenderInvitation", article)

        mail_vars["destPerson"] = common_small_html.mkUser(recommender_id)
        mail_vars["destAddress"] = suggested_recommender.email

        mail_vars["articleDoi"] = article.doi
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = mkAuthors(article)

        mail_vars["linkTarget"] = URL(
            c="recommender", f="article_details", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
        )
        mail_vars["helpUrl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        sugg_recommender_buttons = build_sugg_recommender_buttons(mail_vars["linkTarget"], article.id, recommender_id)
        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, None, None, article.id, sugg_recommender_buttons=sugg_recommender_buttons)


######################################################################################################################################################################
def delete_reminder_for_suggested_recommenders(hashtag_template: str, articleId: int):
    db = current.db
    article = db.t_articles[articleId]
    if article:
        suggested_recommenders = db(
            (db.t_suggested_recommenders.article_id == articleId)
            & (db.t_suggested_recommenders.declined == False)
            & (db.t_suggested_recommenders.recommender_validated == True)
            & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)
        ).select(db.t_suggested_recommenders.ALL, db.auth_user.ALL)

        for sugg_recommender in suggested_recommenders:
            db(
                (db.mail_queue.dest_mail_address == sugg_recommender["auth_user.email"])
                & (db.mail_queue.mail_template_hashtag == hashtag_template)
                & (db.mail_queue.article_id == articleId)
            ).delete()

            if pciRRactivated:
                hashtag_template_rr = hashtag_template + "Stage"
                db(
                    (db.mail_queue.dest_mail_address == sugg_recommender["auth_user.email"])
                    & (db.mail_queue.mail_template_hashtag.startswith(hashtag_template_rr))
                    & (db.mail_queue.article_id == articleId)
                ).delete()


######################################################################################################################################################################
def delete_reminder_for_one_suggested_recommender(hashtag_template: str, articleId: int, suggRecommId: int):
    db = current.db
    user = db.auth_user[suggRecommId]
    article = db.t_articles[articleId]
    if article and user:
        db(
            (db.mail_queue.dest_mail_address == user["email"])
            & (db.mail_queue.mail_template_hashtag == hashtag_template)
            & (db.mail_queue.article_id == articleId)
        ).delete()

        if pciRRactivated:
            hashtag_template_rr = hashtag_template + "Stage"
            db(
                (db.mail_queue.dest_mail_address == user["email"])
                & (db.mail_queue.mail_template_hashtag.startswith(hashtag_template_rr))
                & (db.mail_queue.article_id == articleId)
            ).delete()


###############################################################################
def reviewLink(**kwargs):
    mail_vars = emailing_tools.getMailCommonVars()
    return URL(c="user", f="my_reviews", vars=kwargs, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])


######################################################################################################################################################################
def create_reminder_for_reviewer_review_invitation_new_user(reviewId: int,
                                                            replyto_addresses: str,
                                                            message:str,
                                                            reviewer_invitation_buttons: Optional[DIV] = None,
                                                            hashtag_template: Optional[str] = None,
                                                            new_stage: bool = False):
    session, auth, db = current.session, current.auth, current.db

    review = Review.get_by_id(reviewId)
    if not review:
        return

    recomm = Recommendation.get_by_id(review.recommendation_id)
    if not recomm:
        return

    article = Article.get_by_id(recomm.article_id)
    reviewer = User.get_by_id(review.reviewer_id)

    if review and recomm and article and reviewer:
        sender: Optional[User] = None
        if auth.has_membership(role="manager"):
            sender = User.get_by_id(recomm.recommender_id)
        else:
            sender = cast(User, auth.user)

        if not sender:
            return

        mail_vars = emailing_tools.getMailForReviewerCommonVars(sender, article, recomm, reviewer.last_name)
        mail_vars["message"] = message

        mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
        mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]

        mail_vars["myReviewsLink"] = reviewLink(pendingOnly=True)
        mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)

        mail_vars["reviewDuration"] = (review.review_duration).lower() if review.review_duration else ''


        if pciRRactivated:
            mail_vars.update(getPCiRRstageVars(article))
            mail_vars.update(getPCiRRinvitationTexts(article, new_stage))
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        mail_vars["parallelText"] = ""
        if parallelSubmissionAllowed:
            mail_vars[
                "parallelText"
            ] += """Note that if the authors abandon the process at %(appLongName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appLongName)s website as recognition of their work and in order to enable critical discussion.""" % mail_vars
            if article.parallel_submission:
                mail_vars[
                    "parallelText"
                ] += """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appLongName)s, and hope you will agree to review this preprint.""" % mail_vars

        mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(recomm.id)
        mail_vars["replytoAddresses"] = replyto_addresses

        if hashtag_template is None:
            hashtag_template = emailing_tools.get_correct_hashtag("#ReminderReviewerReviewInvitationNewUser", article)

        sender_name = None
        if not pciRRactivated and sender:
            sender_name = f'{sender.first_name} {sender.last_name}'

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id, reviewer_invitation_buttons=reviewer_invitation_buttons, sender_name=sender_name, review_id=reviewId)


######################################################################################################################################################################
def create_reminder_for_reviewer_review_invitation_registered_user(reviewId: int,
                                                                   replyto_addresses: str,
                                                                   message: str,
                                                                   reviewer_invitation_buttons: Optional[DIV] = None,
                                                                   new_round: bool = False,
                                                                   hashtag_template: Optional[str] = None,
                                                                   new_stage: bool = False):
    session, auth, db = current.session, current.auth, current.db

    review = Review.get_by_id(reviewId)
    if not review:
        return

    recomm = Recommendation.get_by_id(review.recommendation_id)
    if not recomm:
        return

    article = Article.get_by_id(recomm.article_id)
    reviewer = User.get_by_id(review.reviewer_id)

    if review and recomm and article and reviewer:
        sender: Optional[User] = None
        if auth.has_membership(role="manager"):
            sender = User.get_by_id(recomm.recommender_id)
        else:
            sender = cast(User, auth.user)

        if not sender:
            return

        mail_vars = emailing_tools.getMailForReviewerCommonVars(sender, article, recomm, reviewer.last_name)
        mail_vars["message"] = message

        mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
        mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]
        mail_vars["sender"] = mkSender(recomm)

        mail_vars["myReviewsLink"] = reviewLink(pendingOnly=True)
        mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["reviewDuration"] = (review.review_duration).lower() if review.review_duration else ''
        mail_vars["replytoAddresses"] = replyto_addresses

        _recomm = common_tools.get_prev_recomm(recomm) if new_round else recomm
        r2r_url, trackchanges_url = emailing_parts.getAuthorsReplyLinks(_recomm.id)

        r2r_url = str(r2r_url) if r2r_url else "(no author's reply)"
        trackchanges_url = str(trackchanges_url) if trackchanges_url else "(no tracking)"

        mail_vars["r2r_url"] = r2r_url
        mail_vars["trackchanges_url"] = trackchanges_url

        if pciRRactivated:
            mail_vars.update(getPCiRRstageVars(article))
            mail_vars.update(getPCiRRinvitationTexts(article, new_stage))
            mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

        mail_vars["parallelText"] = ""
        if parallelSubmissionAllowed:
            mail_vars[
                "parallelText"
            ] += """Note that if the authors abandon the process at %(appLongName)s after reviewers have written their reports, we will post the reviewers' reports on the %(appLongName)s website as recognition of their work and in order to enable critical discussion.""" % mail_vars
            if article.parallel_submission:
                mail_vars[
                    "parallelText"
                ] += """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appLongName)s, and hope you will agree to review this preprint.""" % mail_vars

        mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(recomm.id)

        if hashtag_template is  None:
            hashtag_template = emailing_tools.get_correct_hashtag("#ReminderReviewerReviewInvitationRegisteredUser", article)
        authors_reply = None
        if new_round:
            hashtag_template = emailing_tools.get_correct_hashtag("#ReminderReviewerInvitationNewRoundRegisteredUser", article)
            prev_recomm = common_tools.get_prev_recomm(recomm)
            authors_reply = emailing_parts.getAuthorsReplyHTML(prev_recomm.id)

        sender_name = None
        if not pciRRactivated and sender:
            sender_name = f'{sender.first_name} {sender.last_name}'

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id, reviewer_invitation_buttons=reviewer_invitation_buttons, authors_reply=authors_reply, sender_name=sender_name, review_id=reviewId)


######################################################################################################################################################################
def create_reminder_for_reviewer_review_soon_due(reviewId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    review = Review.get_by_id(reviewId)
    recomm = Recommendation.get_by_id(review.recommendation_id)
    article = Article.get_by_id(recomm.article_id)
    reviewer = User.get_by_id(review.reviewer_id)

    if review and recomm and article and reviewer:
        if scheduledSubmissionActivated and ((article.scheduled_submission_date is not None) or (article.status.startswith("Scheduled submission"))):
            pass
        else:
            mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
            mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]

            mail_vars["delay"] = review.review_duration.lower()
            mail_vars["articleDoi"] = article.doi
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleAuthors"] = mkAuthors(article)
            mail_vars["myReviewsLink"] = reviewLink()
            mail_vars["reviewDueDate"] = Review.get_due_date(review).strftime(DEFAULT_DATE_FORMAT)
            mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)
            mail_vars["linkTarget"] = URL(c="default", f="invitation_to_review", vars=dict(reviewId=review.id, key=reviewer.reset_password_key), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(recomm.id)

            if isScheduledTrack(article):
                mail_vars["reviewDueDate"] = due_date = getScheduledReviewDueDate(article)
                base_sending_date = datetime.datetime.strptime(due_date, DEFAULT_DATE_FORMAT)
                sending_date_forced = base_sending_date - datetime.timedelta(days=3)
            else:
                sending_date_forced = None

            hashtag_template = emailing_tools.get_correct_hashtag("#ReminderReviewerReviewSoonDue", article)

            emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id, reviewId, sending_date_forced=sending_date_forced)


def isScheduledTrack(art):
    return models.article.is_scheduled_submission(art)


def get_scheduled_submission_date(article: Article) -> Optional[datetime.date]:
    return article.t_report_survey.select().last().q10


def getScheduledReviewDueDate(article):
    _ = getPCiRRScheduledSubmissionsVars(article)
    return _["scheduledReviewDueDate"]


######################################################################################################################################################################
def create_reminder_for_reviewer_review_due(reviewId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    review = Review.get_by_id(reviewId)
    recomm = Recommendation.get_by_id(review.recommendation_id)
    article = Article.get_by_id(recomm.article_id)
    reviewer = User.get_by_id(review.reviewer_id)

    if review and recomm and article and reviewer:
        if scheduledSubmissionActivated and ((article.scheduled_submission_date is not None) or (article.status.startswith("Scheduled submission"))):
            pass
        else:
            mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
            mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]

            mail_vars["delay"] = review.review_duration.lower()
            mail_vars["myReviewsLink"] = reviewLink()
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleAuthors"] = mkAuthors(article)
            mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)
            mail_vars["linkTarget"] = URL(c="default", f="invitation_to_review", vars=dict(reviewId=review.id, key=reviewer.reset_password_key), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(recomm.id)

            if isScheduledTrack(article):
                mail_vars["reviewDueDate"] = due_date = getScheduledReviewDueDate(article)
                base_sending_date = datetime.datetime.strptime(due_date, DEFAULT_DATE_FORMAT)
            else:
                base_sending_date = None

            hashtag_template = emailing_tools.get_correct_hashtag("#ReminderReviewerReviewDue", article)

            emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id, reviewId, base_sending_date=base_sending_date)


######################################################################################################################################################################
def create_reminder_for_reviewer_review_over_due(reviewId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    review = Review.get_by_id(reviewId)
    recomm = Recommendation.get_by_id(review.recommendation_id)
    article = Article.get_by_id(recomm.article_id)
    reviewer = User.get_by_id(review.reviewer_id)

    if review and recomm and article and reviewer:
        if scheduledSubmissionActivated and ((article.scheduled_submission_date is not None) or (article.status.startswith("Scheduled submission"))):
            pass
        else:
            mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
            mail_vars["destAddress"] = db.auth_user[review.reviewer_id]["email"]

            mail_vars["delay"] = review.review_duration.lower()
            mail_vars["myReviewsLink"] = reviewLink()
            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleAuthors"] = mkAuthors(article)
            mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)
            mail_vars["linkTarget"] = URL(c="default", f="invitation_to_review", vars=dict(reviewId=review.id, key=reviewer.reset_password_key), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            mail_vars["ccAddresses"] = [db.auth_user[recomm.recommender_id]["email"]] + emailing_vars.get_co_recommenders_mails(recomm.id)

            if isScheduledTrack(article):
                mail_vars["reviewDueDate"] = due_date = getScheduledReviewDueDate(article)
                base_sending_date = datetime.datetime.strptime(due_date, DEFAULT_DATE_FORMAT)
                sending_date_forced = base_sending_date + datetime.timedelta(days=2)
            else:
                sending_date_forced = None

            hashtag_template = emailing_tools.get_correct_hashtag("#ReminderReviewerReviewOverDue", article)

            emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id, reviewId, sending_date_forced=sending_date_forced)


######################################################################################################################################################################
def create_reminder_for_reviewer_scheduled_review_coming_soon(review: Review):
    session, auth, db = current.session, current.auth, current.db

    recomm = db.t_recommendations[review.recommendation_id]
    article = db.t_articles[recomm.article_id]
    reviewer = db.auth_user[review.reviewer_id]

    if not reviewer: return
    if not review.review_state == "Awaiting review": return

    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars.update(getPCiRRScheduledSubmissionsVars(article))
    mail_vars.update({
        "destPerson": common_small_html.mkUser(reviewer.id),
        "destAddress": reviewer.email,
        "articleTitle": md_to_html(article.title),
        "articleAuthors": mkAuthors(article),
        "recommenderPerson": mk_recommender(article),
        "reviewDueDate": mail_vars["scheduledReviewDueDate"],
        "myReviewsLink": reviewLink(),
    })

    sending_date = get_scheduled_submission_date(article) # = LatestReviewStartDate minus 1 week
    hashtag_template = "#ReminderScheduledReviewComingSoon"

    emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id, review.id, sending_date_forced=sending_date)


######################################################################################################################################################################
def delete_reminder_for_reviewer(hashtag_template: List[str], reviewId: int):
    db = current.db
    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    reviewer = db.auth_user[review.reviewer_id]
    nb_deleted = 0

    for hashtag in hashtag_template:
        if reviewer and recomm:
            nb_deleted += db((db.mail_queue.dest_mail_address == reviewer.email) & (db.mail_queue.mail_template_hashtag == hashtag) & (db.mail_queue.recommendation_id == recomm.id)).delete()

            if pciRRactivated:
                hashtag_template_rr = hashtag + "Stage"
                nb_deleted += db(
                    (db.mail_queue.dest_mail_address == reviewer.email)
                    & (db.mail_queue.mail_template_hashtag.startswith(hashtag_template_rr))
                    & (db.mail_queue.recommendation_id == recomm.id)
                ).delete()

    return nb_deleted

######################################################################################################################################################################
def create_reminder_for_recommender_reviewers_needed(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = Article.get_last_recommendation(articleId)
    recommCount = db((db.t_recommendations.article_id == article.id)).count()

    if recomm and article and recommCount == 1:
        mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        mail_vars["articleAuthors"] = article.authors
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)

        mail_vars["reviewDuration"] = default_review_duration.lower()
    else:
        return

    if pciRRactivated:
        sched_sub_vars = emailing_vars.getPCiRRScheduledSubmissionsVars(article)
        mail_vars["scheduledSubmissionLatestReviewStartDate"] = sched_sub_vars["scheduledSubmissionLatestReviewStartDate"]
        mail_vars["scheduledReviewDueDate"] = sched_sub_vars["scheduledReviewDueDate"]
        mail_vars["scheduledSubmissionDate"] = sched_sub_vars["scheduledSubmissionDate"]
        mail_vars["snapshotUrl"] = sched_sub_vars["snapshotUrl"]

    hashtag_template = emailing_tools.get_correct_hashtag("#ReminderRecommenderReviewersNeeded", article)

    emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_recommender_new_reviewers_needed(recommendation_id: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    recommendation: Recommendation = db.t_recommendations[recommendation_id]
    article: Article = db((db.t_articles.id == recommendation.article_id)).select().last()

    hashtag_template = emailing_tools.get_correct_hashtag("#ReminderRecommenderNewReviewersNeeded", article)

    mail_already_exists = MailQueue.there_are_mails_for_article_recommendation(article.id, recommendation.id, hashtag_template, [SendingStatus.PENDING]) > 0
    if mail_already_exists:
        return

    recommendation_count = int(db((db.t_recommendations.article_id == article.id)).count())

    if recommendation and article and recommendation_count == 1:
        count_reviews_under_consideration = int(db(
            (db.t_reviews.recommendation_id == recommendation_id) & ((db.t_reviews.review_state == "Awaiting review") | (db.t_reviews.review_state == "Review completed"))
        ).count())
        if count_reviews_under_consideration < 2:

            mail_vars["destPerson"] = common_small_html.mkUser(recommendation.recommender_id)
            mail_vars["destAddress"] = db.auth_user[recommendation.recommender_id]["email"]

            mail_vars["articleTitle"] = md_to_html(article.title)
            mail_vars["articleAuthors"] = article.authors
            mail_vars["recommenderName"] = common_small_html.mkUser(recommendation.recommender_id)

            emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recommendation.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_recommender_decision_soon_due(reviewId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    article = db((db.t_articles.id == recomm.article_id)).select().last()

    count_reviews_completed = 0
    count_reviews_under_consideration = 0
    if recomm:
        count_reviews_completed = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Review completed")).count()
        count_reviews_under_consideration = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Awaiting review")).count()

    if recomm and count_reviews_completed >= 2 and count_reviews_under_consideration == 0 and article:
        mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = article.authors
        mail_vars["ccAddresses"] = emailing_vars.get_co_recommenders_mails(recomm.id)

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderRecommenderDecisionSoonDue", article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, recomm.article_id)


######################################################################################################################################################################
def create_reminder_for_recommender_decision_due(reviewId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    article = db((db.t_articles.id == recomm.article_id)).select().last()

    count_reviews_completed = 0
    count_reviews_under_consideration = 0
    if recomm:
        count_reviews_completed = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Review completed")).count()
        count_reviews_under_consideration = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Awaiting review")).count()

    if recomm and count_reviews_completed >= 2 and count_reviews_under_consideration == 0 and article:
        mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = article.authors
        mail_vars["ccAddresses"] = emailing_vars.get_co_recommenders_mails(recomm.id)

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderRecommenderDecisionDue", article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, recomm.article_id)


######################################################################################################################################################################
def create_reminder_for_recommender_decision_over_due(reviewId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    review = db.t_reviews[reviewId]
    recomm = db.t_recommendations[review.recommendation_id]
    article = db((db.t_articles.id == recomm.article_id)).select().last()

    count_reviews_completed = 0
    count_reviews_under_consideration = 0
    if recomm:
        count_reviews_completed = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Review completed")).count()
        count_reviews_under_consideration = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Awaiting review")).count()

    if recomm and count_reviews_completed >= 2 and count_reviews_under_consideration == 0 and article:
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = article.authors
        mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
        mail_vars["ccAddresses"] = emailing_vars.get_co_recommenders_mails(recomm.id)

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderRecommenderDecisionOverDue", article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, recomm.article_id)


######################################################################################################################################################################
def create_reminder_for_recommender_revised_decision_soon_due(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = Article.get_last_recommendation(articleId)

    if recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)

        mail_vars["ccAddresses"] = emailing_vars.get_co_recommenders_mails(recomm.id)

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderRecommenderRevisedDecisionSoonDue", article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_recommender_revised_decision_due(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = Article.get_last_recommendation(articleId)

    if recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)

        mail_vars["ccAddresses"] = emailing_vars.get_co_recommenders_mails(recomm.id)

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderRecommenderRevisedDecisionDue", article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id)


######################################################################################################################################################################
def create_reminder_for_recommender_revised_decision_over_due(articleId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    article = db.t_articles[articleId]
    recomm = Article.get_last_recommendation(articleId)

    if recomm and article:
        mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
        mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["articleAuthors"] = article.authors
        mail_vars["recommenderName"] = common_small_html.mkUser(recomm.recommender_id)

        mail_vars["ccAddresses"] = emailing_vars.get_co_recommenders_mails(recomm.id)

        hashtag_template = emailing_tools.get_correct_hashtag("#ReminderRecommenderRevisedDecisionOverDue", article)

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id)


######################################################################################################################################################################
def delete_reminder_for_recommender(hashtag_template: str, recommendationId: int, force_delete: bool = False, review: Optional[Review] = None):
    db = current.db
    recomm = db.t_recommendations[recommendationId]

    if recomm:
        recomm_mail = db.auth_user[recomm.recommender_id]["email"]

        if (
            hashtag_template in (
                "#ReminderRecommenderNewReviewersNeeded",
                "#ReminderRecommenderNewReviewersNeededStage1",
                "#ReminderRecommenderNewReviewersNeededStage2",
                "#ReminderRecommender2ReviewsReceivedCouldMakeDecision",
            )
            and not force_delete
        ):
            count_reviews_under_consideration = db(
                (db.t_reviews.recommendation_id == recommendationId) & ((db.t_reviews.review_state == "Awaiting review") | (db.t_reviews.review_state == "Review completed"))
            ).count()
            if count_reviews_under_consideration > 0:
                db(
                    (db.mail_queue.dest_mail_address == recomm_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.recommendation_id == recomm.id)
                ).delete()

                if pciRRactivated:
                    hashtag_template_rr = hashtag_template + "Stage"
                    db(
                        (db.mail_queue.dest_mail_address == recomm_mail)
                        & (db.mail_queue.mail_template_hashtag.startswith(hashtag_template_rr))
                        & (db.mail_queue.recommendation_id == recomm.id)
                    ).delete()

        elif hashtag_template in (
            "#ReminderRecommenderRevisedDecisionSoonDue",
            "#ReminderRecommenderRevisedDecisionDue",
            "#ReminderRecommenderRevisedDecisionOverDue",
            "#ReminderRecommenderRevisedDecisionSoonDueStage1",
            "#ReminderRecommenderRevisedDecisionDueStage1",
            "#ReminderRecommenderRevisedDecisionOverDueStage1",
            "#ReminderRecommenderRevisedDecisionSoonDueStage2",
            "#ReminderRecommenderRevisedDecisionDueStage2",
            "#ReminderRecommenderRevisedDecisionOverDueStage2",
        ):
            article = db.t_articles[recomm.article_id]
            db(
                (db.mail_queue.dest_mail_address == recomm_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.article_id == recomm.article_id)
            ).delete()

            if pciRRactivated:
                hashtag_template_rr = hashtag_template + "Stage"
                db(
                    (db.mail_queue.dest_mail_address == recomm_mail)
                    & (db.mail_queue.mail_template_hashtag.startswith(hashtag_template_rr))
                    & (db.mail_queue.article_id == recomm.article_id)
                ).delete()

        else:
            if review:
                MailQueue.get_by_review_for_recommender(hashtag_template, recomm_mail, review).delete()
            else:
                db(
                    (db.mail_queue.dest_mail_address == recomm_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.recommendation_id == recomm.id)
                ).delete()

            if pciRRactivated:
                hashtag_template_rr = hashtag_template + "Stage"
                db(
                    (db.mail_queue.dest_mail_address == recomm_mail)
                    & (db.mail_queue.mail_template_hashtag.startswith(hashtag_template_rr))
                    & (db.mail_queue.recommendation_id == recomm.id)
                ).delete()


######################################################################################################################################################################
def delete_reminder_for_recommender_from_article_id(hashtag_template: str, articleId: int):
    db = current.db
    article = db.t_articles[articleId]
    recomm = Article.get_last_recommendation(articleId)

    if recomm:
        recomm_mail = db.auth_user[recomm.recommender_id]["email"]
        db((db.mail_queue.dest_mail_address == recomm_mail) & (db.mail_queue.mail_template_hashtag == hashtag_template) & (db.mail_queue.article_id == articleId)).delete()

        if pciRRactivated:
            hashtag_template_rr = hashtag_template + "Stage"
            db(
                (db.mail_queue.dest_mail_address == recomm_mail) & (db.mail_queue.mail_template_hashtag.startswith(hashtag_template_rr)) & (db.mail_queue.article_id == articleId)
            ).delete()


######################################################################################################################################################################
def delete_all_reminders_from_article_id(articleId):
    db = current.db
    article = db.t_articles[articleId]
    if article:
        db((db.mail_queue.article_id == articleId) & (db.mail_queue.mail_template_hashtag.startswith("#Reminder"))).delete()


#####################################################################################################################################################################
def delete_all_reminders_from_recommendation_id(recommendationId):
    db = current.db
    recomm = db.t_recommendations[recommendationId]
    if recomm:
        db((db.mail_queue.recommendation_id == recommendationId) & (db.mail_queue.mail_template_hashtag.startswith("#Reminder"))).delete()

#####################################################################################################################################################################
def send_reset_password(user, link):
    mail_vars = emailing_tools.getMailCommonVars()

    mail_vars["destAddress"] = user.email
    mail_vars["linkTarget"] = link

    hashtag_template = "#UserResetPassword"
    emailing_tools.insertMailInQueue(hashtag_template, mail_vars)

######################################################################################################################################################################
def send_to_coar_requester(user, article):
    mail_vars = emailing_tools.getMailCommonVars()

    mail_vars["destPerson"] = common_small_html.mkUser(user.id)
    mail_vars["destAddress"] = user.email
    mail_vars["ccAddresses"] = mail_vars["appContactMail"]
    mail_vars["bccAddresses"] = emailing_vars.getManagersMails()
    mail_vars["aboutEthicsLink"] = URL("about", "ethics", scheme=True)
    mail_vars["helpGenericLink"] = URL("help", "help_generic", scheme=True)
    mail_vars["completeSubmissionLink"] = URL("coar", "complete_submission", scheme=True,
        vars=dict(articleId=article.id, key=user.reset_password_key,
                    coarId=article.coar_notification_id),
    )
    mail_vars["cancelSubmissionLink"] = URL("coar", "cancel_submission", scheme=True,
        vars=dict(articleId=article.id, coarId=article.coar_notification_id),
    )

    hashtag_template = "#UserCompleteSubmissionCOAR"

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, article_id=article.id)
    create_reminder_user_complete_submission(article)

    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports=[])
    emailing_tools.getFlashMessage(reports)


def send_to_coar_resubmitter(user, article):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    mail_vars["destPerson"] = common_small_html.mkUser(user.id)
    mail_vars["destAddress"] = user.email
    mail_vars["ccAddresses"] = mail_vars["appContactMail"]
    mail_vars["bccAddresses"] = emailing_vars.getManagersMails()
    mail_vars["linkTarget"] = URL(
        c="user", f="edit_my_article",
        vars=dict(articleId=article.id, key=user.reset_password_key),
        scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"],
    )

    hashtag_template = "#UserCompleteResubmissionCOAR"

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, article_id=article.id)

    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports=[])
    emailing_tools.getFlashMessage(reports)


def create_reminder_user_complete_submission(article):
    db, auth = current.db, current.auth
    mail_vars = emailing_tools.getMailCommonVars()

    mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
    mail_vars["destAddress"] = User.get_by_id(article.user_id).email
    mail_vars["ccAddresses"] = emailing_vars.getManagersMails()

    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["message"] = MailQueue.get_mail_content(
            MailQueue.get_by_article_and_template(article.id, "#UserCompleteSubmissionCOAR").first())

    hashtag_template = "#ReminderUserCompleteSubmissionCOAR"

    emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, None, None, article.id)


def send_report_coar_post_received(req):
    session, auth, db = current.session, current.auth, current.db

    author = req["actor"]
    doi = req["object"]["ietf:cite-as"]

    mail_vars = emailing_tools.getMailCommonVars()

    mail_vars["destAddress"] = myconf.get("contacts.generic_contact")
    mail_vars["author_email_link"] = f'<a href="{author["id"]}">{author["name"]}</a>'
    mail_vars["notification_link"] = URL("coar_notify", f"show?id={req['id']}", scheme=True)
    mail_vars["submission_doi_link"] = f'<a href="{doi}">{doi}</a>'

    hashtag_template = "#AdminReportCOARPostReceived"

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars)


######################################################################################################################################################################
def check_mail_queue(hashtag, reviewer_mail, recomm_id):
    db = current.db
    hashtag = hashtag + "%"
    return db(
            db.mail_queue.mail_template_hashtag.like(hashtag)
         & (db.mail_queue.dest_mail_address==reviewer_mail)
         & (db.mail_queue.recommendation_id==recomm_id)
    ).count() > 0

######################################################################################################################################################################
def create_cancellation_for_reviewer(review_id: int):
    session, auth, db = current.session, current.auth, current.db

    review = Review.get_by_id(review_id)
    if not review:
        return

    recommendation = Recommendation.get_by_id(review.recommendation_id)
    if not recommendation:
        return

    article = Article.get_by_id(recommendation.article_id)
    if not article:
        return

    reviewer = User.get_by_id(review.reviewer_id)
    if not reviewer: # dest reviewer might have been deleted
        return

    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    mail_vars["destPerson"] = common_small_html.mkUser(reviewer.id).flatten()
    mail_vars["replytoAddresses"] = mail_vars["appContactMail"]
    mail_vars["ccAddresses"] = mail_vars["appContactMail"]
    mail_vars["destAddress"] = reviewer.email
    mail_vars["sender"] = mkSender(recommendation)
    mail_vars["art_doi"] = common_small_html.mkLinkDOI(recommendation.doi or article.doi)
    mail_vars["art_title"] = md_to_html(article.title)
    mail_vars["art_authors"] = mkAuthors(article)

    mail_vars.update({
        "articleTitle": mail_vars["art_title"],
        "articleDoi": mail_vars["art_doi"],
        "articleAuthors": mail_vars["art_authors"],
    })

    if pciRRactivated:
        mail_vars.update(getPCiRRScheduledSubmissionsVars(article))

    hashtag_template: Optional[str] = None
    if review.review_state == ReviewState.AWAITING_RESPONSE.value:
        hashtag_template = emailing_tools.get_correct_hashtag("#DefaultReviewCancellation", article)
    if review.review_state == ReviewState.AWAITING_REVIEW.value and isScheduledTrack(article) and article.report_stage == "STAGE 1":
        hashtag_template = "#DefaultReviewAlreadyAcceptedCancellationStage1ScheduledSubmission"

    if not hashtag_template:
        return

    if not check_mail_queue(hashtag_template, reviewer.email, review.recommendation_id):
        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recommendation.id, None, recommendation.article_id)
        reports = emailing_tools.createMailReport(True, mail_vars["destPerson"], reports)
        emailing_tools.getFlashMessage(reports)

######################################################################################################################################################################
def create_reminder_recommender_could_make_decision(recommId):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    recomm = db.t_recommendations[recommId]
    article = db.t_articles[recomm.article_id]

    mail_vars["destPerson"] = common_small_html.mkUser(recomm.recommender_id)
    mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]

    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["articleAuthors"] = mkAuthors(article)

    mail_vars["ccAddresses"] = emailing_vars.getManagersMails()

    hashtag_template = "#ReminderRecommender2ReviewsReceivedCouldMakeDecision"

    emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id)

################################################################################################
def alert_managers_recommender_action_needed(hashtag_template: str, recommId: int):
    session, auth, db = current.session, current.auth, current.db

    mail_vars = emailing_tools.getMailCommonVars()

    recomm = db.t_recommendations[recommId]
    article = db.t_articles[recomm.article_id]

    if recomm and article:
        mail_vars["destAddress"] = mail_vars["appContactMail"]
        mail_vars["articleTitle"] = md_to_html(article.title)
        mail_vars["recommenderPerson"] = mk_recommender(article)
        mail_vars["ccAddresses"] = emailing_vars.getManagersMails()

        emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recomm.id, None, article.id)

########################################################
def delete_reminder_for_managers(hashtag_template: List[str],
                                 recommendation_id: Optional[int] = None,
                                 article_id: Optional[int] = None,
                                 sending_status: List[SendingStatus] = []):
    db = current.db

    query = (db.mail_queue.mail_template_hashtag.belongs(hashtag_template))
    if recommendation_id:
        query = query & (db.mail_queue.recommendation_id == recommendation_id)
    if article_id:
        query = query & (db.mail_queue.article_id == article_id)
    if sending_status:
        status = [s.value for s in sending_status]
        query = query & (db.mail_queue.sending_status.belongs(status))

    db(query).delete()


def send_warning_to_submitters(article_id):
    db = current.db
    mail_vars = emailing_tools.getMailCommonVars()
    article = db.t_articles[article_id]

    if article:
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]
        mail_vars["replytoAddresses"] = mail_vars["appContactMail"]
        mail_vars["articleTitle"] = md_to_html(article.title)

        hashtag_template = "#SubmitterPendingSurveyWarning"

        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, None, None, article.id)

######################################################################################################################################################################
def send_set_not_considered_mail(subject: str, message: str, article: Article, author: User):
    form = replace_mail_vars_set_not_considered_mail(article, subject, message)
    send_submitter_generic_mail(author.email, article.id, form, "#SubmitterNotConsideredSubmission")

########################################################

def send_conditional_acceptation_review_mail(review: Review):
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    recommendation = Recommendation.get_by_id(review.recommendation_id)
    if not recommendation:
        return

    article = Article.get_by_id(recommendation.article_id)
    if not article:
        return

    recommender = User.get_by_id(recommendation.recommender_id)
    if not recommender:
        return

    mail_vars["delay"] = review.review_duration.lower()
    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
    mail_vars["articleAuthors"] = mkAuthors(article)
    mail_vars["linkTarget"] = URL(
        c="recommender", f="recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(articleId=article.id),
    )
    mail_vars["destPerson"] = common_small_html.mkUser(recommendation.recommender_id)
    mail_vars["destAddress"] = recommender.email
    mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(review.reviewer_id)
    mail_vars["recommenderPerson"] = common_small_html.mkUser(recommendation.recommender_id)

    hashtag_template = "#ConditionalRecommenderAcceptationReview"

    buttons = conditional_acceptation_review_mail_button(review.id, mail_vars)
    conditional_recommender_acceptation_review_mail_id = emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recommendation.id, article_id=article.id, sugg_recommender_buttons=buttons)

    create_reminder_for_conditional_recommender_acceptation_review(review, article, recommendation, recommender, buttons, conditional_recommender_acceptation_review_mail_id)

    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)
    emailing_tools.getFlashMessage(reports)


def conditional_acceptation_review_mail_button(review_id: int, mail_vars: Dict[str, Any]):
    return DIV(
            A(
                SPAN(
                    current.T("I accept"),
                    _style="margin: 10px; font-size: 14px; background: #93c54b; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px; display: block",
                ),
                _href=URL(c="recommender_actions",
                          f="accept_new_delay_to_reviewing",
                          vars=dict(reviewId=review_id),
                          user_signature=True,
                          scheme=mail_vars["scheme"],
                          host=mail_vars["host"],
                          port=mail_vars["port"]),
                _style="text-decoration: none; display: block",
            ),
            B(current.T("OR")),
            A(
                SPAN(
                    current.T("I decline"),
                    _style="margin: 10px; font-size: 14px; background: #f47c3c; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px; display: block",
                ),
                _href=URL(c="recommender_actions",
                          f="decline_new_delay_to_reviewing",
                          vars=dict(reviewId=review_id),
                          user_signature=True,
                          scheme=mail_vars["scheme"],
                          host=mail_vars["host"],
                          port=mail_vars["port"]),
                _style="text-decoration: none; display: block",
            ),
            _style="width: 100%; text-align: center; margin-bottom: 25px;",
        )

########################################################

def send_decision_new_delay_review_mail(accept: bool, review: Review):
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    recommendation = Recommendation.get_by_id(review.recommendation_id)
    if not recommendation:
        return

    article = Article.get_by_id(recommendation.article_id)
    if not article:
        return

    reviewer = User.get_by_id(review.reviewer_id)
    if not reviewer:
        return

    mail_vars["delay"] = review.review_duration.lower()
    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
    mail_vars["articleAuthors"] = mkAuthors(article)
    mail_vars["linkTarget"] = URL(c="default", f="invitation_to_review", vars=dict(reviewId=review.id, key=reviewer.reset_password_key), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
    mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
    mail_vars["destAddress"] = reviewer.email
    mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(review.reviewer_id)
    mail_vars["recommenderPerson"] = common_small_html.mkUser(recommendation.recommender_id)
    mail_vars["reviewDuration"] = review.review_duration.lower() if review.review_duration else ''
    mail_vars["expectedDuration"] = datetime.timedelta(days=get_review_days(review))
    mail_vars["dueTime"] = str((datetime.datetime.now() + mail_vars["expectedDuration"]).strftime(DEFAULT_DATE_FORMAT))

    if accept:
        hashtag_template = "#RecommenderAcceptReviewNewDelay"
    else:
        hashtag_template = "#RecommenderDeclineReviewNewDelay"

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recommendation.id, article_id=article.id)
    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)
    emailing_tools.getFlashMessage(reports)

########################################################

def create_reminder_for_conditional_recommender_acceptation_review(review: Review, article: Article, recommendation: Recommendation, recommender: User, buttons: Any, conditional_recommender_acceptation_review_mail_id: int):
    if not review or not recommendation or not article or not recommender or not buttons:
        return None

    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["delay"] = review.review_duration.lower()
    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
    mail_vars["articleAuthors"] = mkAuthors(article)
    mail_vars["linkTarget"] = URL(
        c="recommender", f="recommendations", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(articleId=article.id),
    )
    mail_vars["destPerson"] = common_small_html.mkUser(recommendation.recommender_id)
    mail_vars["destAddress"] = recommender.email
    mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(review.reviewer_id)
    mail_vars["recommenderPerson"] = common_small_html.mkUser(recommendation.recommender_id)

    mail_vars["message"] = ''
    conditional_recommender_acceptation_review_mail = MailQueue.get_mail_by_id(conditional_recommender_acceptation_review_mail_id)
    if conditional_recommender_acceptation_review_mail:
        mail_vars["message"] = MailQueue.get_mail_content(conditional_recommender_acceptation_review_mail)

    hashtag_template = "#ReminderRecommenderAcceptationReview"

    emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, recommendation.id, None, article.id, review.id, reviewer_invitation_buttons=buttons)

#########################################################

def send_alert_reviewer_due_date_change(review: Review):
    mail_vars = emailing_tools.getMailCommonVars()
    reports = []

    recommendation = Recommendation.get_by_id(review.recommendation_id)
    if not recommendation:
        return

    article = Article.get_by_id(recommendation.article_id)
    if not article:
        return

    reviewer = User.get_by_id(review.reviewer_id)
    if not reviewer:
        return

    recommender = User.get_by_id(recommendation.recommender_id)
    if not recommender:
        return

    mail_vars["myReviewsLink"] = reviewLink()
    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)
    mail_vars["dueDate"] = review.due_date.strftime(DEFAULT_DATE_FORMAT)

    mail_vars["destPerson"] = common_small_html.mkUser(review.reviewer_id)
    mail_vars["destAddress"] = reviewer.email
    mail_vars["ccAddresses"] = [recommender.email] + emailing_vars.get_co_recommenders_mails(recommendation.id)

    hashtag_template = "#RecommenderChangeReviewDueDate"

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, recommendation.id, article_id=article.id)
    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports)
    emailing_tools.getFlashMessage(reports)
##################################################################################################################################################################

def send_import_biorxiv_alert(xml_file_path: str, msg: str):
    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["destAddress"] = mail_vars["appGenericContactMail"]
    pre_style = "overflow-y: scroll; max-width: 100%; height: 100%; color: #8e8c84; background-color: #f5f5f5; border: 1px solid #cccccc; border-radius: 4px; padding: 9.5px;"
    with open(xml_file_path, 'r') as xml_file:
        content = ""
        for line in xml_file:
            content += f"{html.escape(line)}<br/>"

    mail_vars["xmlContent"] = (
            f'<span>{msg}</span>' +
            f'<pre lang="xml" style="{pre_style}">{content}</pre>'
    )
    hashtag_template = "#BiorxivFTPAlert"

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars)


def send_to_biorxiv_requester(user: User, article: Article):
    mail_vars = emailing_tools.getMailCommonVars()

    mail_vars["destPerson"] = common_small_html.mkUser(user.id)
    mail_vars["destAddress"] = user.email
    mail_vars["ccAddresses"] = mail_vars["appContactMail"]
    mail_vars["bccAddresses"] = emailing_vars.getManagersMails()
    mail_vars["aboutEthicsLink"] = URL("about", "ethics", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
    mail_vars["helpGenericLink"] = URL("help", "help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
    mail_vars["completeSubmissionLink"] = URL("biorxiv", "complete_submission", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"],
        vars=dict(articleId=article.id, key=user.reset_password_key),
    )
    mail_vars["cancelSubmissionLink"] = URL("biorxiv", "cancel_submission", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"],
        vars=dict(articleId=article.id, pre_submission_token=article.pre_submission_token)
    )

    hashtag_template = "#UserCompleteSubmissionBiorxiv"

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, article_id=article.id)
    create_reminder_user_complete_submission_biorxiv(article)

    reports = emailing_tools.createMailReport(True, mail_vars["destPerson"].flatten(), reports=[])
    emailing_tools.getFlashMessage(reports)


def create_reminder_user_complete_submission_biorxiv(article: Article):
    mail_vars = emailing_tools.getMailCommonVars()

    mail_vars["destPerson"] = common_small_html.mkUser(article.user_id)
    mail_vars["destAddress"] = User.get_by_id(article.user_id).email
    mail_vars["ccAddresses"] = emailing_vars.getManagersMails()

    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["message"] = MailQueue.get_mail_content(
            MailQueue.get_by_article_and_template(article.id, "#UserCompleteSubmissionBiorxiv").first())

    hashtag_template = "#ReminderUserCompleteSubmissionBiorxiv"

    emailing_tools.insert_reminder_mail_in_queue(hashtag_template, mail_vars, None, None, article.id)

##################################################################################################################################################################
def send_message_to_recommender_and_reviewers(article_id: int):
    db, auth = current.db, current.auth
    mail_vars = emailing_tools.getMailCommonVars()
    article = db.t_articles[article_id]
    hashtag_template = "#ArticlePublishedPCJ"

    if article:
        recommenders_mails = Article.get_recommenders_and_reviewers_mails(article_id)
        if not recommenders_mails:
            return

        mail_vars["destAddress"] = recommenders_mails[0]
        mail_vars["replytoAddresses"] = mail_vars["appContactMail"]
        mail_vars["articleDoi"] = common_small_html.mkLinkDOI(article.doi)
        mail_vars["published_doi"] = common_small_html.mkLinkDOI(article.doi_of_published_article)
        mail_vars["ccAddresses"] = recommenders_mails[1]
        mail_vars["bccAddresses"] = recommenders_mails[2]

        emailing_tools.insertMailInQueue(hashtag_template, mail_vars, None, None, article.id)

##################################################################################################################################################################

def send_unsubscription_alert_for_manager():
    db, auth = current.db, current.auth
    mail_vars = emailing_tools.getMailCommonVars()
    hashtag_template = "#UnsubscriptionAlert"

    mail_vars["person"] = common_small_html.mkUser(auth.user.id)
    mail_vars["address"] = auth.user.email

    mail_vars["destAddress"] = mail_vars["appContactMail"]
    mail_vars["ccAddresses"] = emailing_vars.getManagersMails()

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars)


##################################################################################################################################################################

def send_new_comment_alert(article_id: int):
    article = Article.get_by_id(article_id)
    recommendation = Article.get_last_recommendation(article_id)

    if not article or not recommendation:
        return

    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["destAddress"] = mail_vars["appContactMail"]
    mail_vars["bccAddresses"] = emailing_vars.getManagersMails()
    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["linkTarget"] = URL(c="articles", f="rec", vars=dict(id=article_id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

    hashtag_template = "#CommentPosted"

    emailing_tools.insertMailInQueue(hashtag_template, mail_vars, article_id=article.id)


##################################################################################################################################################################

def send_or_update_mail_manager_valid_suggested_recommender(article_id: int, resend: bool = True):
    template = "#ValidSuggestedRecommender"
    template_reminder = "#ReminderValidSuggestedRecommender"

    article = Article.get_by_id(article_id)
    if not article:
        return

    next_url = URL(c="manager", f="suggested_recommenders", vars=dict(articleId=article_id), scheme=True)

    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["destAddress"] = mail_vars["appContactMail"]
    mail_vars["ccAddresses"] = emailing_vars.getManagersMails()
    mail_vars["submitterPerson"] = str(B(common_small_html.mkUser(article.user_id) if article.user_id else "?"))
    mail_vars["linkTarget"] = str(A(next_url, _href=next_url))
    mail_vars["articleTitle"] = str(B(md_to_html(article.title)))

    suggested_recommenders = SuggestedRecommender.get_by_article(article_id, True, False, SuggestedBy.AUTHORS)
    buttons: DIV = DIV()
    button_style = "font-size: 14px; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px; display: inline-block; margin-right: 5px"

    if len(suggested_recommenders) == 0 or article.status != ArticleStatus.AWAITING_CONSIDERATION.value:
        delete_reminder_for_managers([template, template_reminder],
                                     article_id=article_id,
                                     sending_status=[SendingStatus.PENDING])
        return

    for suggested_recommender in suggested_recommenders:
        recommender = User.get_by_id(suggested_recommender.suggested_recommender_id)
        if not recommender:
            continue

        button = DIV(
                mkUser_U(recommender, True, orcid=True),
                A(f"{recommender.email}", _href=f"mailto:{recommender.email}", _style="display: block"),
                CENTER(
                    A(SPAN(current.T("Valid"), _style=f"background: #93c54b; margin-right: 5px; {button_style}"),
                    _href=URL("manager", "do_valid_suggested_recommender",vars=dict(sugg_recommender_id=suggested_recommender.id, _next=next_url), scheme=True),
                    _style="text-decoration: none;",
                    ),
                    A(
                        SPAN(current.T("Reject"), _style=f"background: #f47c3c; margin-left: 5px; {button_style}"),
                        _href=URL("manager", "do_reject_suggested_recommender",vars=dict(sugg_recommender_id=suggested_recommender.id, _next=next_url), scheme=True),
                        _style="text-decoration: none;",
                    ),
                _style="margin-top: 5px"),
                _style="width: 100%; text-align: center; margin-bottom: 25px;",
            )

        buttons.append(button) # type: ignore

    pending_mails = MailQueue.get_by_article_and_template(article_id, template, [SendingStatus.PENDING])
    sending_date = datetime.datetime.now() + datetime.timedelta(hours=1)

    if len(pending_mails) > 0:
        for pending_mail in pending_mails:
            MailQueue.change_suggested_recommender_button(pending_mail, buttons, mail_vars)
            pending_mail.update_record(sending_date=sending_date) # type: ignore
    else:
        if resend:
            emailing_tools.insert_reminder_mail_in_queue(template,
                                                        mail_vars,
                                                        article_id=article_id,
                                                        sugg_recommender_buttons=buttons,
                                                        sending_date_forced=sending_date)

    if len(pending_mails) > 0 or resend:
        delete_reminder_for_managers([template_reminder], article_id=article_id, sending_status=[SendingStatus.PENDING])

    pending_mails_reminder = MailQueue.get_by_article_and_template(article_id, template_reminder, [SendingStatus.PENDING])
    if len(pending_mails_reminder) > 0:
        for pending_mail in pending_mails_reminder:
            mail = MailQueue.change_suggested_recommender_button(pending_mail, buttons, mail_vars)
            mail.update_record(sending_date=mail.sending_date + datetime.timedelta(hours=1)) # type: ignore
    else:
        if len(pending_mails) > 0 or resend:
            mail_id = emailing_tools.insert_reminder_mail_in_queue(template_reminder,
                                                        mail_vars,
                                                        article_id=article_id,
                                                        sugg_recommender_buttons=buttons)
            if mail_id:
                mail = MailQueue.get_mail_by_id(mail_id)
                if mail:
                    mail.update_record(sending_date=mail.sending_date + datetime.timedelta(hours=1)) # type: ignore


def send_manager_alert_willing_to_recommend(article_id: int):
    if SuggestedRecommender.already_request_willing_to_recommend(article_id, current.auth.user_id):
        return

    mail_template = "#WillingRecommenderValidation"
    recommender_id = int(current.auth.user_id)

    article = Article.get_by_id(article_id)
    if not article:
        return

    mail_vars = emailing_tools.getMailCommonVars()
    mail_vars["destAddress"] = mail_vars["appContactMail"]
    mail_vars["ccAddresses"] = emailing_vars.getManagersMails()
    mail_vars["articleTitle"] = md_to_html(article.title)
    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(recommender_id, True, orcid=True)
    mail_vars["linkTarget"] = URL(c="manager",
                                  f="suggested_recommenders",
                                  vars=dict(articleId=article_id),
                                  scheme=True)

    emailing_tools.insertMailInQueue(mail_template, mail_vars, article_id=article_id)
