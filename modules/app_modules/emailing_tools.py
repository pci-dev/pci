# -*- coding: utf-8 -*-

import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, cast

from dateutil.relativedelta import *

from gluon import current
from gluon.storage import Storage
from gluon.html import *
from gluon.template import render # type: ignore
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon.validators import IS_EMAIL

from gluon.custom_import import track_changes
from models.article import Article
from models.recommendation import Recommendation
from models.review import Review
from models.user import User

track_changes(True)

from app_modules import common_tools
from app_modules import common_small_html
from app_modules import helper
from app_modules import emailing_parts
from app_modules.reminders import getReminder


from app_modules.common_tools import URL

myconf = AppConfig(reload=True)
contact = myconf.take("contacts.managers")

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

# common view for all emails
MAIL_HTML_LAYOUT = os.path.join(os.path.dirname(__file__), "../../views/mail", "mail.html")

######################################################################################################################################################################
# Mailing tools
######################################################################################################################################################################

appName = myconf.take("app.name")

def email_subject_header(articleId):
    return "%s #%s" % (appName, articleId)

def patch_email_subject(subject: str, articleId: int):
    if f"#{articleId}" not in subject:
        return subject.replace(appName, email_subject_header(articleId))
    else:
        return subject


def mkAuthors(article: Article):
    return article.authors if not article.anonymous_submission else current.T("[undisclosed]")


######################################################################################################################################################################
def getMailer():
    mail = current.auth.settings.mailer
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
        appGenericContactMail=myconf.take("contacts.generic_contact"),
        appContactLink=A(myconf.take("contacts.managers"), _href="mailto:" + myconf.take("contacts.managers")),
        siteUrl=URL(c="default", f="index", scheme=myconf.take("alerts.scheme"), host=myconf.take("alerts.host"), port=myconf.take("alerts.port")),
        ethicsurl=URL("about", "ethics", scheme=True),
    )

######################################################################################################################################################################

def getMailForRecommenderCommonVars(sender: User, article: Article, recommendation: Recommendation, recommender: str, new_round: Optional[str] = None):
    db, auth = current.db, current.auth

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    is_co_recommender = helper.is_co_recommender(recommendation.id)

    mail_vars = getMailCommonVars()
    _recomm = common_tools.get_prev_recomm(recommendation) if new_round else recommendation
    r2r_url, trackchanges_url = emailing_parts.getAuthorsReplyLinks(_recomm.id)
    r2r_url = str(r2r_url) if r2r_url else "(no author's reply)"
    trackchanges_url = str(trackchanges_url) if trackchanges_url else "(no tracking)"
    # use: r2r_url = r2r_url['_href'] if r2r_url else "(no author's reply)"
    # to pass only the url value to the template instead of the full link html;
    # doing this yields invalid url for the link in the template when no doc exists.

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
    mail_vars["r2r_url"] = r2r_url
    mail_vars["trackchanges_url"] = trackchanges_url
    mail_vars["destPerson"] = '%s %s'%(recommender.first_name, recommender.last_name)
    mail_vars["LastName"] = recommender.last_name
    
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
        mail_vars["sender"] = common_small_html.mkUser(recommendation.recommender_id).flatten()
        mail_vars["Institution"] = sender.institution
        mail_vars["Department"] = sender.laboratory
        mail_vars["country"] = sender.country

        if sender.first_name and sender.last_name:
            mail_vars["senderName"] = sender.first_name + ' ' + sender.last_name

    elif is_co_recommender:
        sender = cast(User, auth.user)
        mail_vars["sender"] = common_small_html.mkUser(auth.user_id).flatten() + "[co-recommender]"
        mail_vars["Institution"] = sender.institution
        mail_vars["Department"] = sender.laboratory
        mail_vars["country"] = sender.country

        if sender.first_name and sender.last_name:
            mail_vars["senderName"] = sender.first_name + ' ' + sender.last_name
    
    elif auth.has_membership(role="manager"):
        recommender = User.get_by_id(recommendation.recommender_id)
        if recommender:
            mail_vars["sender"] = "The Managing Board of " + myconf.get("app.longname") + " on behalf of " + common_small_html.mkUser(recommendation.recommender_id).flatten()
            mail_vars["Institution"] = recommender.institution
            mail_vars["Department"] = recommender.laboratory
            mail_vars["country"] = recommender.country

            if recommender.first_name and recommender.last_name:
                mail_vars["senderName"] = recommender.first_name + ' ' + recommender.last_name

    return mail_vars


######################################################################################################################################################################

def getMailForReviewerCommonVars(sender: User, article: Article, recommendation: Recommendation, reviewer_last_name: Optional[str] = None, new_round: Optional[bool] = False) :
    db, auth = current.db, current.auth
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    is_co_recommender = helper.is_co_recommender(recommendation.id)

    mail_vars = getMailCommonVars()
    _recomm = common_tools.get_prev_recomm(recommendation) if new_round else recommendation
    r2r_url, trackchanges_url = emailing_parts.getAuthorsReplyLinks(_recomm.id)
    r2r_url = str(r2r_url) if r2r_url else "(no author's reply)"
    trackchanges_url = str(trackchanges_url) if trackchanges_url else "(no tracking)"
    # use: r2r_url = r2r_url['_href'] if r2r_url else "(no author's reply)"
    # to pass only the url value to the template instead of the full link html;
    # doing this yields invalid url for the link in the template when no doc exists.

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
    mail_vars["r2r_url"] = r2r_url
    mail_vars["trackchanges_url"] = trackchanges_url

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
        mail_vars["sender"] = common_small_html.mkUser(recommendation.recommender_id).flatten()
        mail_vars["Institution"] = sender.institution
        mail_vars["Department"] = sender.laboratory
        mail_vars["country"] = sender.country

        if sender.first_name and sender.last_name:
            mail_vars["senderName"] = sender.first_name + ' ' + sender.last_name

    elif is_co_recommender:
        sender = cast(User, auth.user)
        mail_vars["sender"] = common_small_html.mkUser(auth.user_id).flatten() + "[co-recommender]"
        mail_vars["Institution"] = sender.institution
        mail_vars["Department"] = sender.laboratory
        mail_vars["country"] = sender.country

        if sender.first_name and sender.last_name:
            mail_vars["senderName"] = sender.first_name + ' ' + sender.last_name
    
    elif auth.has_membership(role="manager"):
        recommender = User.get_by_id(recommendation.recommender_id)
        if recommender:
            mail_vars["sender"] = "The Managing Board of " + myconf.get("app.longname") + " on behalf of " + common_small_html.mkUser(recommendation.recommender_id).flatten()
            mail_vars["Institution"] = recommender.institution
            mail_vars["Department"] = recommender.laboratory
            mail_vars["country"] = recommender.country

            if recommender.first_name and recommender.last_name:
                mail_vars["senderName"] = recommender.first_name + ' ' + recommender.last_name

    return mail_vars


######################################################################################################################################################################
def get_correct_hashtag(hashtag: str, article: Optional[Article] = None, force_scheduled: bool = False):
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
def exempt_addresses(addresses: List[str], hashtag_template: str):
    db = current.db
    for address in addresses:
        user_id = db(db.auth_user.email == address).select(db.auth_user.id).last()
        if user_id:
            user = db.auth_user[user_id.id]
            email_options = ",".join(user.email_options)
            if hashtag_template == "#ReminderSubmitterScheduledSubmissionDue":
                continue
            elif user.email_options == []:
                addresses.remove(address)
            elif "authors" not in email_options and "Submitter" in hashtag_template:
                addresses.remove(address)
            elif "reviewers"  not in  email_options and ("Reviewer" in hashtag_template or "Review" in hashtag_template):
                addresses.remove(address)
    return addresses

#######################################################################################################################################################################
def clean_addresses(dirty_string_adresses):
    '''
    creates a string of clean mail addresses, divided by comma
    '''
    if dirty_string_adresses == None: return '', ''
    
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

    return ','.join(contacts), ', '.join(errors)

######################################################################################################################################################################
def getMailTemplateHashtag(hashTag: str, myLanguage: str = "default"):
    db = current.db
    query = (db.mail_templates.hashtag == hashTag) & (db.mail_templates.lang == myLanguage)
    item = db(query).select().first()

    if item:
        return dict(subject=item.subject, content=item.contents)
    else:
        if scheduledSubmissionActivated and pciRRactivated:
            return generateNewMailTemplates(hashTag, myLanguage)
        else:
            return dict(error=True, message="hashtag not found")


######################################################################################################################################################################
def generateNewMailTemplates(hashTag: str, myLanguage: str):
    baseHashtag = hashTag
    baseHashtag = baseHashtag.replace("Stage1", "")
    baseHashtag = baseHashtag.replace("Stage2", "")
    baseHashtag = baseHashtag.replace("ScheduledSubmission", "")

    # Create stage 1 template
    result1 = insertNewTemplateInDB(baseHashtag + "Stage1ScheduledSubmission", baseHashtag + "Stage1", myLanguage)

    # Create stage 2 template
    result2 = insertNewTemplateInDB(baseHashtag + "Stage2ScheduledSubmission", baseHashtag + "Stage2", myLanguage)

    if "Stage1" in hashTag:
        return result1
    elif "Stage2" in hashTag:
        if 'error' in result2 and result2['error']:
            return result1
        return result2
    else:
        return dict(error=True, message="hashtag not found")


######################################################################################################################################################################
def insertNewTemplateInDB(newHashTag, baseHashtag, myLanguage):
    db = current.db
    query = (db.mail_templates.hashtag == baseHashtag) & (db.mail_templates.lang == myLanguage)
    item = db(query).select().first()

    if item:
        db.mail_templates.insert(
            hashtag=newHashTag, subject=item.subject + " - scheduled submission", contents=item.contents, description=item.description + " (for scheduled submission)"
        )
        return dict(subject=item.subject, content=item.contents)
    else:
        return dict(error=True, message="hashtag not found")


######################################################################################################################################################################
def createMailReport(mail_resu: bool, destPerson: Union[DIV, str], reports: List[Dict[str, Union[bool, str]]]):
    if common_tools.is_silent_mode():
        reports = []

    if mail_resu:
        reports.append(dict(error=False, message="e-mail sent to %s" % destPerson))
    else:
        reports.append(dict(error=True, message="e-mail NOT SENT to %s" % destPerson))
    return reports


######################################################################################################################################################################
def getFlashMessage(reports: List[Dict[str, Union[bool, str]]]):
    if common_tools.is_silent_mode():
        return
    
    session = current.session
    messages: List[str] = []

    for report in reports:
        if report["error"]:
            session.flash_status = "warning"

        messages.append(str(report["message"]))
        pass

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
def mkFooter():
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

    footer_template = getMailTemplateHashtag("#EmailFooterTemplate")
    if 'content' in footer_template and footer_template["content"]:
        footer_content = replaceMailVars(footer_template["content"], mail_vars)
        return XML(footer_content)
    else:
        return XML(getMailFooter() % mail_vars)


######################################################################################################################################################################
def insertMailInQueue(
    hashtag_template: str,
    mail_vars: Dict[str, Any],
    recommendation_id: Optional[int] = None,
    recommendation: Optional[Recommendation] = None,
    article_id: Optional[int] = None,
    review: Optional[Review] = None,
    authors_reply: Optional[DIV] = None,
    sugg_recommender_buttons: Optional[DIV] = None,
    reviewer_invitation_buttons: Optional[DIV] = None,
    alternative_subject: Optional[str] = None, # for edit/resend mails
    alternative_content: Optional[str] = None, # for edit/resend mails
):
    db, auth = current.db, current.auth

    if common_tools.is_silent_mode():
        return

    mail = build_mail(
        hashtag_template,
        mail_vars,
        recommendation=recommendation,
        review=review,
        authors_reply=authors_reply,
        article_id=article_id,
        sugg_recommender_buttons=sugg_recommender_buttons,
        reviewer_invitation_buttons=reviewer_invitation_buttons,
        alternative_subject=alternative_subject,
        alternative_content=alternative_content,
    )
    ccAddresses = mail_vars.get("ccAddresses") or None
    if pciRRactivated and ccAddresses:
        ccAddresses = exempt_addresses(ccAddresses, hashtag_template)

    if alternative_subject:
        subject = alternative_subject
        content = alternative_content
    else:
        subject = mail["subject"]
        content = mail["content"]

    return db.mail_queue.insert(
        dest_mail_address=mail_vars["destAddress"],
        cc_mail_addresses=ccAddresses,
        replyto_addresses=mail_vars.get("replytoAddresses"),
        bcc_mail_addresses=mail_vars.get("bccAddresses"),
        mail_subject=subject,
        mail_content=content,
        user_id=auth.user_id,
        article_id=article_id,
        recommendation_id=recommendation_id,
        mail_template_hashtag=hashtag_template,
    )


######################################################################################################################################################################
def insert_reminder_mail_in_queue(
    hashtag_template: str,
    mail_vars: Dict[str, Any],
    recommendation_id: Optional[int] = None,
    recommendation: Optional[Recommendation] = None,
    article_id: Optional[int] = None,
    review_id: Optional[int] = None,
    review: Optional[Review] = None,
    authors_reply: Optional[str] = None,
    sending_date_forced: Optional[datetime] = None,
    base_sending_date: Optional[datetime] = None,
    reviewer_invitation_buttons: Optional[DIV] = None,
    sender_name: Optional[str] = None,
    sugg_recommender_buttons: Optional[DIV] = None
) -> Optional[int]:

    db, auth = current.db, current.auth

    if common_tools.is_silent_mode():
        return

    reminder = getReminder(hashtag_template, db.t_reviews[review_id])

    ccAddresses = mail_vars.get("ccAddresses") or None
    replytoAddresses = mail_vars.get("replytoAddresses") or None
    if pciRRactivated and ccAddresses and "OverDue" not in hashtag_template:
            ccAddresses = exempt_addresses(ccAddresses, hashtag_template)

    sending_date: Optional[datetime] = None

    if reminder:
        elapsed_days = int(reminder["elapsed_days"][0])
        sending_date = datetime.now() if not base_sending_date \
                else base_sending_date - timedelta(days=7)
        sending_date += timedelta(days=elapsed_days)

    if sending_date_forced:
        sending_date = sending_date_forced

    if True:

        mail = build_mail(
            hashtag_template, mail_vars, recommendation=recommendation, review=review, authors_reply=authors_reply, reviewer_invitation_buttons=reviewer_invitation_buttons,
            article_id=article_id, sugg_recommender_buttons=sugg_recommender_buttons
        )


        return db.mail_queue.insert(
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


def insert_generic_reminder_mail_in_queue(
    hashtag_template: str,
    subject: str,
    content: str,
    mail_vars: Dict[str, Any],
    recommendation_id: Optional[int] = None,
    article_id: Optional[int] = None,
    review_id: Optional[int] = None,
    sending_date_forced: Optional[datetime] = None,
    base_sending_date: Optional[datetime] = None,
    sender_name: Optional[str] = None,
):

    db, auth = current.db, current.auth

    if common_tools.is_silent_mode():
        return

    reminder = getReminder(hashtag_template, db.t_reviews[review_id])

    ccAddresses = mail_vars.get("ccAddresses") or None
    replytoAddresses = mail_vars.get("replytoAddresses") or None
    if pciRRactivated and ccAddresses and "OverDue" not in hashtag_template:
            ccAddresses = exempt_addresses(ccAddresses, hashtag_template)

    sending_date: Optional[datetime] = None

    if reminder:
        elapsed_days = int(reminder["elapsed_days"][0])
        sending_date = datetime.now() if not base_sending_date \
                else base_sending_date - timedelta(days=7)
        sending_date += timedelta(days=elapsed_days)

    if sending_date_forced:
        sending_date = sending_date_forced

    if True:
        db.mail_queue.insert(
            sending_status="pending",
            sending_date=sending_date,
            dest_mail_address=mail_vars["destAddress"],
            cc_mail_addresses=ccAddresses,
            replyto_addresses=replytoAddresses,
            mail_subject=subject,
            mail_content=content,
            user_id=auth.user_id,
            recommendation_id=recommendation_id,
            article_id=article_id,
            mail_template_hashtag=hashtag_template,
            review_id=review_id,
            sender_name=sender_name
        )

######################################################################################################################################################################
def insert_newsletter_mail_in_queue(
    mail_vars: Dict[str, Any],
    hashtag_template: str,
    newRecommendations: Optional[DIV] = None,
    newRecommendationsCount: int = 0,
    newPreprintSearchingForReviewers: Optional[DIV] = None,
    newPreprintSearchingForReviewersCount: int = 0,
    newPreprintRequiringRecommender: Optional[DIV] = None,
    newPreprintRequiringRecommenderCount: int = 0,
):

    db, auth = current.db, current.auth

    mail = build_newsletter_mail(
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
        dest_mail_address=mail_vars["destAddress"],
        mail_subject=mail["subject"],
        mail_content=mail["content"],
        user_id=auth.user_id,
        mail_template_hashtag=hashtag_template
    )


######################################################################################################################################################################
def build_mail(hashtag_template: str,
              mail_vars: Dict[str, Any],
              recommendation: Optional[Recommendation] = None,
              review: Optional[Review] = None,
              authors_reply: Optional[str] = None,
              sugg_recommender_buttons: Optional[DIV] = None,
              reviewer_invitation_buttons: Optional[DIV] = None,
              article_id: Optional[int] = None,
              alternative_subject: Optional[str] = None,
              alternative_content: Optional[str] = None,
    ):

    mail_template = getMailTemplateHashtag(hashtag_template)

    if alternative_subject:
        subject = alternative_subject
        content = alternative_content
    else:
        subject = replaceMailVars(str(mail_template["subject"]), mail_vars)
        content = replaceMailVars(str(mail_template["content"]), mail_vars)

    if article_id is None:
        subject_without_appname = subject.replace("%s: " % mail_vars["appName"] , "")
    else:
        subject = patch_email_subject(subject, article_id)
        appname_with_article_id = email_subject_header(article_id)
        subject_without_appname = subject.replace("%s: " % appname_with_article_id , "")

    applogo = URL("static", "images/small-background.png", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])

    content_rendered: ... = render(
        filename=MAIL_HTML_LAYOUT,
        context=dict(
            subject=subject_without_appname,
            applogo=applogo,
            appname=mail_vars["appName"],
            content=XML(content),
            footer=mkFooter(),
            recommendation=recommendation,
            review=review,
            authors_reply=authors_reply,
            sugg_recommender_buttons=sugg_recommender_buttons,
            reviewer_invitation_buttons=reviewer_invitation_buttons,
        ),
    )

    return dict(content=content_rendered, subject=subject)


######################################################################################################################################################################
def build_newsletter_mail(
    mail_vars: Dict[str, Any],
    hashtag_template: str,
    newRecommendations: Optional[DIV] = None,
    newRecommendationsCount: int = 0,
    newPreprintSearchingForReviewers: Optional[DIV] = None,
    newPreprintSearchingForReviewersCount: int = 0,
    newPreprintRequiringRecommender: Optional[DIV] = None,
    newPreprintRequiringRecommenderCount: int = 0,
):
    mail_template = getMailTemplateHashtag(hashtag_template)

    subject = replaceMailVars(str(mail_template["subject"]), mail_vars)
    content = replaceMailVars(str(mail_template["content"]), mail_vars)

    full_link = { var: mail_vars[var] for var in ["scheme", "host", "port"] }

    subject_without_appname = subject.replace("%s: " % mail_vars["appName"], "")
    applogo = URL("static", "images/small-background.png", **full_link)

    allRecommendationsLink = A(
        current.T("See more recommendations..."),
        _href=URL('default','index', **full_link),
        _style="border-radius: 5px; font-weight: bold; padding: 6px 20px; color: #ffffff; background-color: #3e3f3a;",
    )

    content_rendered: ... = render(
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
            footer=mkFooter(),
            mail_vars=mail_vars,
        ),
    )

    return dict(content=content_rendered, subject=subject)


######################################################################################################################################################################
def replaceMailVars(text: str, mail_vars: Dict[str, Any]):
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

def replace_mail_vars_set_not_considered_mail(article: Article, subject: str, message: str):
    form = Storage(subject=subject, message=message, cc=contact)

    mail_vars = getMailCommonVars()
    mail_vars['destPerson'] = common_small_html.mkUser(article.user_id)
    mail_vars['articleTitle'] = common_small_html.md_to_html(article.title)
    mail_vars['unconsider_limit_days'] = myconf.get("config.unconsider_limit_days", default=20)
    
    form.subject = replaceMailVars(form.subject, mail_vars)
    form.message = replaceMailVars(form.message, mail_vars)

    return form
