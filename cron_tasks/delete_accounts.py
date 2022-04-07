# -*- coding: utf-8 -*-

from datetime import timedelta
from datetime import date


def delete_accounts():
    invites = db(
            db.mail_queue.mail_template_hashtag.like("#ReminderReviewerReviewInvitationNewUser%")
            & (db.mail_queue.sending_date <= date.today() - timedelta(days=14))
    ).select(
            db.mail_queue.dest_mail_address,
            distinct=True,
    )
    for invite in invites:
        user_email = invite.dest_mail_address
        temporary_account = db(
                (db.auth_user.email == user_email) &
                (db.auth_user.reset_password_key != "") &
                (db.auth_user.country == None )
        )
        if temporary_account.select():
            temporary_account.delete()
            print("deleted temporary user: " + user_email)

delete_accounts()
