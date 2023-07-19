from datetime import datetime
from typing import Optional as _, cast
from pydal.objects import Row
from pydal import DAL


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
    thematics: _[str]
    cv: _[str]
    last_alert: _[datetime]
    registration_datetime: _[datetime]
    ethical_code_approved: bool
    recover_email: _[str]
    recover_email_key: _[str]
    website: _[str]
    keywords: _[str]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(_[User], db.auth_user[id])
    
    
    @staticmethod
    def get_by_reset_password_key(db: DAL, reset_password_key: str):
        user = db(db.auth_user.reset_password_key == reset_password_key).select().first()
        return cast(_[User], user)
