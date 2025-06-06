# -*- coding: utf-8 -*-

from typing import Literal, cast
import datetime

from app_modules.helper import *
from app_modules import emailing
from app_components import app_forms
from gluon.http import HTTP, redirect # type: ignore
from gluon.sqlhtml import SQLFORM
from models.article import Article, ArticleStatus, is_scheduled_submission

from models.review import Review, ReviewState
from models.suggested_recommender import SuggestedRecommender, SuggestedBy
from models.user import User

from app_modules.common_tools import URL

request = current.request
session = current.session
db = current.db
auth = current.auth
response = current.response
T = current.T

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
    skip_checkbox = "skip_checkbox" in current.request.vars and str(current.request.vars["skip_checkbox"]).lower() == 'true' 
    current_user_id = int(auth.user_id)
    current_user = User.get_by_id(current_user_id)
    if not current_user:
        raise HTTP(404, "404: " + T("User not found"))
    
    if "ethics_approved" in request.vars:
        current_user.ethical_code_approved = True
        current_user.update_record() # type: ignore
    if not (current_user.ethical_code_approved):
        session.flash = auth.not_authorized()
        return redirect(request.env.http_referer)
    if not skip_checkbox:
        if "no_conflict_of_interest" not in request.vars:
            raise HTTP(403, "403: " + T("Forbidden"))
        no_conflict = cast(Literal['yes', 'no'], request.vars["no_conflict_of_interest"])
        if no_conflict != "yes":
            raise HTTP(403, "403: " + T("Forbidden"))

    article_id = int(request.vars["articleId"])
    article = Article.get_by_id(article_id)
    if not article:
        raise HTTP(404, "404: " + T("Article not found"))

    if article.status == ArticleStatus.AWAITING_CONSIDERATION.value:
        sugg_recommender = SuggestedRecommender.get_by_article_and_user_id(article_id, current.auth.user_id)
        if not sugg_recommender or not sugg_recommender.recommender_validated:
            emailing.send_manager_alert_willing_to_recommend(article_id)
            SuggestedRecommender.add_suggested_recommender(current.auth.user_id, article_id, SuggestedBy.THEMSELVES)
            return redirect(URL(c="recommender", f="validation_request_new_article_to_recommend", vars=dict(article_id=article_id)))
        else:
            recommendation_id = Article.create_new_recommendation_round(article, current_user_id)
            if is_scheduled_submission(article):
                emailing.create_reminders_for_submitter_scheduled_submission(article)
            return redirect(URL(c="recommender", f="reviewers", vars=dict(recommId=recommendation_id)))
    elif article.status == ArticleStatus.UNDER_CONSIDERATION.value:
        last_recommendation = (
                db((db.t_recommendations.article_id == article_id) & (db.t_recommendations.is_closed == False))
                .select(db.t_recommendations.ALL, orderby=db.t_recommendations.id).last()
        )
        if last_recommendation is not None and last_recommendation.id is not None:
            recommendation_id = last_recommendation.id
            reviewers_list_selection = db((db.t_reviews.recommendation_id == recommendation_id) & (db.t_reviews.reviewer_id == db.auth_user.id)).select(
                db.t_reviews.id, db.t_reviews.review_state, db.auth_user.id
            )
            if len(reviewers_list_selection) == 0:
                return redirect(URL(c="recommender", f="reviewers", vars=dict(recommId=recommendation_id)))
            else:
                session.flash = T("Article no more available", lazy=False)
                return redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=article_id)))
        else:
            session.flash = T("Article no more available", lazy=False)
            return redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=article_id)))
    else:
        session.flash = T("Article no more available", lazy=False)
        return redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=article_id)))

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

def decline_new_article_to_recommend():
    current.response.view = "default/info.html"

    url = URL(f="confirm_decline_new_article_to_recommend", vars=current.request.vars)

    return dict(
        message=CENTER(
            H2("To confirm your decline to act as", BR(), "a recommender for this submission, please click the button below",
               _style="margin-top: 20px; font-weight: bold; width: 550px"),
            A(
                "Please click here to confirm your decline",
                _class="btn btn-warning",
                _onclick=f'window.location.replace("{url}")',
            )
        )
    )


def confirm_decline_new_article_to_recommend():
    article_id = int(current.request.vars["articleId"])
    if not article_id:
        raise HTTP(404, "404: " + current.T("Unavailable"))
    
    if current.auth.user_id:
        suggested_recommender = SuggestedRecommender.get_by_article_and_user_id(article_id, current.auth.user_id)
    else:
        quick_decline_key = current.request.vars.get("quick_decline_key")
        if not quick_decline_key:
            raise HTTP(403, "403: " + current.T("Forbidden"))
        suggested_recommender = SuggestedRecommender.get_suggested_recommender_by_quick_decline_key(quick_decline_key)
    
    if not suggested_recommender:
        raise HTTP(404, "404: " + current.T("Unavailable"))
    
    if suggested_recommender.declined:
        current.session.flash = 'Already declined'
        redirect(URL('default','index'))
    
    SuggestedRecommender.decline(suggested_recommender)
    emailing.delete_reminder_for_one_suggested_recommender("#ReminderSuggestedRecommenderInvitation", article_id, suggested_recommender.suggested_recommender_id)
    
    current.session.flash = current.T("Suggestion declined")
    
    message = current.T("Thank you for taking the time to decline this invitation!")
    return _decline_article_page(message, article_id)


def _decline_article_page(message: str, article_id: int):
    T = current.T
    current.response.view = "default/myLayout.html"

    return dict(
        form=CENTER(
            H2(message, _style="font-weight: bold"),
            H4(T('There is nothing else to do.'), _style="font-weight: bold"),
            P(T('But if you want to send a message to the managing board to indicate the reason(s) why you prefer to decline this invitation to act as a recommender for this preprint, please click here to prepare (and then send) a message.'), _style="width: 800px"),
            A(T('Prepare a message to the managing board'), _href=URL(c="recommender_actions", f="decline_article_confirmed_send_message", vars=current.request.vars, user_signature=True), _class="btn btn-info")
        )
    )

######################################################################################################################################################################

def decline_article_confirmed_send_message():
    article_id = int(current.request.vars["articleId"])
    if not article_id:
        raise HTTP(404, "404: " + current.T("Unavailable"))
    
    if current.auth.user_id:
        suggested_recommender = SuggestedRecommender.get_by_article_and_user_id(article_id, current.auth.user_id)
    else:
        quick_decline_key = current.request.vars.get("quick_decline_key")
        if not quick_decline_key:
            raise HTTP(403, "403: " + current.T("Forbidden"))
        suggested_recommender = SuggestedRecommender.get_suggested_recommender_by_quick_decline_key(quick_decline_key)
    
    if not suggested_recommender:
        raise HTTP(404, "404: " + current.T("Unavailable"))
    
    form = app_forms.recommender_decline_invitation_form(article_id, suggested_recommender.suggested_recommender_id)
    if form:
        return _decline_article_send_message_page(form)


def _decline_article_send_message_page(form: SQLFORM):
    current.response.view = "default/myLayout.html"
    return dict(
        form=CENTER(
            DIV(LABEL(TAG(current.T("Recommender decline message 2")), _class="control-label col-sm-3", _style="margin-top: 30px"),
            _class="form-group"),
            form if form else DIV(_style="height: 20em;"),
        )
    )

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def suggest_review_to():
    reviewerId = request.vars["reviewerId"]
    new_round = request.vars["new_round"]
    new_stage = request.vars["new_stage"]
    reg_user = request.vars["regUser"]

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
    if recomm.recommender_id != auth.user_id and not is_co_recommender(recomm.id) and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        redirect(URL(c="recommender", f="email_for_registered_reviewer", vars=dict(recommId=recommId, reviewerId=reviewerId, new_round=new_round, new_stage=new_stage, regUser=reg_user)))


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
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def del_reviewer_with_confirmation():
    response.view = "default/myLayout.html"

    reviewId = request.vars["reviewId"]
    rediectUrl = request.vars["rediectUrl"]

    if reviewId and rediectUrl: 
        review = db(db.t_reviews.id == reviewId).select().last()
        reviewer = db(db.auth_user.id == review.reviewer_id).select().last()
        
        if review.review_state != "Awaiting response":
            redirect(request.env.http_referer)
            session.flas(T("Unauthorized"), lazy=False)
        # Show reviewer's cedentials
        if reviewer is not None:
            content = DIV(
                P(
                    B(T("Are you sure you want to decline this invitation in the name of ")),
                    B(reviewer.first_name),
                    " ",
                    B(reviewer.last_name),
                    " (",
                    I(reviewer.email),
                    ") ",
                    B("?"),
                    _style="text-align: center; font-size: 16px"
                )
            )
        else: 
            content = DIV(
                P(
                    B(T("Are you sure to decline this review of this ")),
                    I(T("[unknown user] ?")),
                    _style="text-align: center; font-size: 16px"
                )
            )

        form: ... = FORM.confirm(T('Decline this review'), {'Back': rediectUrl}) # type: ignore
        
        if form.accepted:
            if auth.has_membership(role="manager"):
                if db((db.t_reviews.id == reviewId) & (db.t_recommendations.id == db.t_reviews.recommendation_id)).count() > 0:
                    review.review_state = "Declined manually"
                    review.update_record()
            else:
                if db((db.t_reviews.id == reviewId) & (db.t_recommendations.id == db.t_reviews.recommendation_id) & (db.t_recommendations.recommender_id == auth.user_id)).count() > 0:
                    review.review_state = "Declined manually"
                    review.update_record()

            redirect(rediectUrl)

    
        return dict(content=content, form=DIV(form, _class="confirmation-form"))

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
            db.t_reviews.validate_and_insert(
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
def check_accept_decline_request():
    if "reviewId" not in request.vars:
        raise HTTP(404, "404: " + T("Unavailable"))
    reviewId = request.vars["reviewId"]
    rev = db.t_reviews[reviewId]
    if rev is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    recomm = db((db.t_recommendations.id == rev["recommendation_id"])).select(db.t_recommendations.ALL).last()
    if auth.has_membership(role="manager"):
        pass
    elif recomm.recommender_id != auth.user_id:
        raise HTTP(404, "404: " + T("Unavailable"))

    if rev["review_state"] != "Willing to review":
        session.flash = T("Review state has been changed")
        redirect_to_recommendations(recomm)

    return rev, recomm


def redirect_to_recommendations(recomm: Recommendation):
    controller = "manager" if auth.has_membership(role="manager") else "recommender"

    redirect(URL(c=controller, f="recommendations", vars=dict(articleId=recomm["article_id"])))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def accept_review_request():
    rev, recomm = check_accept_decline_request()

    # db(db.t_reviews.id==reviewId).delete()
    rev.review_state = "Awaiting review"
    rev.update_record()
    # email to recommender sent at database level
    redirect_to_recommendations(recomm)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def decline_review_request():
    rev, recomm = check_accept_decline_request()

    # db(db.t_reviews.id==reviewId).delete()
    rev.review_state = "Declined by recommender"
    rev.update_record()
    # email to recommender sent at database level
    redirect_to_recommendations(recomm)


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

    co_recommender = is_co_recommender(recomm.id)
    if recomm.recommender_id != auth.user_id and not recomm.is_closed and not (auth.has_membership(role="administrator") or co_recommender or auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        art = db.t_articles[recomm.article_id]

        art.is_searching_reviewers = True
        art.update_record()
        db.commit()
        emailing.delete_reminder_for_managers(["#ManagersRecommenderAgreedAndNeedsToTakeAction"], recomm.id)
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

    co_recommender = is_co_recommender(recomm.id)
    if recomm.recommender_id != auth.user_id and not recomm.is_closed and not (auth.has_membership(role="administrator") or co_recommender or auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        art = db.t_articles[recomm.article_id]
        art.is_searching_reviewers = False
        art.update_record()
        db.commit()
        session.flash = 'Preprint is removed from the "In need of reviewers" list'
        redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def delete_recommendation_file():
    recommId = request.vars["recommId"]
    recomm = db.t_recommendations[recommId]
    art = db.t_articles[recomm.article_id]

    amICoRecommender = db((db.t_press_reviews.recommendation_id == recomm.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0

    if (recomm.recommender_id != auth.user_id) and not amICoRecommender and not (auth.has_membership(role="manager")):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    elif art.status not in ("Under consideration", "Pre-recommended", "Pre-revision", "Pre-cancelled", "Pre-recommended-private"):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    if not ("recommId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    if not ("fileType" in request.vars):
        session.flash = T("Unavailable")
        redirect(request.env.http_referer)
    else:
        if request.vars.fileType == "reply_pdf":
            recomm.reply_pdf = None
            recomm.reply_pdf_data = None
            recomm.update_record()
        elif request.vars.fileType == "track_change":
            recomm.track_change = None
            recomm.track_change_data = None
            recomm.update_record()
        elif request.vars.fileType == "recommender_file":
            recomm.recommender_file = None
            recomm.recommender_file_data = None
            recomm.update_record()
        else:
            session.flash = T("Unavailable")
            redirect(request.env.http_referer)

    session.flash = T("File successfully deleted")
    
    redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def do_end_scheduled_submission():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Scheduled submission under consideration":
        art.status = "Under consideration"
        art.update_record()

        # Create reminder for reviewers
        awaitingReviews = db(
            (db.t_reviews.recommendation_id == db.t_recommendations.id)
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_articles.id == articleId)
            & (db.t_reviews.review_state == "Awaiting review")
        ).select()
        for review in awaitingReviews:
            reviewId = review["t_reviews.id"]
            emailing.create_reminder_for_reviewer_review_soon_due(reviewId)
            emailing.create_reminder_for_reviewer_review_due(reviewId)
            emailing.create_reminder_for_reviewer_review_over_due(reviewId)
            emailing.delete_reminder_for_reviewer(["#ReminderScheduledReviewComingSoon"], reviewId)

        emailing.delete_reminder_for_submitter("#SubmitterScheduledSubmissionOpen", articleId)

        session.flash = T("Submission now available to reviewers")
    controller = "recommender"
    if auth.has_membership(role="manager"):
        controller = "manager"
    redirect(URL(c=controller, f="recommendations", vars=dict(articleId=articleId), user_signature=True))

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def revise_scheduled_submission():
    articleId = request.vars["articleId"]
    if articleId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.get_last_recomm(articleId)
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    elif  recomm.recommender_id != auth.user_id and not auth.has_membership(role="manager"):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        redirect(URL(c="manager", f="send_submitter_generic_mail", args=["revise_scheduled_submission"], vars=dict(articleId=articleId)))

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def reject_scheduled_submission():
    articleId = request.vars["articleId"]
    if articleId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = db.get_last_recomm(articleId)
    if recomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    elif recomm.recommender_id != auth.user_id and not auth.has_membership(role="manager"):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        redirect(URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id, scheduled_reject=True)))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def edit_resend_auth():
    mailId = request.vars['mailId']
    reviewId = request.vars['reviewId']
    recommId = request.vars['recommId']
    articleId = request.vars['articleId']
    urlFunction = request.vars['urlFunction']
    urlController = request.vars['urlController']
    if mailId is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    redirect(URL(c="recommender", f="edit_and_resend_email", vars=dict(mailId=mailId, reviewId=reviewId, recommId=recommId, articleId=articleId, urlFunction=urlFunction, urlController=urlController)))

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def accept_new_delay_to_reviewing():
    review_id = request.vars["reviewId"]
    if not review_id:
        session.flash = T("Review id not found")
        redirect(URL('default','index'))
        return

    review = Review.get_by_id(review_id)
    if not review:
        session.flash = T("Review not found")
        redirect(URL('default','index'))
        return

    if review.acceptation_timestamp and review.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value:
        Review.set_review_status(review, ReviewState.AWAITING_REVIEW)
        emailing.send_decision_new_delay_review_mail(True, review)
        return _new_delay_to_reviewing_redirection(True)
    else:
        session.flash = T("Unable to validate")
        redirect(URL('default','index'))

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def decline_new_delay_to_reviewing():
    review_id = request.vars["reviewId"]
    if not review_id:
        session.flash = T("Review id not found")
        redirect(URL('default','index'))
        return

    review = Review.get_by_id(review_id)
    if not review:
        session.flash = T("Review not found")
        redirect(URL('default','index'))
        return

    if review.acceptation_timestamp and review.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value:
        Review.set_review_status(review, ReviewState.DECLINED_BY_RECOMMENDER)
        emailing.send_decision_new_delay_review_mail(False, review)
        return _new_delay_to_reviewing_redirection(False)
    else:
        session.flash = T("Unable to decline")
        redirect(URL('default','index'))

######################################################################################################################################################################

def _new_delay_to_reviewing_redirection(accept: bool):
    response.view = "default/myLayout.html"

    message1 = ""
    message2 = ""
    message3 = ""
    if accept:
        message1 = T("Thanks for accepting the extra delay requested to perform this review.")
        message2 = T("An email has been sent to this reviewer to tell them that they can start their review. Automatic reminders will be sent, if necessary, to remind this reviewer to post their review in due time.")
        message3 = T("Thanks again for managing this evaluation process!")
    else:
        message1 = T("You have declined this offer to review. Thank you for managing this request.")
        message2 = T("An email has been sent to the reviewer to convey your decision and, as a result, they will not be reviewing this manuscript.")

    return dict(
        form=CENTER(
            P(message1, _class="info-sub-text"),
            P(message2, _class="info-sub-text", _style="width: 800px"),
            P(message3, _style="font-size: initial; font-weight: bold;"),
            A(T("Back to your dashboard"), _href=URL(c="recommender", f="my_recommendations", vars=dict(pressReviews=False), user_signature=True), _class="btn btn-success")
        )
    )

######################################################################################################################################################################

@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def change_review_due_date():
    response.view = "default/myLayout.html"

    review_id = int(request.vars['reviewId'])
    if not review_id:
        session.flash = T("Review id not found")
        redirect(URL('default','index'))
        return
    
    review = Review.get_by_id(review_id)
    if not review:
        session.flash = T("Review not found")
        redirect(URL('default','index'))
        return
    
    default_value: datetime.datetime
    if review.due_date:
        default_value = review.due_date
    else:
        default_value = Review.get_due_date_from_review_duration(review)
    default_value_str = default_value.strftime('%Y-%m-%d')
    
    form: ... = FORM(CENTER(INPUT(_name="review_duration", type="date", _class="date", _value=default_value_str)),
                CENTER(INPUT(_type="submit", _value=T("Change due date"), _class="btn btn-success"),
                    A("Cancel", _class="btn btn-default", _href=request.env.http_referer), _style="margin-top: 10px;"))
    
    if form.process().accepted:
        try:
            new_duration = datetime.datetime.strptime(form.vars['review_duration'], '%Y-%m-%d')
            if new_duration == review.due_date:
                session.flash = T('This date is already configured. No change.')
                redirect(session.change_review_due_date_previous_page)
            Review.set_due_date(review, new_duration)
        except ValueError as error:
            session.flash =  T('Wrong date: ') + error.args[0]
            redirect(request.env.http_referer)

        soon_due_sent = (emailing.delete_reminder_for_reviewer(["#ReminderReviewerReviewSoonDue"], review.id) or 0) == 0
        review_due_sent = (emailing.delete_reminder_for_reviewer(["#ReminderReviewerReviewDue"], review.id) or 0) == 0
        over_due_sent = (emailing.delete_reminder_for_reviewer(["#ReminderReviewerReviewOverDue"], review.id) or 0) == 0

        if soon_due_sent and review_due_sent:
            emailing.create_reminder_for_reviewer_review_due(review.id)
            emailing.create_reminder_for_reviewer_review_over_due(review.id)
        else:
            if not soon_due_sent:
                emailing.create_reminder_for_reviewer_review_soon_due(review.id)
            if not review_due_sent:
                emailing.create_reminder_for_reviewer_review_due(review.id)
            if not over_due_sent:
                emailing.create_reminder_for_reviewer_review_over_due(review.id)

        emailing.send_alert_reviewer_due_date_change(review)

        session.flash = f"Review date changed to {form.vars['review_duration']}"
        
        if session.change_review_due_date_previous_page:
            redirect(session.change_review_due_date_previous_page)

    elif request.env.http_referer and 'change_review_due_date' not in request.env.http_referer:
            session.change_review_due_date_previous_page = request.env.http_referer
    
    content = CENTER(H3(f'The current review deadline is {default_value_str}.'),
                     P('Please select the updated deadline or click Cancel.', _class="info-sub-text"),
                     _class="col-sm-12", _style="text-align: center; margin-bottom: 10px")

    return dict(content=content, form=form)
