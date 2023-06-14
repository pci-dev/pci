from datetime import datetime
from typing import cast, Union
from pydal.objects import Row
from pydal import DAL


class User(Row):
    id: int
    first_name: Union[str, None]
    last_name: Union[str, None]
    email: Union[str, None]
    password: Union[str, None]
    registration_key: Union[str, None]
    reset_password_key: Union[str, None]
    registration_id: Union[str, None]
    picture_data: Union[bytes, None]
    uploaded_picture: Union[str, None]
    user_title: Union[str, None]
    city: Union[str, None]
    country: Union[str, None]
    laboratory: Union[str, None]
    institution: Union[str, None]
    alerts: Union[str, None]
    thematics: Union[str, None]
    cv: Union[str, None]
    last_alert: Union[datetime, None]
    registration_datetime: Union[datetime, None]
    ethical_code_approved: bool
    recover_email: Union[str, None]
    recover_email_key: Union[str, None]
    website: Union[str, None]
    keywords: Union[str, None]


    @staticmethod
    def get_by_id(db: DAL, id: int):
        return cast(Union[User, None], db.auth_user[id])
