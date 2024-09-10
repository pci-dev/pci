from typing import Optional

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
        
        
