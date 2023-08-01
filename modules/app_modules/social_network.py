from abc import ABCMeta, abstractmethod
from textwrap import wrap
from typing import List, cast
from gluon.contrib.appconfig import AppConfig
from models.article import Article
from models.post import Post, PostTable
from models.recommendation import Recommendation
from models.review import Review, ReviewState
from models.user import User
from pydal.base import DAL

from app_modules.common_tools import generate_recommendation_doi


class SocialNetwork(metaclass=ABCMeta):
    
    POST_MAX_LENGTH: int

    def __init__(self, db: DAL, post_max_length: int, table_name: PostTable):
            self._post_max_length = post_max_length
            self._table_name = table_name

            self._myconf = AppConfig(reload=True)
            self._db = db

            self._tweethash = cast(str, self._myconf.take('social.tweethash'))
            self._description = cast(str, self._myconf.take('app.description'))


    @abstractmethod
    def send_post(self, article_id: int, recommendation_id: int, posts_text: List[str]):
        ''' Send post to social network with general and specific account. Raise an exception if error to send post. '''
        pass


    def generate_post(self, db: DAL, article: Article, recommendation: Recommendation):
        text = self.__generate_post_text(db, article, recommendation)
        posts = self.__cut_post_text(text.strip())

        return posts


    def __cut_post_text(self, text: str) -> List[str]:
        posts = wrap(text, self._post_max_length - 4)
        for i, post in enumerate(posts[:-1]):
            posts[i] = post + '… 🔽'
        
        return posts


    def __get_user_name(self, user_id: int) -> str:
        user = User.get_by_id(self._db, user_id)

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


    def __get_recommenders_names(self, db: DAL, recommendation: Recommendation):
        press_reviews = Recommendation.get_co_recommenders(db, recommendation.id)
        names: List[str] = [self.__get_user_name(recommendation.recommender_id)]
        for press_review in press_reviews:
            if not press_review.contributor_id:
                continue
            recommender_name = self.__get_user_name(press_review.contributor_id)
            if recommender_name not in names:
                names.append(recommender_name)
        formatted_names = ', '.join(names)
        return (formatted_names[::-1].replace(',', ' and'[::-1], 1))[::-1] 


    def __get_reviewers_name(self, article_id: int) -> str:
        reviews = Review.get_by_article_id_and_state(self._db, article_id, ReviewState.REVIEW_COMPLETED)
        nb_anonymous = 0
        names: List[str] = []
        user_id: List[int] = []
        for review in reviews:
            if not review.anonymously and review.reviewer_id not in user_id:
                names.append(self.__get_user_name(review.reviewer_id))
                if review.reviewer_id:
                    user_id.append(review.reviewer_id)
        
        user_id.clear()

        for review in reviews:
            if review.anonymously and review.reviewer_id not in user_id:
                nb_anonymous += 1
                if review.reviewer_id:
                    user_id.append(review.reviewer_id)
        
        if (nb_anonymous > 0):
            anonymous = str(nb_anonymous) + ' anonymous reviewer'
            if (nb_anonymous > 1):
                anonymous += 's'
            names.append(anonymous)
            
        formatted_names = ', '.join(names)

        return (formatted_names[::-1].replace(',', ' and'[::-1], 1))[::-1] 
    

    def __generate_post_text(self, db: DAL, article: Article, recommendation: Recommendation) -> str:
        line1 = f'A new #preprint #OpenScience #PeerReview by @{self._tweethash}: {article.authors} ({article.article_year}) {article.title}. {article.preprint_server}, ver. {article.ms_version} peer-reviewed and recommended by {self._description}. {article.doi} '
        line2 = f'recommended by {self.__get_recommenders_names(db, recommendation)} for @{self._tweethash} based on published reviews by {self.__get_reviewers_name(article.id)} #OpenScience https://doi.org/{generate_recommendation_doi(article.id)}'
        return line1 + line2


    def get_posts_from_db(self, article_id: int, recommendation_id: int):
        return Post.get_posts_from_db(self._db, self._table_name, article_id, recommendation_id)
    

    def has_already_posted(self, article_id: int, recommendation_id: int):
        return Post.has_already_posted(self._db, self._table_name, article_id, recommendation_id)
    

    def _save_posts_in_db(self, post: Post):
        return Post.save_posts_in_db(self._db, self._table_name, post)
