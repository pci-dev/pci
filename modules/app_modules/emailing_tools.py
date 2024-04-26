# -*- coding: utf-8 -*-

import os
import re
from datetime import datetime, timedelta
from typing import Optional, cast

from dateutil.relativedelta import *

from gluon import current
from gluon.storage import Storage
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.appconfig import AppConfig
from gluon.validators import IS_EMAIL
from pydal import DAL

from gluon.custom_import import track_changes
from models.article import Article
from models.recommendation import Recommendation
from models.user import User

track_changes(True)

from app_modules import common_tools
from app_modules import common_small_html
from app_modules import helper
from app_modules import emailing_parts
from app_modules.reminders import getReminder

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
        appGenericContactMail=myconf.take("contacts.generic_contact"),
        appContactLink=A(myconf.take("contacts.managers"), _href="mailto:" + myconf.take("contacts.managers")),
        siteUrl=URL(c="default", f="index", scheme=myconf.take("alerts.scheme"), host=myconf.take("alerts.host"), port=myconf.take("alerts.port")),
    )

######################################################################################################################################################################

def getMailForRecommenderCommonVars(sender: User, article: Article, recommendation: Recommendation, recommender: str, new_round: Optional[str] = None):
    db, auth = current.db, current.auth

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    is_co_recommender = helper.is_co_recommender(recommendation.id)

    mail_vars = getMailCommonVars()
    _recomm = common_tools.get_prev_recomm(db, recommendation) if new_round else recommendation
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
    _recomm = common_tools.get_prev_recomm(db, recommendation) if new_round else recommendation
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
def exempt_addresses(addresses, hashtag_template):
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
def getMailTemplateHashtag(hashTag, myLanguage="default"):
    db = current.db
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
    hashtag_template,
    mail_vars,
    recommendation_id=None,
    recommendation=None,
    article_id=None,
    review=None,
    authors_reply=None,
    sugg_recommender_buttons=None,
    reviewer_invitation_buttons=None,
    alternative_subject=None, # for edit/resend mails
    alternative_content=None, # for edit/resend mails
):
    db, auth = current.db, current.auth

    mail = buildMail(
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
def insertReminderMailInQueue(
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
    sender_name: Optional[str]=None,
    sugg_recommender_buttons: Optional[DIV]=None
):

    db, auth = current.db, current.auth

    reminder = getReminder(hashtag_template, db.t_reviews[review_id])

    ccAddresses = mail_vars.get("ccAddresses") or None
    replytoAddresses = mail_vars.get("replytoAddresses") or None
    if pciRRactivated and ccAddresses and "OverDue" not in hashtag_template:
            ccAddresses = exempt_addresses(ccAddresses, hashtag_template)

    if reminder:
        elapsed_days = reminder["elapsed_days"][0]
        sending_date = datetime.now() if not base_sending_date \
                else base_sending_date - timedelta(days=7)
        sending_date += timedelta(days=elapsed_days)

    if sending_date_forced:
        sending_date = sending_date_forced

    if True:

        mail = buildMail(
            hashtag_template, mail_vars, recommendation=recommendation, review=review, authors_reply=authors_reply, reviewer_invitation_buttons=reviewer_invitation_buttons,
            article_id=article_id, sugg_recommender_buttons=sugg_recommender_buttons
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
    mail_vars,
    hashtag_template,
    newRecommendations=None,
    newRecommendationsCount=0,
    newPreprintSearchingForReviewers=None,
    newPreprintSearchingForReviewersCount=0,
    newPreprintRequiringRecommender=None,
    newPreprintRequiringRecommenderCount=0,
):

    db, auth = current.db, current.auth

    mail = buildNewsLetterMail(
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
def buildMail(hashtag_template, mail_vars, recommendation=None, review=None, authors_reply=None, sugg_recommender_buttons=None, reviewer_invitation_buttons=None,
        article_id=None, alternative_subject=None, alternative_content=None,
    ):

    mail_template = getMailTemplateHashtag(hashtag_template)

    if alternative_subject:
        subject = alternative_subject
        content = alternative_content
    else:
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
def buildNewsLetterMail(
    mail_vars,
    hashtag_template,
    newRecommendations=None,
    newRecommendationsCount=0,
    newPreprintSearchingForReviewers=None,
    newPreprintSearchingForReviewersCount=0,
    newPreprintRequiringRecommender=None,
    newPreprintRequiringRecommenderCount=0,
):
    mail_template = getMailTemplateHashtag(hashtag_template)

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
            footer=mkFooter(),
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

def replace_mail_vars_set_not_considered_mail(article: Article, subject: str, message: str):
    form = Storage(subject=subject, message=message, cc=contact)

    mail_vars = getMailCommonVars()
    mail_vars['destPerson'] = common_small_html.mkUser(article.user_id)
    mail_vars['articleTitle'] = common_small_html.md_to_html(article.title)
    mail_vars['unconsider_limit_days'] = myconf.get("config.unconsider_limit_days", default=20)
    
    form.subject = replaceMailVars(form.subject, mail_vars)
    form.message = replaceMailVars(form.message, mail_vars)

    return form

####################################################################################################
def get_recommenders_and_reviewers_mails(article_id):
    db, auth = current.db, current.auth
    emails = []
    recomm = db.get_last_recomm(article_id)
    recommender = db((db.t_recommendations.article_id == article_id) & (db.auth_user.id == db.t_recommendations.recommender_id)).select(db.auth_user.email)
    reviewers = db((db.t_recommendations.article_id == article_id) & (db.t_reviews.recommendation_id == db.t_recommendations.id) & \
                   (db.t_reviews.review_state == "Review completed") & (db.auth_user.id == db.t_reviews.reviewer_id)).select(db.auth_user.email)
    co_recommenders = db((db.t_press_reviews.recommendation_id == recomm.id) & (db.auth_user.id == db.t_press_reviews.contributor_id)).select(db.auth_user.email) 
    all_mails = recommender + reviewers + co_recommenders
    for mail in all_mails:
        if mail.email not in emails:
            emails.append(mail.email)
    return emails
