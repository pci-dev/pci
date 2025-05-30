from abc import ABCMeta, abstractmethod
from textwrap import wrap
from typing import List, cast
from gluon import current
from gluon.contrib.appconfig import AppConfig # type: ignore
from models.article import Article
from models.post import Post, PostTable
from models.recommendation import Recommendation
from models.review import Review

from app_modules.common_tools import generate_recommendation_doi


class SocialNetwork(metaclass=ABCMeta):

    POST_MAX_LENGTH: int

    def __init__(self, post_max_length: int, table_name: PostTable):
            self._post_max_length = post_max_length
            self._table_name = table_name

            self._myconf = AppConfig(reload=True)
            self._db = current.db

            self._tweethash = cast(str, self._myconf.get('social.twitter'))
            self._description = cast(str, self._myconf.take('app.description'))


    @abstractmethod
    def send_post(self, article_id: int,
                  recommendation_id: int,
                  posts_text: List[str],
                  specific_account: bool = True,
                  general_account: bool = False):
        ''' Send post to social network with general and specific account. Raise an exception if error to send post. '''
        pass


    def generate_post(self, article: Article, recommendation: Recommendation):
        text = self.__generate_post_text(article, recommendation)
        posts = self.__cut_post_text(text.strip())

        return posts


    def __cut_post_text(self, text: str) -> List[str]:
        posts = wrap(text, self._post_max_length - 4)
        for i, post in enumerate(posts[:-1]):
            posts[i] = post + '… 🔽'

        return posts


    def __generate_post_text(self, article: Article, recommendation: Recommendation) -> str:
        line1 = f'A new #preprint #OpenScience #PeerReview by @{self._tweethash}: {article.authors} ({article.article_year}) {article.title}. {article.preprint_server}, ver. {article.ms_version} peer-reviewed and recommended by {self._description}. {article.doi} '
        line2 = f'recommended by {Recommendation.get_recommenders_names(recommendation)} for @{self._tweethash} based on published reviews by {Review.get_reviewers_name(article.id)} #OpenScience https://doi.org/{generate_recommendation_doi(article.id)}'
        return line1 + line2


    def get_posts_from_db(self, article_id: int, recommendation_id: int):
        return Post.get_posts_from_db(self._table_name, article_id, recommendation_id)


    def has_already_posted(self, article_id: int, recommendation_id: int):
        return Post.has_already_posted(self._table_name, article_id, recommendation_id)


    def _save_posts_in_db(self, post: Post):
        return Post.save_posts_in_db(self._table_name, post)
