import argparse

from app_modules import emailing_tools, common_small_html
from models.user import User

def send_mail_for_newsletter_subscriber(subject: str, content: str):
    mail_vars = emailing_tools.getMailCommonVars()
    users_with_newsletter = User.get_all_user_subscribed_newsletter()

    for user in users_with_newsletter:
        mail_vars["destAddress"] = user.email
        mail_vars["destPerson"] = common_small_html.mkUser(user.id)

        mail_vars["subject"] = emailing_tools.replaceMailVars(subject, mail_vars)
        mail_vars["content"] = emailing_tools.replaceMailVars(content, mail_vars)

        emailing_tools.insertMailInQueue(
            "#MailSubscribers",
            mail_vars,
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='To send mail for all subscribed to newsletter users',
        description='Send mail with subject and content to all user that are subscribed to newsletter'
    )

    parser.add_argument('subject', type=str)
    parser.add_argument('content', type=str)

    args = parser.parse_args()

    subject = str(args.subject)
    content = str(args.content)

    send_mail_for_newsletter_subscriber(subject, content)
