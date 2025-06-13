# -*- coding: utf-8 -*-
from typing import Literal, Union
from dateutil.relativedelta import *

from gluon import current
from gluon.html import *
from gluon.contrib.appconfig import AppConfig # type: ignore

from app_modules.helper import *

from app_modules import common_small_html
from models.article import Article
from models.mail_queue import MailQueue
from models.user import User

# frequently used constants
myconf = AppConfig(reload=True)
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)


######################################################################################################################################################################
## Recommender Module
#######################################################################################################################################################################
def mkViewEditArticleRecommenderButton(article: Article):
    return A(
        SPAN(current.T("View"), _class="buttontext btn btn-default pci-button pci-recommender"),
        _href=URL(c="recommender", f="article_details", vars=dict(articleId=article.id)),
        _class="button",
    )


######################################################################################################################################################################
def reopen_review(ids: List[int]):
    db, auth = current.db, current.auth
    if auth.has_membership(role="manager"):
        for myId in ids:
            rev = db.t_reviews[myId]
            if rev.review_state != "Awaiting review":
                rev.review_state = "Awaiting review"
                rev.update_record()
    elif auth.has_membership(role="recommender"):
        for myId in ids:
            rev = db.t_reviews[myId]
            recomm = db.t_recommendations[rev.recommendation_id]
            if (recomm.recommender_id == auth.user_id) and not (rev.review_state == "Awaiting review"):
                rev.review_state = "Awaiting review"
                rev.update_record()


######################################################################################################################################################################
# From common.py
######################################################################################################################################################################
def mkSuggestReviewToButton(row: User, recommId: int, myGoal: Union[Literal['4review'], Literal['4press']], reg_user: bool = False):
    if myGoal == "4review":
        anchor = A(
            SPAN(current.T("Prepare an invitation"), _class="buttontext btn btn-default pci-recommender"),
            _href=URL(c="recommender_actions", f="suggest_review_to", vars=dict(recommId=recommId, reviewerId=row["id"], regUser=reg_user), user_signature=True),
            _class="button",
        )
    elif myGoal == "4press":
        anchor = A(
            SPAN(current.T("Suggest"), _class="buttontext btn btn-default pci-recommender"),
            _href=URL(c="recommender_actions", f="suggest_collaboration_to", vars=dict(recommId=recommId, reviewerId=row["id"]), user_signature=True),
            _class="button",
        )
    else:
        anchor = ""
    return anchor


######################################################################################################################################################################
def mkOtherContributors(row: Recommendation):
    auth = current.auth
    butts: List[UL] = []
    hrevs: List[LI] = []
    revs = Recommendation.get_co_recommenders(row.id)
    for rev in revs:
        if rev.contributor_id:
            if rev.contributor_id != auth.user_id:
                hrevs.append(LI(common_small_html.mkUserWithMail(rev.contributor_id)))
        else:
            hrevs.append(LI(I(current.T("not registered"))))
    butts.append(UL(hrevs, _class="pci-inCell-UL"))
    return butts


######################################################################################################################################################################
def mkRecommendationFormat(row: Recommendation):
    db = current.db
    recommender = db(db.auth_user.id == row.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
    if recommender:
        recommFmt = SPAN("%s %s" % (recommender.first_name, recommender.last_name))
    else:
        recommFmt = ""
    anchor = SPAN(common_small_html.md_to_html(row.recommendation_title), BR(), B(current.T("Recommender:") + " "), recommFmt, BR(), common_small_html.mkDOI(row.doi),)
    return anchor

def cancel_scheduled_reviews(articleId: int):
    db = current.db
    recomm = db.get_last_recomm(articleId)
    pendingReviews =  db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state in ("Awaiting review", "Awaiting response"))).select(orderby=db.t_reviews.id)
    for review in pendingReviews:
        review.update_record(review_state="Cancelled")
        db.commit()


######################################################################################################################################################################
def mkEditResendButton(row: MailQueue,
                       reviewId: Optional[int] = None,
                       recommId: Optional[int] = None,
                       articleId: Optional[int] = None,
                       urlFunction: Optional[str] = None,
                       urlController: Optional[str] = None):
    anchor = A(
        SPAN(current.T("Edit and Resend"), _class="buttontext btn btn-default pci-recommender"),
        _href=URL(c="recommender_actions", f="edit_resend_auth", vars=dict(mailId=row["id"], reviewId=reviewId, recommId=recommId, articleId=articleId, urlFunction=urlFunction, urlController=urlController)),
        _class="button",
    )
    return anchor

