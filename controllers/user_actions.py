# -*- coding: utf-8 -*-

import datetime
from typing import Optional, cast
from app_modules.common_tools import get_next, get_reset_password_key, get_review_id

from app_modules.helper import *

from controller_modules import user_module
from app_modules import common_small_html
from app_components import app_forms
from app_modules import emailing
from gluon.globals import Request
from gluon.http import redirect
from models.review import Review, ReviewState
from models.user import User
from pydal import DAL

db = cast(DAL, db)

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
    excludeList = exclude if type(exclude) is list else exclude.split(",")
    excludeList.append(str(recommenderId))
    myVars["exclude"] = ",".join(excludeList)
    session.flash = T('Suggested recommender "%s" added.') % common_small_html.mkUser(auth, db, recommenderId).flatten()
    # redirect(request.env.http_referer)
    # redirect(URL(c='user', f='add_suggested_recommender', vars=dict(articleId=articleId), user_signature=True))
    # redirect(URL(c='user', f='search_recommenders', vars=dict(articleId=articleId, exclude=excludeList), user_signature=True))
    redirect(URL(c="user", f="search_recommenders", vars=myVars, user_signature=True))

######################################################################################################################################################################
@auth.requires_login()
def suggest_all_selected():
    articleId = request.vars["articleId"]
    recommenderIds = request.vars["recommenderIds"]
    exclusionIds = request.vars["exclusionIds"]
    exclude = request.vars["exclude"]
    myVars = request.vars
    recommender_names = ''
    exclude_names = ''
    excludeList = exclude if type(exclude) is list else exclude.split(",")
    for recommenderId in recommenderIds.split(','):
        if recommenderId == '': continue
        recommender_names += common_small_html.mkUser(auth, db, recommenderId).flatten() + ', '
        user_module.do_suggest_article_to(auth, db, articleId, recommenderId)
        excludeList.append(str(recommenderId))
    for recommenderId in exclusionIds.split(','):
        if recommenderId == '': continue
        exclude_names += common_small_html.mkUser(auth, db, recommenderId).flatten() + ', '
        user_module.do_exclude_article_from(auth, db, articleId, recommenderId)
        excludeList.append(str(recommenderId))
    myVars["exclude"] = ",".join(excludeList)
    flash_news = ''
    if len(recommender_names) > 0:
        flash_news += 'Suggested recommenders "%s" added.'% recommender_names[:-2]
    if len(exclude_names) > 0:
        flash_news += ' Recommenders "%s" excluded from article.' % exclude_names[:-2]
    session.flash = T(flash_news)
    redirect(URL(c="user", f="search_recommenders", vars=myVars, user_signature=True))

######################################################################################################################################################################
@auth.requires_login()
def exclude_article_from():
    articleId = int(request.vars["articleId"])
    recommenderId = int(request.vars["recommenderId"])
    exclude = request.vars["exclude"]
    myVars = request.vars
    user_module.do_exclude_article_from(auth, db, articleId, recommenderId)
    excludeList = exclude if type(exclude) is list else exclude.split(",")
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
        if db(db.t_excluded_recommenders.excluded_recommender_id == exclId).count() > 0:
            db((db.t_excluded_recommenders.excluded_recommender_id == exclId)).delete()
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
    if not ((art.user_id == auth.user_id or auth.has_membership(role="manager")) and art.status in ("Awaiting revision", "Scheduled submission revision")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        if art.status == "Scheduled submission revision":
            art.update_record(status="Scheduled submission pending")
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

    # email to recommender sent at database level
    redirect(URL(c="user_actions", f="decline_review_confirmed", vars=dict(pendingOnly=True,key=rev.quick_decline_key,reviewId=rev.id), user_signature=True))


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
    if reviewId == None: reviewId = request.vars["reviewId"]
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
        form = app_forms.getSendMessageForm(review.quick_decline_key, 'decline')

    return _decline_review_page(message, form)


def _decline_review_page(message, form):
    response.view = "default/info.html"
    return dict(
        message=CENTER(
            P(message),
            form if form else DIV(_style="height: 20em;"),
        )
    )


def accept_review_confirmed(): # no auth required
    '''
    if reviewer accepts invitation, also ask them for more reviewer suggestions
    '''
    review_id = get_review_id(request)
    if not review_id:
        session.flash = current.T('No review id found')
        redirect(URL('default','index'))
        return
    
    review = Review.get_by_id(db, review_id)
    if not review:
        session.flash = current.T('No review found')
        redirect(URL('default','index'))
        return

    if auth.user_id:
        user = User.get_by_id(db, review.reviewer_id)
        if user and user.reset_password_key:
            db(db.auth_user.id == review.reviewer_id).delete()

    next = get_next(request)
    if next and review.suggested_reviewers_send:
        redirect(next)

    message = T("Thank you for agreeing to review this article!")
    form: FORM

    if review.review_state == ReviewState.AWAITING_REVIEW.value:
        form = app_forms.getSendMessageForm(review.quick_decline_key, 'accept', next)
        return _accept_review_page(message, form)
    elif review.review_state == ReviewState.DECLINED_BY_RECOMMENDER.value:
        return _declined_by_recommender_page()
    elif review.acceptation_timestamp:
        if not review.suggested_reviewers_send:
            if review.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value:
                next = URL(c="user_actions", f="suggestion_sent_page")
            form = app_forms.getSendMessageForm(review.quick_decline_key, 'accept', next)
        return _awaiting_recommender_response_page(message, form)


def send_suggestion_page():
    default_next =cast(str, URL(c="user_actions", f="suggestion_sent_page"))
    review_id = get_review_id(request)
    if not review_id:
        session.flash = current.T('No review id found')
        redirect(URL('default','index'))
        return
    
    review = Review.get_by_id(db, review_id)
    if not review:
        session.flash = current.T('No review found')
        redirect(URL('default','index'))
        return
    
    next = get_next(request)
    if review.suggested_reviewers_send:
        if next:
            redirect(next)
        else:
            redirect(default_next)

    if not next:
        next = default_next

    message = T("Thank you for agreeing to review this article!")
    form: FORM

    if review.review_state == ReviewState.AWAITING_REVIEW.value:
        form = app_forms.getSendMessageForm(review.quick_decline_key, 'accept', next)
        return _accept_review_page(message, form)
    elif review.review_state == ReviewState.DECLINED_BY_RECOMMENDER.value:
        return _declined_by_recommender_page()
    elif review.acceptation_timestamp:
        if not review.suggested_reviewers_send:
            if review.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value:
                if auth.user_id:
                    next = cast(str, URL(c="user_actions", f="suggestion_sent_page"))
            form = app_forms.getSendMessageForm(review.quick_decline_key, 'accept', next)
        return _awaiting_recommender_response_page(message, form)

    
def _declined_by_recommender_page():
    response.view = "default/info.html"
    return dict(
        message=CENTER(
            P(T("Following your request for a delay, the recommender decline your reviewing of the article."),
              _class="info-sub-text", _style="width: 800px")
        )
    )

def _awaiting_recommender_response_page(message: str, form: FORM):
    response.view = "default/info.html"
    return dict(
        message=CENTER(
            P(message, _style="font-size: initial; font-weight: bold"),
            P(T("Your request for a delay must be accepted by the recommender before you can review this article. An email will be sent to you after the recommender has made a decision."), _style="font-size: large; font-weight: bold; width: 800px"),
            form if form else DIV(_style="height: 20em;")
        )
    )

def _accept_review_page(message, form):
    '''
    if reviewer accepts invitation, also ask them for more reviewer suggestions
    '''
    response.view = "default/info.html"
    return dict(
        message=CENTER(
            P(message, _class="info-sub-text", _style="width: 800px"),
            form if form else DIV(_style="height: 20em;"),
        )
    )

def suggestion_sent_page():
    response.view = "default/info.html"
    return dict(
        message=CENTER(
            P(T("Thank you for agreeing to evaluate this submission and for any reviewer suggestions."),
              _class="info-sub-text", _style="width: 800px"),
            P(T("Your offer to review under an extended deadline must be accepted by the recommender before your role is confirmed. You will be informed via email as soon as the recommender has decided."),
              _class="info-sub-text", _style="width: 800px")
        )
    )


def send_suggested_reviewers():
    text = request.post_vars.suggested_reviewers_text
    review = db(db.t_reviews.quick_decline_key == request.post_vars.declineKey).select().last()
    no_suggestions_clicked = request.post_vars.noluck
    next = get_next(request)

    if not text.strip() or not review or no_suggestions_clicked or review.suggested_reviewers_send:
        Review.set_suggested_reviewers_send(review)
        if next:
            redirect(next)
        else:
            redirect(URL(c="default", f="index"))

    article = db((db.t_recommendations.id == review.recommendation_id) & (db.t_recommendations.article_id == db.t_articles.id)).select()
    add_suggest_reviewers_to_article(article, review, text)

    emailing.send_to_recommender_reviewers_suggestions(session, auth, db, review, text)
    Review.set_suggested_reviewers_send(review)

    response.view = "default/info.html"

    if next:
        session.flash = T('Thank you for your suggestion!')
        redirect(next)

    return dict(message=H4(T("Thank you for your suggestion!")), _class="decline-review-title")


def add_suggest_reviewers_to_article(article, review, text):
    '''
    Adds suggested reviewers to article
    '''
    reviewer = db(db.auth_user.id == review.reviewer_id).select()
    try: reviewer_name = common_small_html.mkUserNoSpan(auth, db, reviewer[0].id)
    except: reviewer_name = review.reviewer_details
    
    suggested_reviewers = article[0].t_articles.suggest_reviewers or []
    if type(suggested_reviewers) is str:
        suggested_reviewers = [suggested_reviewers] \
                                if suggested_reviewers else []

    for suggestion in text.split('\n'):
        if len(suggestion.strip()) > 0:
            suggested_reviewers.append('%s suggested: %s'%(reviewer_name, suggestion))
    article[0].t_articles.suggest_reviewers = suggested_reviewers
    article[0].t_articles.update_record()


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
        session.flash = T("Already reviewer on this article")
        redirect(URL(c="user", f="recommendations", vars=dict(articleId=recomm.article_id)))
        return
    
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
    elif scheduledSubmissionActivated and ((art.scheduled_submission_date is not None) or (art.status.startswith("Scheduled submission"))):
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
