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
).select(db.mail_queue.id)

db(db.mail_queue.id.belongs(list_mail_to_delete)).delete()

db(
    (db.mail_queue.article_id == None)
    & (db.mail_queue.sending_date <= (datetime.now() - timedelta(days=6*30)))
).delete()
