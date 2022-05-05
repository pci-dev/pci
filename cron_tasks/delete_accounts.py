# -*- coding: utf-8 -*-

from datetime import timedelta
from datetime import date


def get_old_invites():
    return db(
            db.mail_queue.mail_template_hashtag.like("#ReminderReviewerReviewInvitationNewUser%")
            & (db.mail_queue.sending_date <= date.today() - timedelta(days=14))
    ).select(
            db.mail_queue.dest_mail_address,
            distinct=True,
    )


def get_cancelled_invites():
    return db(db.mail_queue.mail_template_hashtag.like("#DefaultReviewCancellation%")).select(
            db.mail_queue.dest_mail_address,
            distinct=True)

def has_newer_invites(user_email):
    return db(
            db.mail_queue.mail_template_hashtag.like("#ReminderReviewerReviewInvitationNewUser%")
            & (db.mail_queue.sending_date > date.today() - timedelta(days=14))
            & (db.mail_queue.dest_mail_address == user_email)
    ).select()


def update_reviews(user_id):
    reviews = db(
            (db.t_reviews.reviewer_id == user_id) &
            (db.t_reviews.review_state == "Awaiting response")
    ).select()
    for rev in reviews:
        rev.review_state = "Cancelled"
        rev.update_record()


def delete_accounts():
    invites = get_old_invites() + get_cancelled_invites()

    for invite in invites:
        user_email = invite.dest_mail_address
        temporary_account = db(
                (db.auth_user.email == user_email) &
                (db.auth_user.reset_password_key != "") &
                (db.auth_user.country == None )
        )
        if has_newer_invites(user_email):
            continue
        account = temporary_account.select().last()
        if account:
            update_reviews(account.id)
            temporary_account.delete()
            print("deleted temporary user: " + user_email)


delete_accounts()
