# -*- coding: utf-8 -*-

import re
import copy
import datetime

from gluon.contrib.markdown import WIKI

from app_modules.helper import *

from controller_modules import user_module
from app_modules import common_small_html
from app_components import app_forms
from app_modules import emailing

# frequently used constants
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)


######################################################################################################################################################################
@auth.requires_login()
def validate_ethics():
    theUser = db.auth_user[auth.user_id]
    if "ethics_approved" in request.vars:
        theUser.ethical_code_approved = True
        theUser.update_record()
    _next = None
    if "_next" in request.vars:
        _next = request.vars["_next"]
    if _next:
        redirect(_next)
    else:
        redirect(URL("default", "index"))


######################################################################################################################################################################
@auth.requires_login()
def do_cancel_article():
    articleId = request.vars["articleId"]
    if articleId is None:
        raise HTTP(404, "404: " + T("Unavailable"))  # Forbidden access
    art = db.t_articles[articleId]
    if art is None:
        raise HTTP(404, "404: " + T("Unavailable"))  # Forbidden access
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if art.user_id != auth.user_id:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        art.status = "Cancelled"
        art.update_record()
        session.flash = T("Preprint submission cancelled")
        redirect(URL(c="user", f="my_articles", user_signature=True))


######################################################################################################################################################################
@auth.requires_login()
def suggest_article_to():
    articleId = int(request.vars["articleId"])
    recommenderId = int(request.vars["recommenderId"])
    exclude = request.vars["exclude"]
    myVars = request.vars
    user_module.do_suggest_article_to(auth, db, articleId, recommenderId)
    excludeList = exclude.split(",") if exclude else []
    excludeList.append(str(recommenderId))
    myVars["exclude"] = ",".join(excludeList)
    session.flash = T('Suggested recommender "%s" added.') % common_small_html.mkUser(auth, db, recommenderId).flatten()
    # redirect(request.env.http_referer)
    # redirect(URL(c='user', f='add_suggested_recommender', vars=dict(articleId=articleId), user_signature=True))
    # redirect(URL(c='user', f='search_recommenders', vars=dict(articleId=articleId, exclude=excludeList), user_signature=True))
    redirect(URL(c="user", f="search_recommenders", vars=myVars, user_signature=True))

######################################################################################################################################################################
@auth.requires_login()
def exclude_article_from():
    articleId = int(request.vars["articleId"])
    recommenderId = int(request.vars["recommenderId"])
    exclude = request.vars["exclude"]
    myVars = request.vars
    user_module.do_exclude_article_from(auth, db, articleId, recommenderId)
    excludeList = exclude if type(exclude) is list else [ exclude ]
    excludeList.append(str(recommenderId))
    myVars["exclude"] = excludeList
    session.flash = T('Recommender "%s" excluded from article.') % common_small_html.mkUser(auth, db, recommenderId).flatten()
    redirect(URL(c="user", f="search_recommenders", vars=myVars, user_signature=True))


######################################################################################################################################################################
@auth.requires_login()
def del_suggested_recommender():
    suggId = request.vars["suggId"]
    if suggId:
        if db((db.t_suggested_recommenders.id == suggId) & (db.t_articles.id == db.t_suggested_recommenders.article_id) & (db.t_articles.user_id == auth.user_id)).count() > 0:
            db((db.t_suggested_recommenders.id == suggId)).delete()
    redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires_login()
def del_excluded_recommender():
    exclId = request.vars["exclId"]
    if exclId:
        if db((db.t_excluded_recommenders.id == exclId) & (db.t_articles.id == db.t_excluded_recommenders.article_id) & (db.t_articles.user_id == auth.user_id)).count() > 0:
            db((db.t_excluded_recommenders.id == exclId)).delete()
    redirect(request.env.http_referer)

######################################################################################################################################################################
@auth.requires_login()
def article_revised():
    articleId = request.vars["articleId"]
    if articleId is None:
        raise HTTP(404, "404: " + T("Unavailable"))  # Forbidden access
    art = db.t_articles[articleId]
    if art is None:
        raise HTTP(404, "404: " + T("Unavailable"))  # Forbidden access
    # NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
    if not ((art.user_id == auth.user_id or auth.has_membership(role="manager")) and art.status == "Awaiting revision"):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        # print('article_revised')
        art.status = "Under consideration"
        art.update_record()
        last_recomm = db(db.t_recommendations.article_id == art.id).select(orderby=db.t_recommendations.id).last()
        last_recomm.is_closed = True
        last_recomm.update_record()
        newRecomm = db.t_recommendations.insert(
            article_id=art.id,
            recommender_id=last_recomm.recommender_id,
            no_conflict_of_interest=last_recomm.no_conflict_of_interest,
            doi=art.doi,
            ms_version=art.ms_version,
            is_closed=False,
            recommendation_state="Ongoing",
            recommendation_title=None,
        )
        # propagate co-recommenders
        corecommenders = db(db.t_press_reviews.recommendation_id == last_recomm.id).select(db.t_press_reviews.contributor_id)
        if len(corecommenders) > 0:
            # NOTE: suspend emailing trigger declared as : db.t_press_reviews._after_insert.append(lambda s,i: newPressReview(s,i))
            db.t_press_reviews._after_insert = []
            for corecommender in corecommenders:
                db.t_press_reviews.validate_and_insert(recommendation_id=newRecomm.id, contributor_id=corecommender.contributor_id)
        redirect(URL(c="user", f="my_articles", user_signature=True))


######################################################################################################################################################################
@auth.requires_login()
def do_accept_new_review():
    if "reviewId" not in request.vars:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    reviewId = request.vars["reviewId"]
    if isinstance(reviewId, list):
        reviewId = reviewId[1]
    theUser = db.auth_user[auth.user_id]
    if "ethics_approved" in request.vars and theUser.ethical_code_approved is False:
        theUser.ethical_code_approved = True
        theUser.update_record()
    if not (theUser.ethical_code_approved):
        raise HTTP(403, "403: " + T("ERROR: Ethical code not approved"))
    if "no_conflict_of_interest" not in request.vars:
        raise HTTP(403, "403: " + T('ERROR: Value "no conflict of interest" missing'))
    noConflict = request.vars["no_conflict_of_interest"]
    if noConflict != "yes":
        raise HTTP(403, "403: " + T("ERROR: No conflict of interest not checked"))
    rev = db.t_reviews[reviewId]
    if rev is None:
        raise HTTP(404, "404: " + T("ERROR: Review unavailable"))
    if rev.reviewer_id != auth.user_id:
        raise HTTP(403, "403: " + T("ERROR: Forbidden access"))
    rev.review_state = "Awaiting review"
    rev.no_conflict_of_interest = True
    rev.acceptation_timestamp = datetime.datetime.now()
    rev.anonymous_agreement=request.vars["anonymous_agreement"] or False
    rev.update_record()
    # email to recommender sent at database level
    recomm = db.t_recommendations[rev.recommendation_id]
    redirect(URL(c="user", f="recommendations", vars=dict(articleId=recomm.article_id)))
    # redirect(URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), user_signature=True))


######################################################################################################################################################################
@auth.requires_login()
def decline_new_review():
    if "reviewId" not in request.vars:
        raise HTTP(404, "404: " + T("Unavailable"))
    reviewId = request.vars["reviewId"]
    rev = db.t_reviews[reviewId]
    if rev is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    if rev.reviewer_id != auth.user_id:
        session.flash = T("Unauthorized", lazy=False)
        redirect(URL(c="user", f="my_reviews"))

    if rev["review_state"] in ["Declined", "Declined manually", "Review completed", "Cancelled"]:
        recomm = db((db.t_recommendations.id == rev["recommendation_id"])).select(db.t_recommendations.ALL).last()
        session.flash = T("Review state has been changed")
        redirect(URL(c="user", f="recommendations", vars=dict(articleId=recomm["article_id"])))

    # db(db.t_reviews.id==reviewId).delete()
    rev.review_state = "Declined"
    rev.update_record()
    # email to recommender sent at database level
    redirect(URL(c="user", f="my_reviews", vars=dict(pendingOnly=True), user_signature=True))


######################################################################################################################################################################
def decline_review(): # no auth required
    review, message = _check_decline_review_request()

    if review:
        message = A(
                T("Please click to confirm review decline"),
                _class="pci-decline-review-confirm btn btn-warning",
                _href=URL(f="decline_review_confirmed", vars=request.vars),
        )

    return _decline_review_page(message, form=None)


def _check_decline_review_request():
    reviewId = request.vars["id"]
    quickDeclineKey = request.vars["key"]

    review = db.t_reviews[reviewId]

    if review is None:
        message = "Review '{}' not found".format(reviewId)
    elif review["review_state"] in ["Declined", "Declined manually", "Review completed", "Cancelled"]:
        message = T("You have already declined this invitation to review")
    elif review.quick_decline_key != quickDeclineKey:
        message = "Incorrect decline key: '{}'".format(quickDeclineKey)
    else:
        message = None

    if message:
        review = None

    return review, message


def decline_review_confirmed(): # no auth required
    review, message = _check_decline_review_request()
    form = None
    if review:
        review.review_state = "Declined"
        review.update_record()

        user = db.auth_user[review.reviewer_id]
        if user and user.reset_password_key: # user (auto-created) did not register yet
            db(db.auth_user.id == review.reviewer_id).delete()

        message = T("Thank you for taking the time to decline this invitation!")
        form = app_forms.getSendMessageForm(review.quick_decline_key)

    return _decline_review_page(message, form)


def _decline_review_page(message, form):
    response.view = "default/info.html"
    return dict(
        message=CENTER(
            H4(message, _class="decline-review-title"),
            form if form else DIV(_style="height: 20em;"),
        )
    )

def send_suggested_reviewers():
    text = request.post_vars.suggested_reviewers_text
    review = db(db.t_reviews.quick_decline_key == request.post_vars.declineKey).select().last()
    no_suggestions_clicked = request.post_vars.noluck

    if not text.strip() or not review or no_suggestions_clicked:
        redirect(URL(c="default", f="index"))

    emailing.send_to_recommender_reviewers_suggestions(session, auth, db, review, text)

    response.view = "default/info.html"
    return dict(message=H4(T("Thank you for your suggestion!")), _class="decline-review-title")


######################################################################################################################################################################
@auth.requires_login()
def do_ask_to_review():
    if "articleId" not in request.vars:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    if isinstance(articleId, list):
        articleId = articleId[1]

    article = db.t_articles[articleId]
    if not (article.is_searching_reviewers):
        raise HTTP(403, "403: " + T("ERROR: The recommender is not searching for reviewers"))
    if article.user_id == auth.user_id:
        raise HTTP(403, "403: " + T("ERROR: You are the submitter this article"))

    theUser = db.auth_user[auth.user_id]
    if "ethics_approved" in request.vars and theUser.ethical_code_approved is False:
        theUser.ethical_code_approved = True
        theUser.update_record()
    if not (theUser.ethical_code_approved):
        raise HTTP(403, "403: " + T("ERROR: Ethical code not approved"))
    if "no_conflict_of_interest" not in request.vars:
        raise HTTP(403, "403: " + T('ERROR: Value "no conflict of interest" missing'))
    noConflict = request.vars["no_conflict_of_interest"]
    if noConflict != "yes":
        raise HTTP(403, "403: " + T("ERROR: No conflict of interest not checked"))
    recomm = db(db.t_recommendations.article_id == articleId).select(
                orderby=db.t_recommendations.id).last()
    amIReviewer = auth.user_id in user_module.getReviewers(recomm, db)

    if amIReviewer:
        raise HTTP(403, "403: " + T("ERROR: Already reviewer on this article"))
    
    if recomm.recommender_id == auth.user_id:
        raise HTTP(403, "403: " + T("ERROR: You are the recommender this article"))

    reviewerId = request.vars.reviewerId

    revId = db.t_reviews.update_or_insert(
        recommendation_id=recomm.id,
        reviewer_id=theUser.id,
        review_state="Willing to review",
        no_conflict_of_interest=True,
        acceptation_timestamp=datetime.datetime.now(),
        anonymous_agreement=request.vars["anonymous_agreement"] or False,
    )

    # email to recommender sent at database level
    redirect(URL(c="user", f="recommendations", vars=dict(articleId=recomm.article_id)))


######################################################################################################################################################################
@auth.requires_login()
def review_completed():
    if "reviewId" not in request.vars:
        raise HTTP(404, "404: " + T("Unavailable"))
    reviewId = request.vars["reviewId"]
    rev = db.t_reviews[reviewId]
    if rev is None:
        raise HTTP(404, "404: " + T("Unavailable"))
    if rev.reviewer_id != auth.user_id:
        session.flash = T("Unauthorized", lazy=False)
        redirect(URL(c="user", f="my_reviews"))
    rev.review_state = "Review completed"
    rev.update_record()
    # email to recommender sent at database level
    redirect(URL(c="user", f="my_reviews"))



@auth.requires_login()
def delete_recommendation_file():
    response.view = "default/myLayout.html"

    if not ("recommId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    
    recomm = db.t_recommendations[request.vars.recommId]

    if recomm is None:
        session.flash = T("Unavailable")
        redirect(request.env.http_referer)
    
    art = db.t_articles[recomm.article_id]
    if not ((art.user_id == auth.user_id or auth.has_membership(role="manager")) and (art.status == "Awaiting revision")):
        session.flash = T("Unauthorized", lazy=False)
        redirect(URL(c="user", f="my_articles"))

    if not ("fileType" in request.vars):
        session.flash = T("Unavailable")
        redirect(request.env.http_referer)
    else:
        print(request.vars.fileType)
        if request.vars.fileType == "reply_pdf":
            recomm.reply_pdf = None
            recomm.reply_pdf_data = None
            recomm.update_record()
        elif request.vars.fileType == "track_change":
            recomm.track_change = None
            recomm.track_change_data = None
            recomm.update_record()
        else:
            session.flash = T("Unavailable")
            redirect(request.env.http_referer)

    session.flash = T("File successfully deleted")
    
    redirect(request.env.http_referer)



@auth.requires_login()
def delete_review_file():
    if "reviewId" not in request.vars:
        raise HTTP(404, "404: " + T("ID Unavailable"))
    reviewId = request.vars["reviewId"]

    review = db.t_reviews[reviewId]
    if review is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    recomm = db.t_recommendations[review.recommendation_id]
    if recomm is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    art = db.t_articles[recomm.article_id]
    # Check if article have correct status
    if review.reviewer_id != auth.user_id or review.review_state != "Awaiting review" or art.status != "Under consideration":
        session.flash = T("Unauthorized", lazy=False)
        redirect(URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True))
    # Check if article is Scheduled submission without doi
    elif scheduledSubmissionActivated and art.doi is None and art.scheduled_submission_date is not None:
        session.flash = T("Unauthorized", lazy=False)
        redirect(URL(c="user", f="recommendations", vars=dict(articleId=art.id), user_signature=True))

    if not ("fileType" in request.vars):
        session.flash = T("Unavailable")
        redirect(request.env.http_referer)
    else:
        print(request.vars.fileType)
        if request.vars.fileType == "review_pdf":
            review.review_pdf = None
            review.review_pdf_data = None
            review.update_record()
        else:
            session.flash = T("Unavailable")
            redirect(request.env.http_referer)

    session.flash = T("File successfully deleted")
    
    redirect(request.env.http_referer)

######################################################################################################################################################################
## (gab) Unused ?
######################################################################################################################################################################
# @auth.requires_login()
# def do_delete_article():
# 	articleId = request.vars['articleId']
# 	if articleId is None:
# 		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
# 	art = db.t_articles[articleId]
# 	if art is None:
# 		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
# 	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
# 	if art.user_id != auth.user_id:
# 		session.flash = auth.not_authorized()
# 		redirect(request.env.http_referer)
# 	else:
# 		db(db.t_articles.id == articleId).delete()
# 		session.flash = T('Preprint submission deleted')
# 		redirect(URL(c='user', f='my_articles', user_signature=True))


# ######################################################################################################################################################################
# def suggest_article_to_all(articleId, recommenderIds):
# 	added = []
# 	for recommenderId in recommenderIds:
# 		do_suggest_article_to(auth, db, articleId, recommenderId)
# 		added.append(common_small_html.mkUser(auth, db, recommenderId))
# 	#redirect(URL(c='user', f='add_suggested_recommender', vars=dict(articleId=articleId), user_signature=True))
# 	session.flash = T('Suggested recommenders %s added.') % (', '.join(added))
# 	redirect(request.env.http_referer)
