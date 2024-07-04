from typing import Any, List, Union, cast
from models.post import  Post, PostTable
from requests_oauthlib import OAuth1Session

from app_modules.social_network import SocialNetwork


class Twitter(SocialNetwork):

    POST_MAX_LENGTH = 280

    def __init__(self):
        super().__init__(self.POST_MAX_LENGTH, PostTable.TWEETS)

        self.__general_api_key = self.get_config('general_api_key')
        self.__general_api_secret = self.get_config('general_api_secret')
        self.__general_access_token = self.get_config('general_access_token')
        self.__general_access_secret = self.get_config('general_access_secret')

        self.__twitter = OAuth1Session(self.__general_api_key,
                                        client_secret=self.__general_api_secret,
                                        resource_owner_key=self.__general_access_token,
                                        resource_owner_secret=self.__general_access_secret)
        
        self.__specific_api_key = self.get_config('specific_api_key')
        self.__specific_api_secret = self.get_config('specific_api_secret')
        self.__specific_access_token = self.get_config('specific_access_token')
        self.__specific_access_secret = self.get_config('specific_access_secret')

        self.__specific_twitter = OAuth1Session(self.__specific_api_key,
                                        client_secret=self.__specific_api_secret,
                                        resource_owner_key=self.__specific_access_token,
                                        resource_owner_secret=self.__specific_access_secret)


    def get_config(self, key: str) -> str:
        return cast(str, self._myconf.get(f'social_twitter.{key}')) or ''


    def has_specific_twitter_config(self) -> bool:
         return len(self.__specific_api_key) > 0 \
            and len(self.__specific_api_secret) > 0 \
            and len(self.__specific_access_token) > 0 \
            and len(self.__specific_access_secret) > 0
    

    def has_general_twitter_config(self) -> bool:
         return len(self.__general_api_key) > 0 \
            and len(self.__general_api_secret) > 0 \
            and len(self.__general_access_token) > 0 \
            and len(self.__general_access_secret) > 0


    def send_post(self, article_id: int, recommendation_id: int, posts_text: List[str]):
        if self.has_general_twitter_config():
            self.__twitter_post(self.__twitter, article_id, recommendation_id, posts_text)
        
        if self.has_specific_twitter_config():
            self.__twitter_post(self.__specific_twitter, article_id, recommendation_id, posts_text)


    def __twitter_post(self, twitter: OAuth1Session, article_id: int, recommendation_id: int, posts_text: List[str]):
        url = 'https://api.twitter.com/2/tweets'

        parent_id: Union[int, None] = None
        parent_tweet_id: Union[int, None] = None
        for i, post_text in enumerate(posts_text):
            payload: dict[str, Any] = {'text': post_text}
            if parent_tweet_id:
                    payload['reply'] = {}
                    payload['reply']['in_reply_to_tweet_id'] = parent_tweet_id

            response = twitter.post(url, json=payload)
            
            tweet = response.json()
            if response.status_code == 201:
                tweet = tweet['data']
                tweet_post = Post(tweet['id'], tweet['text'], i, article_id, recommendation_id, parent_id)
                parent_id = self._save_posts_in_db(tweet_post)
                parent_tweet_id = tweet['id']
            else:
                raise Exception(tweet['detail'])
