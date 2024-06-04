# -*- coding: utf-8 -*-
import os
from re import sub
from typing import Any, Dict, List, Optional, cast
from dateutil.relativedelta import *

import io

from gluon import current, IS_IN_DB
from gluon.globals import Request, Response
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.sqlhtml import *
from app_modules.helper import *
from models.recommendation import Recommendation, RecommendationState
from pydal import DAL

from app_modules import common_tools
from app_modules import common_small_html
from app_modules import hypothesis
from models.article import ArticleStatus, Article

from controller_modules import manager_module
from models.article import is_scheduled_submission
from models.group import Role
from models.review import Review, ReviewState

myconf = AppConfig(reload=True)

scheme = myconf.take("alerts.scheme")
host = myconf.take("alerts.host")
port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

########################################################################################################################################################################
def getRecommStatusHeader(auth: Auth, db: DAL, response: Response, art: Article, controller_name: str, request: Request, userDiv: DIV, printable: bool, quiet: bool = True):
    lastRecomm = db.get_last_recomm(art.id)
    if lastRecomm:
        co_recommender = is_co_recommender(auth, db, lastRecomm.id)

    if userDiv:
        statusDiv = DIV(
            common_small_html.mkStatusBigDivUser(auth, db, art.status, printable),
            _class="pci2-flex-center pci2-full-width",
        )
    else:
        statusDiv = DIV(common_small_html.mkStatusBigDiv(auth, db, art.status, printable), _class="pci2-flex-center pci2-full-width")


    myTitle = DIV(
        IMG(_src=URL(r=request, c="static", f="images/small-background.png", scheme=scheme, host=host, port=port)),
        DIV(statusDiv, _class="pci2-flex-grow"),
        _class="pci2-flex-row",
    )

    # author's button allowing article edition
    allowEditArticle = False
    if ((art.user_id == auth.user_id) and (art.status in ("Pending", "Awaiting revision", "Scheduled submission revision", "Pending-survey", "Pre-submission"))) and not (quiet):
        allowEditArticle = True

    # manager buttons
    allowManageRecomms = False
    if (lastRecomm or art.status == "Under consideration") and auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (quiet):
        allowManageRecomms = True

    back2 = URL(re.sub(r".*/([^/]+)$", "\\1", request.env.request_uri), scheme=scheme, host=host, port=port)

    allowManageRequest = False
    manageRecommendersButton = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (quiet):
        allowManageRequest = True
        manageRecommendersButton = manager_module.mkSuggestedRecommendersManagerButton(art, back2, auth, db)
    
    if pciRRactivated and lastRecomm and ((lastRecomm.recommender_id == auth.user_id or co_recommender) and lastRecomm.recommendation_state in ("Ongoing", "Revision")) and auth.has_membership(role="recommender") and not(quiet):
       allowManageRequest = True

    printableUrl = None
    verifyUrl = None
    if auth.has_membership(role="manager"):
        printableUrl = URL(c="manager", f="article_emails", vars=dict(articleId=art.id, printable=True), user_signature=True, scheme=scheme, host=host, port=port)
    
    if (auth.has_membership(role="recommender") or auth.has_membership(role="manager")) and art.user_id != auth.user_id:
        verifyUrl = URL(c="recommender", f="verify_co_authorship", vars=dict(articleId=art.id, printable=True), user_signature=True, scheme=scheme, host=host, port=port)

    recommenderSurveyButton = None
    if lastRecomm and (auth.user_id == lastRecomm.recommender_id or co_recommender):
        printableUrl = URL(c="recommender", f="article_reviews_emails", vars=dict(articleId=art.id), user_signature=True, scheme=scheme, host=host, port=port)
        recommenderSurveyButton = True

    componentVars = dict(
        statusTitle=myTitle,
        allowEditArticle=allowEditArticle,
        allowEditTranslations=Article.current_user_has_edit_translation_right(art),
        allowManageRecomms=allowManageRecomms,
        allowManageRequest=allowManageRequest,
        manageRecommendersButton=manageRecommendersButton,
        articleId=art.id,
        printableUrl=printableUrl,
        verifyUrl=verifyUrl,
        printable=printable,
        pciRRactivated=pciRRactivated,
        recommenderSurveyButton=recommenderSurveyButton
    )

    return XML(response.render("components/recommendation_header.html", componentVars))


######################################################################################################################################################################
def getRecommendationTopButtons(auth, db, art, printable=False, quiet=True):

    myContents = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))
    nbRecomms = db(db.t_recommendations.article_id == art.id).count()
    myButtons = DIV()

    if (
        nbRecomms == 0
        and auth.has_membership(role="recommender")
        and not (art.user_id == auth.user_id)
        and art.status == "Awaiting consideration"
        and not (printable)
        and not (quiet)
    ):
        # suggested or any recommender's button for recommendation consideration
        btsAccDec = [
            A(
                SPAN(current.T("Yes, I would like to handle the evaluation process"), _class="buttontext btn btn-success pci-recommender"),
                _href=URL(c="recommender", f="accept_new_article_to_recommend", vars=dict(articleId=art.id), user_signature=True, scheme=scheme, host=host, port=port),
                _class="button",
            ),

        ]
        amISugg = db(
            (db.t_suggested_recommenders.article_id == art.id)
            & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
            & (db.t_suggested_recommenders.declined == False)
        ).count()
        if amISugg > 0:
            # suggested recommender's button for declining recommendation
            btsAccDec.append(
                A(
                    SPAN(current.T("No, I would rather not"), _class="buttontext btn btn-warning pci-recommender"),
                    _href=URL(c="recommender_actions", f="decline_new_article_to_recommend", vars=dict(articleId=art.id), user_signature=True, scheme=scheme, host=host, port=port),
                    _class="button",
                ),
            )

        haveDeclined = db(
            (db.t_suggested_recommenders.article_id == art.id)
            & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
            & (db.t_suggested_recommenders.declined == True)
        ).count()
        buttonDivClass = ""
        if haveDeclined > 0:
            buttonDivClass = " pci2-flex-column"
            btsAccDec.append(
                BR(),
            )
            btsAccDec.append(
                B(current.T("You have declined the invitation to handle the evaluation process of this preprint.")),
            )

        myButtons.append(DIV(btsAccDec, _class="pci2-flex-grow pci2-flex-center" + buttonDivClass, _style="margin:10px"))

    if (
        (art.user_id == auth.user_id)
        and not (art.already_published)
        and (art.status not in ("Cancelled", "Rejected", "Pre-recommended", "Recommended", "Not considered"))
        and not (printable)
        and not (quiet)
    ):
        myButtons.append(
            DIV(
                A(
                    SPAN(current.T("I wish to cancel my submission"), _class="buttontext btn btn-warning pci-submitter"),
                    _href=URL(c="user_actions", f="do_cancel_article", vars=dict(articleId=art.id), user_signature=True, scheme=scheme, host=host, port=port),
                    _title=current.T("Click here in order to cancel this submission"),
                ),
                _class="pci-EditButtons pci2-flex-grow pci2-flex-center",
                _id="cancel-submission-button",
            )
        )  # author's button allowing cancellation

    myContents.append(myButtons)

    return myContents


########################################################################################################################################################################
def getRecommendationProcessForSubmitter(auth, db, response, art, printable):
    recommendationDiv = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))

    submissionValidatedClassClass = "step-default"
    havingRecommenderClass = "step-default"
    reviewInvitationsAcceptedClass = "step-default"
    reviewsStepDoneClass = "step-default"
    recommendationStepClass = "step-default"
    managerDecisionDoneClass = "step-default"
    isRecommAvalaibleToSubmitter = False

    if not (art.status in ["Pending", "Pending-survey", "Pre-submission"]):
        submissionValidatedClassClass = "step-done"
    uploadDate = art.upload_timestamp.strftime("%d %B %Y")

    suggestedRecommendersCount = db(db.t_suggested_recommenders.article_id == art.id).count()

    recomms = db(db.t_recommendations.article_id == art.id).select(orderby=db.t_recommendations.id)
    totalRecomm = len(recomms)

    if totalRecomm > 0:
        havingRecommenderClass = "step-done"

    roundNumber = 1

    recommStatus = None
    reviewCount = 0
    acceptedReviewCount = 0
    completedReviewCount = 0

    recommenderName = None

    if totalRecomm > 0:
        for recomm in recomms:
            reviewInvitationsAcceptedClass = "step-default"
            reviewsStepDoneClass = "step-default"
            recommendationStepClass = "step-default"
            managerDecisionDoneClass = "step-default"
            authorsReplyClass = "step-default"
            recommDate = recomm.last_change.strftime("%d %B %Y")
            validationDate = recomm.validation_timestamp.strftime("%d %B %Y") if recomm.validation_timestamp else None
            if roundNumber < totalRecomm:
                nextRound = recomms[roundNumber]
                authorsReplyDate = nextRound.recommendation_timestamp.strftime(DEFAULT_DATE_FORMAT)
            else:
                authorsReplyDate = None # current round

            recommenderName = common_small_html.getRecommAndReviewAuthors(
                auth, db, recomm=recomm, with_reviewers=False, linked=not (printable), host=host, port=port, scheme=scheme
            )

            recommStatus = None
            reviewCount = 0
            acceptedReviewCount = 0
            completedReviewCount = 0

            reviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state != "Cancelled")).select(
                orderby=db.t_reviews.id
            )

            lastReviewDate = None
            for review in reviews:
                reviewCount += 1
                if review.review_state == "Awaiting review":
                    acceptedReviewCount += 1
                if review.review_state == "Review completed":
                    acceptedReviewCount += 1
                    completedReviewCount += 1
                lastReviewDate = review.last_change.strftime("%d %B %Y")

            if acceptedReviewCount >= 2:
                reviewInvitationsAcceptedClass = "step-done"

            if completedReviewCount == acceptedReviewCount and completedReviewCount != 0:
                reviewsStepDoneClass = "step-done"

            if recomm.recommendation_state == "Rejected" or recomm.recommendation_state == "Recommended" or recomm.recommendation_state == "Revision":
                recommendationStepClass = "step-done"
                recommStatus = recomm.recommendation_state

            if (roundNumber == totalRecomm and art.status in ("Rejected", "Recommended", "Awaiting revision", "Scheduled submission revision")) or (roundNumber < totalRecomm and (((recomm.reply is not None) and (len(recomm.reply) > 0)) or (recomm.reply_pdf is not None))):
                managerDecisionDoneClass = "step-done"

            if recommStatus == "Revision" and managerDecisionDoneClass == "step-done":
                managerDecisionDoneStepClass = "progress-step-div"
            else:
                managerDecisionDoneStepClass = "progress-last-step-div"

            if (roundNumber < totalRecomm) and (((recomm.reply is not None) and (len(recomm.reply) > 0)) or (recomm.reply_pdf is not None)):
                authorsReplyClass = "step-done"

            if roundNumber == totalRecomm and recommStatus == "Revision" and managerDecisionDoneClass == "step-done":
                authorsReplyClassStepClass = "progress-last-step-div"
            else:
                authorsReplyClassStepClass = "progress-step-div"

            recommendationLink = None
            if recommStatus == "Recommended" and managerDecisionDoneClass == "step-done":
                recommendationLink = URL(c="articles", f="rec", vars=dict(id=art.id), user_signature=True, scheme=scheme, host=host, port=port)

            componentVars = dict(
                printable=printable,
                roundNumber=roundNumber,
                articleStatus=art.status,
                submissionValidatedClassClass=submissionValidatedClassClass,
                havingRecommenderClass=havingRecommenderClass,
                suggestedRecommendersCount=suggestedRecommendersCount,
                recommenderName=recommenderName,
                reviewInvitationsAcceptedClass=reviewInvitationsAcceptedClass,
                reviewCount=reviewCount,
                lastReviewDate=lastReviewDate,
                acceptedReviewCount=acceptedReviewCount,
                reviewsStepDoneClass=reviewsStepDoneClass,
                completedReviewCount=completedReviewCount,
                recommendationStepClass=recommendationStepClass,
                recommStatus=recommStatus,
                recommDate=recommDate,
                validationDate = validationDate,
                authorsReplyDate=authorsReplyDate,
                managerDecisionDoneClass=managerDecisionDoneClass,
                managerDecisionDoneStepClass=managerDecisionDoneStepClass,
                authorsReplyClass=authorsReplyClass,
                authorsReplyClassStepClass=authorsReplyClassStepClass,
                totalRecomm=totalRecomm,
                recommendationLink=recommendationLink,
                uploadDate=uploadDate,
            )
            recommendationDiv.append(XML(response.render("components/recommendation_process_for_submitter.html", componentVars)))

            roundNumber += 1

    else:
        managerDecisionDoneStepClass = "progress-last-step-div"
        recommDate = False
        lastReviewDate = False
        authorsReplyDate = False
        validationDate = False

        componentVars = dict(
            printable=printable,
            roundNumber=roundNumber,
            articleStatus=art.status,
            submissionValidatedClassClass=submissionValidatedClassClass,
            havingRecommenderClass=havingRecommenderClass,
            suggestedRecommendersCount=suggestedRecommendersCount,
            recommenderName=recommenderName,
            reviewInvitationsAcceptedClass=reviewInvitationsAcceptedClass,
            reviewCount=reviewCount,
            lastReviewDate=lastReviewDate,
            acceptedReviewCount=acceptedReviewCount,
            reviewsStepDoneClass=reviewsStepDoneClass,
            completedReviewCount=completedReviewCount,
            recommendationStepClass=recommendationStepClass,
            recommStatus=recommStatus,
            recommDate=recommDate,
            validationDate = validationDate,
            authorsReplyDate=authorsReplyDate,
            managerDecisionDoneClass=managerDecisionDoneClass,
            managerDecisionDoneStepClass=managerDecisionDoneStepClass,
            totalRecomm=totalRecomm,
            uploadDate=uploadDate,
        )

        recommendationDiv.append(XML(response.render("components/recommendation_process_for_submitter.html", componentVars)))
    if (managerDecisionDoneClass == "step-done") or (managerDecisionDoneClass == "step-default" and art.status == "Recommended-private"):
        isRecommAvalaibleToSubmitter = True
    return dict(roundNumber=totalRecomm, isRecommAvalaibleToSubmitter=isRecommAvalaibleToSubmitter, content=recommendationDiv)


########################################################################################################################################################################
# Preprint recommendation process (rounds, recomms, reviews, author's reply)

def _am_I_engaged_in_stage2_process(article: Article):
    db, auth = current.db, current.auth

    am_I_engaged_in_stage2_process = False
    if pciRRactivated and article.art_stage_1_id is None:
        auth_cpt = 0
        # if currentUser is reviewer of a related stage 2
        auth_cpt += int(db(
            (db.t_articles.art_stage_1_id == article.id)
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.id == db.t_reviews.recommendation_id)
            & (db.t_reviews.reviewer_id == auth.user_id)
            & (db.t_reviews.review_state != ReviewState.WILLING_TO_REVIEW.value)
        ).count())
        # if currentUser is reviewer of a related stage 2
        auth_cpt += int(db(
            (db.t_articles.art_stage_1_id == article.id) & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommender_id == auth.user_id)
        ).count())
        # if currentUser is reviewer of a related stage 2
        if article.status == ArticleStatus.RECOMMENDED.value:
            auth_cpt += 1
        am_I_engaged_in_stage2_process = auth_cpt > 0

    if pciRRactivated and article.status == ArticleStatus.RECOMMENDED.value:
        am_I_engaged_in_stage2_process = True

    return am_I_engaged_in_stage2_process


def _is_pending_recommender_acceptation(article: Article):
    db, auth = current.db, current.auth

    return bool(db(
          (db.t_recommendations.article_id == article.id)
        & (db.t_recommendations.id == db.t_reviews.recommendation_id)
        & (db.t_reviews.reviewer_id == auth.user_id)
        & (db.t_reviews.review_state == ReviewState.WILLING_TO_REVIEW.value)
    ).count() > 0)


def _current_user_is_recommender(recommendation: Recommendation):
    db, auth = current.db, current.auth
    return bool(db((db.t_press_reviews.recommendation_id == recommendation.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0)


def _current_user_is_reviewer(article: Article):
    db, auth = current.db, current.auth

    return bool((
            db((db.t_recommendations.article_id == article.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_reviews.reviewer_id == auth.user_id)).count() > 0
        ))


def _must_hide_on_going_recommendation(article: Article, recommendation: Recommendation, am_I_co_recommender: bool):
    auth = current.auth

    if auth.has_membership(role=Role.RECOMMENDER.value) and (recommendation.recommender_id == auth.user_id or am_I_co_recommender):
        return False
    # or a manager
    if auth.has_membership(role=Role.MANAGER.value) and (article.user_id != auth.user_id):
        return False
    
    return ((article.status in (ArticleStatus.UNDER_CONSIDERATION.value, ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value)) or (article.status.startswith("Pre-"))) and not (recommendation.is_closed)  # (iRecomm==1)

    
def _get_author_reply(recommendation: Recommendation):
    authors_reply: Optional[DIV] = None
    if (recommendation.reply is not None) and (len(recommendation.reply) > 0):
        authors_reply = DIV(WIKI(recommendation.reply or "", safe_mode=''))
    return authors_reply


def _get_author_reply_date(recommendation: Recommendation, next_round: Optional[Recommendation], nb_round: int, nb_recommendations: int):
    if (recommendation.reply is not None and len(recommendation.reply) > 0) or recommendation.reply_pdf is not None or recommendation.track_change is not None:
            if nb_round < nb_recommendations:
                if next_round and next_round.recommendation_timestamp:
                    return next_round.recommendation_timestamp.strftime(DEFAULT_DATE_FORMAT+ " %H:%M")


def _get_author_reply_link(article: Article, recommendation: Recommendation, printable: bool, i_recommendation: int):
    auth = current.auth

    if (article.user_id == auth.user_id) and (article.status == ArticleStatus.AWAITING_REVISION.value) and not (printable) and (i_recommendation == 1):
        return common_tools.URL(c="user", f="edit_reply", vars=dict(recommId=recommendation.id), user_signature=True, scheme=scheme, host=host, port=port)


def _get_authors_reply_pdf_link(recommendation: Recommendation):
    if recommendation.reply_pdf:
        return A(
            I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
            current.T("Download author's reply (PDF file)"),
            _href=common_tools.URL("default", "download", args=recommendation.reply_pdf, scheme=scheme, host=host, port=port),
            _style="font-weight: bold; margin-bottom: 5px; display:block",
        )


def _is_scheduled_submission_revision(article: Article, printable: bool):
    auth = current.auth

    if (article.status == ArticleStatus.SCHEDULED_SUBMISSION_REVISION.value) and (article.user_id == auth.user_id) and not (printable):
        return common_tools.URL(c="user_actions", f="article_revised", vars=dict(articleId=article.id), user_signature=True, scheme=scheme, host=host, port=port)
    

def _get_authors_reply_track_change_file_link(recommendation: Recommendation):
    if recommendation.track_change:
        return A(
            I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
            current.T("Download tracked changes file"),
            _href=common_tools.URL("default", "download", args=recommendation.track_change, scheme=scheme, host=host, port=port),
            _style="font-weight: bold; margin-bottom: 5px; display:block",
        )
    

def _is_recommendation_review_filled_or_null(recommendation: Recommendation):
    db = current.db

    # If the recommender is also a reviewer, did he/she already completed his/her review?
    recommendation_review_filled_or_null = False  # Let's say no by default
    # Get reviews states for this case
    recommender_own_reviews = cast(List[Review], db((db.t_reviews.recommendation_id == recommendation.id) & (db.t_reviews.reviewer_id == recommendation.recommender_id)).select())
    if len(recommender_own_reviews) == 0:
        # The recommender is not also a reviewer
        recommendation_review_filled_or_null = True  # He/she is allowed to see other's reviews
    else:
        # The recommender is also a reviewer
        for recommender_own_review in recommender_own_reviews:
            if recommender_own_review.review_state == ReviewState.REVIEW_COMPLETED.value:
                recommendation_review_filled_or_null = True  # Yes, his/her review is completed
    return recommendation_review_filled_or_null


def _get_hide_on_going_review_and_set_show_review_request(article: Article, recommendation: Recommendation, review: Review, am_I_co_recommender: bool, review_vars: Dict[str, Any], printable: bool):
    auth = current.auth
    recommendation_review_filled_or_null = _is_recommendation_review_filled_or_null(recommendation)

    hide_on_going_review = True

    # ... but:
    # ... the author for a closed decision/recommendation ...
    if (article.user_id == auth.user_id) and (recommendation.is_closed or article.status in (ArticleStatus.AWAITING_REVISION.value, ArticleStatus.SCHEDULED_SUBMISSION_REVISION.value)):
        hide_on_going_review = False
    # ...  the reviewer himself once accepted ...
    if (review.reviewer_id == auth.user_id) and (review.review_state in (ReviewState.AWAITING_REVIEW.value, ReviewState.REVIEW_COMPLETED.value)):
        hide_on_going_review = False
    # ...  a reviewer himself once the decision made up ...
    if (
        (_current_user_is_reviewer(article))
        and (recommendation.recommendation_state in (RecommendationState.RECOMMENDED.value, RecommendationState.REJECTED.value, RecommendationState.REVISION.value))
        and recommendation.is_closed
        and (article.status in (ArticleStatus.UNDER_CONSIDERATION.value, ArticleStatus.RECOMMENDED.value, ArticleStatus.REJECTED.value, ArticleStatus.AWAITING_REVISION.value, ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value))
    ):
        hide_on_going_review = False
    # ... or he/she is THE recommender and he/she already filled his/her own review ...
    if auth.has_membership(role=Role.RECOMMENDER.value) and (recommendation.recommender_id == auth.user_id or am_I_co_recommender) and recommendation_review_filled_or_null:
        hide_on_going_review = False
    # ... or he/she is A CO-recommender and he/she already filled his/her own review ...
    if auth.has_membership(role=Role.RECOMMENDER.value) and am_I_co_recommender and recommendation_review_filled_or_null:
        hide_on_going_review = False
    # ... or a manager, unless submitter
    if auth.has_membership(role=Role.MANAGER.value) and not (article.user_id == auth.user_id):
        hide_on_going_review = False

    # ... or if engaged in stage 2 process (pci RR)
    if review.review_state == ReviewState.REVIEW_COMPLETED.value and _am_I_engaged_in_stage2_process(article):
        hide_on_going_review = False

    if auth.has_membership(role=Role.RECOMMENDER.value) and (recommendation.recommender_id == auth.user_id or am_I_co_recommender) and (review.review_state == ReviewState.WILLING_TO_REVIEW.value) and (article.status == ArticleStatus.UNDER_CONSIDERATION.value):
        review_vars.update([("showReviewRequest", True)])

    if (review.reviewer_id == auth.user_id) and (review.reviewer_id != recommendation.recommender_id) and (article.status in (ArticleStatus.UNDER_CONSIDERATION.value, ArticleStatus.SCHEDULED_SUBMISSION_PENDING.value, ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value)) and not (printable):
        if review.review_state == ReviewState.AWAITING_RESPONSE.value:
            # reviewer's buttons in order to accept/decline pending review
            review_vars.update([("showInvitationButtons", True)])
        elif review.review_state == ReviewState.WILLING_TO_REVIEW.value or review.review_state == ReviewState.DECLINED_BY_RECOMMENDER.value:
            # reviewer's buttons in order to accept/decline pending review
            review_vars.update([("showPendingAskForReview", True)])
            if review.review_state == ReviewState.DECLINED_BY_RECOMMENDER.value:
                review_vars.update([("declinedByRecommender", True)])

    elif review.review_state == ReviewState.AWAITING_RESPONSE.value or review.review_state == ReviewState.DECLINED_BY_RECOMMENDER.value:
        hide_on_going_review = True

    if (recommendation.recommender_id != auth.user_id and am_I_co_recommender == False) and review.review_state == ReviewState.WILLING_TO_REVIEW.value:
        review_vars.update([("showReviewRequest", False)])
        hide_on_going_review = True
        
    if auth.has_membership(role=Role.MANAGER.value)  and review.review_state == ReviewState.WILLING_TO_REVIEW.value:
        review_vars.update([("showReviewRequest", True)])
        hide_on_going_review = False

    if (review.reviewer_id == auth.user_id) and review.review_state == ReviewState.WILLING_TO_REVIEW.value:
        review_vars.update([("showReviewRequest", False)])
        hide_on_going_review = False

    return hide_on_going_review


def _build_review_vars(article: Article, recommendation: Recommendation, review: Review, am_I_co_recommender: bool, printable: bool, count_anonymous_review: int, role: Optional[Role]):
    auth, db = current.auth, current.db

    review_vars: Dict[Any, Any] = dict(
                id=review.id,
                review_duration=review.review_duration.lower() if review.review_duration else '',
                due_date=Review.get_due_date(review),
                showInvitationButtons=False,
                showReviewRequest=False,
                showPendingAskForReview=False,
                declinedByRecommender=False,
                showEditButtons=False,
                showReviewExtraTimeButtons=False,
                authors=None,
                text=None,
                pdfLink=None,
                state=None,
            )

    hide_on_going_review = _get_hide_on_going_review_and_set_show_review_request(article, recommendation, review, am_I_co_recommender, review_vars, printable)

    if auth.has_membership(role=Role.MANAGER.value) and review.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value:
        review_vars.update([("showReviewExtraTimeButtons", True)])

    # reviewer's buttons in order to edit/complete pending review
    if (review.reviewer_id == auth.user_id) and (review.review_state == ReviewState.AWAITING_REVIEW.value) and (article.status in (ArticleStatus.UNDER_CONSIDERATION.value, ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value)) and not (printable):
        review_vars.update([("showEditButtons", True)])

    review_date: Optional[datetime.datetime] = None
    if review.review_state == ReviewState.REVIEW_COMPLETED.value:
        review_date = review.last_change
    else:
        review_date = review.acceptation_timestamp
    review_date_str = review_date.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review_date else ""

    if not (hide_on_going_review):
        # display the review
        if review.anonymously:
            count_anonymous_review += 1
            reviewer_number = common_tools.find_reviewer_number(db, review, count_anonymous_review)
            review_vars.update(
                [
                    (
                        "authors",
                        SPAN(
                            current.T("anonymous reviewer " + reviewer_number),
                            (", " + review_date_str),
                        ),
                    )
                ]
            )
        else:
            review_vars.update(
                [
                    (
                        "authors",
                        SPAN(
                            Review.get_reviewer_name(review) or
                            common_small_html.mkUser(auth, db, review.reviewer_id, linked=True),
                            (", " + review_date_str),
                        ),
                    )
                ]
            )

        if len(review.review or "") > 2:
            review_vars.update([("text", WIKI(review.review, safe_mode=''))])

        if review.review_pdf:
            pdfLink = A(
                I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
                current.T("Download the review (PDF file)"),
                _href=common_tools.URL("default", "download", args=review.review_pdf, scheme=scheme, host=host, port=port),
                _style="font-weight: bold; margin-bottom: 5px; display:block",
            )
            review_vars.update([("pdfLink", pdfLink)])
    review_vars.update([("state", review.review_state)])


    if review_vars["showReviewRequest"] and role:
            review_vars.update([
                ("acceptReviewRequestLink", _mk_link(role, "accept", review_vars)),
                ("rejectReviewRequestLink", _mk_link(role, "decline", review_vars)),
            ])

    return (review_vars, count_anonymous_review)
    

def _get_recommendation_label(recommendation: Recommendation, am_I_co_recommender: bool):
    auth = current.auth

    if recommendation.recommendation_state == RecommendationState.RECOMMENDED.value:
        if recommendation.recommender_id == auth.user_id:
            recommendation_label = current.T("Your recommendation")
        elif am_I_co_recommender:
            recommendation_label = current.T("Your co-recommendation")
        elif auth.has_membership(role=Role.MANAGER.value):
            recommendation_label = current.T("Decision")
        else:
            recommendation_label = current.T("Recommendation")
    else:
        if recommendation.recommender_id == auth.user_id:
            recommendation_label = current.T("Your decision")
        elif am_I_co_recommender:
            recommendation_label = current.T("Your co-decision")
        elif recommendation.is_closed:
            recommendation_label = current.T("Decision")
        else:
            recommendation_label = current.T("Decision")

    return recommendation_label


def _get_recommender_buttons(article: Article, recommendation: Recommendation, am_I_co_recommender: bool, nb_completed: int, nb_on_going: int, nb_round: int, printable: bool):
    auth = current.auth

    edit_recommendation_link = None
    edit_recommendation_disabled = None
    edit_recommendation_button_text = None

    if not (recommendation.is_closed) and (recommendation.recommender_id == auth.user_id or am_I_co_recommender) and (article.status == ArticleStatus.UNDER_CONSIDERATION.value) and not (printable):
        # recommender's button for recommendation edition
        edit_recommendation_button_text = current.T("Write or edit your decision / recommendation")
        edit_recommendation_link = common_tools.URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recommendation.id), scheme=scheme, host=host, port=port)
        if pciRRactivated:
            pass
        elif (nb_completed >= 2 and nb_on_going == 0) or nb_round > 1:
            pass
        else:
            edit_recommendation_disabled = True
            edit_recommendation_button_text = current.T("Write your decision / recommendation")

    return dict(
        edit_recommendation_link=edit_recommendation_link,
        edit_recommendation_disabled=edit_recommendation_disabled,
        edit_recommendation_button_text=edit_recommendation_button_text)


def _get_invite_reviewer_links(article: Article, recommendation: Recommendation, am_I_co_recommender: bool):
    auth = current.auth

    invite_reviewer_link = None
    show_remove_searching_for_reviewers_button = None
    if not (recommendation.is_closed) and (recommendation.recommender_id == auth.user_id or am_I_co_recommender or auth.has_membership(role=Role.MANAGER.value)) and (article.status in (ArticleStatus.UNDER_CONSIDERATION.value, ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value)):
        invite_reviewer_link = common_tools.URL(c="recommender", f="reviewers", vars=dict(recommId=recommendation.id), scheme=scheme, host=host, port=port)
        show_remove_searching_for_reviewers_button = article.is_searching_reviewers
    
    return dict(
        invite_reviewer_link=invite_reviewer_link,
        show_remove_searching_for_reviewers_button=show_remove_searching_for_reviewers_button
    )


def _show_scheduled_submission_ending_button(article: Article, recommendation: Recommendation, am_I_co_recommender: bool, printable: bool):
    auth = current.auth

    scheduled_submission_ending_button = False
    if pciRRactivated and (recommendation.recommender_id == auth.user_id or am_I_co_recommender or auth.has_membership(role=Role.MANAGER.value)) and (article.status == ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value) and not (printable):
        scheduled_submission_ending_button = True

    return scheduled_submission_ending_button


def _get_recommendation_text(recommendation: Recommendation, hide_on_going_recommendation: bool):
    recommendation_text = ""
    if len(recommendation.recommendation_comments or "") > 2:
        recommendation_text = WIKI(recommendation.recommendation_comments or "", safe_mode='') if (hide_on_going_recommendation is False) else ""
    return recommendation_text


def _get_recommendation_pdf_link(recommendation: Recommendation, hide_on_going_recommendation: bool):
    recommendation_pdf_link = None
    if hide_on_going_recommendation is False and recommendation.recommender_file:
        recommendation_pdf_link = A(
            I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
            current.T("Download recommender's annotations (PDF)"),
            _href=common_tools.URL("default", "download", args=recommendation.recommender_file, scheme=scheme, host=host, port=port),
            _style="font-weight: bold; margin-bottom: 5px; display:block",
        )
    return recommendation_pdf_link


def _mk_link(role: Role, action: str, review_item: Dict[Any, Any]):
    return common_tools.URL(c=role.value+"_actions", f=action+"_review_request", vars=dict(reviewId=review_item["id"]), scheme=scheme, host=host, port=port)


def _get_role_current_user():
    auth = current.auth

    role: Optional[Role] = None
    if auth.has_membership(role=Role.MANAGER.value):
        role = Role.MANAGER
    elif auth.has_membership(role=Role.RECOMMENDER.value):
        role = Role.RECOMMENDER
    return role


def _reply_button_disabled(article: Article, recommendation: Recommendation):
    return (
            recommendation.recommendation_state == RecommendationState.REVISION.value and article.request_submission_change
            and not pciRRactivated
        )


def _suspend_submissions():
    suspend_submissions = False
    status = current.db.config[1]
    if pciRRactivated and status['allow_submissions'] is False:
        suspend_submissions = True
    return suspend_submissions


def _get_active_reviews(recommendation: Recommendation):
    db = current.db

    return cast(List[Review], db((db.t_reviews.recommendation_id == recommendation.id) & (db.t_reviews.review_state != ReviewState.DECLINED_MANUALLY.value) & (db.t_reviews.review_state != ReviewState.DECLINED.value) & (db.t_reviews.review_state != ReviewState.CANCELLED.value)).select(
            orderby=db.t_reviews.id
        ))


def _get_manager_button(article: Article, is_recommender: bool):
    auth = current.auth

    if article.user_id == auth.user_id:
        return None

    if pciRRactivated and (auth.has_membership(role="recommender") or auth.has_membership(role="manager")):
        if article.status == "Scheduled submission pending":
            return validate_scheduled_submission_button(articleId=article.id, recommender=auth.user_id)

    if not auth.has_membership(role="manager"):
        return None

    if pciRRactivated and is_scheduled_track(article) and is_stage_1(article):
        return validate_stage_button(article)

    manager_coauthor = common_tools.check_coauthorship(auth.user_id, article)
    if is_recommender:
        return sorry_you_are_recommender_note()
    elif manager_coauthor:
        return sorry_you_are_coauthor_note()
    else:
        return validate_stage_button(article)
    

def _get_recommendation_process_components(article: Article, printable: bool = False):
    auth, db = current.auth, current.db
    recommendation_process_components: List[Dict[str, Any]] = []

    am_I_in_recommender_list: bool = False
    am_I_in_co_recommender_list: bool = False
    i_recommendation: int = 0
    recommendations = Recommendation.get_by_article_id(article.id, ~current.db.t_recommendations.id)
    nb_recommendations = len(recommendations)
    nb_round = nb_recommendations + 1
    previous_recommendation: Optional[Recommendation] = None

    for recommendation in recommendations:
        manager_coauthor = common_tools.check_coauthorship(auth.user_id, article)
        if manager_coauthor:
            break

        i_recommendation += 1
        nb_round -= 1
        nb_completed: int = 0
        nb_on_going: int = 0
        who_did_it_html = common_small_html.getRecommAndReviewAuthors(auth, db, recomm=recommendation, with_reviewers=False, linked=not (printable),
                        host=host, port=port, scheme=scheme,
                        this_recomm_only=True,
                        )

        if recommendation.recommender_id == auth.user_id:
            am_I_in_recommender_list = True

        am_I_co_recommender = _current_user_is_recommender(recommendation)
        if am_I_co_recommender:
            am_I_in_co_recommender_list = True

        role = _get_role_current_user()
        hide_on_going_recommendation = _must_hide_on_going_recommendation(article, recommendation, am_I_co_recommender)

        reviews = _get_active_reviews(recommendation)

        reviews_list: List[Any] = []
        count_anonymous_review: int = 0
        for review in reviews:
            if review.review_state == ReviewState.AWAITING_REVIEW.value:
                nb_on_going += 1
            if review.review_state == ReviewState.REVIEW_COMPLETED.value:
                nb_completed += 1
            
            review_vars, count_anonymous_review = _build_review_vars(article, recommendation, review, am_I_co_recommender, printable, count_anonymous_review, role)
            reviews_list.append(review_vars)            

        recommender_buttons = _get_recommender_buttons(article, recommendation, am_I_co_recommender, nb_completed, nb_on_going, nb_round, printable)
        invite_reviewer_links_buttons= _get_invite_reviewer_links(article, recommendation, am_I_co_recommender)

        component_vars = dict(
            articleId=article.id,
            recommId=recommendation.id,
            printable=printable,
            roundNumber=nb_round,
            nbRecomms=nb_recommendations,
            lastChanges=None,
            authorsReply=_get_author_reply(recommendation),
            authorsReplyDate=_get_author_reply_date(recommendation, previous_recommendation, nb_round, nb_recommendations),
            authorsReplyPdfLink=_get_authors_reply_pdf_link(recommendation),
            authorsReplyTrackChangeFileLink=_get_authors_reply_track_change_file_link(recommendation),
            editAuthorsReplyLink=_get_author_reply_link(article, recommendation, printable, i_recommendation),
            recommendationAuthor=I(current.T("by "), B(who_did_it_html), SPAN(", " + recommendation.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if recommendation.last_change else "")),
            manuscriptDoi=SPAN(current.T("Manuscript:") + " ", common_small_html.mkDOI(recommendation.doi)) if (recommendation.doi) else SPAN(""),
            recommendationVersion=SPAN(" " + current.T("version:") + " ", recommendation.ms_version) if (recommendation.ms_version) else SPAN(""),
            recommendationTitle=H4(common_small_html.md_to_html(recommendation.recommendation_title) or "", _style="font-weight: bold; margin-top: 5px; margin-bottom: 20px") if (hide_on_going_recommendation is False) else "",
            recommendationLabel=_get_recommendation_label(recommendation, am_I_co_recommender),
            recommendationText=_get_recommendation_text(recommendation, hide_on_going_recommendation),
            recommendationStatus=recommendation.recommendation_state,
            recommendationPdfLink=_get_recommendation_pdf_link(recommendation, hide_on_going_recommendation),
            inviteReviewerLink=invite_reviewer_links_buttons['invite_reviewer_link'],
            editRecommendationButtonText=recommender_buttons['edit_recommendation_button_text'],
            editRecommendationLink=recommender_buttons['edit_recommendation_link'],
            editRecommendationDisabled=recommender_buttons['edit_recommendation_disabled'],
            reviewsList=reviews_list,
            showSearchingForReviewersButton=False,
            showRemoveSearchingForReviewersButton=invite_reviewer_links_buttons['show_remove_searching_for_reviewers_button'],
            scheduledSubmissionRevision=_is_scheduled_submission_revision(article, printable),
            isScheduledSubmission=is_scheduled_submission(article),
            isScheduledReviewOpen=is_scheduled_review_open(article),
            isArticleSubmitter=(article.user_id == auth.user_id),
            replyButtonDisabled=_reply_button_disabled(article, recommendation),
            scheduledSubmissionEndingButton=_show_scheduled_submission_ending_button(article, recommendation, am_I_co_recommender, printable),
            suspend_submissions=_suspend_submissions(),
            isSchedulingTrack=(pciRRactivated and article.report_stage == "STAGE 1" and (article.is_scheduled or is_scheduled_submission(article))),
            pciRRactivated=pciRRactivated
        )
        
        recommendation_process_components.append(component_vars)
        previous_recommendation = recommendation # iteration is most recent first; last round (final reco) has no author's reply

        # show only current round if user is pending RecommenderAcceptation
        if nb_round == nb_recommendations and _is_pending_recommender_acceptation(article):
            break

    return dict(
        am_I_in_recommender_list=am_I_in_recommender_list,
        am_I_in_co_recommender_list=am_I_in_co_recommender_list,
        components=recommendation_process_components
    )


def get_recommendation_process(article: Article, printable: bool = False):
    response = current.response
    
    process = _get_recommendation_process_components(article)
    process_components = cast(Dict[str, Any], process['components'])
    am_I_in_recommender_list= bool(process['am_I_in_recommender_list'])
    am_I_in_co_recommender_list = bool(process['am_I_in_co_recommender_list'])
        
    recommendation_rounds_html = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))
    for component in process_components:
        recommendation_rounds_html.append(XML(response.render("components/recommendation_process.html", component))) # type: ignore

    # Manager button
    manager_button = _get_manager_button(article, am_I_in_recommender_list or am_I_in_co_recommender_list) \
            if not printable else None

    return DIV(recommendation_rounds_html, BR(), manager_button or "")

########################################################################################################################################################################

def is_scheduled_review_open(article):
    return scheduledSubmissionActivated and (
        article.scheduled_submission_date is not None
        or article.status.startswith("Scheduled submission")
    )


# TODO: investigate why this is not is_scheduled_submission()
def is_scheduled_track(article):
    return article.status == "Scheduled submission pending"


def is_stage_1(article):
    return article.report_stage == "STAGE 1"


def sorry_you_are_coauthor_note():
            if pciRRactivated: note = "Note: Since you have been declared as a co-author of this submission, you cannot take part in the reviewing process."
            else: note = "Note: Since you have been declared as a co-author of this submitted preprint, you cannot take part in the reviewing process."
            return DIV(
                B(current.T(note)),
                _class="pci2-flex-center"
            )


def sorry_you_are_recommender_note():
            return DIV(
                B(current.T("Note: you also served as the Recommender for this submission, please ensure that another member of the Managing Board performs the validation")),
                _class="pci2-flex-center"
            )


def validate_stage_button(article: Article):
            if article.status == ArticleStatus.PENDING.value:
                button = manager_action_button(
                    "do_validate_article",
                    "Validate this submission",
                    "Click here to validate this request and start recommendation process",
                    article,
                    extra_button=[put_in_presubmission_button(article), set_to_not_considered(article)],
                )
                return SPAN(
                    validation_checklist('do_validate_article') if not pciRRactivated else "",
                    button)
            elif article.status == ArticleStatus.PRE_SUBMISSION.value:
                return manager_action_button(
                    "send_submitter_generic_mail",
                    "Request Changes from Author",
                    "Click here to validate recommendation of this article",
                    article, base="manager",
                    style="default",
                )
            elif article.status == ArticleStatus.PRE_RECOMMENDED.value or article.status == ArticleStatus.PRE_RECOMMENDED_PRIVATE.value:
                onclick_content = 'return;'

                if not pciRRactivated and hypothesis.Hypothesis.may_have_annotation(article.doi):
                    onclick_content = 'showInfoDialogBeforeValidateRecommendation(event);'

                button = manager_action_button(
                    "do_recommend_article",
                    "Validate this recommendation",
                    "Click here to validate recommendation of this article",
                    article, send_back_button(article), onclick=onclick_content
                )

                return SPAN(H2(I(_style="margin-right: 10px", _class="glyphicon glyphicon-education"),
                    "To be checked",
                    _style="margin-top:40px", 
                    _id="title-recomm-process", 
                    _class="pci2-recomm-article-h2 pci2-flex-grow pci2-flex-row pci2-align-items-center" ),
                    validation_checklist('do_recommend_article') if not pciRRactivated else "",
                    button)
            
            elif article.status == ArticleStatus.PRE_REVISION.value:
                button = manager_action_button(
                    "do_revise_article",
                    "Validate this decision",
                    "Click here to validate revision of this article",
                    article, send_back_button(article),
                    style="info",
                )

                return SPAN(H2(I(_style="margin-right: 10px", _class="glyphicon glyphicon-education"),
                    "To be checked",
                    _style="margin-top:40px", 
                    _id="title-recomm-process", 
                    _class="pci2-recomm-article-h2 pci2-flex-grow pci2-flex-row pci2-align-items-center" ),
                    validation_checklist('do_revise_article') if not pciRRactivated else "",
                    button)
            elif article.status == ArticleStatus.PRE_REJECTED.value:
                button = manager_action_button(
                    "do_reject_article",
                    "Validate this rejection",
                    "Click here to validate the rejection of this article",
                    article, send_back_button(article),
                    style="info",
                )

                return SPAN(H2(I(_style="margin-right: 10px", _class="glyphicon glyphicon-education"),
                    "To be checked",
                    _style="margin-top:40px", 
                    _id="title-recomm-process", 
                    _class="pci2-recomm-article-h2 pci2-flex-grow pci2-flex-row pci2-align-items-center" ),
                    validation_checklist('do_reject_article') if not pciRRactivated else "",
                    button)
            
            elif article.status == ArticleStatus.SCHEDULED_SUBMISSION_PENDING.value:
                managerButton = validate_scheduled_submission_button(articleId=article.id)

            return None


def manager_action_button(action, text, info_text, art, extra_button="", style="success", base="manager_actions", onclick="return;"):
    return DIV(
        A(
            SPAN(current.T(text),
                _style="width: 100%; margin: 0",
                _class="buttontext btn btn-"+str(style)+" pci-manager"),
            _href=URL(c=base, f=action, vars=dict(articleId=art.id)),
            _title=current.T(info_text),
            _style="display: inline-block",
            _id=action,
            _onclick=onclick
        ),
       LI(extra_button,_style="display: inline-block"),
        _class="pci-EditButtons-centered  nav",
    )


def put_in_presubmission_button(art):
    return manager_action_button(
            "pre_submission_list",
            "Put in Pre-submission list",
            "Click here to put this article in a pre-submission stage",
            art,
            style="default",
    )[0]

def set_to_not_considered(art):
    return manager_action_button(
            "set_not_considered",
            current.T('Prepare email informing authors that preprint not considered'),
            "Click here to set this article to not considered",
            art,
            style="danger",
            onclick=f'callNotConsideredDialog(event, {art.id}, "{URL(c="manager_actions", f="get_not_considered_dialog", vars=dict(articleId=art.id), user_signature=True)}");'
    )[0]

def send_back_button(art):
    return A(
        SPAN(current.T("Send back this decision to the recommender"), _class="buttontext btn btn-danger pci-manager"),
        _href=URL(c="manager_actions", f="prepare_send_back", vars=dict(articleId=art.id), user_signature=True),
        _title=current.T("Click here to send back this decision to the recommender"),
        _id="btn-send-back-decision",
    )


def validate_scheduled_submission_button(articleId, **extra_vars):
    return DIV(
            A(
                SPAN(current.T("Validate this scheduled submission"), _class="buttontext btn btn-success pci-manager"),
                _href=URL(c="manager_actions", f="do_validate_scheduled_submission", vars=dict(articleId=articleId, **extra_vars)),
                _title=current.T("Click here to validate the full manuscript of this scheduled submission"),
            ),
            A(
                SPAN(current.T("Revise prior to review"), _class="buttontext btn btn-warning pci-manager"),
                _href=URL(c="recommender_actions", f="revise_scheduled_submission", vars=dict(articleId=articleId, **extra_vars)),
                _title=current.T("Click here to revise the full manuscript of this scheduled submission"),
            ),
            A(
                SPAN(current.T("Reject without review"), _class="buttontext btn btn-danger pci-manager"),
                _href=URL(c="recommender_actions", f="reject_scheduled_submission", vars=dict(articleId=articleId, **extra_vars)),
                _title=current.T("Click here to reject the full manuscript of this scheduled submission"),
            ),
            _class="pci-EditButtons-centered",
    )

def validation_checklist(validation_type):
    if validation_type == 'do_validate_article':
        checkboxes = {
            "article_doi_correct":
            "DOI/URL of article is correct",

            "data_ok":
            "Link for data is ok",

            "code_and_scripts_ok":
            "Link for code and scripts is ok",

            "scope_ok":
            "Scope is ok",

            "information_consistent":
            "The information about the data/scripts/codes on the submission page and in the manuscript are consistent",

            "no_plagiarism":
            "No plagiarism has been detected ",
        }
    elif validation_type == 'do_recommend_article':
        checkboxes = {
            "title_present":
            "The recommendation has a title",

            "recommendation_explains":
            "The recommendation explains why the article is recommended",

            "recommendation_cites":
            "The recommendation text cites at least the recommended preprint",

            "format_ok":
            "The recommendation is correctly formatted (DOIs in references, links of URLs, title of the 'References' section, cf other published recommendations)",
        }
    elif validation_type in ['do_revise_article', 'do_reject_article']:
        checkboxes = {
            "reviews_ok":
            "Reviews are not too short, are comprehensive and look fine in their tone",

            "reviews_not_copied":
            "Reviews have not been copied by the recommender in their editorial decision box",

            "decision_ok":
            "The editorial decision looks fine on the tone and is overall in agreement with the reviews",
        }

    fields = [
        DIV(INPUT(
            _name=name,
            _type="checkbox",
            _id=name,
            requires=IS_NOT_EMPTY(),
        ), LABEL(H5(label), _for=name), _id='chckbxs_mandatory')
        for name, label in checkboxes.items()
    ]
    script = common_tools.get_script("validate_submission.js")
    return DIV(*fields, script, _id="validation_checklist")

######################################################################################################################################
# Postprint recommendation process
######################################################################################################################################
def getPostprintRecommendation(auth, db, response, art, printable=False, quiet=True):
    recommendationDiv = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))

    recomm = db.get_last_recomm(art.id)

    if not recomm:
        recommendationDiv.append("NO RECOMMENDATION")
        return recommendationDiv

    whoDidIt = common_small_html.getRecommAndReviewAuthors(auth, db, recomm=recomm, with_reviewers=False, linked=not (printable), host=host, port=port, scheme=scheme)

    amICoRecommender = db((db.t_press_reviews.recommendation_id == recomm.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0

    contributors = []
    contrQy = db((db.t_press_reviews.recommendation_id == recomm.id)).select(orderby=db.t_press_reviews.id)
    for contr in contrQy:
        contributors.append(contr.contributor_id)

    editRecommendationLink = None
    sendRecommendationLink = None
    isRecommendationTooShort = True
    addContributorLink = None
    cancelSubmissionLink = None
    if (recomm.recommender_id == auth.user_id or amICoRecommender) and (art.status in ("Under consideration", "Scheduled submission under consideration")) and not (recomm.is_closed) and not (printable):
        # recommender's button allowing recommendation edition
        editRecommendationLink = URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id), user_signature=True, scheme=scheme, host=host, port=port)

        minimal_number_of_corecommenders = 0

        if len(contributors) >= minimal_number_of_corecommenders:
            sendRecommendationLink = URL(c="recommender_actions", f="recommend_article", vars=dict(recommId=recomm.id), user_signature=True, scheme=scheme, host=host, port=port)
            if recomm.recommendation_comments is not None:
                if len(recomm.recommendation_comments) > 50:
                    # recommender's button allowing recommendation submission, provided there are co-recommenders
                    isRecommendationTooShort = False
            else:
                isRecommendationTooShort = True
        else:
            # otherwise button for adding co-recommender(s)
            addContributorLink = URL(c="recommender", f="add_contributor", vars=dict(recommId=recomm.id), user_signature=True, scheme=scheme, host=host, port=port)

        # recommender's button allowing cancellation
        cancelSubmissionLink = URL(c="recommender_actions", f="do_cancel_press_review", vars=dict(recommId=recomm.id), user_signature=True, scheme=scheme, host=host, port=port)

    showRecommendation = False
    if recomm.is_closed or art.status == "Awaiting revision" or art.user_id != auth.user_id:
        showRecommendation = True

    recommendationText = ""
    if len(recomm.recommendation_comments or "") > 2:
        recommendationText = WIKI(recomm.recommendation_comments or "", safe_mode=False)

    validateRecommendationLink = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable):
        if art.status == "Pre-recommended":
            validateRecommendationLink = URL(c="manager_actions", f="do_recommend_article", vars=dict(articleId=art.id), user_signature=True, scheme=scheme, host=host, port=port)

    componentVars = dict(
        printable=printable,
        showRecommendation=True,
        recommendationAuthor=I(current.T("by "), B(whoDidIt), SPAN(", " + recomm.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if recomm.last_change else "")),
        recommendationDoi=SPAN(current.T("Recommendation: "), common_small_html.mkDOI(recomm.recommendation_doi)) if (recomm.recommendation_doi) else "",
        manuscriptDoi=SPAN(current.T("Manuscript: "), common_small_html.mkDOI(recomm.doi)) if (recomm.doi) else "",
        recommendationTitle=H4(common_small_html.md_to_html(recomm.recommendation_title) or "", _style="font-weight: bold; margin-top: 5px; margin-bottom: 20px")
        if (recomm.recommendation_title or "") != ""
        else "",
        recommendationText=recommendationText,
        editRecommendationLink=editRecommendationLink,
        sendRecommendationLink=sendRecommendationLink,
        isRecommendationTooShort=isRecommendationTooShort,
        addContributorLink=addContributorLink,
        cancelSubmissionLink=cancelSubmissionLink,
        validateRecommendationLink=validateRecommendationLink,
    )
    recommendationDiv.append(XML(response.render("components/postprint_recommendation.html", componentVars)))

    return recommendationDiv
