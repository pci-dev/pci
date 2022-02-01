# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
import time
from .mail_queue_log import tryToSendMail, logMailsInQueue
from gluon.contrib.appconfig import AppConfig


myconf = AppConfig(reload=True)
MAIL_DELAY = float(myconf.get("config.mail_delay", default=3))  # in seconds; must be smaller than cron intervals
MAIL_MAX_SENDING_ATTEMPTS = int(15)

log = None
if (myconf.get("config.use_logger", default=True) is True):
	try:
		import logging
		from systemd.journal import JournalHandler
		logName = myconf.take("app.name")
		log = logging.getLogger(logName)
		hand = JournalHandler(SYSLOG_IDENTIFIER=logName)
		hand.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
		log.root.addHandler(hand)
		log.setLevel(logging.INFO)
		print("systemd logging used")
	except:
		print("systemd logging not available")
else:
	print("systemd logging not enabled in config")


def getMailsInQueue():
    return db((db.mail_queue.sending_status.belongs("failed")) & (db.mail_queue.removed_from_queue == False) & (db.mail_queue.sending_date <= datetime.now())).select(
        orderby=db.mail_queue.sending_date
    )

######################################################################################################################################################################
# Run Mailing Queue Once
######################################################################################################################################################################
mails_in_queue = getMailsInQueue()
logMailsInQueue(len(mails_in_queue))
# As the cron runs every hour, we break when the threshold of 59m50s is reached.
# Remaining emails will be sent on next cron.
start_ts = datetime.now().timestamp()
for mail_item in mails_in_queue:
    curr_ts = datetime.now().timestamp()
    if (curr_ts - start_ts) < 3590.0:
        tryToSendMail(mail_item)
        # wait beetween email sendings
        time.sleep(MAIL_DELAY)
