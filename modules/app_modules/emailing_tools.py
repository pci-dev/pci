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
from app_modules import old_common


myconf = AppConfig(reload=True)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)

MAIL_DELAY = 1.5  # in seconds

# common view for all emails
MAIL_HTML_LAYOUT = os.path.join(os.path.dirname(__file__), "../../views/mail", "mail.html")

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
def getMailCommonVars():
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
def getMailTemplateHashtag(db, hashTag, myLanguage="default"):
    print(hashTag)
    query = (db.mail_templates.hashtag == hashTag) & (db.mail_templates.lang == myLanguage)
    item = db(query).select().first()

    if item:
        return dict(subject=item.subject, content=item.contents)
    else:
        return dict(error=True, message="hashtag not found")


######################################################################################################################################################################
def createMailReport(mail_resu, destPerson, reports):
    if mail_resu:
        reports.append(dict(error=False, message="email sent to %s" % destPerson))
    else:
        reports.append(dict(error=True, message="email NOT SENT to %s" % destPerson))
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

    return XML(getMailFooter() % mail_vars)


######################################################################################################################################################################
def insertMailInQueue(auth, db, hashtag_template, mail_vars, recommendation_id=None, recommendation=None):
    mail_template = getMailTemplateHashtag(db, hashtag_template)
    subject = mail_template["subject"] % mail_vars
    subject_without_appname = subject.replace("%s: " % mail_vars["appname"], "")
    applogo = URL("static", "images/small-background.png", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
    content = mail_template["content"] % mail_vars
    message = render(
        filename=MAIL_HTML_LAYOUT,
        context=dict(subject=subject_without_appname, applogo=applogo, appname=mail_vars["appname"], content=XML(content), footer=mkFooter(), recommendation=recommendation),
    )

    db.mail_queue.insert(
        dest_mail_address=mail_vars["destAddress"],
        mail_subject=subject,
        mail_content=message,
        user_id=auth.user_id,
        recommendation_id=recommendation_id,
        mail_template_hashtag=hashtag_template,
    )


######################################################################################################################################################################
def insertReminderMailInQueue(auth, db, hashtag_template, mail_vars, days, recommendation_id=None, recommendation=None):
    sending_date = datetime.now() + timedelta(days=days)

    mail_template = getMailTemplateHashtag(db, hashtag_template)
    subject = mail_template["subject"] % mail_vars
    subject_without_appname = subject.replace("%s: " % mail_vars["appname"], "")
    applogo = URL("static", "images/small-background.png", scheme=mail_vars["scheme"], host=mail_vars["host"], port=mail_vars["port"])
    content = mail_template["content"] % mail_vars
    message = render(
        filename=MAIL_HTML_LAYOUT,
        context=dict(subject=subject_without_appname, applogo=applogo, appname=mail_vars["appname"], content=XML(content), footer=mkFooter(), recommendation=recommendation),
    )

    db.mail_queue.insert(
        sending_status="pending",
        sending_date=sending_date,
        dest_mail_address=mail_vars["destAddress"],
        mail_subject=subject,
        mail_content=message,
        user_id=auth.user_id,
        recommendation_id=recommendation_id,
        mail_template_hashtag=hashtag_template,
    )
