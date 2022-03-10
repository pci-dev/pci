# -*- coding: utf-8 -*-

import re
import copy
import tempfile
from datetime import datetime, timedelta
import glob
import os

# sudo pip install tweepy
# import tweepy

import codecs

# import html2text
from gluon.contrib.markdown import WIKI

from app_modules.helper import *

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)


csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get("config.trgm_limit") or 0.4
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
not_considered_delay_in_days = myconf.get("config.unconsider_limit_days", default=20)


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
        art.update_record()
        session.flash = T("Request now available to recommenders")
    redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))


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
                redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))

    # stage 1 recommended privately 
    if art.status == "Pre-recommended-private":	
        art.status = "Recommended-private"
        art.update_record()
        redirect(URL(c="manager", f="recommendations", vars=dict(articleId=art.id), user_signature=True))   
    elif art.status == "Pre-recommended":
        art.status = "Recommended"
        art.update_record()
        redirect(URL(c="articles", f="rec", vars=dict(id=art.id), user_signature=True))    
    else:
        redirect(URL(c="manager", f="recommendations", vars=dict(articleId=articleId), user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role="manager"))
def do_revise_article():
    if not ("articleId" in request.vars):
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    articleId = request.vars["articleId"]
    art = db.t_articles[articleId]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Pre-revision":
        art.status = "Awaiting revision"
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
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Pre-rejected":
        art.status = "Rejected"
        art.update_record()
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
    lastRecomm = db((db.t_recommendations.article_id == articleId)).select().last()
    
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
