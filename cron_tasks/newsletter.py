# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from app_modules import emailing
from app_modules import newsletter

from gluon import current


news = newsletter.interval


def send_newsletter(freq: str):
    db = current.db

    my_date = datetime.now()

    newsletter_date = my_date - timedelta(days=news[freq])
    users_with_newsletter = db(
        (
            ((db.auth_user.last_alert != None) & (newsletter_date >= db.auth_user.last_alert))
          | ((db.auth_user.last_alert == None) & (newsletter_date >= db.auth_user.registration_datetime))
        )
        & (db.auth_user.country != '') # users with filled profile (country is a mandatory field)
        & db.auth_user.alerts.contains(freq)
    ).select()

    for user in users_with_newsletter:
        print(freq + " newsletter: " + user.first_name + " " + user.last_name)
        emailing.delete_newsletter_mail(user.id)
        emailing.send_newsletter_mail(user.id, freq)
        user.last_alert = datetime.now()
        user.update_record()


def main():
    for freq in news:
        send_newsletter(freq)


main()
