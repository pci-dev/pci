import re
from typing import Any, List, Union, cast
from models.post import Post, PostTable

from app_modules.social_network import SocialNetwork
from app_modules.httpClient import HttpClient


class Mastodon(SocialNetwork) :

    POST_MAX_LENGTH = 500

    def __init__(self):
        super().__init__(self.POST_MAX_LENGTH, PostTable.TOOTS)

        self.__general_access_token = self.get_config('general_access_token')
        self.__general_instance_url = self.__get_instance_url()
        self.__general_mastodon = HttpClient(default_headers = {
                'Authorization': f'Bearer {self.__general_access_token}',
                'content-type': 'application/json',
            })
        
        self.__specific_access_token = self.get_config('specific_access_token')
        self.__specific_instance_url = self.__get_instance_url(True)
        self.__specific_mastodon = HttpClient(default_headers = {
                'Authorization': f'Bearer {self.__specific_access_token}',
                'content-type': 'application/json',
            })
        

    def has_mastodon_specific_config(self) -> bool:
        return len(self.__specific_access_token) > 0 and len(self.__specific_instance_url) > 0
    

    def has_mastodon_general_config(self) -> bool:
        return len(self.__general_access_token) > 0 and len(self.__general_instance_url) > 0


    def get_config(self, key: str) -> str:
        return cast(str, self._myconf.get(f'social_mastodon.{key}')) or ''


    def __get_instance_url(self, specific: bool = False):
        if specific:
            instance_url = self.get_config('specific_instance_url')
        else:
            instance_url = self.get_config('general_instance_url')

        if instance_url.endswith('/'):
            return instance_url[:-1]
        return instance_url
    

    def get_instance_name(self, specific: bool = False):
        if specific:
            instance_url = self.__specific_instance_url
        else:
            instance_url = self.__general_instance_url

        regex = re.compile(r"https?://(www\.)?")
        return regex.sub('', instance_url).strip().strip('/')
              

    def send_post(self, article_id: int, recommendation_id: int, posts_text: List[str]):
            if self.has_mastodon_general_config():
                self.__mastodon_post(self.__general_mastodon, self.__general_instance_url, article_id, recommendation_id, posts_text)

            if self.has_mastodon_specific_config():
                self.__mastodon_post(self.__specific_mastodon, self.__specific_instance_url, article_id, recommendation_id, posts_text)


    def __mastodon_post(self, mastodon: HttpClient, instance_url: str, article_id: int, recommendation_id: int, posts_text: List[str]) -> Union[str, None]:
        url = f'{instance_url}/api/v1/statuses'

        parent_id: Union[int, None] = None
        parent_toot_id: Union[str, None] = None
        for i, post_text in enumerate(posts_text):
            payload: dict[str, Any] = {'status': post_text}
            if parent_toot_id:
                payload['in_reply_to_id'] = parent_toot_id

            response = mastodon.post(url, json=payload)

            toot = response.json()
            if response.status_code == 200:
                text_post = self.remove_html_tag(toot['content'])
                toot_post = Post(toot['id'], text_post, i, article_id, recommendation_id, parent_id)
                parent_id = self._save_posts_in_db(toot_post)
                parent_toot_id = toot['id']
            else:
                raise Exception(toot['error'])


    def remove_html_tag(self, html_text: str):
        regex = re.compile('<.*?>')
        return re.sub(regex, '', html_text)
