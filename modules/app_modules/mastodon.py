import re
from typing import Any, List, Union, cast

from pydal.objects import Row
from pydal import DAL

from app_modules.social_network import SocialNetwork
from app_modules.httpClient import HttpClient


class Mastodon(SocialNetwork) :

    TOOT_MAX_LENGTH = 500
    TABLE_NAME = 'toots'

    def __init__(self, db: DAL):
        super().__init__(db, self.TOOT_MAX_LENGTH, self.TABLE_NAME)

        self.__access_token = cast(str, self._myconf.take('social_mastodon.access_token'))
        self.__instance_url = self.__get_instance_url()
        self.__mastodon = HttpClient(default_headers = {
                'Authorization': f'Bearer {self.__access_token}',
                'content-type': 'application/json',
            })
    

    def __get_instance_url(self):
         instance_url = cast(str, self._myconf.take('social_mastodon.instance_url'))
         if instance_url.endswith('/'):
              return instance_url[:-1]
         return instance_url
    

    def get_instance_name(self):
         regex = re.compile(r"https?://(www\.)?")
         return regex.sub('', self.__instance_url).strip().strip('/')
              

    def send_post(self, article: Row, recommendation: Row, posts_text: List[str]) -> Union[str, None]:
        url = f'{self.__instance_url}/api/v1/statuses'

        parent_id: Union[int, None] = None
        parent_toot_id: Union[str, None] = None
        for i, post_text in enumerate(posts_text):
            payload: dict[str, Any] = {'status': post_text}
            if parent_toot_id:
                    payload['in_reply_to_id'] = parent_toot_id

            response = self.__mastodon.post(url, json=payload)

            status_code = cast(int, response.status_code)
            toot = response.json()
            if status_code == 200:
                text_post = self.remove_html_tag(toot['content'])
                parent_id = self._save_posts_in_db(toot['id'], text_post, i, article.id, recommendation.id, parent_id)
                parent_toot_id = toot['id']
            else:
                return toot['error']


    def remove_html_tag(self, html_text: str):
        regex = re.compile('<.*?>')
        return re.sub(regex, '', html_text)
