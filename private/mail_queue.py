## in file /app/private/mail_queue.py
from datetime import datetime
import time

QUEUE_CHECK_INTERVAL = 15  # in seconds
MAIL_DELAY = 1.5  # in seconds
MAIL_MAX_ATTEMPTS = 3  # in seconds


def getPendingMails():
    return db((db.mail_queue.sending_status == "pending") & (db.mail_queue.sending_date <= datetime.now())).select(orderby=db.mail_queue.sending_date)


def tryToSendMail(mail_item):
    if mail.send(to=mail_item.dest_mail_address, subject=mail_item.mail_subject, message=mail_item.mail_content):
        isSent = True
    else:
        isSent = False

    logSendingStatus(mail_item, isSent)
    updateSendingStatus(mail_item, isSent)

    # wait beetween email sendings
    time.sleep(MAIL_DELAY)


def updateSendingStatus(mail_item, isSent):
    attempts = mail_item.sending_attempts + 1

    if isSent:
        new_status = "sent"
    if not isSent and attempts >= MAIL_MAX_ATTEMPTS:
        new_status = "failed"
    elif not isSent and attempts < MAIL_MAX_ATTEMPTS:
        new_status = "pending"

    mail_item.update_record(sending_status=new_status, sending_attempts=attempts)
    db.commit()


def logMailsInQueue(queue_length):
    if queue_length > 0:
        colored_queue_length = "\033[1m\033[93m%i\033[0m" % queue_length
    else:
        colored_queue_length = "\033[1m\033[90m%i\033[0m" % queue_length

    colored_date = "[\033[90m%s\033[0m]" % datetime.now().strftime("%m-%d-%Y %H:%M:%S")

    print("%s Mail(s) in queue : %s" % (colored_date, colored_queue_length))


def logSendingStatus(mail_item, isSent):
    if isSent:
        sending_status = "\033[92msent\033[0m"
    else:
        sending_status = "\033[91mnot sent\033[0m"

    mail_dest = "\033[4m%s\033[0m" % mail_item.dest_mail_address
    hashtag_text = "\033[3m%s\033[0m" % mail_item.mail_template_hashtag

    print("\t- mail %s to : %s => %s" % (sending_status, mail_dest, hashtag_text))


######################################################################################################################################################################
# Mailing Queue :
######################################################################################################################################################################
while True:
    pending_mails = getPendingMails()
    logMailsInQueue(len(pending_mails))

    for mail_item in pending_mails:
        tryToSendMail(mail_item)

    time.sleep(QUEUE_CHECK_INTERVAL)  # check every minute
