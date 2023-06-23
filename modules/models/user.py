from datetime import datetime
from typing import Optional, cast
from pydal.objects import Row
from pydal import DAL


class User(Row):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    password: Optional[str]
    registration_key: Optional[str]
    reset_password_key: Optional[str]
    registration_id: Optional[str]
    picture_data: Optional[bytes]
    uploaded_picture: Optional[str]
    user_title: Optional[str]
    city: Optional[str]
    country: Optional[str]
    laboratory: Optional[str]
    institution: Optional[str]
    alerts: Optional[str]
    thematics: Optional[str]
    cv: Optional[str]
    last_alert: Optional[datetime]
    registration_datetime: Optional[datetime]
    ethical_code_approved: bool
    recover_email: Optional[str]
    recover_email_key: Optional[str]
    website: Optional[str]
    keywords: Optional[str]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(Optional[User], db.auth_user[id])
