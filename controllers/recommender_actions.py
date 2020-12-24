# -*- coding: utf-8 -*-

import re
import copy
from dateutil.relativedelta import *
from gluon.utils import web2py_uuid
from gluon.contrib.markdown import WIKI
from gluon.html import markmin_serializer


from app_modules.helper import *


# frequently used constants
myconf = AppConfig(reload=True)
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
trgmLimit = myconf.take("config.trgm_limit") or 0.4


######################################################################################################################################################################
## Actions

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def do_cancel_press_review():
    recommId = request.vars["recommId"]
    if recommId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.t_recommendations[recommId]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    art = db.t_articles[recomm.article_id]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if recomm.recommender_id != auth.user_id:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        art.status = "Cancelled"
        art.update_record()
        redirect(URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=True)))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def del_contributor():
    pressId = request.vars["pressId"]
    if pressId:
        if auth.has_membership(role="recommender"):
            if (
                db(
                    (db.t_press_reviews.id == pressId) & (db.t_recommendations.id == db.t_press_reviews.recommendation_id) & (db.t_recommendations.recommender_id == auth.user_id)
                ).count()
                > 0
            ):
                db((db.t_press_reviews.id == pressId)).delete()
        if auth.has_membership(role="manager"):
            db((db.t_press_reviews.id == pressId)).delete()

    redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def do_accept_new_article_to_recommend():
    theUser = db.auth_user[auth.user_id]
    if "ethics_approved" in request.vars:
        theUser.ethical_code_approved = True
        theUser.update_record()
    if not (theUser.ethical_code_approved):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if "no_conflict_of_interest" not in request.vars:
        raise HTTP(403, "403: " + T("Forbidden"))
    noConflict = request.vars["no_conflict_of_interest"]
    if noConflict != "yes":
        raise HTTP(403, "403: " + T("Forbidden"))

    articleId = request.vars["articleId"]
    article = db.t_articles[articleId]

    if article.status == "Awaiting consideration":
        recommId = db.t_recommendations.insert(article_id=articleId, recommender_id=auth.user_id, doi=article.doi, recommendation_state="Ongoing", no_conflict_of_interest=True)
        db.commit()
        article = db.t_articles[articleId]  # reload due to trigger!
        article.status = "Under consideration"
        article.update_record()
        redirect(URL(c="recommender", f="reviewers", vars=dict(recommId=recommId)))
    else:
        if article.status == "Under consideration":
            lastRecomm = db((db.t_recommendations.article_id == articleId) & (db.t_recommendations.is_closed == False)).select(db.t_recommendations.ALL)
            if lastRecomm is not None and lastRecomm.id is not None:
                recommId = lastRecomm.id
                reviewersListSel = db((db.t_reviews.recommendation_id == recommId) & (db.t_reviews.reviewer_id == db.auth_user.id)).select(
                    db.t_reviews.id, db.t_reviews.review_state, db.auth_user.id
                )
                if len(reviewersListSel) == 0:
                    redirect(URL(c="recommender", f="reviewers", vars=dict(recommId=recommId)))
                else:
                    print("Bug (reviewersListSel) : " + reviewersListSel)
                    session.flash = T("Article no more available", lazy=False)
                    redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=articleId)))
            else:
                print("Bug (lastRecomm) : " + lastRecomm)
                session.flash = T("Article no more available", lazy=False)
                redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=articleId)))
        else:
            print("Bug (articleStatus) : " + article.status)
            session.flash = T("Article no more available", lazy=False)
            redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=articleId)))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def recommend_article():
    recommId = request.vars["recommId"]
    if recommId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.t_recommendations[recommId]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if recomm.recommender_id != auth.user_id:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        # recomm.is_closed=True # No: recomm closed when validated by managers
        recomm.recommendation_state = "Recommended"
        recomm.update_record()
        art = db.t_articles[recomm.article_id]
        art.status = "Pre-recommended"
        art.update_record()
        # db.commit()
        redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=recomm.article_id)))

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def reject_article():
    recommId = request.vars["recommId"]
    if recommId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.t_recommendations[recommId]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if recomm.recommender_id != auth.user_id:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        recomm.is_closed = True
        recomm.recommendation_state = "Rejected"
        recomm.update_record()
        art = db.t_articles[recomm.article_id]
        art.status = "Rejected"
        art.update_record()
        db.commit()
        redirect(URL("my_recommendations", vars=dict(pressReviews=False)))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def revise_article():
    recommId = request.vars["recommId"]
    if recommId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.t_recommendations[recommId]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if recomm.recommender_id != auth.user_id:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        # Do not close recommendation due to reply
        art = db.t_articles[recomm.article_id]
        art.status = "Awaiting revision"
        art.update_record()
        recomm.recommendation_state = "Awaiting revision"
        recomm.update_record()
        db.commit()
        redirect(URL("my_recommendations", vars=dict(pressReviews=False)))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def decline_new_article_to_recommend():
    articleId = request.vars["articleId"]
    if articleId is not None:
        # NOTE: No security hole as only logged user can be deleted
        sug_rec = db((db.t_suggested_recommenders.article_id == articleId) & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)).select().first()
        if sug_rec is not None:
            sug_rec.declined = True
            sug_rec.update_record()
            db.commit()
            session.flash = T("Suggestion declined")
    redirect(URL(c="recommender", f="my_awaiting_articles"))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def suggest_review_to():
    reviewerId = request.vars["reviewerId"]
    if reviewerId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recommId = request.vars["recommId"]
    if recommId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.t_recommendations[recommId]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if recomm.recommender_id != auth.user_id and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        revId = db.t_reviews.update_or_insert(recommendation_id=recommId, reviewer_id=reviewerId)
        redirect(URL(c="recommender", f="email_for_registered_reviewer", vars=dict(reviewId=revId)))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def suggest_collaboration_to():
    reviewerId = request.vars["reviewerId"]
    if reviewerId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recommId = request.vars["recommId"]
    if recommId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.t_recommendations[recommId]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if recomm.recommender_id != auth.user_id:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        db.t_press_reviews.update_or_insert(recommendation_id=recommId, contributor_id=reviewerId)
        redirect(URL("my_recommendations", vars=dict(pressReviews=True)))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def del_reviewer():
    reviewId = request.vars["reviewId"]
    if reviewId:
        if db((db.t_reviews.id == reviewId) & (db.t_recommendations.id == db.t_reviews.recommendation_id) & (db.t_recommendations.recommender_id == auth.user_id)).count() > 0:
            db((db.t_reviews.id == reviewId)).delete()
    redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender"))
def process_opinion():
    if "recommender_opinion" in request.vars and "recommId" in request.vars:
        ro = request.vars["recommender_opinion"]
        rId = request.vars["recommId"]
        if ro == "do_recommend":
            redirect(URL(c="recommender_actions", f="recommend_article", vars=dict(recommId=rId)))
        elif ro == "do_revise":
            redirect(URL(c="recommender_actions", f="revise_article", vars=dict(recommId=rId)))
        elif ro == "do_reject":
            redirect(URL(c="recommender_actions", f="reject_article", vars=dict(recommId=rId)))
    redirect(URL("my_recommendations", vars=dict(pressReviews=False)))


###############################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def add_recommender_as_reviewer():
    recommId = request.vars["recommId"]
    recomm = db.t_recommendations[recommId]
    if (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
    else:
        # check if review previously cancelled, then reopen
        reviews = db((db.t_reviews.reviewer_id == recomm.recommender_id) & (db.t_reviews.recommendation_id == recommId)).select()
        if len(reviews) > 0:
            for review in reviews:
                review.update_record(review_state="Awaiting review")
                db.commit()
        else:  # create review
            rid = db.t_reviews.validate_and_insert(
                recommendation_id=recommId, reviewer_id=recomm.recommender_id, no_conflict_of_interest=recomm.no_conflict_of_interest, review_state="Awaiting review"
            )
    redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def cancel_recommender_as_reviewer():
    recommId = request.vars["recommId"]
    if recommId:
        recomm = db.t_recommendations[recommId]
        if (recomm.recommender_id != auth.user_id) and not (auth.has_membership(role="manager")):
            session.flash = auth.not_authorized()
        else:
            reviews = db((db.t_reviews.reviewer_id == recomm.recommender_id) & (db.t_reviews.recommendation_id == recommId)).select()
            for review in reviews:
                if (recomm.recommender_id == auth.user_id) or (auth.has_membership(role="manager")):
                    review.update_record(review_state="Cancelled")
                    db.commit()
                else:
                    session.flash = auth.not_authorized()
    else:
        session.flash = auth.not_authorized()
    redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def accept_review_request():
    if "reviewId" not in request.vars:
        raise HTTP(404, "404: " + T("Unavailable"))
    reviewId = request.vars["reviewId"]
    rev = db.t_reviews[reviewId]
    if rev is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    if rev["review_state"] != "Willing to review":
        session.flash = T("Review state has been changed")
        redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=recomm["article_id"])))

    recomm = db((db.t_recommendations.id == rev["recommendation_id"])).select(db.t_recommendations.ALL).last()
    if recomm.recommender_id != auth.user_id:
        raise HTTP(404, "404: " + T("Unavailable"))

    # db(db.t_reviews.id==reviewId).delete()
    rev.review_state = "Awaiting review"
    rev.update_record()
    # email to recommender sent at database level
    redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=recomm["article_id"])))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def decline_review_request():
    if "reviewId" not in request.vars:
        raise HTTP(404, "404: " + T("Unavailable"))
    reviewId = request.vars["reviewId"]
    rev = db.t_reviews[reviewId]
    if rev is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    if rev["review_state"] != "Willing to review":
        session.flash = T("Review state has been changed")
        redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=recomm["article_id"])))

    recomm = db((db.t_recommendations.id == rev["recommendation_id"])).select(db.t_recommendations.ALL).last()
    if recomm.recommender_id != auth.user_id:
        raise HTTP(404, "404: " + T("Unavailable"))

    # db(db.t_reviews.id==reviewId).delete()
    rev.review_state = "Declined by recommender"
    rev.update_record()
    # email to recommender sent at database level
    redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=recomm["article_id"])))


######################################################################################################################################################################
def make_preprint_searching_for_reviewers():
    recommId = request.vars["recommId"]
    if recommId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    recomm = db.t_recommendations[recommId]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    if recomm.recommender_id != auth.user_id and not recomm.is_closed and not (auth.has_membership(role="administrator") or auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        art = db.t_articles[recomm.article_id]

        art.is_searching_reviewers = True
        art.update_record()
        db.commit()
        session.flash = 'Preprint now appear in the "In need of reviewers" list'
        redirect(request.env.http_referer)


######################################################################################################################################################################
def make_preprint_not_searching_for_reviewers():
    recommId = request.vars["recommId"]
    if recommId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    recomm = db.t_recommendations[recommId]
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    if recomm.recommender_id != auth.user_id and not recomm.is_closed and not (auth.has_membership(role="administrator") or auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        art = db.t_articles[recomm.article_id]
        art.is_searching_reviewers = False
        art.update_record()
        db.commit()
        session.flash = 'Preprint is removed from the "In need of reviewers" list'
        redirect(request.env.http_referer)
