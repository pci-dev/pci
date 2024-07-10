import re
from typing import List, Optional, Union

from urllib.parse import urlparse
from pydal.validators import IS_HTTP_URL
from pydal.validators import Validator

class CUSTOM_VALID_URL(Validator):

    def __init__(self, allow_empty_netloc: bool = False):
        self.error_message = 'Enter a valid URL'
        self._allow_empty_netloc = allow_empty_netloc
        self._is_http_url = IS_HTTP_URL()


    def __call__(self, value: Optional[str], record_id: Optional[int] = None):
        if not value or len(value) == 0:
            return value, None

        try:
            url = urlparse(value)
        except ValueError as error:
            return value, f"{self.error_message}: {error}"
        
        if not url.scheme:
            return value, f"{self.error_message}: Missing http(s)://"
        
        if not url.netloc and not self._allow_empty_netloc:
            return value, self.error_message
        
        _, error = self._is_http_url(value)
        if error:
            return value, error
        
        return value, None


class VALID_LIST_NAMES_MAIL(Validator):

    _regex: str
    _error_message: str

    def __init__(self, is_list_string: bool = False, without_email: bool = False):
        if without_email:
            self._regex = r"(([\w\-\.]+ )*[\w\-]+)+"
        else:
            self._regex = r"(([\w\-\.]+ )*[\w\-]+ [a-zA-Z_\-\.]+@[a-zA-Z_\-\.]+\.[a-z]+)+"

        if is_list_string:
            if without_email:
                self._error_message = 'Pattern must be: <first name> <last name>'
            else:
                self._error_message = 'Pattern must be: <first name> <last name> <mail>'

        else:
            if without_email:
                self._error_message = 'Pattern must be: <first name> <last name>, <first name> <last name>, ...'
            else:
                self._error_message = 'Pattern must be: <first name> <last name> <mail>, <first name> <last name> <mail>, ...'


    def __call__(self, value: Optional[Union[str, List[str]]], record_id: Optional[int] = None):
        if not value or len(value) == 0:
            return value, None
        
        self._pattern = re.compile(self._regex)
        
        if isinstance(value, str):
            people = value.split(',')
            for person in people:
                person = person.strip()
                match = self._pattern.fullmatch(person)
                if not match:
                    return value, self._error_message
        else:
            for person in value:
                match = self._pattern.fullmatch(person)
                if not match:
                    return value, self._error_message
                
        return value, None
