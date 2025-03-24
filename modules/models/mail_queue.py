from datetime import datetime
from enum import Enum
import re
from typing import Any, Dict, List, Optional as _, Union, cast
from app_modules.emailing_tools import build_mail
from models.review import Review
from pydal.objects import Row
from gluon import DIV, current

class SendingStatus(Enum):
    SENT = 'sent'
    FAILED = 'failed'
    IN_QUEUE = 'in queue'
    PENDING = 'pending'


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
    def get_mail_content(mail: 'MailQueue'):
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


    @staticmethod
    def get_by_article_and_template(article_id: int,
                                    hastag_template: Union[str, List[str]],
                                    sending_status: List[SendingStatus] = [],
                                    order_by: _[Any] = None,
                                    user_id: _[int] = None) -> List['MailQueue']:
        db = current.db
        sending_status_values = [s.value for s in sending_status]

        if isinstance(hastag_template, str):
            hastag_template = [hastag_template]

        query = (db.mail_queue.article_id == article_id) \
                & (db.mail_queue.mail_template_hashtag.belongs(hastag_template))

        if len(sending_status_values) > 0:
           query = query & (db.mail_queue.sending_status.belongs(sending_status_values))

        if user_id is not None:
            query = query & (db.mail_queue.user_id == user_id)

        query = db(query)
        if order_by:
            mails = query.select(orderby=order_by)
        else:
            mails = query.select()
            
        return mails


    @staticmethod
    def get_by_review_and_template(review_id: List[int],
                                   hastag_template: List[str],
                                   sending_status: List[SendingStatus] = [],
                                   order_by: _[Any] = None) -> List['MailQueue'] :
        db = current.db
        sending_status_values = [s.value for s in sending_status]

        if len(sending_status_values) == 0:
            query = db(
                (db.mail_queue.review_id.belongs(review_id)) &
                (db.mail_queue.mail_template_hashtag.belongs(hastag_template))
            )
        else:
            query = db(
                (db.mail_queue.review_id.belongs(review_id)) &
                (db.mail_queue.mail_template_hashtag.belongs(hastag_template)) &
                (db.mail_queue.sending_status.belongs(sending_status_values))
            )

        if order_by:
            mails = query.select(orderby=order_by)
        else:
            mails = query.select()
            
        return mails


    @staticmethod
    def there_are_mails_for_article_recommendation(article_id: int, recommendation_id: int, hastag_template: str, sending_status: List[SendingStatus] = []):
        db = current.db
        sending_status_values = [s.value for s in sending_status]

        if len(sending_status_values) == 0:
            mails = db(
            (db.mail_queue.article_id == article_id) &
            (db.mail_queue.recommendation_id == recommendation_id) &
            (db.mail_queue.mail_template_hashtag == hastag_template)
        ).count()
        else:
            mails = db(
                (db.mail_queue.article_id == article_id) &
                (db.mail_queue.recommendation_id == recommendation_id) &
                (db.mail_queue.sending_status.belongs(sending_status_values)) &
                (db.mail_queue.mail_template_hashtag == hastag_template)
            ).count()
        return int(mails)


    @staticmethod
    def update_dest_mail_address(mail_id: int, dest_mail_address: str):
        current.db(current.db.mail_queue.id == mail_id).update(dest_mail_address=dest_mail_address)


    @staticmethod
    def change_suggested_recommender_button(mail: 'MailQueue', sugg_recommender_buttons: DIV, mail_vars: Dict[str, Any]):
        try:
            mail_content = build_mail(mail.mail_template_hashtag, 
                                      mail_vars, 
                                      sugg_recommender_buttons=sugg_recommender_buttons, 
                                      article_id=mail.article_id)['content']
            mail.update_record(mail_content=mail_content) # type: ignore
        except:
            return mail
        return mail

