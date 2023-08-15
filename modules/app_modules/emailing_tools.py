# -*- coding: utf-8 -*-

import os
import time
import re
from re import sub, match
from lxml import html
from datetime import datetime, timedelta
from typing import Optional, cast

# from copy import deepcopy
from dateutil.relativedelta import *
import traceback
from pprint import pprint

from gluon import current
from gluon.storage import Storage
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail
from gluon.validators import IS_EMAIL
from models.article import Article
from pydal import DAL

from gluon.custom_import import track_changes
from models.article import Article
from models.recommendation import Recommendation
from models.user import User

track_changes(True)
import socket

from uuid import uuid4
from contextlib import closing
import shutil

from app_modules import common_tools
from app_modules import common_small_html
from app_modules import old_common
from app_modules import helper
from app_modules.reminders import getReminder

myconf = AppConfig(reload=True)
contact = myconf.take("contacts.managers")
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

MAIL_DELAY = 1.5  # in seconds

# common view for all emails
MAIL_HTML_LAYOUT = os.path.join(os.path.dirname(__file__), "../../views/mail", "mail.html")

CLEANR = re.compile('<.*?>')

######################################################################################################################################################################
# Mailing tools
######################################################################################################################################################################

appName = myconf.take("app.name")

def email_subject_header(articleId):
    return "%s #%s" % (appName, articleId)

def patch_email_subject(subject, articleId):
    return subject.replace(appName, email_subject_header(articleId))


def mkAuthors(article):
    return article.authors if not article.anonymous_submission else current.T("[undisclosed]")


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
def getMailCommonVars():
    return dict(
        scheme=myconf.take("alerts.scheme"),
        host=myconf.take("alerts.host"),
        port=myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v)),
        appDescription=myconf.take("app.description"),
        appName=myconf.take("app.name"),
        appLongName=myconf.take("app.longname"),
        longname=myconf.take("app.longname"),  # DEPRECATED: for compatibility purposes; to be removed after checking
        appThematics=myconf.take("app.thematics"),
        appContactMail=myconf.take("contacts.managers"),
        appContactLink=A(myconf.take("contacts.managers"), _href="mailto:" + myconf.take("contacts.managers")),
        siteUrl=URL(c="default", f="index", scheme=myconf.take("alerts.scheme"), host=myconf.take("alerts.host"), port=myconf.take("alerts.port")),
    )

######################################################################################################################################################################

def getMailForReviewerCommonVars(auth: Auth, db: DAL, sender: User, article: Article, recommendation: Recommendation, reviewer_last_name: Optional[str] = None):
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    is_co_recommender = helper.is_co_recommender(auth, db, recommendation.id)

    mail_vars = getMailCommonVars()

    mail_vars["description"] = myconf.take("app.description")
    mail_vars["longname"] = myconf.take("app.longname") # DEPRECATED
    mail_vars["appLongName"] = myconf.take("app.longname")
    mail_vars["appName"] = myconf.take("app.name")
    mail_vars["thematics"] = myconf.take("app.thematics")
    mail_vars["scheme"] = scheme
    mail_vars["host"] = host
    mail_vars["port"] = port
    mail_vars["site_url"] = URL(c="default", f="index", scheme=scheme, host=host, port=port)
    mail_vars["art_authors"] = mkAuthors(article)
    mail_vars["authors"] = mail_vars["art_authors"]
    mail_vars["articleAuthors"] = mail_vars["art_authors"]

    if reviewer_last_name:
        mail_vars["LastName"] = reviewer_last_name
    
    if recommendation.doi:
        mail_vars["art_doi"] = common_small_html.mkLinkDOI(recommendation.doi)
        mail_vars["articleDoi"] = mail_vars["art_doi"]
    elif article.doi:
        mail_vars["art_doi"] = common_small_html.mkLinkDOI(article.doi)
        mail_vars["articleDoi"] = mail_vars["art_doi"]

    if article.title:
        mail_vars["art_title"] = common_small_html.md_to_html(article.title)
        mail_vars["articleTitle"] = mail_vars["art_title"]

    if auth.user_id == recommendation.recommender_id:
        mail_vars["sender"] = common_small_html.mkUser(auth, db, recommendation.recommender_id).flatten()
        mail_vars["Institution"] = sender.institution
        mail_vars["Department"] = sender.laboratory
        mail_vars["country"] = sender.country

        if sender.first_name and sender.last_name:
            mail_vars["senderName"] = sender.first_name + ' ' + sender.last_name

    elif is_co_recommender:
        sender = cast(User, auth.user)
        mail_vars["sender"] = common_small_html.mkUser(auth, db, auth.user_id).flatten() + "[co-recommender]"
        mail_vars["Institution"] = sender.institution
        mail_vars["Department"] = sender.laboratory
        mail_vars["country"] = sender.country

        if sender.first_name and sender.last_name:
            mail_vars["senderName"] = sender.first_name + ' ' + sender.last_name
    
    elif auth.has_membership(role="manager"):
        recommender = User.get_by_id(db, recommendation.recommender_id)
        if recommender:
            mail_vars["sender"] = "The Managing Board of " + myconf.get("app.longname") + " on behalf of " + common_small_html.mkUser(auth, db, recommendation.recommender_id).flatten()
            mail_vars["Institution"] = recommender.institution
            mail_vars["Department"] = recommender.laboratory
            mail_vars["country"] = recommender.country

            if recommender.first_name and recommender.last_name:
                mail_vars["senderName"] = recommender.first_name + ' ' + recommender.last_name

    return mail_vars


######################################################################################################################################################################
def getCorrectHashtag(hashtag, article=None, force_scheduled=False):
    if pciRRactivated and article is not None:
        if article.art_stage_1_id is not None or article.report_stage == "STAGE 2":
            hashtag += "Stage2"
        else:
            hashtag += "Stage1"

    if scheduledSubmissionActivated and article is not None:
        if (article.scheduled_submission_date is not None) or (article.status.startswith("Scheduled submission")) or (force_scheduled):
            hashtag += "ScheduledSubmission"

    return hashtag

#######################################################################################################################################################################
def to_string_addresses(address_list):
    return str(address_list).replace('[','').replace(']','').replace("'",'').replace('"','')


#######################################################################################################################################################################
def list_addresses(addresses):
    return [x.strip(' ') for x in list(re.split("[,; ]", addresses))] \
                if addresses else []

#######################################################################################################################################################################
def clean_addresses(dirty_string_adresses):
    '''
    creates a string of clean mail addresses, divided by comma
    '''
    list_of_contacts = [contact.strip() for contact in list(re.split("[,;]", dirty_string_adresses))]
    contacts = []
    errors = []
    validator = IS_EMAIL()
    for contact in list_of_contacts:
        if len(contact.split(' ')) > 1:
            for word in contact.split(' '):
                if '@' in word:
                    contact = word
        contact = contact.strip('<>')
        value, error = validator(contact)
        if error is None: contacts.append(contact)
        else: errors.append(contact)

    return ', '.join(contacts), ', '.join(errors)

######################################################################################################################################################################
def getMailTemplateHashtag(db, hashTag, myLanguage="default"):
    print(hashTag)
    query = (db.mail_templates.hashtag == hashTag) & (db.mail_templates.lang == myLanguage)
    item = db(query).select().first()

    if item:
        return dict(subject=item.subject, content=item.contents)
    else:
        if scheduledSubmissionActivated and pciRRactivated:
            return generateNewMailTemplates(db, hashTag, myLanguage)
        else:
            return dict(error=True, message="hashtag not found")


######################################################################################################################################################################
def generateNewMailTemplates(db, hashTag, myLanguage):
    baseHashtag = hashTag
    baseHashtag = baseHashtag.replace("Stage1", "")
    baseHashtag = baseHashtag.replace("Stage2", "")
    baseHashtag = baseHashtag.replace("ScheduledSubmission", "")

    # Create stage 1 template
    result1 = insertNewTemplateInDB(db, baseHashtag + "Stage1ScheduledSubmission", baseHashtag + "Stage1", myLanguage)

    # Create stage 2 template
    result2 = insertNewTemplateInDB(db, baseHashtag + "Stage2ScheduledSubmission", baseHashtag + "Stage2", myLanguage)

    if "Stage1" in hashTag:
        return result1
    elif "Stage2" in hashTag:
        if 'error' in result2 and result2['error']:
            return result1
        return result2
    else:
        return dict(error=True, message="hashtag not found")


######################################################################################################################################################################
def insertNewTemplateInDB(db, newHashTag, baseHashtag, myLanguage):
    query = (db.mail_templates.hashtag == baseHashtag) & (db.mail_templates.lang == myLanguage)
    item = db(query).select().first()

    if item:
        print("new template created :" + newHashTag)
        db.mail_templates.insert(
            hashtag=newHashTag, subject=item.subject + " - scheduled submission", contents=item.contents, description=item.description + " (for scheduled submission)"
        )
        return dict(subject=item.subject, content=item.contents)
    else:
        return dict(error=True, message="hashtag not found")


######################################################################################################################################################################
def createMailReport(mail_resu, destPerson, reports):
    if mail_resu:
        reports.append(dict(error=False, message="e-mail sent to %s" % destPerson))
    else:
        reports.append(dict(error=True, message="e-mail NOT SENT to %s" % destPerson))
    return reports


######################################################################################################################################################################
def getFlashMessage(session, reports):
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
def getMailFooter():
    with open(os.path.join(os.path.dirname(__file__), "../../views/mail", "mail_footer.html"), encoding="utf-8") as myfile:
        data = myfile.read()
    return data

######################################################################################################################################################################
# Footer for all mails
def mkFooter(db):
    # init mail_vars with common infos
    mail_vars = getMailCommonVars()

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

    footer_template = getMailTemplateHashtag(db, "#EmailFooterTemplate")
    if 'content' in footer_template and footer_template["content"]:
        footer_content = replaceMailVars(footer_template["content"], mail_vars)
        return XML(footer_content)
    else:
        return XML(getMailFooter() % mail_vars)


######################################################################################################################################################################
def insertMailInQueue(
    auth,
    db,
    hashtag_template,
    mail_vars,
    recommendation_id=None,
    recommendation=None,
    article_id=None,
    review=None,
    authors_reply=None,
    sugg_recommender_buttons=None,
    reviewer_invitation_buttons=None,
):
    mail = buildMail(
        db,
        hashtag_template,
        mail_vars,
        recommendation=recommendation,
        review=review,
        authors_reply=authors_reply,
        article_id=article_id,
        sugg_recommender_buttons=sugg_recommender_buttons,
        reviewer_invitation_buttons=reviewer_invitation_buttons,
    )

    db.mail_queue.insert(
        dest_mail_address=mail_vars["destAddress"],
        cc_mail_addresses=mail_vars.get("ccAddresses"),
        replyto_addresses=mail_vars.get("replytoAddresses"),
        bcc_mail_addresses=mail_vars.get("bccAddresses"),
        mail_subject=mail["subject"],
        mail_content=mail["content"],
        user_id=auth.user_id,
        article_id=article_id,
        recommendation_id=recommendation_id,
        mail_template_hashtag=hashtag_template,
    )


######################################################################################################################################################################
def insertReminderMailInQueue(
    auth,
    db,
    hashtag_template,
    mail_vars,
    recommendation_id=None,
    recommendation=None,
    article_id=None,
    review_id=None,
    review=None,
    authors_reply=None,
    sending_date_forced=None,
    base_sending_date=None,
    reviewer_invitation_buttons=None,
    sender_name: Optional[str]=None
):

    reminder = getReminder(db, hashtag_template, review_id)

    ccAddresses = None
    replytoAddresses = None
    if "ccAddresses" in mail_vars:
        ccAddresses = mail_vars["ccAddresses"]
    if "replytoAddresses" in mail_vars:
        replytoAddresses = mail_vars["replytoAddresses"]

    if reminder:
        elapsed_days = reminder["elapsed_days"][0]
        sending_date = datetime.now() if not base_sending_date \
                else base_sending_date - timedelta(days=7)
        sending_date += timedelta(days=elapsed_days)

    if sending_date_forced:
        sending_date = sending_date_forced

    if True:

        mail = buildMail(
            db, hashtag_template, mail_vars, recommendation=recommendation, review=review, authors_reply=authors_reply, reviewer_invitation_buttons=reviewer_invitation_buttons,
            article_id=article_id,
        )


        db.mail_queue.insert(
            sending_status="pending",
            sending_date=sending_date,
            dest_mail_address=mail_vars["destAddress"],
            cc_mail_addresses=ccAddresses,
            replyto_addresses=replytoAddresses,
            mail_subject=mail["subject"],
            mail_content=mail["content"],
            user_id=auth.user_id,
            recommendation_id=recommendation_id,
            article_id=article_id,
            mail_template_hashtag=hashtag_template,
            review_id=review_id,
            sender_name=sender_name
        )


######################################################################################################################################################################
def insertNewsLetterMailInQueue(
    auth,
    db,
    mail_vars,
    hashtag_template,
    newRecommendations=None,
    newRecommendationsCount=0,
    newPreprintSearchingForReviewers=None,
    newPreprintSearchingForReviewersCount=0,
    newPreprintRequiringRecommender=None,
    newPreprintRequiringRecommenderCount=0,
):

    mail = buildNewsLetterMail(
        db,
        mail_vars,
        hashtag_template,
        newRecommendations,
        newRecommendationsCount,
        newPreprintSearchingForReviewers,
        newPreprintSearchingForReviewersCount,
        newPreprintRequiringRecommender,
        newPreprintRequiringRecommenderCount,
    )

    db.mail_queue.insert(
        dest_mail_address=mail_vars["destAddress"], mail_subject=mail["subject"], mail_content=mail["content"], user_id=auth.user_id, mail_template_hashtag=hashtag_template
    )


######################################################################################################################################################################
def buildMail(db, hashtag_template, mail_vars, recommendation=None, review=None, authors_reply=None, sugg_recommender_buttons=None, reviewer_invitation_buttons=None,
        article_id=None,
    ):

    mail_template = getMailTemplateHashtag(db, hashtag_template)

    subject = replaceMailVars(mail_template["subject"], mail_vars)
    content = replaceMailVars(mail_template["content"], mail_vars)

    if article_id is None:
        subject_without_appname = subject.replace("%s: " % mail_vars["appName"] , "")
    else:
        subject = patch_email_subject(subject, article_id)
        appname_with_article_id = email_subject_header(article_id)
        subject_without_appname = subject.replace("%s: " % appname_with_article_id , "")

    applogo = URL("static", "images/small-background.png", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

    content_rendered = render(
        filename=MAIL_HTML_LAYOUT,
        context=dict(
            subject=subject_without_appname,
            applogo=applogo,
            appname=mail_vars["appName"],
            content=XML(content),
            footer=mkFooter(db),
            recommendation=recommendation,
            review=review,
            authors_reply=authors_reply,
            sugg_recommender_buttons=sugg_recommender_buttons,
            reviewer_invitation_buttons=reviewer_invitation_buttons,
        ),
    )

    return dict(content=content_rendered, subject=subject)


######################################################################################################################################################################
def buildNewsLetterMail(
    db,
    mail_vars,
    hashtag_template,
    newRecommendations=None,
    newRecommendationsCount=0,
    newPreprintSearchingForReviewers=None,
    newPreprintSearchingForReviewersCount=0,
    newPreprintRequiringRecommender=None,
    newPreprintRequiringRecommenderCount=0,
):
    mail_template = getMailTemplateHashtag(db, hashtag_template)

    subject = replaceMailVars(mail_template["subject"], mail_vars)
    content = replaceMailVars(mail_template["content"], mail_vars)

    full_link = { var: mail_vars[var] for var in ["scheme", "host", "port"] }

    subject_without_appname = subject.replace("%s: " % mail_vars["appName"], "")
    applogo = URL("static", "images/small-background.png", **full_link)

    allRecommendationsLink = A(
        current.T("See more recommendations..."),
        _href=URL('default','index', **full_link),
        _style="border-radius: 5px; font-weight: bold; padding: 6px 20px; color: #ffffff; background-color: #3e3f3a;",
    )

    content_rendered = render(
        filename=MAIL_HTML_LAYOUT,
        context=dict(
            subject=subject_without_appname,
            applogo=applogo,
            appname=mail_vars["appName"],
            content=XML(content),
            newRecommendations=XML(newRecommendations),
            newRecommendationsCount=newRecommendationsCount,
            allRecommendationsLink=allRecommendationsLink,
            newPreprintSearchingForReviewers=XML(newPreprintSearchingForReviewers),
            newPreprintSearchingForReviewersCount=newPreprintSearchingForReviewersCount,
            newPreprintRequiringRecommender=XML(newPreprintRequiringRecommender),
            newPreprintRequiringRecommenderCount=newPreprintRequiringRecommenderCount,
            pciRRactivated=pciRRactivated,
            footer=mkFooter(db),
            mail_vars=mail_vars,
        ),
    )

    return dict(content=content_rendered, subject=subject)


######################################################################################################################################################################
def replaceMailVars(text, mail_vars):
    mail_vars_list = mail_vars.keys()

    for var in mail_vars_list:
        if text.find("{{" + var + "}}") > -1:
            if isinstance(mail_vars[var], str):
                replacement_var = mail_vars[var]
            elif isinstance(mail_vars[var], int):
                replacement_var = str(mail_vars[var])
            else:
                try:
                    replacement_var = mail_vars[var].flatten()
                except:
                    replacement_var = str(mail_vars[var])

            text = text.replace("{{" + var + "}}", replacement_var)

    return text

############################################

def replace_mail_vars_set_not_considered_mail(auth: Auth, db: DAL, article: Article, subject: str, message: str):
    form = Storage(subject=subject, message=message, cc=contact)

    mail_vars = getMailCommonVars()
    mail_vars['destPerson'] = common_small_html.mkUser(auth, db, article.user_id)
    mail_vars['articleTitle'] = common_small_html.md_to_html(article.title)
    mail_vars['unconsider_limit_days'] = myconf.get("config.unconsider_limit_days", default=20)
    
    form.subject = replaceMailVars(form.subject, mail_vars)
    form.message = replaceMailVars(form.message, mail_vars)

    return form
