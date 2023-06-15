from gluon.contrib.appconfig import AppConfig
from requests.models import Response
from typing import Dict, Any, Union
from models.article import Article

from app_modules.helper import *
from app_modules.httpClient import HttpClient
from app_modules.common_tools import generate_recommendation_doi

class Hypothesis:

    API_URL = "https://api.hypothes.is/api"
    
    def __init__(self, article: Article):
        self.__article = article
        self.__myconf = AppConfig(reload=True)
        self.__http = HttpClient(
            default_headers = {
                'Authorization': f"Bearer {self.__myconf.take('hypothesis.api_key')}",
                'content-type': 'application/json',
                'Accept': 'application/vnd.hypothesis.v1+json',
            }
        )


    @property
    def __session_id(self) -> str:
        return f'hypothesis_{self.__article.id}'
    

    @staticmethod
    def may_have_annotation(article_doi: str) -> bool:
        return article_doi.lower().strip().startswith('https://doi.org/10.1101/') # doi biorxiv
    

    def has_already_annotation(self) -> bool:
        return self.get_annotation() != None


    def post_annotation(self):
        if not self.__article.doi or not Hypothesis.may_have_annotation(self.__article.doi):
            return

        article_url = self.get_url_from_doi()
        
        if not self.has_stored_annotation():
            annotation_text = self.generate_annotation_text()
        else:
            annotation_text = self.get_stored_annotation()
            self.__remove_stored_annotation()

        if annotation_text:
            self.post_annotation_for_article(article_url, annotation_text)


    def generate_html_annotation_text(self) -> str:
        doi = generate_recommendation_doi(self.__article.id)

        line1 = f'Version {self.__article.ms_version} of this preprint has been <strong>peer-reviewed and recommended by <a href="{siteUrl}" target="_blank">{description}</a><strong>.<br>'
        line2 = f'See <a href="https://doi.org/{doi}" target="_blank">the peer reviews and the recommendation</a>.'

        return '<p id="hypothesis-annotation">' + line1 + line2 + '</p>'
    

    def get_annotation(self) -> Union[Any, None]:
        payload: Any = {
            'limit': 1,
            'uri': self.get_url_from_doi(),
            'group': self.__get_PCI_group_id()
        }

        response = self.__http.get(self.API_URL + '/search', params=self.__remove_empty(payload))
        
        if response.status_code == 200:
            annotations = response.json()
            if annotations['total'] >= 1:
                return annotations['rows'][0]

        return None


    def update_annotation(self, annotation: Any):
        return self.__http.patch(self.API_URL + f"/annotations/{annotation['id']}", json=self.__remove_empty(annotation))


    def generate_annotation_text(self) -> str:
        doi = generate_recommendation_doi(self.__article.id)

        line1 = f'Version {self.__article.ms_version} of this preprint has been **peer-reviewed and recommended by [{description}]({siteUrl})**.  \n'
        line2 = f'See [the peer reviews and the recommendation](https://doi.org/{doi}).'

        return line1 + line2


    def post_annotation_for_article(self, article_url: str, annotation_text: str) -> Response:
        group_id = self.__get_PCI_group_id()
        payload: Dict[str, Any] = {
            'uri': article_url,
            'text': annotation_text,
            'group': group_id,
            'permissions': {'read': [f'group:{group_id}']}
        }

        response = self.__http.post(self.API_URL + '/annotations', json=self.__remove_empty(payload))
        return response


    def get_url_from_doi(self) -> str:
        try:
            response = HttpClient().get(self.__article.doi, None, allow_redirects=True)
            return response.url
        except:
            return None


    def __get_PCI_group_id(self) -> str:
        response = self.__http.get(self.API_URL + '/profile/groups')
        groups = response.json()
        for group in groups:
            if group['name'] == 'PCI':
                return group['id']
        return 'error'


    def __remove_empty(self, dictionary: Dict[Any, Any]):
        return {k: v for k, v in dictionary.items() if v}


    def store_annotation(self, annotation_text: str):
        current.session[self.__session_id] = annotation_text


    def get_stored_annotation(self) -> Union[str, None]:
        return current.session[self.__session_id]

    
    def has_stored_annotation(self) -> bool:
        return current.session[self.__session_id] != None


    def __remove_stored_annotation(self):
        current.session[self.__session_id] = None
