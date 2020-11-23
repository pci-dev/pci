# -*- coding: utf-8 -*-
from gluon import current, IS_IN_DB
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.tools import Mail
from gluon.sqlhtml import *

from app_modules import common_small_html


######################################################################################################################################################################
def getReviewsSubTable(auth, db, response, recomm):
    art = db.t_articles[recomm.article_id]
    recomm_round = db((db.t_recommendations.article_id == recomm.article_id) & (db.t_recommendations.id <= recomm.id)).count()
    reviews = db(db.t_reviews.recommendation_id == recomm.id).select(
        db.t_reviews.reviewer_id, db.t_reviews.review_state, db.t_reviews.acceptation_timestamp, db.t_reviews.last_change, db.t_reviews._id, orderby=~db.t_reviews.last_change
    )
    nbUnfinishedReviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state.belongs("Awaiting response", "Awaiting review"))).count()
    isRecommenderAlsoReviewer = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.reviewer_id == recomm.recommender_id)).count()

    allowed_to_see_reviews = True
    if (nbUnfinishedReviews > 0) and (isRecommenderAlsoReviewer == 1):
        allowed_to_see_reviews = False

    nbCompleted = 0
    nbOnGoing = 0

    reviewList = []
    for review in reviews:
        if review.reviewer_id is not None:
            reviewVars = dict(
                reviewer=common_small_html.mkUserWithMail(auth, db, review.reviewer_id),
                status=common_small_html.mkReviewStateDiv(auth, db, review.review_state),
                lastChange=common_small_html.mkElapsedDays(review.last_change),
                actions=[],
            )
            reviewVars["actions"].append(dict(text=current.T("View e-mails"), link=URL(c="recommender", f="review_emails", vars=dict(reviewId=review.id))))
    
            if allowed_to_see_reviews and review.review_state == "Review completed":
                reviewVars["actions"].append(dict(text=current.T("See review"), link=URL(c="recommender", f="one_review", vars=dict(reviewId=review.id))))
    
            if art.status == "Under consideration" and not (recomm.is_closed):
                if (review.reviewer_id == auth.user_id) and (review.review_state == "Awaiting review"):
                    reviewVars["actions"].append(dict(text=current.T("Write, edit or upload your review"), link=URL(c="user", f="edit_review", vars=dict(reviewId=review.id))))
    
                if (review.reviewer_id != auth.user_id) and ((review.review_state or "Awaiting response") == "Awaiting response"):
                    reviewVars["actions"].append(
                        dict(text=current.T("Prepare a cancellation"), link=URL(c="recommender", f="send_review_cancellation", vars=dict(reviewId=review.id)))
                    )
    
            reviewList.append(reviewVars)
            if review.review_state == "Review completed":
                nbCompleted += 1
            if review.review_state == "Awaiting review":
                nbOnGoing += 1

    showDecisionLink = False
    writeDecisionLink = None
    inviteReviewerLink = None
    if (
        not (recomm.is_closed)
        and ((recomm.recommender_id == auth.user_id) or auth.has_membership(role="manager") or auth.has_membership(role="administrator"))
        and (art.status == "Under consideration")
    ):
        inviteReviewerLink = URL(c="recommender", f="reviewers", vars=dict(recommId=recomm.id))

        showDecisionLink = True
        if (nbCompleted >= 2 and nbOnGoing == 0) or recomm_round > 1:
            writeDecisionLink = URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id))

    roundNumber = recomm_round
    componentVars = dict(
        roundNumber=roundNumber, reviewList=reviewList, showDecisionLink=showDecisionLink, inviteReviewerLink=inviteReviewerLink, writeDecisionLink=writeDecisionLink
    )

    return XML(response.render("components/review_sub_table.html", componentVars))