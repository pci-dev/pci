# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
import time
import email
from gluon.contrib.appconfig import AppConfig

from app_modules.reminders import getReminder

myconf = AppConfig(reload=True)
MAIL_DELAY = float(myconf.get("config.mail_delay", default=1.5))  # in seconds; must be smaller than cron intervals

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
	except:
		print("systemd logging not available")
else:
	print("systemd logging not enabled in config")


def getMailsInQueue():
    return db(
            (db.mail_queue.sending_status.belongs(
                "in queue",
                "pending"
            )) &
            (db.mail_queue.removed_from_queue == False) &
            (db.mail_queue.sending_date <= datetime.now())
    ).select(
        orderby=db.mail_queue.sending_date
    )


def tryToSendMail(mail_item):
    if not isTimeToTrySending(mail_item):
        return
    
    sender = None
    if mail_item.sender_name:
        sender = email.utils.formataddr((
            mail_item.sender_name,
            email.utils.parseaddr(mail.settings.sender)[1],
        ))

    try:
        isSent = mail.send(
                to=mail_item.dest_mail_address,
                cc=mail_item.cc_mail_addresses,
                bcc=mail_item.bcc_mail_addresses,
                reply_to=mail_item.replyto_addresses,
                subject=mail_item.mail_subject,
                message=mail_item.mail_content,
                sender=sender
        )
        #isSent = True
        if isSent is False:
            raise Exception('Email not sent!')
    except Exception as err:
        log_error(err)
        isSent = False

    if mail_item.sending_status == "pending":
        prepareNextReminder(mail_item)

    updateSendingStatus(mail_item, isSent)
    logSendingStatus(mail_item, isSent)


def isTimeToTrySending(mail_item):
    """
    - first 3 attempts every 1 min. (cron freq.)
    - next  6 attempts every 5 min.
    - next  6 attempts every hour
    - other attempts every 5 hours
    """
    if mail_item.sending_attempts < 3:
        return True
    if mail_item.sending_attempts < 9:
        return isNowSendingDatePlus(mail_item, minutes=5)
    if mail_item.sending_attempts < 15:
        return isNowSendingDatePlus(mail_item, hours=1)
    return isNowSendingDatePlus(mail_item, hours=5)


def isNowSendingDatePlus(mail_item, **arg):
    return mail_item.sending_date + timedelta(**arg) < datetime.now()


def log_error(err):
    if log:
        try:
            log.error(err)
        except:
            print(err)
    else:
        print(err)


def prepareNextReminder(mail_item):
    reminder_count = mail_item["reminder_count"]
    hashtag_template = mail_item["mail_template_hashtag"]
    review_id = mail_item["review_id"]
    reminder = getReminder(db, hashtag_template, review_id)
    reminder_days = reminder["elapsed_days"] if reminder else []

    if len(reminder_days) > reminder_count + 1:
        current_reminder_elapsed_days = reminder_days[reminder_count]
        next_reminder_elapsed_days = reminder_days[reminder_count + 1]

        days_between_reminders = next_reminder_elapsed_days - current_reminder_elapsed_days
        sending_date = datetime.now() + timedelta(days=days_between_reminders)

        db.mail_queue.insert(
            sending_status="pending",
            reminder_count=reminder_count + 1,
            sending_date=sending_date,
            dest_mail_address=mail_item["dest_mail_address"],
            cc_mail_addresses=mail_item["cc_mail_addresses"],
            replyto_addresses=mail_item["replyto_addresses"],
            mail_subject=mail_item["mail_subject"],
            mail_content=mail_item["mail_content"],
            user_id=mail_item["user_id"],
            recommendation_id=mail_item["recommendation_id"],
            article_id=mail_item["article_id"],
            mail_template_hashtag=mail_item["mail_template_hashtag"],
            review_id=mail_item["review_id"]
        )


def updateSendingStatus(mail_item, isSent):
    attempts = mail_item.sending_attempts + 1
    senddate = datetime.now()

    if isSent:
        new_status = "sent"
    else:
        new_status = "in queue"

        if attempts > 28: # approx 70h = 3 days
            new_status = "failed"

    mail_item.update_record(sending_status=new_status, sending_attempts=attempts, sending_date=senddate)
    db.commit()


def logMailsInQueue(mails_in_queue):
    if not mails_in_queue:
        return

    queue_length = len(mails_in_queue)
    date_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print("%s Mail(s) in queue : %s" % (date_time, queue_length))
    if log:
         msg = "Queue length = %(queue_length)s" % locals()
         log.info(msg)

def logSendingStatus(mail_item, isSent):
    if isSent:
        sending_status = "\033[92msent\033[0m"
        sending_log = "SENT"
    else:
        sending_status = "\033[91mnot sent\033[0m"
        sending_log = "NOT SENT"

    mail_dest = "\033[4m%s\033[0m" % mail_item.dest_mail_address
    hashtag_text = "\033[3m%s\033[0m" % mail_item.mail_template_hashtag
    print("\t- mail %s to : %s => %s" % (sending_status, mail_dest, hashtag_text))
    
    if log:
         to_log = mail_item.dest_mail_address
         hashtag_log = mail_item.mail_template_hashtag
         msg = "Email %(sending_log)s to %(to_log)s [%(hashtag_log)s]" % locals()
         if isSent:
             log.info(msg)
         else:
             log.warning(msg)


######################################################################################################################################################################
# Run Mailing Queue Once
######################################################################################################################################################################
#print("Entering sendQueuedMails")
mails_in_queue = getMailsInQueue()
logMailsInQueue(mails_in_queue)
# As the cron runs every minute, we break when the threshold of 50s is reached.
# Remaining emails will be sent on next cron.
start_ts = datetime.now().timestamp()
for mail_item in mails_in_queue:
    curr_ts = datetime.now().timestamp()
    if (curr_ts - start_ts) < 50.0:
        tryToSendMail(mail_item)
        # wait beetween email sendings
        time.sleep(MAIL_DELAY)


