# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta



def delete_accounts():
    invites = db(
            db.mail_queue.mail_template_hashtag.like("#ReminderReviewerReviewInvitationNewUser%")
    ).select(
            db.mail_queue.sending_date,
            db.mail_queue.dest_mail_address,
    )
    for invite in invites:
        invite_date = invite.sending_date.date()
        user_email = invite.dest_mail_address
        week_span = invite_date - datetime.date.today() <= timedelta(days=-14)
        temporary_account = db(
                (db.auth_user.email == user_email) &
                (db.auth_user.reset_password_key != "") &
                (db.auth_user.country == None )
        ).select(db.auth_user.id)
        if temporary_account and week_span:
            id = [account.id for account in temporary_account]
            db(db.auth_user.id == id[0]).delete()
            print("deleting temporary user: " + user_email)

delete_accounts()
