from __future__ import annotations # for self-ref param type Post in save_posts_in_db()
from typing import List, Optional as _, cast
from pydal.objects import Row
from enum import Enum
from pydal.objects import Table
from gluon import current


class PostTable(Enum):
    TOOTS = 'toots'
    TWEETS = 'tweets'
    BLUESKY_POSTS = 'bluesky_posts'


class Post(Row):
    id: int
    post_id: int | str
    text_content: str
    thread_position: int
    article_id: int
    recommendation_id: int
    parent_id: _[int]


    def __init__(self, post_id: int | str, text_content: str, thread_position: int, article_id: int, recommendation_id: int, parent_id: _[int]):
        self.post_id = post_id
        self.text_content = text_content
        self.thread_position = thread_position
        self.article_id = article_id
        self.recommendation_id = recommendation_id
        self.parent_id = parent_id


    @staticmethod
    def get_posts_from_db(table_name: PostTable, article_id: int, recommendation_id: int):
        db = current.db
        table = cast(Post, db[table_name.value])
        return cast(List[Post], db((table.article_id == article_id) & (table.recommendation_id == recommendation_id)).select(orderby=table.thread_position, distinct=table.thread_position))


    @staticmethod
    def has_already_posted(table_name: PostTable, article_id: int, recommendation_id: int) -> bool:
        return len(Post.get_posts_from_db(table_name, article_id, recommendation_id)) > 0


    @staticmethod
    def save_posts_in_db(table_name: PostTable, post: Post) -> int:
        db = current.db
        table = cast(Table, db[table_name.value])
        id = cast(int, table.insert(post_id=post.post_id, # type: ignore
                        text_content=post.text_content,
                        thread_position=post.thread_position,
                        article_id=post.article_id,
                        recommendation_id=post.recommendation_id,
                        parent_id=post.parent_id
                        ))
        db.commit()
        return id
