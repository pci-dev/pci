from typing import List, Optional, Union

from urllib.parse import urlparse
from gluon import STRONG
from gluon.html import A, P
from pydal.validators import IS_HTTP_URL
from pydal.validators import Validator
from app_modules.suggested_reviewers_parser import Reviewer

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
    
    _error_message: str
    _error_message_suggested: str

    _without_email: bool
    _optional_email: bool

    def __init__(self, is_list_string: bool = False, without_email: bool = False, optional_email: bool = False):

        self._without_email = without_email
        self._optional_email = optional_email

        if is_list_string:
            if optional_email:
                self._error_message = 'Pattern must be: <first name> <last name> <mail> (mail is optional)'
                self._error_message_suggested = 'Pattern must be: <first name> <last name> <optional mail> suggested: <first name> <last name> <mail> (mail is optional)'
            elif without_email:
                self._error_message = 'Pattern must be: <first name> <last name>'
                self._error_message_suggested = 'Pattern must be: <first name> <last name> <optional mail> suggested: <first name> <last name>'
            else:
                self._error_message = 'Pattern must be: <first name> <last name> <mail>'
                self._error_message_suggested = 'Pattern must be: <first name> <last name> <optional mail> suggested: <first name> <last name> <mail>'

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
        
        if isinstance(value, str):
            people = value.split(',')
            for person in people:
                try:
                    reviewer = Reviewer.parse(person)
                    self._check_constraints(reviewer)
                except Exception as e:
                    return value, f"{self._error_message} -> {person}: {e}"
        else:
            for person in value:
                try:
                    reviewer = Reviewer.parse(person)
                    self._check_constraints(reviewer)
                except Exception as e:
                    if "suggested:" in person:
                        error_message = self._error_message_suggested
                    else:
                        error_message = self._error_message
                        
                    return value, f"{error_message} -> {person}: {e}"
                
        return value, None


    def _check_constraints(self, reviewer: Reviewer):
        if self._without_email:
            if reviewer.suggested.email is not None:
                raise Exception("Email is forbidden")
        else:
            if not self._optional_email and reviewer.suggested.email is None:
                raise Exception("Email is required")
