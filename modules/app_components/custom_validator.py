import re
from typing import List, Optional, Union

from urllib.parse import urlparse
from gluon import STRONG
from gluon.html import A, P
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
        
        _, error = self._is_http_url(value) # type: ignore
        if error:
            return value, error
        
        return value, None


class VALID_DOI(Validator):
     
    _preprint_server: Optional[str]
    error_message: P

    def __init__(self, preprint_server: Optional[str]):
        if preprint_server is None:
            self._preprint_server = None
        else:
            self._preprint_server = preprint_server.lower().strip()

        self.error_message = P("The preprint server you have indicated provides DOIs.",
                            " Please replace this URL with a DOI, in the format ",
                            STRONG("https://doi.org/10.xxx", _style="white-space: nowrap;"),
                            ". In case of OSFHOME, please see ", 
                            A("https://help.osf.io/article/220-create-dois", _href="https://help.osf.io/article/220-create-dois", _target="_blank", _rel="noreferrer noopener"),
                            " to create a DOI. OSF Preprints and all derived preprint servers (such as PsyArxiv) provide DOIs.")


    def __call__(self, value: Optional[str], record_id: Optional[int] = None):
        if self._preprint_server is None or not value:
            return value, None

        if self._preprint_server not in ('osf', 'zenodo') and 'rxiv' not in self._preprint_server:
            return CUSTOM_VALID_URL()(value, record_id)
        
        if value.startswith('https://doi.org/10.'):
            return CUSTOM_VALID_URL()(value, record_id)
        else:
            return value, self.error_message
        
        
class VALID_LIST_NAMES_MAIL(Validator):

    _regex: str
    _error_message: str

    def __init__(self, is_list_string: bool = False, without_email: bool = False, optional_email: bool = False):
        if optional_email:
            self._regex = r"((([\w\-\.]+ )*[\w\-]+)+)|((([\w\-\.]+ )*[\w\-]+ [a-zA-Z0-9_\-\.]+@[a-zA-Z0-9_\-\.]+\.[a-z]+)+)"
        elif without_email:
            self._regex = r"(([\w\-\.]+ )*[\w\-]+)+"
        else:
            self._regex = r"(([\w\-\.]+ )*[\w\-]+ [a-zA-Z0-9_\-\.]+@[a-zA-Z0-9_\-\.]+\.[a-z]+)+"

        if is_list_string:
            if optional_email:
                self._error_message = 'Pattern must be: <first name> <last name> <mail> (mail is optional)'
            elif without_email:
                self._error_message = 'Pattern must be: <first name> <last name>'
            else:
                self._error_message = 'Pattern must be: <first name> <last name> <mail>'

        else:
            if optional_email:
                self._error_message = 'Pattern must be: <first name> <last name> <mail>, <first name> <last name> <mail>, ... (mail is optional)'
            elif without_email:
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
