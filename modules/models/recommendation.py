from __future__ import annotations # for self-ref param type Post in save_posts_in_db()
from datetime import datetime
from enum import Enum
import html
import re
import string
from typing import List, Optional as _, cast
from gluon.html import TAG
from models.pdf import PDF
from models.press_reviews import PressReview
from models.user import User
from pydal.objects import Row
from gluon import current


class RecommendationState(Enum):
    REJECTED = 'Rejected'
    AWAITING_REVISION = 'Awaiting revision'
    ONGOING = 'Ongoing'
    RECOMMENDED = 'Recommended'
    REVISION = 'Revision'


class Recommendation(Row):
    id: int
    article_id: int
    recommendation_comments: _[str]
    recommendation_timestamp: _[datetime]
    doi: _[str]
    recommender_id: int
    last_change: _[datetime]
    reply: _[str]
    is_closed: _[bool]
    is_press_review: _[bool]
    auto_nb_agreements: _[int]
    no_conflict_of_interest: _[bool]
    recommendation_title: _[str]
    recommendation_doi: _[str]
    recommendation_state: _[str]
    reply_pdf: _[str]
    reply_pdf_data: _[bytes]
    track_change: _[str]
    track_change_data: _[bytes]
    ms_version: _[str]
    recommender_file: _[str]
    recommender_file_data: _[bytes]
    author_last_change: _[datetime]
    validation_timestamp: _[datetime]


    @staticmethod
    def get_by_id(id: int):
        db = current.db
        return cast(_[Recommendation], db.t_recommendations[id])
    
    @staticmethod
    def get_by_article_id(article_id: int, order_by: ... = None):
        db = current.db
        if order_by:
            recommendations = db(db.t_recommendations.article_id == article_id).select(orderby=order_by)
        else:
            recommendations = db(db.t_recommendations.article_id == article_id).select()
        return cast(List[Recommendation], recommendations)


    @staticmethod
    def get_co_recommenders(recommendation_id: int):
        db = current.db
        return cast(List[PressReview], db((db.t_recommendations.id == recommendation_id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id))\
            .select(db.t_press_reviews.ALL, distinct=db.t_press_reviews.contributor_id))


    @staticmethod
    def get_current_round_number(recommendation: Recommendation):
        db = current.db
        return cast(int, db((db.t_recommendations.article_id == recommendation.article_id) & (db.t_recommendations.id <= recommendation.id)).count())
    

    @staticmethod
    def get_all(recommendation_states: List[RecommendationState] = []):
        db = current.db
        if len(recommendation_states) == 0:
            return cast(List[Recommendation], db().select(db.t_recommendations.ALL))
        else:
            states_values = [state.value for state in recommendation_states]
            return cast(List[Recommendation], db(db.t_recommendations.recommendation_state.belongs(states_values))
                        .select(orderby=db.t_recommendations.id))


    @staticmethod
    def get_last_pdf(recommendation_id: int) -> _[PDF]:
        db = current.db
        return db(db.t_pdf.recommendation_id == recommendation_id).select().last() 


    @staticmethod
    def get_recommenders_names(recommendation: Recommendation):
        press_reviews = Recommendation.get_co_recommenders(recommendation.id)
        names: List[str] = []
        recommender_name = User.get_name_by_id(recommendation.recommender_id)
        if recommender_name:
            names.append(recommender_name)
        for press_review in press_reviews:
            if not press_review.contributor_id:
                continue
            contributor_name = User.get_name_by_id(press_review.contributor_id)
            if contributor_name and contributor_name not in names:
                names.append(contributor_name)
        formatted_names = ', '.join(names)
        return (formatted_names[::-1].replace(',', ' and'[::-1], 1))[::-1] 


    @staticmethod
    def get_doi_id(recommendation: Recommendation):
        regex = re.search("([0-9]+$)", recommendation.recommendation_doi or "", re.IGNORECASE)
        if regex:
            return regex.group(1)


    @staticmethod
    def get_references(recommendation: Recommendation, remove_html_tag: bool = False):
        recommendation_text = recommendation.recommendation_comments or ''
        references: List[str] = []
        start_reference = False
        lines = recommendation_text.splitlines() 
        for line in lines:
            sub_lines = line.split('<br>&nbsp;<br>')
            for sub_line in sub_lines:
                line_text = _get_reference_line_text(sub_line)

                if not start_reference:
                    if line_text in ['reference', 'references']:
                        start_reference = True
                else:
                    if len(line_text) > 4:
                        if remove_html_tag:
                            sub_line = re.sub('<[^<]+?>', '', sub_line)
                            sub_line = html.unescape(sub_line)
                        else:
                            sub_line = re.sub('^<p>|</p>$', '', sub_line)
                        references.append(sub_line)

        return references


def _get_reference_line_text(line: str):
    try:
        line_text = str(TAG(line).flatten().lower().strip()) # type: ignore
    except:
        line_text = line
    line_text = line_text.translate(str.maketrans('', '', string.punctuation))
    return line_text
