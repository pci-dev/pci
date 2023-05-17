from requests_oauthlib import OAuth1Session
from textwrap import wrap

from app_modules.common_tools import generate_recommendation_doi
from random import randrange

from gluon.contrib.appconfig import AppConfig


class Twitter:

    TWEET_MAX_LENGTH = 280

    def __init__(self, db):
        self.__myconf = AppConfig(reload=True)
        self.__db = db

        self.__tweethash = self.__myconf.take('social.tweethash')
        self.__description = self.__myconf.take('app.description')

        self.__api_key = self.__myconf.take('social_twitter.api_key')
        self.__api_secret = self.__myconf.take('social_twitter.api_secret')
        self.__access_token = self.__myconf.take('social_twitter.access_token')
        self.__access_secret = self.__myconf.take('social_twitter.access_secret')

        self.__headers = {'Content-Type': 'application/json'}
        self.__twitter = OAuth1Session(self.__api_key,
                                              client_secret=self.__api_secret,
                                              resource_owner_key=self.__access_token,
                                              resource_owner_secret=self.__access_secret)


    def post_tweets(self, article, recommendation, tweets_text):
        url = 'https://api.twitter.com/2/tweets'

        parent_id = None
        parent_tweet_id = None
        for i, tweet_text in enumerate(tweets_text):
            payload = {'text': tweet_text}
            if parent_tweet_id:
                    payload['reply'] = {}
                    payload['reply']['in_reply_to_tweet_id'] = parent_tweet_id

            response = self.__twitter.post(url, json=payload)
            
            if response.status_code == 201:
                tweet = response.json()['data']
                parent_id = self.__save_tweet_in_db(tweet['id'], tweet['text'], i, article.id, recommendation.id, parent_id)
                parent_tweet_id = tweet['id']
            else:
                break


    def generate_tweet(self, article, recommendation):
        text = self.__generate_tweet_text(article, recommendation)
        tweets = self.__cut_tweet(text.strip())

        return tweets


    def get_tweets_from_db(self, article_id, recommendation_id) -> int:
        return self.__db((self.__db.tweets.article_id == article_id) & (self.__db.tweets.recommendation_id == recommendation_id)).select(orderby=self.__db.tweets.thread_position)


    def __generate_tweet_text(self, article, recommendation) -> str:
        line1 = f'A new #preprint #OpenScience #PeerReview by @{self.__tweethash}: {article.authors} ({article.article_year}) {article.title}. {article.preprint_server}, ver. {article.ms_version} peer-reviewed and recommended by {self.__description}. {article.doi} '
        line2 = f'recommended by {self.__get_user_name(recommendation.recommender_id)} for @{self.__tweethash} based on published reviews by {self.__get_reviewers_name(recommendation.id)} #OpenScience https://doi.org/{generate_recommendation_doi(article.id)}'
        return line1 + line2
        

    def __save_tweet_in_db(self, tweet_id: int, text_content: str, position: int, article_id: int, recommendation_id: int, parent_id: int) -> int:
        id = self.__db.tweets.insert(tweet_id=tweet_id, # À changer
                        text_content=text_content, 
                        thread_position=position, 
                        article_id=article_id,
                        recommendation_id=recommendation_id,
                        parent_id=parent_id
                        )
        self.__db.commit()
        return id


    def __cut_tweet(self, text: str) -> [str]:
        tweets = wrap(text, self.TWEET_MAX_LENGTH - 3)
        for i, tweet in enumerate(tweets[:-1]):
            tweets[i] += '… 🔽'
        
        return tweets

    
    def __get_user_name(self, user_id) -> str:
        user = self.__db.auth_user[user_id]

        if not user:
            return 'Anonymous'
        
        name = ''
        if user.first_name and len(user.first_name) > 0:
            name = user.first_name
        if user.last_name and len(user.last_name) > 0:
            if len(name) > 0:
                name += ' '
            name += user.last_name
        
        return name

    
    def __get_reviewers_name(self, recommendation_id) -> [str]:
        reviews = self.__db(self.__db.t_reviews.recommendation_id == recommendation_id).select()
        nb_anonymous = 0
        names = []
        for review in reviews:
            if review.anonymous_agreement:
                nb_anonymous += 1
            else:
                names.append(self.__get_user_name(review.reviewer_id))
        
        if (nb_anonymous > 0):
            anonymous = str(nb_anonymous) + ' anonymous reviewer'
            if (nb_anonymous > 1):
                anonymous += 's'
            names.append(anonymous)
            
        formatted_names = ', '.join(names)

        return (formatted_names[::-1].replace(',', ' and'[::-1], 1))[::-1]


