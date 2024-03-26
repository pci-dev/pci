from __future__ import annotations # for self-ref param type
from datetime import datetime
import re
from typing import List, Optional as _, cast
from models.review import Review
from pydal.objects import Row
from gluon import current


class MailQueue(Row):
    id: int
    sending_status: str
    sending_attempts: int
    sending_date: datetime
    dest_mail_address: str
    user_id: int
    article_id: int
    recommendation_id: int
    mail_subject: _[str]
    mail_content: _[str]
    mail_template_hashtag: str
    reminder_count: int
    removed_from_queue: bool
    cc_mail_addresses: str
    replyto_addresses: _[str]
    review_id: _[int]
    bcc_mail_addresses: _[str]
    sender_name: _[str]


    @staticmethod
    def get_mail_by_id(id: int):
        db = current.db
        return cast(_[MailQueue], db.mail_queue[id])
    

    @staticmethod
    def get_mail_content(mail: MailQueue):
        if not mail.mail_content:
            return ''
        
        content = re.search('<!-- CONTENT START -->(.*?)<!-- CONTENT END -->', mail.mail_content, re.DOTALL)
        if content:
            return content.group(1)
        else:
            return ''
        
    
    @staticmethod
    def get_by_review_for_recommender(hastag_template: str, recommender_mail: str, review: Review):
        db = current.db
        mails = db(
            (db.mail_queue.dest_mail_address == recommender_mail) &
            (db.mail_queue.mail_template_hashtag == hastag_template) &
            (db.mail_queue.recommendation_id == review.recommendation_id) &
            (db.mail_queue.review_id == review.id))
        return cast(List[MailQueue], mails)
