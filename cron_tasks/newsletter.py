# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from app_modules import emailing


conditions = ["client" not in request, auth.has_membership(role="manager")]
if any(conditions):
    my_date = date.today()
    print("Cron newsletter start : " + str(my_date)) 

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
        emailing.delete_newsletter_mail(session, auth, db, user.id)
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
        emailing.delete_newsletter_mail(session, auth, db, user.id)
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
        emailing.delete_newsletter_mail(session, auth, db, user.id)
        emailing.send_newsletter_mail(session, auth, db, user.id, "Monthly")
        user.last_alert = datetime.now()
        user.update_record()
