# -*- coding: utf-8 -*-

from datetime import timedelta
from datetime import date


def has_newer_invites(user_email):
    return db(
            db.mail_queue.mail_template_hashtag.like("#ReminderReviewerReviewInvitationNewUser%")
            & (db.mail_queue.sending_date > date.today() - timedelta(days=21))
            & (db.mail_queue.dest_mail_address == user_email)
    ).select()


def delete_accounts():
    temporary_accounts = db(
            (db.auth_user.reset_password_key != "") &
            (db.auth_user.country == None)
    ).select()

    for account in temporary_accounts:
        user_email = account.email

        if has_newer_invites(user_email):
            print("not deleting temporary user: " + user_email)
            continue

        #db(db.auth_user.id == account.id).delete()
        print("deleted temporary user: " + user_email)


from datetime import datetime
print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " delete accounts")
delete_accounts()
