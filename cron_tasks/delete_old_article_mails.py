# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
import time
from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)
DELETE_DELAY = float(myconf.get("config.delete_mail_delay", default=60))  # in days;

list_mail_to_delete = db(
    (db.mail_queue.sending_status == "sent")
    & (db.mail_queue.article_id == db.t_articles.id)
    & (db.t_articles.status.belongs(["Cancelled", "Recommended", "Rejected", "Not considered"]))
    & (db.t_articles.last_status_change <= (datetime.now() - timedelta(days=DELETE_DELAY)))
).select()

for mail in list_mail_to_delete:
    db(db.mail_queue.id == mail.mail_queue.id).delete()

