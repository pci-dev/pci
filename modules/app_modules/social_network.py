from abc import ABCMeta, abstractmethod
from textwrap import wrap
from typing import List, Union, cast
from gluon.contrib.appconfig import AppConfig
from pydal.base import DAL
from pydal.objects import Row, Rows
from pydal.objects import Table

from app_modules.common_tools import generate_recommendation_doi


class SocialNetwork(metaclass=ABCMeta):
    
    TABLE_NAME: str
    POST_MAX_LENGTH: int

    def __init__(self, db: DAL, post_max_length: int, table_name: str):
            self._post_max_length = post_max_length
            self._table_name = table_name

            self._myconf = AppConfig(reload=True)
            self._db = db

            self._tweethash = cast(str, self._myconf.take('social.tweethash'))
            self._description = cast(str, self._myconf.take('app.description'))


    @abstractmethod
    def send_post(self, article_id: int, recommendation_id: int, posts_text: List[str]) -> Union[str, None]:
        ''' Return text error if error, or None if all is ok'''
        pass


    def generate_post(self, article: Row, recommendation: Row):
        text = self.__generate_post_text(article, recommendation)
        posts = self.__cut_post_text(text.strip())

        return posts


    def __cut_post_text(self, text: str) -> List[str]:
        posts = wrap(text, self._post_max_length - 3)
        for i, post in enumerate(posts[:-1]):
            posts[i] = post + '… 🔽'
        
        return posts


    def __get_user_name(self, user_id: int) -> str:
        user = self._db.auth_user[user_id]

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


    def __get_reviewers_name(self, recommendation_id: int) -> str:
        reviews = cast(Rows, self._db(self._db.t_reviews.recommendation_id == recommendation_id).select())
        nb_anonymous = 0
        names: List[str] = []
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
    

    def __generate_post_text(self, article: Row, recommendation: Row) -> str:
        line1 = f'A new #preprint #OpenScience #PeerReview by @{self._tweethash}: {article.authors} ({article.article_year}) {article.title}. {article.preprint_server}, ver. {article.ms_version} peer-reviewed and recommended by {self._description}. {article.doi} '
        line2 = f'recommended by {self.__get_user_name(recommendation.recommender_id)} for @{self._tweethash} based on published reviews by {self.__get_reviewers_name(recommendation.id)} #OpenScience https://doi.org/{generate_recommendation_doi(article.id)}'
        return line1 + line2

    
    def get_posts_from_db(self, article_id: int, recommendation_id: int) -> Rows:
        table = cast(Table, self._db[self._table_name])
        return self._db((table.article_id == article_id) & (table.recommendation_id == recommendation_id)).select(orderby=table.thread_position)
    

    def has_already_posted(self, article_id: int, recommendation_id: int) -> bool:
        return len(self.get_posts_from_db(article_id, recommendation_id)) > 0


    def _save_posts_in_db(self, post_id: int, text_content: str, position: int, article_id: int, recommendation_id: int, parent_id: Union[int,None]) -> int:
        table = cast(Table, self._db[self._table_name])
        id = cast(int, table.insert(post_id=post_id, # À changer
                        text_content=text_content, 
                        thread_position=position, 
                        article_id=article_id,
                        recommendation_id=recommendation_id,
                        parent_id=parent_id
                        ))
        self._db.commit()
        return id
