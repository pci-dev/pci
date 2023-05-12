from gluon.contrib.appconfig import AppConfig
from app_modules.helper import *
from app_modules.httpClient import HttpClient
from app_modules.common_tools import generate_recommendation_doi
from requests.models import Response
import json
from typing import Dict, Any

class Hypothesis:

    API_URL = "https://api.hypothes.is/api"
    
    def __init__(self):
        self.__myconf = AppConfig(reload=True)
        self.__http = HttpClient(
            default_headers = {
                'Authorization': f"Bearer {self.__myconf.take('hypothesis.api_key')}",
                'content-type': 'application/json',
                'Accept': 'application/vnd.hypothesis.v1+json',
            }
        )

    
    @staticmethod
    def may_have_annotation(article_doi) -> bool:
        return article_doi.lower().strip().startswith('https://doi.org/10.1101/') # doi biorxiv


    def post_annotation(self, article):
        if not Hypothesis.may_have_annotation(article.doi):
            return

        article_url = self.get_url_from_doi(article.doi)
        annotation_text = self.generate_annotation_text(article)
        self.post_annotation_for_article(article_url, annotation_text)


    def generate_html_annotation_text(self, article) -> str:
        doi = generate_recommendation_doi(article.id)

        line1 = f'Version {article.ms_version} of this preprint has been <strong>peer-reviewed and recommended by <a href="{siteUrl}" target="_blank">{shortname}</a><strong>.<br>'
        line2 = f'See <a href="https://doi.org/{doi}" target="_blank">the peer reviews and the recommendation</a>.'

        return '<p id="hypothesis-annotation">' + line1 + line2 + '</p>'
    

    def get_annotation(self, article_doi):
        payload = {
            'limit': 1,
            'uri': self.get_url_from_doi(article_doi),
            'group': self.__get_PCI_group_id()
        }

        response = self.__http.get(self.API_URL + '/search', params=self.__remove_empty(payload))
        
        if response.status_code == 200:
            annotations = response.json()
            if annotations['total'] >= 1:
                return annotations['rows'][0]

        return None


    def update_annotation(self, annotation):
        return self.__http.patch(self.API_URL + f"/annotations/{annotation['id']}", json=self.__remove_empty(annotation))


    def generate_annotation_text(self, article) -> str:
        doi = generate_recommendation_doi(article.id)

        line1 = f'Version {article.ms_version} of this preprint has been **peer-reviewed and recommended by [{shortname}]({siteUrl})**.  \n'
        line2 = f'See [the peer reviews and the recommendation](https://doi.org/{doi}).'

        return line1 + line2


    def post_annotation_for_article(self, article_url, annotation_text) -> Response:
        group_id = self.__get_PCI_group_id()
        payload = {
            'uri': article_url,
            'text': annotation_text,
            'group': group_id,
            'permissions': {'read': [f'group:{group_id}']}
        }

        response = self.__http.post(self.API_URL + '/annotations', json=self.__remove_empty(payload))
        return response


    def get_url_from_doi(self, article_doi) -> str:
        response = HttpClient().get(article_doi, None, allow_redirects=True)
        return response.url


    def __get_PCI_group_id(self) -> str:
        response = self.__http.get(self.API_URL + '/profile/groups')
        groups = response.json()
        for group in groups:
            if group['name'] == 'PCI':
                return group['id']
        return 'error'


    def __remove_empty(self, dictionary: Dict[Any, Any]):
        return {k: v for k, v in dictionary.items() if v}
