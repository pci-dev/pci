# -*- coding: utf-8 -*-

from app_modules.helper import *



######################################################################################################################################################################
## Manager Actions
######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def do_validate_article():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Pending":
        art.status = "Awaiting consideration"
        art.validation_timestamp = request.now
        art.update_record()
        session.flash = T("Request now available to recommenders")
    redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def pre_submission_list():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Pending":
        art.status = "Pre-submission"
        art.update_record()
        session.flash = T("Submission now in pre-submission list")
    redirect(URL(c="manager", f="presubmissions", vars=dict(articleId=articleId), user_signature=True))

######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def do_cancel_article():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    else:
        # art.status = 'Cancelled' #TEST
        art.status = "Rejected"
        art.update_record()
    redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def do_recommend_article():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    recomm = get_last_recomm(articleId)

    redir_url = URL(c="manager", f="recommendations", vars=dict(articleId=art.id))

    # PCI RR
    # update stage 1 article status from "Recommended-private" to "Recommended"
    if art.art_stage_1_id is not None and art.status == "Pre-recommended":
        artStage1 = db.t_articles[art.art_stage_1_id]
        if artStage1 is not None:
            if artStage1.status.startswith("Recommended"):
                if artStage1.status == "Recommended-private":
                    artStage1.status = "Recommended"
                    artStage1.update_record()
            else:
                session.flash = T("Stage 1 report recommendation process is not finished yet")
                redirect(redir_url)

    # stage 1 recommended privately 
    if art.status == "Pre-recommended-private":	
        art.status = "Recommended-private"
        recomm.validation_timestamp = request.now
        recomm.update_record()
        art.update_record()
        redirect(redir_url)
    elif art.status == "Pre-recommended":
        art.status = "Recommended"
        recomm.validation_timestamp = request.now
        recomm.update_record()
        art.update_record()
        redirurl = URL(c="articles", f="rec", vars=dict(id=art.id))

    redirect(redir_url)


# from db import get_last_recomm
get_last_recomm = db.get_last_recomm


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def do_revise_article():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    recomm = get_last_recomm(articleId)
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Pre-revision":
        art.status = "Awaiting revision"
        recomm.validation_timestamp = request.now
        recomm.update_record()
        art.update_record()
    redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def do_reject_article():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    recomm = get_last_recomm(articleId)
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Pre-rejected":
        art.status = "Rejected"
        recomm.validation_timestamp = request.now
        recomm.update_record()
        art.update_record()
    redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager") or is_recommender(auth, request))
def do_validate_scheduled_submission():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Scheduled submission pending":

        recomm = (
            db((db.t_recommendations.article_id == art.id)).select().last()
        )
        if recomm and recomm.recommender_id:
            art.status = "Scheduled submission under consideration"
        else:
            art.status = "Awaiting consideration"
        
        art.update_record()
        session.flash = T("Request now available to recommenders")

    if is_recommender(auth, request):
        redirect(URL(c="recommender", f="recommendations", vars=dict(articleId=articleId)))

    redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def suggest_article_to():
    articleId = request.vars["articleId"]
    whatNext = request.vars["whatNext"]
    recommenderId = request.vars["recommenderId"]
    db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)
    redirect(whatNext)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def set_not_considered():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Awaiting consideration":
        session.flash = T('Article set "Not considered"')
        art.status = "Not considered"
        art.update_record()
    redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def delete_recommendation_file():

    if not ("recommId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    
    recomm = db.t_recommendations[request.vars.recommId]

    if recomm is None:
        session.flash = T("Unavailable")
        redirect(request.env.http_referer)

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
@auth.requires(auth.has_membership(role="manager"))
def do_send_back_decision():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    lastRecomm = get_last_recomm(articleId)
    
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if lastRecomm is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)

    if art.status.startswith("Pre-"):
        lastRecomm.is_closed = False
        lastRecomm.recommendation_state = "Ongoing"
        lastRecomm.update_record()
        art.status = "Under consideration"
        art.update_record()
        session.flash = T('Recommendation sent back to recommender')

    redirect(request.env.http_referer)

#####################################################################################################################################################################
def get_check_rev_recomm_from_request():
    if "reviewId" not in request.vars:
        raise HTTP(404, "404: " + T("Unavailable"))
    reviewId = request.vars["reviewId"]
    rev = db.t_reviews[reviewId]
    if rev is None:
        raise HTTP(404, "404: " + T("Unavailable"))

    recomm = db((db.t_recommendations.id == rev["recommendation_id"])).select(db.t_recommendations.ALL).last()
    if recomm.recommender_id != auth.user_id and not (auth.has_membership(role="manager")):
        raise HTTP(404, "404: " + T("Unavailable"))

    if rev["review_state"] != "Willing to review":
        session.flash = T("Review state has been changed")
        redirect(URL(c="manager", f="recommendations", vars=dict(articleId=recomm["article_id"])))

    return rev, recomm


@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def accept_review_request():
    rev, recomm = get_check_rev_recomm_from_request()

    rev.review_state = "Awaiting review"
    rev.update_record()
    # email to recommender sent at database level
    redirect(URL(c="manager", f="recommendations", vars=dict(articleId=recomm["article_id"])))


@auth.requires(auth.has_membership(role="recommender") or auth.has_membership(role="manager"))
def decline_review_request():
    rev, recomm = get_check_rev_recomm_from_request()

    rev.review_state = "Declined by recommender"
    rev.update_record()
    # email to recommender sent at database level
    redirect(URL(c="manager", f="recommendations", vars=dict(articleId=recomm["article_id"])))
