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


myconf = AppConfig(reload=True)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)

mail_sleep = 1.5  # in seconds

# common view for all emails
mail_layout = os.path.join(os.path.dirname(__file__), "../../views/mail", "mail.html")

######################################################################################################################################################################
# Mailing tools
######################################################################################################################################################################

######################################################################################################################################################################
def getMailer(auth):
    mail = auth.settings.mailer
    mail.settings.server = myconf.take("smtp.server")
    mail.settings.sender = myconf.take("smtp.sender")
    mail.settings.login = myconf.take("smtp.login")
    mail.settings.tls = myconf.get("smtp.tls", default=False)
    mail.settings.ssl = myconf.get("smtp.ssl", default=False)
    return mail


######################################################################################################################################################################
def get_mail_common_vars():
    return dict(
        scheme=myconf.take("alerts.scheme"),
        host=myconf.take("alerts.host"),
        port=myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v)),
        appdesc=myconf.take("app.description"),
        appname=myconf.take("app.name"),
        applongname=myconf.take("app.longname"),
        appthematics=myconf.take("app.thematics"),
        contact=myconf.take("contacts.managers"),
        contactMail=myconf.take("contacts.managers"),
    )


######################################################################################################################################################################
def get_mail_template_hashtag(db, hashTag, myLanguage="default"):
    print(hashTag)
    query = (db.mail_templates.hashtag == hashTag) & (db.mail_templates.lang == myLanguage)
    item = db(query).select().first()

    if item:
        return dict(subject=item.subject, content=item.contents)
    else:
        return dict(error=True, message="hashtag not found")


######################################################################################################################################################################
def create_mail_report(mail_resu, destPerson, reports):
    if mail_resu:
        reports.append(dict(error=False, message="email sent to %s" % destPerson))
    else:
        reports.append(dict(error=True, message="email NOT SENT to %s" % destPerson))
    return reports


######################################################################################################################################################################
def get_flash_message(session, reports):
    messages = []

    for report in reports:
        if report["error"]:
            session.flash_status = "warning"

        messages.append(report["message"])
        pass

    print("\n".join(messages))
    if session.flash is None:
        session.flash = "; ".join(messages)
    else:
        session.flash += "; " + "; ".join(messages)


######################################################################################################################################################################
def get_mail_template(templateName):
    with open(os.path.join(os.path.dirname(__file__), "../../templates/mail", templateName), encoding="utf-8") as myfile:
        data = myfile.read()
    return data


######################################################################################################################################################################
# Footer for all mails
def mkFooter():
    # init mail_vars with common infos
    mail_vars = get_mail_common_vars()

    # add vars to mail_vars
    mail_vars["baseurl"] = URL(c="default", f="index", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
    mail_vars["profileurl"] = URL(
        c="default",
        f="user",
        args=("login"),
        vars=dict(_next=URL(c="default", f="user", args=("profile"))),
        scheme=mail_vars["scheme"],
        host=mail_vars["host"],
        port=mail_vars["port"],
    )

    return XML(get_mail_template("mail_footer.html") % mail_vars)


# Get list of emails for all users with role 'manager'
######################################################################################################################################################################
def get_MB_emails(session, auth, db):
    managers = []
    for mm in db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "manager")).select(
        db.auth_user.email
    ):
        managers.append(mm["email"])
    return managers


######################################################################################################################################################################
# Mailing functions
######################################################################################################################################################################

######################################################################################################################################################################
# TEST MAIL (or "How to properly create an emailing function")
def do_send_email_to_test(session, auth, db, userId):
    print("do_send_email_to_test")
    # Get common variables :
    mail_vars = get_mail_common_vars()
    mail = getMailer(auth)

    mail_resu = False
    reports = []

    # Set custom variables :
    mail_vars["destAddress"] = db.auth_user[userId]["email"]
    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, userId)
    mail_vars["linkTarget"] = URL(c="default", f="index", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

    # Get mail content and subject from template and fill them with mail_vars :
    mail_template = get_mail_template_hashtag(db, "#TestMail")
    subject = mail_template["subject"] % mail_vars
    content = mail_template["content"] % mail_vars

    # Try to send mail (will be replaced by "Send mail in queue") :
    try:
        message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
        mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
    except:
        pass

    # Report error (to remove when queued mail) :
    reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
    time.sleep(mail_sleep)

    # Send report (to remove when queued mail) :
    get_flash_message(session, reports)


######################################################################################################################################################################
# Send email to the requester (if any)
def do_send_email_to_submitter(session, auth, db, articleId, newStatus):
    print("do_send_email_to_submitter")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
    reports = []

    mail_vars["unconsider_limit_days"] = myconf.get("config.unconsider_limit_days", default=20)
    mail_vars["recomm_limit_days"] = myconf.get("config.recomm_limit_days", default=50)

    article = db.t_articles[articleId]
    if article and article.user_id is not None:
        mail_vars["destPerson"] = common_small_html.mkUser(auth, db, article.user_id)
        mail_vars["destAddress"] = db.auth_user[article.user_id]["email"]
        mail_vars["articleTitle"] = article.title

        recommendation = None
        mail_vars["linkTarget"] = URL(c="user", f="my_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

        # Define template depending on the article status changed
        if article.status == "Pending" and newStatus == "Awaiting consideration":
            if article.parallel_submission:
                mail_template = get_mail_template_hashtag(db, "#SubmitterParallelPreprintSubmitted")
            else:
                mail_vars["parallelText"] = ""
                if parallelSubmissionAllowed:
                    mail_vars["parallelText"] += (
                        """Please note that if you abandon the process with %(appname)s after reviewers have contributed their time toward evaluation and before the end of the evaluation, we will post the reviewers' reports on the %(appname)s website as recognition of their work and in order to enable critical discussion.<p>"""
                        % mail_vars
                    )
                mail_template = get_mail_template_hashtag(db, "#SubmitterPreprintSubmitted")

        elif article.status == "Awaiting consideration" and newStatus == "Under consideration":
            if article.parallel_submission:
                mail_template = get_mail_template_hashtag(db, "#SubmitterParallelPreprintUnderConsideration")
            else:
                mail_template = get_mail_template_hashtag(db, "#SubmitterPreprintUnderConsideration")

        elif article.status != newStatus and newStatus == "Cancelled":
            mail_template = get_mail_template_hashtag(db, "#SubmitterCancelledSubmission")

        elif article.status != newStatus and newStatus == "Rejected":
            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["recommTarget"] = URL(
                c="user", f="recommendations", vars=dict(articleId=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )

            mail_template = get_mail_template_hashtag(db, "#SubmitterRejectedSubmission")

        elif article.status != newStatus and newStatus == "Not considered":
            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["recommTarget"] = URL(
                c="user", f="recommendations", vars=dict(articleId=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )

            mail_template = get_mail_template_hashtag(db, "#SubmitterNotConsideredSubmission")

        elif article.status != newStatus and newStatus == "Awaiting revision":
            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["recommTarget"] = URL(
                c="user", f="recommendations", vars=dict(articleId=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )

            mail_template = get_mail_template_hashtag(db, "#SubmitterAwaitingSubmission")

        elif article.status != newStatus and newStatus == "Pre-recommended":
            return  # patience!

        elif article.status != newStatus and newStatus == "Recommended":
            lastRecomm = db((db.t_recommendations.article_id == article.id) & (db.t_recommendations.recommendation_state == "Recommended")).select().last()
            mail_vars["linkTarget"] = URL(c="articles", f="rec", vars=dict(id=articleId), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["doiRecomm"] = XML(common_small_html.mkLinkDOI(lastRecomm.recommendation_doi))
            mail_vars["recommVersion"] = lastRecomm.ms_version
            mail_vars["recommsList"] = SPAN(common_small_html.getRecommAndReviewAuthors(auth, db, recomm=lastRecomm, with_reviewers=False, linked=False)).flatten()
            mail_vars["contact"] = A(myconf.take("contacts.contact"), _href="mailto:" + myconf.take("contacts.contact"))

            mail_template = get_mail_template_hashtag(db, "#SubmitterRecommendedPreprint")

        elif article.status != newStatus:
            mail_vars["tOldStatus"] = current.T(article.status)
            mail_vars["tNewStatus"] = current.T(newStatus)

            mail_template = get_mail_template_hashtag(db, "#SubmitterPreprintStatusChanged")
        else:
            return

        # Fill define template with mail_vars :
        if mail_template["content"] is not None:
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

        # Send Mail:
        if mail_vars["destAddress"] and content is not None:
            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

        reports = create_mail_report(mail_resu, "submitter " + mail_vars["destPerson"].flatten(), reports)
        time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# Send email to the recommenders (if any) for postprints (gab ex en : 337)
def do_send_email_to_recommender_postprint_status_changed(session, auth, db, articleId, newStatus):
    print("do_send_email_to_recommender_postprint_status_changed")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

            mail_template = get_mail_template_hashtag(db, "#RecommenderPostprintStatusChanged")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

            reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# Send email to the recommenders (if any)
def do_send_email_to_recommender_status_changed(session, auth, db, articleId, newStatus):
    print("do_send_email_to_recommender_status_changed")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
    reports = []
    attach = []

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
                closedRecomm = (
                    db((db.t_recommendations.article_id == articleId) & (db.t_recommendations.recommender_id == recommender_id) & (db.t_recommendations.is_closed == True))
                    .select(orderby=db.t_recommendations.id)
                    .last()
                )
                mail_vars["mailManagers"] = A(myconf.take("contacts.managers"), _href="mailto:" + myconf.take("contacts.managers"))
                mail_vars["deadline"] = (datetime.date.today() + datetime.timedelta(weeks=1)).strftime("%a %b %d")

                # write fields to temp files
                directory = os.path.join(os.path.dirname(__file__), "../../tmp/attachments")
                if not os.path.exists(directory):
                    os.makedirs(directory)

                # NOTE: include answer & track-change (append to "attach")
                if closedRecomm:
                    if closedRecomm.reply is not None and closedRecomm.reply != "":
                        tmpR0 = os.path.join(directory, "Answer_%d.txt" % closedRecomm.id)
                        f0 = open(tmpR0, "w+")
                        f0.write(closedRecomm.reply)
                        f0.close()
                        attach.append(mail.Attachment(tmpR0, content_id="Answer"))
                        try:
                            os.unlink(tmpR0)
                        except:
                            print("unable to delete temp file %s" % tmpR0)
                            pass
                    if closedRecomm.reply_pdf is not None and closedRecomm.reply_pdf != "":
                        (fnR1, stream) = db.t_recommendations.reply_pdf.retrieve(closedRecomm.reply_pdf)
                        tmpR1 = os.path.join(directory, str(uuid4()))
                        with closing(stream) as src, closing(open(tmpR1, "wb")) as dest:
                            shutil.copyfileobj(src, dest)
                        attach.append(mail.Attachment(tmpR1, fnR1))
                        try:
                            os.unlink(tmpR1)
                        except:
                            print("unable to delete temp file %s" % tmpR1)
                            pass
                    if closedRecomm.track_change is not None and closedRecomm.track_change != "":
                        (fnTr, stream) = db.t_recommendations.track_change.retrieve(closedRecomm.track_change)
                        tmpTr = os.path.join(directory, str(uuid4()))
                        with closing(stream) as src, closing(open(tmpTr, "wb")) as dest:
                            shutil.copyfileobj(src, dest)
                        attach.append(mail.Attachment(tmpTr, fnTr))
                        try:
                            os.unlink(tmpTr)
                        except:
                            print("unable to delete temp file %s" % tmpTr)
                            pass

                mail_template = get_mail_template_hashtag(db, "#RecommenderStatusChangedToUnderConsideration")

            elif newStatus == "Recommended":
                mail_vars["linkRecomm"] = URL(c="articles", f="rec", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(id=article.id))
                mail_vars["doiRecomm"] = common_small_html.mkLinkDOI(myRecomm.recommendation_doi)

                mail_template = get_mail_template_hashtag(db, "#RecommenderStatusChangedUnderToRecommended")

            else:
                mail_template = get_mail_template_hashtag(db, "#RecommenderArticleStatusChanged")

            # Fill define template with mail_vars :
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                if len(attach) > 0:
                    mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message, attachments=attach)
                    # NOTE: delete attachment files -> see below
                else:
                    mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

            reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# Do send email to suggested recommenders for a given NO MORE available article
def do_send_email_to_suggested_recommenders_not_needed_anymore(session, auth, db, articleId):
    print("do_send_email_to_suggested_recommenders_not_needed_anymore")
    mail_vars = get_mail_common_vars()
    reports = []

    article = db.t_articles[articleId]
    if article:
        mail_vars["articleTitle"] = article.title
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)

        if article.anonymous_submission:
            mail_vars["articleAuthors"] = current.T("[undisclosed]")
        else:
            mail_vars["articleAuthors"] = article.authors

        # TODO: removing auth.user_id is not the best solution... Should transmit recommender_id
        suggestedQy = db(
            (db.t_suggested_recommenders.article_id == articleId)
            & (db.t_suggested_recommenders.suggested_recommender_id != auth.user_id)
            & (db.t_suggested_recommenders.declined == False)
            & (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)
        ).select(db.t_suggested_recommenders.ALL, db.auth_user.ALL)
        for theUser in suggestedQy:
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, theUser["auth_user.id"])
            mail_vars["destAddress"] = db.auth_user[theUser["auth_user.id"]]["auth_user.email"]

            mail_vars["mailManagers"] = A(myconf.take("contacts.managers"), _href="mailto:" + myconf.take("contacts.managers"))

            # TODO: parallel submission
            mail_template = get_mail_template_hashtag(db, "#RecommenderSuggestionNotNeededAnymore")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            mail = getMailer(auth)
            mail_resu = False
            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

            suggRecom = db.t_suggested_recommenders[theUser["t_suggested_recommenders.id"]]
            if suggRecom.emailing:
                emailing0 = suggRecom.emailing
            else:
                emailing0 = ""
            if mail_resu:
                emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="green">SENT</font></h2>'
                suggRecom.email_sent = True
            else:
                emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="red">NOT SENT</font></h2>'
                suggRecom.email_sent = False
            emailing += message
            emailing += "<hr>"
            emailing += emailing0
            suggRecom.emailing = emailing
            suggRecom.update_record()

            reports = create_mail_report(mail_resu, "suggested recommender" + mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# Do send email to suggested recommenders for a given available article
def do_send_email_to_suggested_recommenders(session, auth, db, articleId):
    print("do_send_email_to_suggested_recommenders")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()
    mail_resu = False
    reports = []

    article = db.t_articles[articleId]
    if article:
        mail_vars["articleTitle"] = article.title
        mail_vars["articleDoi"] = common_small_html.mkDOI(article.doi)

        if article.anonymous_submission:
            mail_vars["articleAuthors"] = current.T("[undisclosed]")
        else:
            mail_vars["articleAuthors"] = article.authors

        suggestedQy = db.executesql(
            "SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND sr.declined IS FALSE AND article_id=%s;",
            placeholders=[article.id],
            as_dict=True,
        )
        for theUser in suggestedQy:
            mail_vars["destPerson"] = common_small_html.mkUser(auth, db, theUser["id"])
            mail_vars["destAddress"] = db.auth_user[theUser["id"]]["email"]
            mail_vars["linkTarget"] = URL(
                c="recommender", f="article_details", vars=dict(articleId=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"]
            )
            mail_vars["helpurl"] = URL(c="help", f="help_generic", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["ethicsurl"] = URL(c="about", f="ethics", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            if article.parallel_submission:
                mail_vars["addNote"] = (
                    "<b>Note:</b> The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appname)s, and hope you will agree to manage this preprint. If the authors abandon the process at %(appname)s after reviewers have written their reports, we will post the reviewers' reports on the %(appname)s website as recognition of the reviewers' work and in order to enable critical discussion.<p>"
                    % mail_vars
                )
            else:
                mail_vars["addNote"] = ""

            mail_template = get_mail_template_hashtag(db, "#RecommenderSuggestedArticle")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

            suggRecom = db.t_suggested_recommenders[theUser["sr_id"]]
            if suggRecom.emailing:
                emailing0 = suggRecom.emailing
            else:
                emailing0 = ""
            if mail_resu:
                emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="green">SENT</font></h2>'
                suggRecom.email_sent = True
            else:
                emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="red">NOT SENT</font></h2>'
                suggRecom.email_sent = False
            emailing += message
            emailing += "<hr>"
            emailing += emailing0
            suggRecom.emailing = emailing
            suggRecom.update_record()

            reports = create_mail_report(mail_resu, "suggested recommender" + mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# Individual reminder for previous message
def do_send_reminder_email_to_suggested_recommender(session, auth, db, suggRecommId):
    print("do_send_reminder_email_to_suggested_recommenders")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
    reports = []

    suggRecomm = db.t_suggested_recommenders[suggRecommId]
    if suggRecomm:
        article = db.t_articles[suggRecomm.article_id]
        if article:
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

            theUser = db.auth_user[suggRecomm.suggested_recommender_id]
            if theUser:
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, theUser["id"])
                mail_vars["destAddress"] = db.auth_user[theUser["id"]]["email"]

                mail_template = get_mail_template_hashtag(db, "#RecommenderSuggestedArticleReminder")
                subject = mail_template["subject"] % mail_vars
                content = mail_template["content"] % mail_vars

                try:
                    message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                    mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
                except:
                    pass

                if suggRecomm.emailing:
                    emailing0 = suggRecomm.emailing
                else:
                    emailing0 = ""
                if mail_resu:
                    emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="green">SENT</font></h2>'
                    suggRecomm.email_sent = True
                else:
                    emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="red">NOT SENT</font></h2>'
                    suggRecomm.email_sent = False
                emailing += message
                emailing += "<hr>"
                emailing += emailing0
                suggRecomm.emailing = emailing
                suggRecomm.update_record()

                reports = create_mail_report(mail_resu, "suggested recommender" + mail_vars["destPerson"].flatten(), reports)
                time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# Do send email to recommender when a review is re-opened
def do_send_email_to_reviewer_review_reopened(session, auth, db, reviewId, newForm):
    print("do_send_email_to_reviewer_review_reopened")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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
            theUser = db.auth_user[rev.reviewer_id]
            if theUser:
                mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id) or ""
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.reviewer_id)
                mail_vars["destAddress"] = db.auth_user[rev.reviewer_id]["email"]

                mail_template = get_mail_template_hashtag(db, "#ReviewerReviewReopened")
                subject = mail_template["subject"] % mail_vars
                content = mail_template["content"] % mail_vars

                try:
                    message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                    mail_resu = mail.send(to=[mail_vars["destAddres"]], subject=subject, message=message)

                    if newForm["emailing"]:
                        emailing0 = newForm["emailing"]
                    else:
                        emailing0 = ""
                    emailing = "<h2>" + str(datetime.datetime.now()) + "</h2>"
                    emailing += message
                    emailing += "<hr>"
                    emailing += emailing0
                    newForm["emailing"] = emailing
                    # rev.update_record()
                except:
                    pass

                reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# Do send email to recommender when a review is closed
def do_send_email_to_recommenders_review_completed(session, auth, db, reviewId):
    print("do_send_email_to_recommenders_review_completed")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
    reports = []
    attach = []

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

            theUser = db.auth_user[recomm.recommender_id]
            if theUser:

                directory = os.path.join(os.path.dirname(__file__), "../../tmp/attachments")
                if not os.path.exists(directory):
                    os.makedirs(directory)

                revText = ""
                if rev.review is not None and rev.review != "":
                    revText = WIKI(rev.review)
                    tmpR0 = os.path.join(directory, "Review_%d.html" % rev.id)
                    f0 = open(tmpR0, "w+")
                    f0.write(revText.flatten())
                    f0.close()
                    attach.append(mail.Attachment(tmpR0, content_id="Review"))
                    try:
                        os.unlink(tmpR0)
                    except:
                        print("unable to delete temp file %s" % tmpR0)
                        pass

                # (gab) This part cause mail is not sent when there's a pdf file to send
                if rev.review_pdf is not None and rev.review_pdf != "":
                    (fnR1, stream) = db.t_reviews.review_pdf.retrieve(rev.review_pdf)
                    tmpR1 = os.path.join(directory, str(uuid4()))
                    with closing(stream) as src, closing(open(tmpR1, "wb")) as dest:
                        shutil.copyfileobj(src, dest)
                    attach.append(mail.Attachment(tmpR1, fnR1))
                    try:
                        os.unlink(tmpR1)
                    except:
                        print("unable to delete temp file %s" % tmpR1)
                        pass
                # (gab) end

                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)
                mail_vars["destAddress"] = db.auth_user[recomm.recommender_id]["email"]
                mail_vars["reviewerPerson"] = common_small_html.mkUserWithMail(auth, db, rev.reviewer_id)

                mail_template = get_mail_template_hashtag(db, "#ReviewerReviewCompleted")
                subject = mail_template["subject"] % mail_vars
                content = mail_template["content"] % mail_vars

                try:
                    message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter(), revText=revText))
                    if len(attach) > 0:
                        mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message, attachments=attach,)
                    else:
                        mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
                except:
                    pass

                reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# Do send email to recommender when a co correcommender accepted recommendation
def do_send_email_to_recommender_co_recommender_considerated(session, auth, db, pressId):
    print("do_send_email_to_recommender_co_recommender_considerated")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

            mail_template = get_mail_template_hashtag(db, "#RecommenderCoRecommenderConsiderated")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

            reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_recommenders_co_recommender_declined(session, auth, db, pressId):
    print("do_send_email_to_recommenders_co_recommender_declined")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

            mail_template = get_mail_template_hashtag(db, "#RecommenderCoRecommenderDeclined")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

            reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_recommenders_co_recommender_agreement(session, auth, db, pressId):
    print("do_send_email_to_recommenders_co_recommender_agreement")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

            mail_template = get_mail_template_hashtag(db, "#RecommenderCoRecommenderAgreement")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                messaage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=messaage)
            except:
                pass

            reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# Do send email to recommender when a review is accepted for consideration
def do_send_email_to_recommenders_review_considered(session, auth, db, reviewId):
    print("do_send_email_to_recommenders_review_considered")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

            mail_template = get_mail_template_hashtag(db, "#RecommenderReviewConsidered")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

            reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_recommenders_review_declined(session, auth, db, reviewId):
    print("do_send_email_to_recommenders_review_declined")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

            mail_template = get_mail_template_hashtag(db, "#RecommenderReviewDeclined")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

            reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_reviewer_review_invitation(session, auth, db, reviewsList):
    print("do_send_email_to_reviewer_review_invitation")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

                        mail_template = get_mail_template_hashtag(db, "#ReviewerReviewInvitation")
                        subject = mail_template["subject"] % mail_vars
                        content = mail_template["content"] % mail_vars

                        try:
                            message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                            mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
                        except:
                            pass

                        if mail_resu:
                            rev.review_state = "Pending"
                            rev.update_record()

                        reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                        time.sleep(mail_sleep)

                    else:
                        print("do_send_email_to_reviewer_review_invitation: Article not found")
                else:
                    print("do_send_email_to_reviewer_review_invitation: recommender = reviewer")
            else:
                print("do_send_email_to_reviewer_review_invitation: Recommendation not found")
        else:
            print("do_send_email_to_reviewer_review_invitation: Review not found")

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_reviewers_article_cancellation(session, auth, db, articleId, newStatus):
    print("do_send_email_to_reviewers_article_cancellation")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

                    mail_template = get_mail_template_hashtag(db, "#ReviewersArticleCancellation")
                    subject = mail_template["subject"] % mail_vars
                    content = mail_template["content"] % mail_vars

                    try:
                        message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                        mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
                    except:
                        pass

                    if rev.emailing:
                        emailing0 = rev.emailing
                    else:
                        emailing0 = ""
                    if mail_resu:
                        emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="green">SENT</font></h2>'
                    else:
                        emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="red">NOT SENT</font></h2>'
                    emailing += message
                    emailing += "<hr>"
                    emailing += emailing0
                    rev.emailing = emailing
                    rev.review_state = "Cancelled"
                    rev.update_record()

                    reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                    time.sleep(mail_sleep)
        else:
            print("do_send_email_to_reviewers_article_cancellation: Recommendation not found")
    else:
        print("do_send_email_to_reviewers_article_cancellation: Article not found")

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_mail_admin_new_user(session, auth, db, userId):
    print("do_send_mail_admin_new_user")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
    reports = []

    admins = db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "administrator")).select(
        db.auth_user.ALL
    )
    dest = []
    for admin in admins:
        dest.append(admin.email)
    user = db.auth_user[userId]
    if user:
        mail_vars["userTxt"] = common_small_html.mkUser(auth, db, userId)
        mail_vars["userMail"] = user.email

        mail_template = get_mail_template_hashtag(db, "#AdminNewUser")
        subject = mail_template["subject"] % mail_vars
        content = mail_template["content"] % mail_vars

        if len(dest) > 0:  # TODO: also check elsewhere
            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=dest, subject=subject, message=message)
            except:
                pass

    reports = create_mail_report(mail_resu, "administrators", reports)
    time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_mail_new_user(session, auth, db, userId):
    print("do_send_mail_new_user")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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
            mail_template = get_mail_template_hashtag(db, "#NewUserParallelSubmissionAllowed")
        else:
            mail_template = get_mail_template_hashtag(db, "#NewUser")

        subject = mail_template["subject"] % mail_vars
        content = mail_template["content"] % mail_vars

        try:
            message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
            mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
        except:
            pass

        reports = create_mail_report(mail_resu, "new user " + mail_vars["destPerson"].flatten(), reports)
        time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_mail_new_membreship(session, auth, db, membershipId):
    print("do_send_mail_new_membreship")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

            mail_template = get_mail_template_hashtag(db, "#NewMembreshipRecommender")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
                time.sleep(mail_sleep)
            except:
                pass

            reports = create_mail_report(mail_resu, "new recommender " + mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

        elif group.role == "manager":
            mail_template = get_mail_template_hashtag(db, "#NewMembreshipRecommender")
            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
                time.sleep(mail_sleep)
            except:
                pass

            reports = create_mail_report(mail_resu, "new manager " + mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

        else:
            return

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_managers(session, auth, db, articleId, newStatus):
    print("do_send_email_to_managers")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
    reports = []

    managers = db((db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == "manager")).select(db.auth_user.ALL)
    article = db.t_articles[articleId]
    if article:
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

            mail_template = get_mail_template_hashtag(db, "#ManagersPreprintSubmission")

        elif newStatus.startswith("Pre-"):
            recomm = db((db.t_recommendations.article_id == articleId)).select(orderby=db.t_recommendations.id).last()
            if recomm is not None:
                mail_vars["recommenderPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id) or ""  # recommender
            else:
                mail_vars["recommenderPerson"] = "?"
            mail_vars["linkTarget"] = URL(c="manager", f="pending_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_template = get_mail_template_hashtag(db, "#ManagersRecommendationOrDecision")

        elif newStatus == "Under consideration":
            recomm = db((db.t_recommendations.article_id == articleId)).select(orderby=db.t_recommendations.id).last()
            if recomm is not None:
                mail_vars["recommenderPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id) or ""  # recommender
            else:
                mail_vars["recommenderPerson"] = "?"

            mail_vars["linkTarget"] = URL(c="manager", f="ongoing_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            recommendation = old_common.mkFeaturedArticle(auth, db, article, printable=True, scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            if article.status == "Awaiting revision":
                mail_template = get_mail_template_hashtag(db, "#ManagersArticleResubmited")
            else:
                mail_template = get_mail_template_hashtag(db, "#ManagersArticleConsideredForRecommendation")

        elif newStatus == "Cancelled":
            mail_vars["linkTarget"] = URL(c="manager", f="completed_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

            mail_template = get_mail_template_hashtag(db, "#ManagersArticleCancelled")

        else:
            mail_vars["linkTarget"] = URL(c="manager", f="all_articles", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
            mail_vars["tOldStatus"] = current.T(article.status)
            mail_vars["tNewStatus"] = current.T(newStatus)

            mail_template = get_mail_template_hashtag(db, "#ManagersArticleStatusChanged")

        subject = mail_template["subject"] % mail_vars
        content = mail_template["content"] % mail_vars

        for manager in managers:
            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
                mail_resu = mail.send(to=[manager.email], subject=subject, message=message)
            except:
                pass

            reports = create_mail_report(mail_resu, "manager " + (manager.email or ""), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_thank_recommender_postprint(session, auth, db, recommId):
    print("do_send_email_to_thank_recommender_postprint")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

            theUser = db.auth_user[recomm.recommender_id]
            if theUser:
                # recommender = common_small_html.mkUser(auth, db, recomm.recommender_id)
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, recomm.recommender_id)

                mail_template = get_mail_template_hashtag(db, "#RecommenderThankForPostprint")
                subject = mail_template["subject"] % mail_vars
                content = mail_template["content"] % mail_vars

                try:
                    message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                    mail_resu = mail.send(to=[theUser["email"]], subject=subject, message=message)
                except:
                    pass

                reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_thank_recommender_preprint(session, auth, db, articleId):
    print("do_send_email_to_thank_recommender_preprint")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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
            theUser = db.auth_user[recomm.recommender_id]
            if theUser:
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, theUser.id)

                if article.parallel_submission:
                    mail_template = get_mail_template_hashtag(db, "#RecommenderThankForPreprintParallelSubmission")
                else:
                    mail_template = get_mail_template_hashtag(db, "#RecommenderThankForPreprint")

                subject = mail_template["subject"] % mail_vars
                content = mail_template["content"] % mail_vars

                try:
                    message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                    mail_resu = mail.send(to=[theUser["email"]], subject=subject, message=message)
                except:
                    pass

                reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_thank_reviewer_acceptation(session, auth, db, reviewId, newForm):
    print("do_send_email_to_thank_reviewer_acceptation")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

                theUser = db.auth_user[rev.reviewer_id]
                if theUser:
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id) or ""
                    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.reviewer_id)
                    mail_vars["expectedDuration"] = datetime.timedelta(days=21)  # three weeks
                    mail_vars["dueTime"] = str((datetime.datetime.now() + mail_vars["expectedDuration"]).date())

                    mail_template = get_mail_template_hashtag(db, "#ReviewerThankForReviewAcceptation")
                    subject = mail_template["subject"] % mail_vars
                    content = mail_template["content"] % mail_vars

                    try:
                        message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                        mail_resu = mail.send(to=[theUser["email"]], subject=subject, message=message)
                        # rev.update_record()
                    except:
                        pass

                    if newForm["emailing"]:
                        emailing0 = newForm["emailing"]
                    else:
                        emailing0 = ""
                    if mail_resu:
                        emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="green">SENT</font></h2>'
                    else:
                        emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="red">NOT SENT</font></h2>'
                    emailing += message
                    emailing += "<hr>"
                    emailing += emailing0
                    newForm["emailing"] = emailing

                    reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                    time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_thank_reviewer_done(session, auth, db, reviewId, newForm):
    print("do_send_email_to_thank_reviewer_done")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

                theUser = db.auth_user[rev.reviewer_id]
                if theUser:
                    mail_vars["recommenderPerson"] = common_small_html.mkUserWithMail(auth, db, recomm.recommender_id) or ""
                    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.reviewer_id)

                    mail_template = get_mail_template_hashtag(db, "#ReviewerThankForReviewDone")
                    subject = mail_template["subject"] % mail_vars
                    content = mail_template["content"] % mail_vars

                    try:
                        message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                        mail_resu = mail.send(to=[theUser["email"]], subject=subject, message=message)
                        # rev.update_record()
                    except:
                        pass

                    if newForm["emailing"]:
                        emailing0 = newForm["emailing"]
                    else:
                        emailing0 = ""
                    if mail_resu:
                        emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="green">SENT</font></h2>'
                    else:
                        emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="red">NOT SENT</font></h2>'
                    emailing += message
                    emailing += "<hr>"
                    emailing += emailing0
                    newForm["emailing"] = emailing

                    reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                    time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_delete_one_corecommender(session, auth, db, contribId):
    print("do_send_email_to_delete_one_corecommender")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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

                    mail_template = get_mail_template_hashtag(db, "#CoRecommenderRemovedFromArticle")
                    subject = mail_template["subject"] % mail_vars
                    content = mail_template["content"] % mail_vars

                    try:
                        message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                        mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
                    except:
                        pass

                    reports = create_mail_report(mail_resu, "contributor " + mail_vars["destPerson"].flatten(), reports)
                    time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_one_corecommender(session, auth, db, contribId):
    print("do_send_email_to_one_corecommender")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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
                            mail_template = get_mail_template_hashtag(db, "#CoRecommenderAddedOnArticleAlreadyPublished")
                        else:
                            mail_template = get_mail_template_hashtag(db, "#CoRecommenderAddedOnArticle")

                        subject = mail_template["subject"] % mail_vars
                        content = mail_template["content"] % mail_vars

                        try:
                            message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                            mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
                        except:
                            pass

                        reports = create_mail_report(mail_resu, "contributor " + mail_vars["destPerson"].flatten(), reports)
                        time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_to_corecommenders(session, auth, db, articleId, newStatus):
    print("do_send_email_to_corecommenders")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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
                mail_template = get_mail_template_hashtag(db, "#CoRecommendersArticleRecommended")
            else:
                mail_template = get_mail_template_hashtag(db, "#CoRecommendersArticleStatusChanged")

            subject = mail_template["subject"] % mail_vars
            content = mail_template["content"] % mail_vars

            try:
                message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
            except:
                pass

            reports = create_mail_report(mail_resu, "contributor " + mail_vars["destPerson"].flatten(), reports)
            time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def alert_new_recommendations(session, auth, db, userId, msgArticles):
    print("alert_new_recommendations")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
    reports = []

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    applongname = myconf.take("app.longname")
    appname = myconf.take("app.name")
    appdesc = myconf.take("app.description")

    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, userId)
    mail_vars["destAddress"] = db.auth_user[userId]["email"]

    mail_template = get_mail_template_hashtag(db, "#AlertNewRecommendations")
    subject = mail_template["subject"] % mail_vars
    content = mail_template["content"] % mail_vars

    if mail_vars["destAddress"]:
        try:
            message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
            mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
        except:
            pass

        reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
        time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
def do_send_email_decision_to_reviewers(session, auth, db, articleId, newStatus):
    print("do_send_email_decision_to_reviewers")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
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
                ).select(db.t_reviews.id, db.auth_user.ALL)
            else:
                reviewers = db((db.auth_user.id == db.t_reviews.reviewer_id) & (db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Completed")).select(
                    db.t_reviews.id, db.auth_user.ALL
                )

            for rev in reviewers:
                review = db.t_reviews[rev.t_reviews.id]
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, rev.auth_user.id)

                if newStatus == "Recommended":
                    mail_vars["recommDOI"] = common_small_html.mkLinkDOI(recomm.recommendation_doi)
                    mail_vars["linkRecomm"] = URL(c="articles", f="rec", vars=dict(id=article.id), scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
                    mail_template = get_mail_template_hashtag(db, "#ReviewersArticleRecommended")
                else:
                    mail_template = get_mail_template_hashtag(db, "#ReviewersArticleStatusChanged")

                subject = mail_template["subject"] % mail_vars
                content = mail_template["content"] % mail_vars

                try:
                    message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                    mail_resu = mail.send(to=[rev.auth_user.email], subject=subject, message=message)
                except:
                    pass

                if review.emailing:
                    emailing0 = review.emailing
                else:
                    emailing0 = ""
                # emailing = '<h2>'+str(datetime.datetime.now())+'</h2>'
                if mail_resu:
                    emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="green">SENT</font></h2>'
                else:
                    emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="red">NOT SENT</font></h2>'
                    # review.review_state = ''
                emailing += message
                emailing += "<hr>"
                emailing += emailing0
                review.emailing = emailing
                review.update_record()

                reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# RESET PASSWORD EMAIL
def do_send_email_to_reset_password(session, auth, db, userId):
    print("do_send_email_decision_to_reviewers")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
    reports = []

    fkey = db.auth_user[userId]["reset_password_key"]
    mail_vars["destPerson"] = common_small_html.mkUser(auth, db, userId)
    mail_vars["destAddress"] = db.auth_user[userId]["email"]
    mail_vars["siteName"] = I(applongname)
    mail_vars["linkTarget"] = URL(
        c="default", f="user", args=["reset_password"], scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"], vars=dict(key=fkey)
    )  # default/user/reset_password?key=1561727068-2946ea7b-54fe-4caa-87af-9c5e459b3487.
    mail_vars["linkTargetA"] = A(mail_vars["linkTarget"], _href=mail_vars["linkTarget"])

    mail_template = get_mail_template_hashtag(db, "#UserResetPassword")
    subject = mail_template["subject"] % mail_vars
    content = mail_template["content"] % mail_vars

    try:
        message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
        mail_resu = mail.send(to=[mail_vars["destAddress"]], subject=subject, message=message)
    except:
        pass

    reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
    time.sleep(mail_sleep)

    get_flash_message(session, reports)


######################################################################################################################################################################
# No template for this one :
# Will be changed by gab soon...
######################################################################################################################################################################
def do_send_personal_email_to_reviewer(session, auth, db, reviewId, replyto, cc, subject, message, reset_password_key=None, linkTarget=None):
    print("do_send_personal_email_to_reviewer")
    mail = getMailer(auth)
    mail_vars = get_mail_common_vars()

    mail_resu = False
    reports = []

    review = db.t_reviews[reviewId]
    if review:
        recomm = db.t_recommendations[review.recommendation_id]
        if recomm:
            rev = db.auth_user[review["reviewer_id"]]
            if rev:
                mail_vars["destPerson"] = common_small_html.mkUser(auth, db, review.reviewer_id)
                content = DIV(WIKI(message))

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
                    content.append(P())
                    content.append(P(B(current.T("TO ACCEPT OR DECLINE CLICK ON THE FOLLOWING LINK:"))))
                    content.append(A(link, _href=link))
                    content.append(P(B(current.T('THEN GO TO "Contribute —> invitations to review a preprint?" IN THE TOP MENU'))))

                elif linkTarget:
                    content.append(P())
                    if review.review_state is None or review.review_state == "Pending" or review.review_state == "":
                        content.append(P(B(current.T("TO ACCEPT OR DECLINE CLICK ON THE FOLLOWING LINK:"))))
                    elif review.review_state == "Under consideration":
                        content.append(P(B(current.T("TO WRITE, EDIT OR UPLOAD YOUR REVIEW CLICK ON THE FOLLOWING LINK:"))))

                    content.append(A(linkTarget, _href=linkTarget))

                try:
                    message = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
                    mail_resu = mail.send(
                        to=[rev["email"]],
                        cc=[cc, replyto],
                        # bcc=managers,
                        reply_to=replyto,
                        subject=subject,
                        message=message,
                    )
                except:
                    pass

                if review.emailing:
                    emailing0 = review.emailing
                else:
                    emailing0 = ""
                if mail_resu:
                    emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="green">SENT</font></h2>'
                    if review.review_state is None:
                        review.review_state = "Pending"
                else:
                    emailing = "<h2>" + str(datetime.datetime.now()) + ' -- <font color="red">NOT SENT</font></h2>'
                    # review.review_state = ''
                emailing += message
                emailing += "<hr>"
                emailing += emailing0
                review.emailing = emailing
                review.update_record()

                reports = create_mail_report(mail_resu, mail_vars["destPerson"].flatten(), reports)
                time.sleep(mail_sleep)

    get_flash_message(session, reports)
