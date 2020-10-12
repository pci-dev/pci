# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import re
import os

# from gluon.contrib.markdown import WIKI

from datetime import date, datetime
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
MAIL_HTML_LAYOUT = os.path.join(os.path.dirname(__file__), "..", "views", "mail", "mail.html")


@auth.requires(auth.has_membership(role="developper"))
def test_flash():
    session.flash = "Coucou !"
    redirect(request.env.http_referer)


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def testMyNewsletterMail():
    emailing.send_newsletter_mail(session, auth, db, auth.user_id)
    redirect(request.env.http_referer)


# function called daily
def sendNewsletterMails():
    conditions = ["client" not in request, auth.has_membership(role="manager")]
    if any(conditions):
        my_date = date.today()
        my_day = calendar.day_name[my_date.weekday()]
        usersQy = db(db.auth_user.alerts.contains(my_day, case_sensitive=False)).select()

        for user in usersQy:
            emailing.send_newsletter_mail(session, auth, db, user.id)
            user.last_alert = datetime.now()
            user.update_record()

    redirect(request.env.http_referer)

