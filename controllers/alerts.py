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
MAIL_HTML_LAYOUT = os.path.join(os.path.dirname(__file__), "..", "views", "mail", "mail.html")


@auth.requires(auth.has_membership(role="developper"))
def test_flash():
    session.flash = "Coucou !"
    redirect(request.env.http_referer)


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def testMyNewsletterMail():
    user = db.auth_user[auth.user_id]
    emailing.send_newsletter_mail(session, auth, db, auth.user_id, user.alerts)
    redirect(request.env.http_referer)

# DEPRECATED -- see cron_tasks/newsletter.py
"""
# function called daily
def sendNewsletterMails():
    print("Cron newsletter start")
    conditions = ["client" not in request, auth.has_membership(role="manager")]
    if any(conditions):
        my_date = date.today()

        # Weekly newsletter
        weekly_newsletter_date = my_date - timedelta(days=7)
        users_with_weekly_newsletter = db(
            (
                ((db.auth_user.last_alert != None) & (weekly_newsletter_date >= db.auth_user.last_alert))
                | ((db.auth_user.last_alert == None) & (weekly_newsletter_date >= db.auth_user.registration_datetime))
            )
            & db.auth_user.alerts.contains("Weekly")
        ).select()

        for user in users_with_weekly_newsletter:
            print("Weekly newsletter: " + user.first_name + " " + user.last_name)
            emailing.send_newsletter_mail(session, auth, db, user.id, "Weekly")
            user.last_alert = datetime.now()
            user.update_record()

        # Two weeks newsletter
        two_weeks_newsletter_date = my_date - timedelta(days=14)
        users_with_two_weeks_newsletter = db(
            (
                ((db.auth_user.last_alert != None) & (two_weeks_newsletter_date >= db.auth_user.last_alert))
                | ((db.auth_user.last_alert == None) & (two_weeks_newsletter_date >= db.auth_user.registration_datetime))
            )
            & db.auth_user.alerts.contains("Every two weeks")
        ).select()

        for user in users_with_two_weeks_newsletter:
            print("Every two weeks newsletter: " + user.first_name + " " + user.last_name)
            emailing.send_newsletter_mail(session, auth, db, user.id, "Every two weeks")
            user.last_alert = datetime.now()
            user.update_record()

        # Monthly newsletter
        monthly_newsletter_date = my_date - timedelta(days=30)
        users_with_monthly_newsletter = db(
            (
                ((db.auth_user.last_alert != None) & (monthly_newsletter_date >= db.auth_user.last_alert))
                | ((db.auth_user.last_alert == None) & (monthly_newsletter_date >= db.auth_user.registration_datetime))
            )
            & db.auth_user.alerts.contains("Monthly")
        ).select()

        for user in users_with_monthly_newsletter:
            print("Monthly newsletter: " + user.first_name + " " + user.last_name)
            emailing.send_newsletter_mail(session, auth, db, user.id, "Monthly")
            user.last_alert = datetime.now()
            user.update_record()

    redirect(request.env.http_referer)
"""
