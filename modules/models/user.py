from __future__ import annotations # for self-ref param type Post in save_posts_in_db()
from datetime import datetime
from typing import List, Optional as _, cast
from pydal.objects import Row
from gluon import current


class User(Row):
    id: int
    first_name: _[str]
    last_name: _[str]
    email: _[str]
    password: _[str]
    registration_key: _[str]
    reset_password_key: _[str]
    registration_id: _[str]
    picture_data: _[bytes]
    uploaded_picture: _[str]
    user_title: _[str]
    city: _[str]
    country: _[str]
    laboratory: _[str]
    institution: _[str]
    alerts: _[str]
    thematics: _[List[str]]
    cv: _[str]
    last_alert: _[datetime]
    registration_datetime: _[datetime]
    ethical_code_approved: bool
    recover_email: _[str]
    recover_email_key: _[str]
    website: _[str]
    keywords: _[str]
    orcid: _[str]
    no_orcid: bool

    @staticmethod
    def get_by_id(id: int):
        db = current.db
        return cast(_[User], db.auth_user[id])
    
    
    @staticmethod
    def get_by_reset_password_key(reset_password_key: str):
        db = current.db
        user = db(db.auth_user.reset_password_key == reset_password_key).select().first()
        return cast(_[User], user)
    

    @staticmethod
    def set_orcid(user: User, orcid: str):
        user.orcid = orcid
        return user.update_record()


    @staticmethod
    def set_no_orcid(user: User, no_orcid: bool = True):
        user.no_orcid = no_orcid
        return user.update_record()
    

    @staticmethod
    def is_profile_completed(user: User): 
        return user.first_name != None and len(user.first_name) > 0 \
            and user.last_name != None and len(user.last_name) > 0 \
            and user.email != None and len(user.email) > 0 \
            and user.laboratory != None and len(user.laboratory) > 0 \
            and user.institution != None and len(user.institution) > 0 \
            and user.city != None and len(user.city) > 0 \
            and user.country != None and len(user.country) > 0 \
            and user.thematics != None and len(user.thematics) > 0 \
            and user.cv != None and len(user.cv) > 0 \
            and user.keywords != None and len(user.keywords) > 0 \
            and user.website != None and len(user.website) > 0 \
            and user.alerts != None and len(user.alerts) > 0


