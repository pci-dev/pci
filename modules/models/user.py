from datetime import datetime
import time
from typing import Any, Dict, List, Optional as _, cast
from pydal.validators import CRYPT

from gluon.utils import web2py_uuid # type: ignore
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
    email_options = List[str]
    orcid: _[str]
    no_orcid: bool
    deleted: bool
    new_article_cache: _[Dict[Any, Any]]

    @staticmethod
    def get_by_id(id: int):
        db = current.db
        try: user = db.auth_user[id]
        except: user = None
        return cast(_[User], user)


    @staticmethod
    def get_by_email(email: str):
        db = current.db
        user = db(db.auth_user.email == email).select().first()
        return cast(_[User], user)


    @staticmethod
    def get_by_reset_password_key(reset_password_key: str):
        db = current.db
        user = db(db.auth_user.reset_password_key == reset_password_key).select().first()
        return cast(_[User], user)


    @staticmethod
    def get_by_recover_email_key(recover_email_key: str):
        db = current.db
        user = db(db.auth_user.recover_email_key == recover_email_key).select().first()
        return cast(_[User], user)


    @staticmethod
    def set_orcid(user: 'User', orcid: str) -> 'User':
        user.orcid = orcid
        return user.update_record() # type: ignore


    @staticmethod
    def set_no_orcid(user: 'User', no_orcid: bool = True) -> 'User':
        user.no_orcid = no_orcid
        return user.update_record() # type: ignore


    @staticmethod
    def is_profile_completed(user: 'User'):
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


    @staticmethod
    def change_email(user_id: int, new_email: str):
        user = User.get_by_id(user_id)
        if not user:
            raise Exception('User not found')

        max_time = (15 * 24 * 60 * 60) + int(time.time())
        recover_email_key = str( max_time) + "-" + web2py_uuid()
        user.update_record(recover_email_key=recover_email_key, recover_email=new_email) # type: ignore

        return recover_email_key


    @staticmethod
    def confirm_change_email(recover_email_key: str):
        try:
            max_time = int(recover_email_key.split('-')[0])
        except:
            raise Exception('Invalid key')

        user = User.get_by_recover_email_key(recover_email_key)
        if not user:
            raise Exception('Unknown key')

        current_time = int(time.time())
        if current_time >= max_time:
            raise Exception('Expired key')

        user.email = user.recover_email
        user.recover_email = None
        user.recover_email_key = None
        user.update_record() # type: ignore


    @staticmethod
    def delete(user_id: int):
        from app_modules.common_tools import delete_user_from_PCI
        user = User.get_by_id(user_id)
        if user:
            delete_user_from_PCI(user)
        else:
            raise Exception("User {user_id} not found!")


    @staticmethod
    def get_name(user: 'User'):
        name: List[str] = []
        if user.first_name:
            name.append(user.first_name)
        if user.last_name:
            name.append(user.last_name)

        return " ".join(name) or "?"


    @staticmethod
    def get_name_by_id(user_id: int):
        user = User.get_by_id(user_id)
        if user:
            return User.get_name(user)
        else:
            return "?"


    @staticmethod
    def set_deleted(user: 'User'):
        user.deleted = True
        user.update_record() # type: ignore
        return user


    @staticmethod
    def empty_user_data(user: 'User'):
        user.email = None
        user.password = None
        user.registration_key = None
        user.reset_password_key = None
        user.registration_id = None
        user.picture_data = None
        user.uploaded_picture = None
        user.user_title = None
        user.city = None
        user.country = None
        user.laboratory = None
        user.institution = None
        user.alerts = None
        user.thematics = None
        user.cv = None
        user.last_alert = None
        user.recover_email = None
        user.recover_email_key = None
        user.website = None
        user.keywords = None
        user.email_options = []
        user.orcid = None

        user.update_record() # type: ignore


    @staticmethod
    def generate_new_reset_password_key():
        reset_password_key = str((15 * 24 * 60 * 60) + int(time.time())) + "-" + web2py_uuid()
        return reset_password_key


    @staticmethod
    def create_new_user(first_name: str,
                        last_name: str,
                        email: str,
                        reset_password_key: _[str] = None,
                        institution: _[str] = None,
                        country: _[str] = None,
                        orcid: _[str] = None):
        db = current.db
        my_crypt = CRYPT(key=current.auth.settings.hmac_key)
        crypt_pass = my_crypt(current.auth.random_password())[0] # type: ignore

        if not reset_password_key:
            reset_password_key = User.generate_new_reset_password_key()

        new_user_id = db.auth_user.insert(
            email=email,
            password=crypt_pass,
            reset_password_key=reset_password_key,
            first_name=first_name,
            last_name=last_name,
            institution=institution,
            country=country,
            orcid=orcid)

        return User.get_by_id(new_user_id)


    @staticmethod
    def set_in_new_article_cache(user: 'User', article_data: Dict[Any, Any]) -> 'User':
        user.new_article_cache = article_data
        return user.update_record() # type: ignore


    @staticmethod
    def clear_new_article_cache(user: 'User') -> 'User':
        user.new_article_cache = None
        return user.update_record() # type: ignore


    @staticmethod
    def get_all_user_subscribed_newsletter():
        db = current.db
        users: List[User] = db((db.auth_user.alerts != None)
                               & (db.auth_user.alerts != "Never")
                               & (db.auth_user.alerts != "")
                               & (db.auth_user.deleted == False)
                               & (db.auth_user.email != None)
                               ).select(distinct=True)
        return users


    @staticmethod
    def get_affiliation(user: 'User'):
        if hasattr(user, "is_pseudo"):
            return "(unavailable)"

        affiliation = ""
        if user.laboratory:
            affiliation += user.laboratory
        if user.laboratory and user.institution:
            affiliation += ", "
        if user.institution:
            affiliation += f"{user.institution}"
        if user.city or user.country:
            affiliation += " – "
        if user.city:
            affiliation += user.city
        if user.city and user.country:
            affiliation += ", "
        if user.country:
            affiliation += user.country

        return affiliation
