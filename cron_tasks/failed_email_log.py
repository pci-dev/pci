# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
import time
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


def tryToSendMail(mail_item):
    try:
        isSent = mail.send(to=mail_item.dest_mail_address, cc=mail_item.cc_mail_addresses, reply_to=mail_item.replyto_addresses, subject=mail_item.mail_subject, message=mail_item.mail_content)
        #isSent = True
        if isSent is False:
            raise Exception('Email not sent!')
    except Exception as err:
        if log:
            try:
                #journal.write(err)
                log.error(err)
            except:
                print(err)
        else:
            print(err)
        isSent = False

    updateSendingStatus(mail_item, isSent)
    logSendingStatus(mail_item, isSent)


def updateSendingStatus(mail_item, isSent):
    attempts = mail_item.sending_attempts + 1

    if isSent:
        new_status = "sent"
    if not isSent and attempts >= MAIL_MAX_SENDING_ATTEMPTS:
        new_status = "failed"
    elif not isSent and attempts < MAIL_MAX_SENDING_ATTEMPTS:
        new_status = "in queue"

    mail_item.update_record(sending_status=new_status, sending_attempts=attempts)
    db.commit()


def logMailsInQueue(queue_length):
    if queue_length > 0:
        colored_queue_length = "\033[1m\033[93m%i\033[0m" % queue_length
    else:
        colored_queue_length = "\033[1m\033[90m%i\033[0m" % queue_length
    colored_date = "[\033[90m%s\033[0m]" % datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    print("%s Mail(s) in queue : %s" % (colored_date, colored_queue_length))
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
