# -*- coding: utf-8 -*-
from gluon import current, IS_IN_DB
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.tools import Mail
from gluon.sqlhtml import *
from gluon.contrib.appconfig import AppConfig

from app_modules import common_small_html

myconf = AppConfig(reload=True)

pciRRactivated = myconf.get("config.registered_reports", default=False)

######################################################################################################################################################################
def getReviewsSubTable(auth, db, response, request, recomm):
    art = db.t_articles[recomm.article_id]
    recomm_round = db((db.t_recommendations.article_id == recomm.article_id) & (db.t_recommendations.id <= recomm.id)).count()
    reviews = db(db.t_reviews.recommendation_id == recomm.id).select(
        db.t_reviews.reviewer_id, db.t_reviews.review_state, db.t_reviews.acceptation_timestamp, db.t_reviews.last_change, db.t_reviews._id, db.t_reviews.reviewer_details, orderby=~db.t_reviews.last_change
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
            reviewVars = dict(
                reviewer=TAG(review.reviewer_details) if review.reviewer_details else \
                         common_small_html.mkUserWithMail(auth, db, review.reviewer_id),
                status=common_small_html.mkReviewStateDiv(auth, db, review.review_state),
                lastChange=common_small_html.mkElapsedDays(review.last_change),
                actions=[],
            )
            reviewVars["actions"].append(dict(text=current.T("View e-mails"), link=URL(c="recommender", f="review_emails", vars=dict(reviewId=review.id))))
            reviewVars["actions"].append(dict(text=current.T("Prepare an e-mail"), link=URL(c="recommender", f="send_reviewer_generic_mail", vars=dict(reviewId=review.id))))

            if allowed_to_see_reviews and review.review_state == "Review completed":
                reviewVars["actions"].append(dict(text=current.T("See review"), link=URL(c="recommender", f="one_review", vars=dict(reviewId=review.id))))

            if review.review_state == "Willing to review":
                reviewVars["actions"].append(dict(text=current.T("Accept"), link=URL(c="recommender_actions", f="accept_review_request", vars=dict(reviewId=review.id))))
                reviewVars["actions"].append(dict(text=current.T("Decline"), link=URL(c="recommender_actions", f="decline_review_request", vars=dict(reviewId=review.id))))

            if review.review_state == "Awaiting review" and not (recomm.is_closed):
                reviewVars["actions"].append(
                        dict(text=current.T("Prepare a cancellation"), link=URL(c="recommender", f="send_review_cancellation", vars=dict(reviewId=review.id)))
                    )   

            if art.status in ("Under consideration", "Scheduled submission under consideration") and not (recomm.is_closed):
                if (review.reviewer_id == auth.user_id) and (review.review_state == "Awaiting review"):
                    reviewVars["actions"].append(dict(text=current.T("Write, edit or upload your review"), link=URL(c="user", f="edit_review", vars=dict(reviewId=review.id))))

                if (review.reviewer_id != auth.user_id) and ((review.review_state or "Awaiting response") == "Awaiting response"):
                    reviewVars["actions"].append(
                        dict(text=current.T("Prepare a cancellation"), link=URL(c="recommender", f="send_review_cancellation", vars=dict(reviewId=review.id)))
                    )
            if review.review_state == "Awaiting response" and art.status != "Recommended":
                reviewVars["actions"].append(
                    dict(
                        text=current.T("Decline invitation manually"), 
                        link=URL(c="recommender_actions", f="del_reviewer_with_confirmation", vars=dict(
                            reviewId=review.id, 
                            rediectUrl=URL(args=request.args, vars=request.get_vars)
                        ))
                    )
                )

            reviewList.append(reviewVars)
            if review.review_state == "Review completed":
                nbCompleted += 1
            if review.review_state == "Awaiting review":
                nbOnGoing += 1

    showDecisionLink = False
    writeDecisionLink = None
    inviteReviewerLink = None
    showSearchingForReviewersButton = None
    showRemoveSearchingForReviewersButton = None
    if (
        not (recomm.is_closed)
        and ((recomm.recommender_id == auth.user_id) or auth.has_membership(role="manager") or auth.has_membership(role="administrator"))
        and (art.status in ("Under consideration", "Scheduled submission under consideration"))
    ):
        inviteReviewerLink = URL(c="recommender", f="reviewers", vars=dict(recommId=recomm.id))

        showSearchingForReviewersButton = not art.is_searching_reviewers
        showRemoveSearchingForReviewersButton = art.is_searching_reviewers

        showDecisionLink = True
        if (nbCompleted >= 2 and nbOnGoing == 0) or recomm_round > 1 or (pciRRactivated):
            writeDecisionLink = URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id))

    roundNumber = recomm_round
    componentVars = dict(
        recommId=recomm.id,
        roundNumber=roundNumber,
        reviewList=reviewList,
        showDecisionLink=showDecisionLink,
        inviteReviewerLink=inviteReviewerLink,
        writeDecisionLink=writeDecisionLink,
        showSearchingForReviewersButton=showSearchingForReviewersButton,
        showRemoveSearchingForReviewersButton=showRemoveSearchingForReviewersButton,
        isArticleSubmitter=(art.user_id == auth.user_id),
    )

    return XML(response.render("components/review_sub_table.html", componentVars))
