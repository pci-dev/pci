# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import re
import os

# from gluon.contrib.markdown import WIKI

from datetime import date, datetime, timedelta
import calendar
from time import sleep

# import socket
# host=socket.getfqdn()
from gluon.contrib.appconfig import AppConfig

from app_components import article_components

from app_modules import emailing
from app_modules import common_tools
from app_modules import common_small_html

myconf = AppConfig(reload=True)
DELETE_DELAY = float(myconf.get("config.delete_mail_delay", default=60))


@auth.requires(auth.has_membership(role="developer"))
def test_flash():
    session.flash = "Coucou !"
    redirect(request.env.http_referer)


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def testMyNewsletterMail():
    user = db.auth_user[auth.user_id]
    emailing.delete_newsletter_mail(session, auth, db, auth.user_id)
    emailing.send_newsletter_mail(session, auth, db, auth.user_id, user.alerts)
    redirect(request.env.http_referer)


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developer"))
def testDeleteMail():
    list_mail_to_delete = db(
        (db.mail_queue.sending_status == "sent")
        & (db.mail_queue.article_id == db.t_articles.id)
        & (db.t_articles.status.belongs(["Cancelled", "Recommended", "Rejected", "Not considered"]))
        & (db.t_articles.last_status_change <= (datetime.now() - timedelta(days=DELETE_DELAY)))
    ).select()

    for mail in list_mail_to_delete:
        db(db.mail_queue.id == mail.mail_queue.id).delete()

    redirect(request.env.http_referer)
