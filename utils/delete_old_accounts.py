# -*- coding: utf-8 -*-

from datetime import timedelta
from datetime import date


def has_newer_invites(user_email):
    return db(
            db.mail_queue.mail_template_hashtag.like("#ReminderReviewerReviewInvitationNewUser%")
            & (db.mail_queue.sending_date > date.today() - timedelta(days=21))
            & (db.mail_queue.dest_mail_address == user_email)
    ).select()


def get_stale_reviews(user_id):
    return db(
            (db.t_reviews.reviewer_id == user_id) &
            (db.t_reviews.review_state == "Awaiting response")
    ).select()


def update_reviews(reviews):
    for rev in reviews:
        print("updating review: " + str(rev.id))
        if dry_run:
            continue
        rev.review_state = "Cancelled"
        rev.reviewer_id = None
        rev.update_record()


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

        print("deleting temporary user: " + user_email)
        reviews = get_stale_reviews(account.id)
        if not dry_run:
            db(db.auth_user.id == account.id).delete()
        update_reviews(reviews)


from datetime import datetime
print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " delete accounts")

dry_run = True

delete_accounts()
