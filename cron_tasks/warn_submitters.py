# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from gluon.contrib.appconfig import AppConfig
from app_modules import emailing

myconf = AppConfig(reload=True)
pciRRactivated = myconf.get("config.registered_reports", default=False)

def warning_sent(article_id):
    return db(
            (db.mail_queue.mail_template_hashtag == "#SubmitterPendingSurveyWarning")
            & (db.mail_queue.article_id == article_id)
    ).count() > 0

def delete_submission(article_id):
    mail_duration_elapsed = db(
        (db.mail_queue.mail_template_hashtag == "#SubmitterPendingSurveyWarning")
            & (db.mail_queue.article_id == article_id) & ((db.mail_queue.sending_date <= (date.today() - timedelta(days=14))))
    ).count() > 0
    if mail_duration_elapsed:
        db(db.t_articles.id == article_id).delete()


if pciRRactivated:
    pending_surveys = db((db.t_articles.status=="Pending-survey") & (db.t_articles.last_status_change <= (datetime.now() - timedelta(days=14)))).select()
    for survey in pending_surveys:
        if warning_sent(survey.t_articles.id):
            delete_submission(survey.t_articles.id)
        else:
            emailing.send_warning_to_submitters(survey.t_articles.id)
