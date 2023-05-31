from typing import Any, List, Union, cast
from pydal.base import DAL
from requests_oauthlib import OAuth1Session

from app_modules.social_network import SocialNetwork

class Twitter(SocialNetwork):

    TABLE_NAME = 'tweets'
    POST_MAX_LENGTH = 280

    def __init__(self, db: DAL):
        super().__init__(db, self.POST_MAX_LENGTH, self.TABLE_NAME)

        self.__api_key = cast(str, self._myconf.take('social_twitter.api_key'))
        self.__api_secret = cast(str, self._myconf.take('social_twitter.api_secret'))
        self.__access_token = cast(str, self._myconf.take('social_twitter.access_token'))
        self.__access_secret = cast(str, self._myconf.take('social_twitter.access_secret'))

        self.__twitter = OAuth1Session(self.__api_key,
                                        client_secret=self.__api_secret,
                                        resource_owner_key=self.__access_token,
                                        resource_owner_secret=self.__access_secret)
        

    def send_post(self, article_id: int, recommendation_id: int, posts_text: List[str]) -> Union[str, None]:
        url = 'https://api.twitter.com/2/tweets'

        parent_id: Union[int, None] = None
        parent_tweet_id: Union[int, None] = None
        for i, post_text in enumerate(posts_text):
            payload: dict[str, Any] = {'text': post_text}
            if parent_tweet_id:
                    payload['reply'] = {}
                    payload['reply']['in_reply_to_tweet_id'] = parent_tweet_id

            try:
                response = self.__twitter.post(url, json=payload)
            except Exception as e:
                 return f'{e}'

            tweet = response.json()
            if response.status_code == 201:
                tweet = tweet['data']
                parent_id = self._save_posts_in_db(tweet['id'], tweet['text'], i, article_id, recommendation_id, parent_id)
                parent_tweet_id = tweet['id']
            else:
                return tweet['detail']
