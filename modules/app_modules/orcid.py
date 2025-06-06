from http.client import HTTPException
from typing import Any, Dict, List, Optional, cast
from dataclasses import dataclass

from gluon.dal import SQLCustomType
from gluon.contrib.appconfig import AppConfig
from gluon.html import A, CENTER, FORM, IMG, URL, SPAN, DIV, STRONG
from gluon.http import redirect
from gluon.sqlhtml import SQLFORM
from gluon import current

from app_modules.httpClient import HttpClient
from app_modules.common_tools import get_next, get_script, sget
from app_modules.country import Country


class OrcidTools:

    @staticmethod
    def add_hyphen(value: Optional[str]):
        if not value or len(value) == 0:
            return None
        return '-'.join(value[i:i+4] for i in range(0, len(value), 4))


    @staticmethod
    def remove_hyphen(value: Optional[str]):
        if not value or len(value) == 0:
            return None
        return value.replace('-', '')
    

    @staticmethod
    def get_orcid_formatter_script():
        return get_script("orcid_formatter.js")
    

    @staticmethod
    def configure_orcid_input(form: DIV):
        form.element(_name="orcid")["_maxlength"] = ORCID_NUMBER_LENGTH_WITH_HYPHEN
        return form
    

    @staticmethod
    def add_orcid_auth_user_form(auth_user_form: SQLFORM, redirect_url: Optional[str] = None):
        session = current.session
        
        OrcidTools.configure_orcid_input(auth_user_form)
        if not redirect_url or len(redirect_url) == 0:
            return

        orcid_api = OrcidAPI(redirect_url)
        orcid_row = auth_user_form.element(_class="form-horizontal")
        orcid_row.components.insert(0, CENTER(orcid_api.get_orcid_html_button()))
        if session.click_orcid:
            try:
                orcid_api.update_form(auth_user_form)
            except HTTPException as e:
                session.flash = e
            session.click_orcid = False


    @staticmethod
    def redirect_ORCID_authentication():
        session = current.session

        session.click_orcid = True
        next = get_next()
        if not next:
            session.flash = current.T('Redirection URL is required for ORCID authentication')
            return redirect(URL('default','index'))
        code = OrcidAPI.get_code_in_url()
        if not code:
            orcid_api = OrcidAPI(next)
            orcid_api.go_to_authentication_page()
        else:
            redirect(next)

    
    @staticmethod
    def get_orcid_number_label():
        return DIV(STRONG("ORCID number"), SPAN(" (using the following format: 0000-000X-XXX-XXX)", _style="font-size: small; font-weight: initial"))


    @staticmethod
    def build_name_with_orcid(user_name: Any, orcid_id: Optional[str], before: bool = False, height: str = '20px', width: str = '20px', style: str = '', force_style: bool = False):
        if not orcid_id:
            return user_name

        if not force_style:
            if before:
                style += ";position: relative; right: 3px; bottom: 1px;"
            else:
                style += ";position: relative; left: 3px; bottom: 1px;" 
        
        orcid_link = A(IMG(_alt="ORCID_LOGO", _src=URL(c="static", f="images/ORCID_ID.svg"), _heigth=height, _width=width), 
                  _title=orcid_id, _href=f"https://orcid.org/{orcid_id}", _target="_blank", _rel="noreferrer noopener", _style=style)
        
        if before:
            return SPAN(orcid_link, user_name)
        else:
            return SPAN(user_name, orcid_link)

ORCID_NUMBER_FIELD_TYPE = SQLCustomType("string", "string", OrcidTools.remove_hyphen, OrcidTools.add_hyphen)
ORCID_NUMBER_LENGTH = 16
ORCID_NUMBER_LENGTH_WITH_HYPHEN = ORCID_NUMBER_LENGTH + 3


class OrcidValidator:

    def __init__(self):
        self.error_message = 'Invalid ORCID number'


    def __call__(self, value: Optional[str]):
        value = OrcidTools.remove_hyphen(value)
        if not value or len(value) == 0:
            return value, None

        if len(value) != ORCID_NUMBER_LENGTH:
            return value, f'{self.error_message}: expected length 16, got {len(value)}'
        
        if value[-1] == "X":
            digits = value[:-1]
        else:
            digits = value

        if not digits.isdigit():
            return value, f'{self.error_message}: must contain only digits, optionally a trailing X'
        
        return value, None


class OrcidAPI:

    @dataclass(frozen=True)
    class OrcidKeys:
        token: str
        orcid: str

    AUTHORIZE_URL = 'https://orcid.org/oauth/authorize'
    OAUTH_TOKEN_URL = 'https://orcid.org/oauth/token'
    API_URL = 'https://pub.orcid.org/v3.0/'

    def __init__(self, redirect_url: str):
        self.__redirect_url = redirect_url

        self.__myconf = AppConfig()
        self.__client_id = self.__myconf.get('ORCID.client_id') or ''
        self.__client_secret = self.__myconf.get('ORCID.client_secret') or ''

        self.__orcid_keys: Optional[OrcidAPI.OrcidKeys] = None

    def go_to_authentication_page(self):
        authorization_url = f'{self.AUTHORIZE_URL}?client_id={self.__client_id}&response_type=code&scope=/authenticate&redirect_uri={self.__redirect_url}'
        redirect(authorization_url)


    def get_orcid_html_button(self, style: Optional[str] = None):
        return A(IMG(_alt="ORCID_LOGO", _src=URL(c="static", f="images/ORCID_ID.svg"), _heigth="20px", _width="20px", _style="position: relative; bottom: 2px; right: 6px;"),
                 current.T('Log to your ORCID account to partially fill your profile'), _href=URL("default", "redirect_ORCID_authentication", vars=dict(_next=self.__redirect_url)), _class="btn btn-info", _style=style)


    def update_form(self, form: FORM):
        session = current.session

        if not session.token_orcid:
            code = OrcidAPI.get_code_in_url()
            if not code:
                return

            if self.__orcid_keys:
                session.token_orcid = self.__orcid_keys
            else:
                self.__init_token_orcid(code)
                session.token_orcid = self.__orcid_keys
        else:
            self.__orcid_keys = session.token_orcid
                
        user_infos = self.__retrieve_user_infos()
        self.__fill_form(user_infos, form)


    def __fill_form(self, user_infos: Any, form: FORM):
        first_name_value = cast(Optional[str], sget(user_infos, 'person', 'name', 'given-names', 'value'))
        last_name_value = cast(Optional[str], sget(user_infos, 'person', 'name', 'family-name', 'value'))
        orcid_value = cast(Optional[str], sget(user_infos, 'orcid-identifier', 'path'))
        cv_value = cast(Optional[str], sget(user_infos, 'person', 'biography', 'content'))
        institution_value = self.__extract_institution_value(user_infos)
        keyword_value = self.__extract_keyword_value(user_infos)
        website_value = self.__extract_website_value(user_infos)
        country_value = self.__extract_country_value(user_infos)
        laboratory_value = self.__extract_laboratory_value(user_infos)
        city_value = self.__extract_city_value(user_infos)
        email_value = self.__extract_email_value(user_infos)

        self.__set_value_in_form(form, 'first_name', first_name_value)
        self.__set_value_in_form(form, 'last_name', last_name_value)
        self.__set_value_in_form(form, 'orcid', orcid_value)
        self.__set_value_in_form(form, 'institution', institution_value)
        self.__set_value_in_form(form, 'keywords', keyword_value)
        self.__set_value_in_form(form, 'cv', cv_value)
        self.__set_value_in_form(form, 'website', website_value)
        self.__set_value_in_form(form, 'country', country_value)
        self.__set_value_in_form(form, 'laboratory', laboratory_value)
        self.__set_value_in_form(form, 'city', city_value)
        self.__set_value_in_form(form, 'email', email_value)
    

    def __extract_email_value(self, user_infos: Any):
        email_value: Optional[str] = ''
        emails = cast(Optional[List[Any]], sget(user_infos, 'person', 'emails', 'email'))
        if emails and len(emails) > 0:
            email_value = cast(Optional[str], emails[0].get('email'))
        return email_value


    def __extract_city_value(self, user_infos: Any):
        city_value: Optional[str] = ''
        affiliations = cast(Optional[List[Any]], sget(user_infos, 'activities-summary', 'employments', 'affiliation-group'))
        if affiliations and len(affiliations) > 0:
            affiliation = cast(Dict[str, Any], affiliations[0])
            summaries = cast(Optional[List[Any]], affiliation.get('summaries'))
            if summaries and len(summaries) > 0:
                summary = cast(Dict[str, Any], summaries[0])
                city_value = cast(Optional[str], sget(summary, 'employment-summary', 'organization', 'address', 'city'))
        return city_value


    def __extract_laboratory_value(self, user_infos: Any):
        laboratory_value: Optional[str] = ''
        affiliations = cast(Optional[List[Any]], sget(user_infos, 'activities-summary', 'employments', 'affiliation-group'))
        if affiliations and len(affiliations) > 0:
            affiliation = cast(Dict[str, Any], affiliations[0])
            summaries = cast(Optional[List[Any]], affiliation.get('summaries'))
            if summaries and len(summaries) > 0:
                summary = cast(Dict[str, Any], summaries[0])
                laboratory_value = cast(Optional[str], sget(summary, 'employment-summary', 'department-name'))
        return laboratory_value


    def __extract_country_value(self, user_infos: Any):
        country_value: Optional[str] = ''
        addresses = cast(Optional[List[Any]], sget(user_infos, 'person', 'addresses', 'address'))
        if addresses and len(addresses) > 0:
            address = cast(Dict[str, Any], addresses[0])
            country_code = cast(Optional[str], sget(address, 'country', 'value'))
            if country_code and len(country_code) > 0:
                country_value = Country.get_by_code(country_code).value
        return country_value


    def __extract_institution_value(self, user_infos: Any):
        insitution_value: Optional[str] = ''
        affiliations = cast(Optional[List[Any]], sget(user_infos, 'activities-summary', 'employments', 'affiliation-group'))
        if affiliations and len(affiliations) > 0:
            affiliation = cast(Dict[str, Any], affiliations[0])
            summaries = cast(Optional[List[Any]], affiliation.get('summaries'))
            if summaries and len(summaries) > 0:
                summary = cast(Dict[str, Any], summaries[0])
                insitution_value = cast(Optional[str], sget(summary, 'employment-summary', 'organization', 'name'))
        return insitution_value


    def __extract_keyword_value(self, user_infos: Any):
        keywords = cast(Optional[List[Any]], sget(user_infos, 'person', 'keywords', 'keyword'))
        keyword_value = ''
        if keywords and len(keywords) > 0:
            for keyword in keywords:
                keyword_value += keyword.get('content', '') + ','
            keyword_value = keyword_value[:-1]
        return keyword_value
    

    def __extract_website_value(self, user_infos: Any):
        website_value: Optional[str] = ''
        websites = cast(Optional[List[Any]], sget(user_infos, 'person', 'researcher-urls', 'researcher-url'))
        if websites and len(websites) > 0:
            website = cast(Dict[str, Any], websites[0])
            website_value = cast(Optional[str], sget(website, 'url', 'value'))
        return website_value


    def __set_value_in_form(self, form: FORM, form_name: str, value: Optional[str]):
        if not value or len(value) == 0:
            return
                
        input = form.element(_name=form_name)
        if not input:
            return
        
        if input.tag == 'textarea':
            if len(input.components) > 0:
                input.components[0] = value
            else:
                input.components.append(value)
            return
        
        input["_value"] = value

        if input.tag == 'select':
            for component in input.components:
                if component["_selected"]:
                    component["_selected"] = None
                if component["_value"] == value:
                    component["_selected"] = 'selected'


    def __retrieve_user_infos(self) -> Optional[Dict[str, Any]]:
        if not self.__orcid_keys:
            return
        
        http_client = HttpClient(default_headers={'Accept': 'application/json', 'Authorization': f'Bearer {self.__orcid_keys.token}'})
        response = http_client.get(self.API_URL + self.__orcid_keys.orcid)

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(response.text)


    def __init_token_orcid(self, code: str):
        if not code:
            return None
        
        payload = f'client_id={self.__client_id}&client_secret={self.__client_secret}&grant_type=authorization_code&redirect_uri={self.__redirect_url}&code={code}'
        
        http_client = HttpClient({'Content-Type': 'application/x-www-form-urlencoded'})
        response = http_client.post(self.OAUTH_TOKEN_URL, data=payload)
        json_response = response.json()

        if 'access_token' in json_response and 'orcid' in json_response:
            self.__orcid_keys = OrcidAPI.OrcidKeys(json_response['access_token'], json_response['orcid'])
        else:
            raise HTTPException(response.text)


    @staticmethod
    def get_code_in_url():
        request = current.request

        if 'code' in request.vars:
            return cast(str, request.vars['code'])
        return None
