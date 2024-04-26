# -*- coding: utf-8 -*-
import re
import copy
import datetime
from dateutil.relativedelta import *
from gluon.utils import web2py_uuid
from gluon.contrib.markdown import WIKI

from gluon import current
from gluon.html import *
from gluon.contrib.appconfig import AppConfig

from app_modules.helper import *

from app_modules import common_small_html
from app_modules import emailing

# frequently used constants
myconf = AppConfig(reload=True)
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)


######################################################################################################################################################################
## Recommender Module
#######################################################################################################################################################################
def mkViewEditArticleRecommenderButton(row):
    db, auth = current.db, current.auth
    return A(
        SPAN(current.T("View"), _class="buttontext btn btn-default pci-button pci-recommender"),
        _href=URL(c="recommender", f="article_details", vars=dict(articleId=row.id)),
        _class="button",
    )


######################################################################################################################################################################
def reopen_review(ids):
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
def mkSuggestReviewToButton(row, recommId, myGoal, reg_user=False):
    db, auth = current.db, current.auth
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
def mkOtherContributors(row):
    db, auth = current.db, current.auth
    butts = []
    hrevs = []
    revs = db(db.t_press_reviews.recommendation_id == row.id).select()
    for rev in revs:
        if rev.contributor_id:
            if rev.contributor_id != auth.user_id:
                hrevs.append(LI(common_small_html.mkUserWithMail(rev.contributor_id)))
        else:
            hrevs.append(LI(I(current.T("not registered"))))
    butts.append(UL(hrevs, _class="pci-inCell-UL"))
    return butts


######################################################################################################################################################################
def mkRecommendationFormat(row):
    db, auth = current.db, current.auth
    recommender = db(db.auth_user.id == row.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
    if recommender:
        recommFmt = SPAN("%s %s" % (recommender.first_name, recommender.last_name))
    else:
        recommFmt = ""
    art = db.t_articles[row.article_id]
    anchor = SPAN(common_small_html.md_to_html(row.recommendation_title), BR(), B(current.T("Recommender:") + " "), recommFmt, BR(), common_small_html.mkDOI(row.doi),)
    return anchor

def cancel_scheduled_reviews(session, auth, db, articleId):
    recomm = db.get_last_recomm(articleId)
    pendingReviews =  db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state in ("Awaiting review", "Awaiting response"))).select(orderby=db.t_reviews.id)
    for review in pendingReviews:
        review.update_record(review_state="Cancelled")
        db.commit()


######################################################################################################################################################################
def mkEditResendButton(row, reviewId=None, recommId=None, articleId=None, urlFunction=None, urlController=None):
    db, auth = current.db, current.auth
    anchor = A(
        SPAN(current.T("Edit and Resend"), _class="buttontext btn btn-default pci-recommender"),
        _href=URL(c="recommender_actions", f="edit_resend_auth", vars=dict(mailId=row["id"], reviewId=reviewId, recommId=recommId, articleId=articleId, urlFunction=urlFunction, urlController=urlController)),
        _class="button",
    )
    return anchor

