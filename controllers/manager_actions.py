# -*- coding: utf-8 -*-

from typing import cast
from app_modules.common_small_html import custom_mail_dialog
from app_modules.emailing_tools import getMailTemplateHashtag, replace_mail_vars_set_not_considered_mail
from app_modules.helper import *
from app_modules import crossref
from app_modules.hypothesis import Hypothesis
from gluon.contrib.appconfig import AppConfig
from gluon.http import redirect
from gluon.storage import Storage
from app_modules.common_tools import cancel_decided_article_pending_reviews
from app_modules import emailing
from models.article import Article, ArticleStatus
from models.user import User
from pydal import DAL

myconf = AppConfig(reload=True)
db = cast(DAL, db)

crossref.init_conf(db)
pciRRactivated = myconf.get("config.registered_reports", default=False)
contact = myconf.take("contacts.managers")


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
        crossref.post_and_forget(recomm)

        art.status = "Recommended"
        recomm.validation_timestamp = request.now
        recomm.update_record()
        art.update_record()
        redirurl = URL(c="articles", f="rec", vars=dict(id=art.id))

    if not pciRRactivated:
        Hypothesis(art).post_annotation()
    
    crossref.post_and_forget(recomm)
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
    author = db.auth_user[art.user_id]
    recomm = get_last_recomm(articleId)
    recommender = db.auth_user[recomm.recommender_id]
    if art is None:
        session.flash = auth.not_authorized()
        redirect(request.env.http_referer)
    if art.status == "Pre-rejected":
        art.status = "Rejected"
        recomm.validation_timestamp = request.now
        recomm.update_record()
        art.update_record()
        if art.is_scheduled:
            cancel_decided_article_pending_reviews(db, recomm)
            cc=  ", ".join([recommender.email, contact])
            form = Storage(
                subject=recomm.recommendation_title, message=recomm.recommendation_comments, cc=cc, replyto=cc
            )
            emailing.send_submitter_generic_mail(session, auth, db, author.email, art.id, form, "#SubmitterScheduledSubmissionDeskReject")
            recomm.update_record(recommendation_title="", recommendation_comments="")
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
            art.is_scheduled = False
        else:
            art.status = "Awaiting consideration"
        
        art.update_record()
        session.flash = T("Submission validated")

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
    if not 'articleId' in request.vars:
        session.flash = 'Article id missing'
        redirect(request.env.http_referer, client_side=True)
    article_id = int(request.vars['articleId'])

    if not 'subject' in request.vars:
        session.flash = 'Subject missing'
        redirect(request.env.http_referer, client_side=True)
    subject = cast(str, request.vars['subject'])

    if not 'message' in request.vars:
        session.flash = 'Message missing'
        redirect(request.env.http_referer, client_side=True)
    message = cast(str, request.vars['message'])

    article = Article.get_by_id(db, article_id)
    if not article:
        session.flash = auth.not_authorized()
        return redirect(request.env.http_referer, client_side=True)
    
    if not article.user_id:
        session.flash = T('No author for this article')
        return redirect(request.env.http_referer, client_side=True)

    author = User.get_by_id(db, article.user_id)
    if not author:
        session.flash = T('No author for this article')
        return redirect(request.env.http_referer, client_side=True)

    if article.status in (ArticleStatus.AWAITING_CONSIDERATION.value, ArticleStatus.PENDING.value):
        session.flash = T('Article set "Not considered"')
        article.status = ArticleStatus.NOT_CONSIDERED.value
        article.update_record()
        emailing.send_set_not_considered_mail(session, auth, db, subject, message, article, author)
    return redirect(request.env.http_referer, client_side=True)


@auth.requires(auth.has_membership(role="manager"))
def get_not_considered_dialog():
    article_id = int(request.vars["articleId"])
    article = Article.get_by_id(db, article_id)
    if not article:
        session.flash = auth.not_authorized()
        return redirect(request.env.http_referer, client_side=True)

    template = getMailTemplateHashtag(db, "#SubmitterNotConsideredSubmission")
    content = replace_mail_vars_set_not_considered_mail(auth, db, article, template['subject'], template['content'])
    submit_url = cast(str, URL(c="manager_actions", f="set_not_considered", vars=dict(articleId=article_id), user_signature=True))
    return custom_mail_dialog(article.id, content.subject, content.message, submit_url)

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
def prepare_send_back():
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

    redirect(URL(c="manager", f="email_for_recommender", vars=dict(articleId=articleId, lastRecomm=lastRecomm)))


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
        art.status = "Under consideration" if not art.is_scheduled else "Scheduled submission pending"
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
