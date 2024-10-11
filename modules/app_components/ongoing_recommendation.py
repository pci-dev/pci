# -*- coding: utf-8 -*-
from datetime import timedelta
from typing import Any, Dict, List, Optional, cast
from dateutil.relativedelta import *

from gluon import current
from gluon.html import *
from gluon.contrib.markdown import WIKI # type: ignore
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon.sqlhtml import *
from app_modules.helper import *
from models.mail_queue import MailQueue, SendingStatus
from models.recommendation import Recommendation, RecommendationState

from app_modules import common_tools
from app_modules import common_small_html
from app_modules import hypothesis
from models.article import ArticleStatus, Article

from controller_modules import manager_module
from models.article import is_scheduled_submission
from models.group import Role
from models.review import Review, ReviewState
from models.suggested_recommender import SuggestedRecommender

myconf = AppConfig(reload=True)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

########################################################################################################################################################################
def getRecommStatusHeader(art: Article, userDiv: bool, printable: bool, quiet: bool = True):
    db, auth, request = current.db, current.auth, current.request

    lastRecomm = db.get_last_recomm(art.id)
    co_recommender = False
    if lastRecomm:
        co_recommender = is_co_recommender(lastRecomm.id)

    if userDiv:
        statusDiv = DIV(
            common_small_html.mkStatusBigDivUser(art.status, printable),
            _class="pci2-flex-center pci2-full-width",
        )
    else:
        statusDiv = DIV(common_small_html.mkStatusBigDiv(art.status, printable), _class="pci2-flex-center pci2-full-width")


    myTitle = DIV(
        IMG(_src=common_tools.URL(r=request, c="static", f="images/small-background.png", scheme=True)),
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

    back2 = common_tools.URL(re.sub(r".*/([^/]+)$", "\\1", request.env.request_uri), scheme=True)

    allowManageRequest = False
    manageRecommendersButton = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (quiet):
        allowManageRequest = True
        manageRecommendersButton = manager_module.mkSuggestedRecommendersManagerButton(art, back2)
    
    if pciRRactivated and lastRecomm and ((lastRecomm.recommender_id == auth.user_id or co_recommender) and lastRecomm.recommendation_state in ("Ongoing", "Revision")) and auth.has_membership(role="recommender") and not(quiet):
       allowManageRequest = True

    printableUrl = None
    verifyUrl = None
    if auth.has_membership(role="manager"):
        printableUrl = common_tools.URL(c="manager", f="article_emails", vars=dict(articleId=art.id, printable=True), scheme=True)
    
    if (auth.has_membership(role="recommender") or auth.has_membership(role="manager")) and art.user_id != auth.user_id:
        verifyUrl = common_tools.URL(c="recommender", f="verify_co_authorship", vars=dict(articleId=art.id, printable=True), scheme=True)

    recommenderSurveyButton = None
    if lastRecomm and (auth.user_id == lastRecomm.recommender_id or co_recommender):
        printableUrl = common_tools.URL(c="recommender", f="article_reviews_emails", vars=dict(articleId=art.id), scheme=True)
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

    return XML(current.response.render("components/recommendation_header.html", componentVars))


######################################################################################################################################################################
def getRecommendationTopButtons(art: Article, printable: bool = False, quiet: bool = True):
    db, auth = current.db, current.auth

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
        btsAccDec: List[DIV] = [
            A(
                SPAN(current.T("Yes, I would like to handle the evaluation process"), _class="buttontext btn btn-success pci-recommender"),
                _href=common_tools.URL(c="recommender", f="accept_new_article_to_recommend", vars=dict(articleId=art.id), scheme=True),
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
                    _href=common_tools.URL(c="recommender_actions", f="decline_new_article_to_recommend", vars=dict(articleId=art.id), scheme=True),
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

        myButtons.append(DIV(btsAccDec, _class="pci2-flex-grow pci2-flex-center" + buttonDivClass, _style="margin:10px")) # type: ignore

    if (
        (art.user_id == auth.user_id)
        and not (art.already_published)
        and (art.status not in ("Cancelled", "Rejected", "Pre-recommended", "Recommended", "Not considered"))
        and not (printable)
        and not (quiet)
    ):
        myButtons.append( # type: ignore
            DIV(
                A(
                    SPAN(current.T("I wish to cancel my submission"), _class="buttontext btn btn-warning pci-submitter"),
                    _href=common_tools.URL(c="user_actions", f="do_cancel_article", vars=dict(articleId=art.id), scheme=True),
                    _title=current.T("Click here in order to cancel this submission"),
                ),
                _class="pci-EditButtons pci2-flex-grow pci2-flex-center",
                _id="cancel-submission-button",
            )
        ) # author's button allowing cancellation 

    myContents.append(myButtons) # type: ignore

    return myContents


########################################################################################################################################################################
def getRecommendationProcessForSubmitter(art: Article, printable: bool):
    if pciRRactivated:
        return getRecommendationProcessForSubmitterRR(art, printable)
    
    db = current.db

    is_submitter = bool(art.user_id == current.auth.user_id)

    recommendationDiv = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))

    submissionValidatedClass = "step-done"
    havingRecommenderClass = "step-default"
    reviewInvitationsAcceptedClass = "step-default"
    reviewsStepDoneClass = "step-default"
    recommendationStepClass = "step-default"
    managerDecisionDoneClass = "step-default"
    articleHasBeenCompleted = True
    isRecommAvalaibleToSubmitter = False
    nb_days_since_completion = 0

    if art.status == ArticleStatus.PRE_SUBMISSION.value:
        articleHasBeenCompleted = False

    if art.upload_timestamp: 
        nb_days = (datetime.datetime.now() - art.upload_timestamp).days

        if nb_days == 0:
            nb_days_since_completion = -1
        else:
            nb_days_since_completion = nb_days

    if not articleHasBeenCompleted and not art.validation_timestamp:
        submissionValidatedClass = "step-default"

    uploadDate = art.upload_timestamp.strftime("%d %B %Y") if art.upload_timestamp else ''
    validation_article_date = art.validation_timestamp.strftime("%d %B %Y") if art.validation_timestamp else ""

    invited_suggested_recommender_count = SuggestedRecommender.nb_suggested_recommender(art.id)
    declined_suggested_recommender_count = SuggestedRecommender.nb_suggested_recommender(art.id, declined=True)

    scheduled_reminder_suggested_recommender = \
    len(MailQueue.get_by_article_and_template(art, "#ReminderSubmitterSuggestedRecommenderNeeded", [SendingStatus.PENDING])) > 0 or \
    len(MailQueue.get_by_article_and_template(art, "#ReminderSubmitterNewSuggestedRecommenderNeeded", [SendingStatus.PENDING])) > 0

    recomms = Article.get_last_recommendations(art.id, db.t_recommendations.id)
    totalRecomm = len(recomms)

    if validation_article_date:
        havingRecommenderClass = "step-done"

    roundNumber = 1

    recommStatus: Optional[str] = None
    reviewCount = 0
    acceptedReviewCount = 0
    completedReviewCount = 0
    declined_review_count = 0
    there_are_review_reminder = False
    reviewers: List[DIV] = []

    recommenderName: Optional[List[Any]] = None

    if totalRecomm > 0:
        for recomm in recomms:
            reviewInvitationsAcceptedClass = "step-done"
            reviewsStepDoneClass = "step-default"
            recommendationStepClass = "step-default"
            managerDecisionDoneClass = "step-default"
            authorsReplyClass = "step-default"
            recommendation_last_change = recomm.last_change.strftime("%d %B %Y") if recomm.last_change else ""
            recommendation_date = recomm.recommendation_timestamp.strftime("%d %B %Y") if recomm.recommendation_timestamp else ""
            validationDate = recomm.validation_timestamp.strftime("%d %B %Y") if recomm.validation_timestamp else None
            nb_days_since_decision = 0
            nb_days_since_validation = 0
            decision_due_date: Optional[datetime.datetime] = None

            if recomm.last_change:
                nb_days = (datetime.datetime.now() - recomm.last_change).days

                if nb_days == 0:
                    nb_days_since_decision = -1
                else:
                    nb_days_since_decision = nb_days

            if recomm.validation_timestamp:
                nb_days = (datetime.datetime.now() - recomm.validation_timestamp).days

                if nb_days == 0:
                    nb_days_since_validation = -1
                else:
                    nb_days_since_validation = nb_days


            if roundNumber < totalRecomm:
                nextRound = recomms[roundNumber]
                authorsReplyDate = nextRound.recommendation_timestamp.strftime(DEFAULT_DATE_FORMAT) if nextRound.recommendation_timestamp else ""
            else:
                authorsReplyDate = None # current round

            recommenderName = common_small_html.getRecommAndReviewAuthors(
                recomm=recomm, with_reviewers=False, linked=not (printable), fullURL=True,
            )

            recommStatus = None
            reviewCount = 0
            acceptedReviewCount = 0
            completedReviewCount = 0
            declined_review_count = 0

            if roundNumber < 2:
                there_are_review_reminder = \
                len(MailQueue.get_by_article_and_template(art, "#ReminderRecommenderReviewersNeeded", [SendingStatus.PENDING])) > 0 or \
                len(MailQueue.get_by_article_and_template(art, "#ReminderRecommenderNewReviewersNeeded", [SendingStatus.PENDING])) > 0

                there_are_recommendation_reminder = len(MailQueue.get_by_article_and_template(art,
                                                                                              ["#ReminderRecommenderDecisionOverDue"
                                                                                               "#ReminderRecommenderDecisionSoonDue",
                                                                                               "#ReminderRecommenderDecisionDue"],
                                                                                               [SendingStatus.PENDING])) > 0
            else:
                there_are_recommendation_reminder = len(MailQueue.get_by_article_and_template(art,
                                                                                              ["#ReminderRecommenderRevisedDecisionOverDue",
                                                                                               "#ReminderRecommenderDecisionOverDue"
                                                                                               "#ReminderRecommenderDecisionSoonDue",
                                                                                               "#ReminderRecommenderDecisionDue"], [SendingStatus.PENDING])) > 0

                there_are_review_reminder = \
                    len(MailQueue.get_by_article_and_template(art, "#ReminderReviewerReviewInvitationNewUser", [SendingStatus.PENDING])) > 0 or \
                    len(MailQueue.get_by_article_and_template(art, "#ReminderReviewerReviewInvitationRegisteredUser", [SendingStatus.PENDING])) > 0 or \
                    len(MailQueue.get_by_article_and_template(art, "#ReminderReviewerInvitationNewRoundRegisteredUser", [SendingStatus.PENDING])) > 0

            reviews = Review.get_by_recommendation_id(recomm.id, db.t_reviews.id)

            lastReviewDate: Optional[datetime.datetime] = None
            reviewer_name: Optional[str] = None
            reviewers = []

            for review in reviews:
                reviewCount += 1
                if review.review_state == ReviewState.AWAITING_REVIEW.value:
                    acceptedReviewCount += 1
                if review.review_state == ReviewState.REVIEW_COMPLETED.value:
                    acceptedReviewCount += 1
                    completedReviewCount += 1
                if review.review_state in (ReviewState.DECLINED.value, ReviewState.DECLINED_MANUALLY.value, ReviewState.DECLINED_BY_RECOMMENDER.value, ReviewState.CANCELLED.value):
                    declined_review_count += 1
                if review.last_change and review.review_state == ReviewState.REVIEW_COMPLETED.value:
                    if not lastReviewDate:
                        lastReviewDate = review.last_change
                    elif review.last_change > lastReviewDate:
                        lastReviewDate = review.last_change

                if is_submitter:
                    reviewer_name = f"Anonymous reviewer"
                elif current.auth.has_membership(role=Role.MANAGER.value) or current.auth.has_membership(role=Role.RECOMMENDER.value):
                    reviewer_name = Review.get_reviewer_name(review)
                else:
                    if review.anonymously:
                        reviewer_name = f"Anonymous reviewer"
                    else:
                        reviewer_name = Review.get_reviewer_name(review)

                if review.review_state == ReviewState.REVIEW_COMPLETED.value:
                    completed_date = review.last_change.strftime("%d %B %Y") if review.last_change else ""
                    reviewers.append(DIV(SPAN(SPAN(reviewer_name, _style="color: #29abe0") + ", completed: " , _style="font-weight: bold"), completed_date))
                elif review.review_state == ReviewState.AWAITING_REVIEW.value:
                    due_date = Review.get_due_date(review).strftime("%d %B %Y")
                    reviewers.append(DIV(SPAN(SPAN(reviewer_name, _style="color: #29abe0") + ", due date: ", _style="font-weight: bold"), due_date))

            if acceptedReviewCount == 0 and not there_are_review_reminder and art.last_status_change:
                decision_due_date = art.last_status_change + timedelta(days=10)

            if roundNumber < 2:
                if acceptedReviewCount >= 2:
                    reviewsStepDoneClass = "step-done"
            else:
                if completedReviewCount == acceptedReviewCount and completedReviewCount >= 1 and not there_are_review_reminder:
                    reviewsStepDoneClass = "step-done"

            if reviewsStepDoneClass == "step-done" and lastReviewDate:
                decision_due_date = lastReviewDate + timedelta(days=10)
                
            if completedReviewCount == acceptedReviewCount and completedReviewCount >= 2:
                recommendationStepClass = "step-done"

            if recomm.recommendation_state == "Rejected" or recomm.recommendation_state == "Recommended" or recomm.recommendation_state == "Revision":
                recommendationStepClass = "step-done"
                managerDecisionDoneClass = "step-done"
                recommStatus = recomm.recommendation_state

            if (roundNumber == totalRecomm and art.status in (ArticleStatus.REJECTED.value,
                                                              ArticleStatus.RECOMMENDED.value,
                                                              ArticleStatus.AWAITING_REVISION.value,
                                                              ArticleStatus.SCHEDULED_SUBMISSION_REVISION.value,
                                                              ArticleStatus.PRE_REJECTED.value,
                                                              ArticleStatus.PRE_REVISION.value,
                                                              ArticleStatus.PRE_RECOMMENDED.value)) \
                or (roundNumber < totalRecomm and (((recomm.reply is not None) and (len(recomm.reply) > 0)) or (recomm.reply_pdf is not None))):
                managerDecisionDoneClass = "step-done"

            if recommStatus == "Revision" and managerDecisionDoneClass == "step-done":
                managerDecisionDoneStepClass = "progress-step-div"
            else:
                managerDecisionDoneStepClass = "progress-last-step-div"

            if validationDate:
                authorsReplyClass = "step-done"

            if (roundNumber < totalRecomm) and (((recomm.reply is not None) and (len(recomm.reply) > 0)) or (recomm.reply_pdf is not None)):
                authorsReplyClass = "step-done"
            else:
                authorsReplyClass = "step-done current-step"

            if roundNumber == totalRecomm and recommStatus == "Revision" and managerDecisionDoneClass == "step-done":
                authorsReplyClassStepClass = "progress-last-step-div"
            else:
                authorsReplyClassStepClass = "progress-step-div"

            recommendationLink: Optional[str] = None
            if recommStatus == "Recommended" and managerDecisionDoneClass == "step-done":
                recommendationLink = common_tools.URL(c="articles", f="rec", vars=dict(id=art.id), scheme=True)

            componentVars = dict(
                printable=printable,
                roundNumber=roundNumber,
                article=art,
                submissionValidatedClass=submissionValidatedClass,
                havingRecommenderClass=havingRecommenderClass,
                invitedSuggestedRecommenderCount=invited_suggested_recommender_count,
                declined_suggested_recommender_count=declined_suggested_recommender_count,
                recommenderName=recommenderName,
                reviewInvitationsAcceptedClass=reviewInvitationsAcceptedClass,
                reviewCount=reviewCount,
                lastReviewDate=lastReviewDate.strftime("%d %B %Y") if lastReviewDate else '',
                acceptedReviewCount=acceptedReviewCount,
                reviewsStepDoneClass=reviewsStepDoneClass,
                completedReviewCount=completedReviewCount,
                recommendationStepClass=recommendationStepClass,
                recommStatus=recommStatus,
                recommendation_last_change=recommendation_last_change,
                validationDate = validationDate,
                authorsReplyDate=authorsReplyDate,
                managerDecisionDoneClass=managerDecisionDoneClass,
                managerDecisionDoneStepClass=managerDecisionDoneStepClass,
                authorsReplyClass=authorsReplyClass,
                authorsReplyClassStepClass=authorsReplyClassStepClass,
                totalRecomm=totalRecomm,
                recommendationLink=recommendationLink,
                uploadDate=uploadDate,
                validationArticleDate=validation_article_date,
                articleHasBeenCompleted=articleHasBeenCompleted,
                nbDaysSinceCompletion=nb_days_since_completion,
                scheduled_reminder_suggested_recommender=scheduled_reminder_suggested_recommender,
                recommendation_date=recommendation_date,
                declined_review_count=declined_review_count,
                there_are_review_reminder=there_are_review_reminder,
                reviewers=reviewers,
                there_are_recommendation_reminder=there_are_recommendation_reminder,
                nb_days_since_decision=nb_days_since_decision,
                nb_days_since_validation=nb_days_since_validation,
                decision_due_date=decision_due_date.strftime("%d %B %Y") if decision_due_date else ''
            )
            recommendationDiv.append(XML(current.response.render("components/recommendation_process_for_submitter.html", componentVars))) # type: ignore

            roundNumber += 1

    else:
        managerDecisionDoneStepClass = "progress-last-step-div"
        recommendation_last_change = False
        lastReviewDate: Optional[datetime.datetime] = None
        authorsReplyDate = False
        validationDate = False

        componentVars = dict(
            printable=printable,
            roundNumber=roundNumber,
            article=art,
            submissionValidatedClass=submissionValidatedClass,
            havingRecommenderClass=havingRecommenderClass,
            invitedSuggestedRecommenderCount=invited_suggested_recommender_count,
            declined_suggested_recommender_count=declined_suggested_recommender_count,
            recommenderName=recommenderName,
            reviewInvitationsAcceptedClass=reviewInvitationsAcceptedClass,
            reviewCount=reviewCount,
            lastReviewDate=lastReviewDate.strftime("%d %B %Y") if lastReviewDate else '',
            acceptedReviewCount=acceptedReviewCount,
            reviewsStepDoneClass=reviewsStepDoneClass,
            completedReviewCount=completedReviewCount,
            recommendationStepClass=recommendationStepClass,
            recommStatus=recommStatus,
            recommendation_last_change=recommendation_last_change,
            validationDate = validationDate,
            validationArticleDate=validation_article_date,
            authorsReplyDate=authorsReplyDate,
            managerDecisionDoneClass=managerDecisionDoneClass,
            managerDecisionDoneStepClass=managerDecisionDoneStepClass,
            totalRecomm=totalRecomm,
            uploadDate=uploadDate,
            articleHasBeenCompleted=articleHasBeenCompleted,
            nbDaysSinceCompletion=nb_days_since_completion,
            scheduled_reminder_suggested_recommender=scheduled_reminder_suggested_recommender,
            declined_review_count=declined_review_count,
            there_are_review_reminder=there_are_review_reminder,
            recommendation_date="",
            reviewers=reviewers,
            there_are_recommendation_reminder=False,
            nb_days_since_decision=0,
            nb_days_since_validation=0,
            decision_due_date=None
        )

        recommendationDiv.append(XML(current.response.render("components/recommendation_process_for_submitter.html", componentVars))) # type: ignore
    if (managerDecisionDoneClass == "step-done") or (managerDecisionDoneClass == "step-default" and art.status == "Recommended-private"):
        isRecommAvalaibleToSubmitter = True
    return dict(roundNumber=totalRecomm, isRecommAvalaibleToSubmitter=isRecommAvalaibleToSubmitter, content=recommendationDiv)


def getRecommendationProcessForSubmitterRR(art: Article, printable: bool):
    db = current.db

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
    uploadDate = art.upload_timestamp.strftime("%d %B %Y") if art.upload_timestamp else ''

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
                recomm=recomm, with_reviewers=False, linked=not (printable), fullURL=True,
            )

            recommStatus = None
            reviewCount = 0
            acceptedReviewCount = 0
            completedReviewCount = 0

            reviews = cast(List[Review], db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state != "Cancelled")).select(
                orderby=db.t_reviews.id
            ))

            lastReviewDate: Optional[datetime.datetime] = None
            for review in reviews:
                reviewCount += 1
                if review.review_state == "Awaiting review":
                    acceptedReviewCount += 1
                if review.review_state == "Review completed":
                    acceptedReviewCount += 1
                    completedReviewCount += 1
                if review.last_change:
                    if not lastReviewDate:
                        lastReviewDate = review.last_change
                    elif review.last_change > lastReviewDate:
                        lastReviewDate = review.last_change

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
                recommendationLink = common_tools.URL(c="articles", f="rec", vars=dict(id=art.id), scheme=True)

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
                lastReviewDate=lastReviewDate.strftime("%d %B %Y") if lastReviewDate else '',
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
            recommendationDiv.append(XML(current.response.render("components/recommendation_process_for_submitter_rr.html", componentVars))) # type: ignore

            roundNumber += 1

    else:
        managerDecisionDoneStepClass = "progress-last-step-div"
        recommDate = False
        lastReviewDate = None
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
            lastReviewDate=lastReviewDate.strftime("%d %B %Y") if lastReviewDate else '',
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

        recommendationDiv.append(XML(current.response.render("components/recommendation_process_for_submitter_rr.html", componentVars))) # type: ignore
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
                    return next_round.recommendation_timestamp


def _get_author_reply_formatted_date(recommendation: Recommendation, next_round: Optional[Recommendation], nb_round: int, nb_recommendations: int):
    date = _get_author_reply_date(recommendation, next_round, nb_round, nb_recommendations)
    if date:
        return date.strftime(DEFAULT_DATE_FORMAT+ " %H:%M")


def _get_author_reply_link(article: Article, recommendation: Recommendation, printable: bool, i_recommendation: int):
    auth = current.auth

    if (article.user_id == auth.user_id) and (article.status == ArticleStatus.AWAITING_REVISION.value) and not (printable) and (i_recommendation == 1):
        return common_tools.URL(c="user", f="edit_reply", vars=dict(recommId=recommendation.id), user_signature=True, scheme=True)


def _get_authors_reply_pdf_link(recommendation: Recommendation):
    if recommendation.reply_pdf:
        return A(
            I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
            current.T("Download author's reply (PDF file)"),
            _href=common_tools.URL("default", "download", args=recommendation.reply_pdf, scheme=True),
            _style="font-weight: bold; margin-bottom: 5px; display:block",
        )


def _is_scheduled_submission_revision(article: Article, printable: bool):
    auth = current.auth

    if (article.status == ArticleStatus.SCHEDULED_SUBMISSION_REVISION.value) and (article.user_id == auth.user_id) and not (printable):
        return common_tools.URL(c="user_actions", f="article_revised", vars=dict(articleId=article.id), user_signature=True, scheme=True)
    

def _get_authors_reply_track_change_file_link(recommendation: Recommendation):
    if recommendation.track_change:
        return A(
            I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
            current.T("Download tracked changes file"),
            _href=common_tools.URL("default", "download", args=recommendation.track_change, scheme=True),
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
    auth = current.auth

    review_vars: Dict[str, Any] = dict(
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
                review=review,
                reviewDatetime=None
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
    review_vars.update([("reviewDatetime", review_date)])
    review_date_str = review_date.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review_date else ""

    if not (hide_on_going_review):
        # display the review
        if review.anonymously:
            count_anonymous_review += 1
            reviewer_number = common_tools.find_reviewer_number(review, count_anonymous_review)
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
                            common_small_html.mkUser(review.reviewer_id, linked=True),
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
                _href=common_tools.URL("default", "download", args=review.review_pdf, scheme=True),
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
        edit_recommendation_link = common_tools.URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recommendation.id), scheme=True)
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
        invite_reviewer_link = common_tools.URL(c="recommender", f="reviewers", vars=dict(recommId=recommendation.id), scheme=True)
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
            _href=common_tools.URL("default", "download", args=recommendation.recommender_file, scheme=True),
            _style="font-weight: bold; margin-bottom: 5px; display:block",
        )
    return recommendation_pdf_link


def _mk_link(role: Role, action: str, review_item: Dict[Any, Any]):
    return common_tools.URL(c=role.value+"_actions", f=action+"_review_request", vars=dict(reviewId=review_item["id"]), scheme=True)


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
    

def get_recommendation_process_components(article: Article, printable: bool = False):
    auth = current.auth
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
        who_did_it_html = common_small_html.getRecommAndReviewAuthors(recomm=recommendation, with_reviewers=False, linked=not (printable),
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
            authorsReplyDate=_get_author_reply_formatted_date(recommendation, previous_recommendation, nb_round, nb_recommendations),
            authorsReplyDatetime=_get_author_reply_date(recommendation, previous_recommendation, nb_round, nb_recommendations),
            authorsReplyPdfLink=_get_authors_reply_pdf_link(recommendation),
            authorsReplyTrackChangeFileLink=_get_authors_reply_track_change_file_link(recommendation),
            editAuthorsReplyLink=_get_author_reply_link(article, recommendation, printable, i_recommendation),
            recommendationAuthor=I(current.T("by "), B(who_did_it_html), SPAN(", " + recommendation.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if recommendation.last_change else "")),
            recommendationAuthorName=B(who_did_it_html),
            recommendationDate=recommendation.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if recommendation.last_change else "",
            recommendationDatetime=recommendation.last_change,
            recommendationValidationDate=recommendation.validation_timestamp.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if recommendation.validation_timestamp else "",
            recommendationValidationDatetime=recommendation.validation_timestamp,
            manuscriptDoi=SPAN(current.T("Manuscript:") + " ", common_small_html.mkDOI(recommendation.doi)) if (recommendation.doi) else SPAN(""),
            recommendationVersion=SPAN(" " + current.T("version:") + " ", recommendation.ms_version) if (recommendation.ms_version) else SPAN(""),
            recommendationTitle=H4(common_small_html.md_to_html(recommendation.recommendation_title) or "", _style="font-weight: bold; margin-top: 5px; margin-bottom: 20px") if (hide_on_going_recommendation is False and recommendation.recommendation_title) else "",
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
            pciRRactivated=pciRRactivated,
            recommenderId=recommendation.recommender_id
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
    
    process = get_recommendation_process_components(article)
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

def is_scheduled_review_open(article: Article):
    return scheduledSubmissionActivated and (
        article.scheduled_submission_date is not None
        or article.status.startswith("Scheduled submission")
    )


# TODO: investigate why this is not is_scheduled_submission()
def is_scheduled_track(article: Article):
    return article.status == "Scheduled submission pending"


def is_stage_1(article: Article):
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

            return None


def manager_action_button(action: str, text: str, info_text: str, art: Article, extra_button: Any = "", style: str ="success", base: str = "manager_actions", onclick: str = "return;"):
    return DIV(
        A(
            SPAN(current.T(text),
                _style="width: 100%; margin: 0",
                _class="buttontext btn btn-"+str(style)+" pci-manager"),
            _href=common_tools.URL(c=base, f=action, vars=dict(articleId=art.id)),
            _title=current.T(info_text),
            _style="display: inline-block",
            _id=action,
            _onclick=onclick
        ),
       LI(extra_button,_style="display: inline-block"),
        _class="pci-EditButtons-centered  nav",
    )


def put_in_presubmission_button(art: Article) -> Optional[Any]:
    return manager_action_button(
            "pre_submission_list",
            "Put in Pre-submission list",
            "Click here to put this article in a pre-submission stage",
            art,
            style="default",
    )[0] # type: ignore

def set_to_not_considered(art: Article) -> Optional[Any]:
    return manager_action_button(
            "set_not_considered",
            current.T('Prepare email informing authors that preprint not considered'),
            "Click here to set this article to not considered",
            art,
            style="danger",
            onclick=f'callNotConsideredDialog(event, {art.id}, "{common_tools.URL(c="manager_actions", f="get_not_considered_dialog", vars=dict(articleId=art.id), user_signature=True)}");'
    )[0] # type: ignore

def send_back_button(art: Article):
    return A(
        SPAN(current.T("Send back this decision to the recommender"), _class="buttontext btn btn-danger pci-manager"),
        _href=common_tools.URL(c="manager_actions", f="prepare_send_back", vars=dict(articleId=art.id), user_signature=True),
        _title=current.T("Click here to send back this decision to the recommender"),
        _id="btn-send-back-decision",
    )


def validate_scheduled_submission_button(articleId: int, **extra_vars: ...):
    return DIV(
            A(
                SPAN(current.T("Validate this scheduled submission"), _class="buttontext btn btn-success pci-manager"),
                _href=common_tools.URL(c="manager_actions", f="do_validate_scheduled_submission", vars=dict(articleId=articleId, **extra_vars)),
                _title=current.T("Click here to validate the full manuscript of this scheduled submission"),
            ),
            A(
                SPAN(current.T("Revise prior to review"), _class="buttontext btn btn-warning pci-manager"),
                _href=common_tools.URL(c="recommender_actions", f="revise_scheduled_submission", vars=dict(articleId=articleId, **extra_vars)),
                _title=current.T("Click here to revise the full manuscript of this scheduled submission"),
            ),
            A(
                SPAN(current.T("Reject without review"), _class="buttontext btn btn-danger pci-manager"),
                _href=common_tools.URL(c="recommender_actions", f="reject_scheduled_submission", vars=dict(articleId=articleId, **extra_vars)),
                _title=current.T("Click here to reject the full manuscript of this scheduled submission"),
            ),
            _class="pci-EditButtons-centered",
    )

def validation_checklist(validation_type: str):
    checkboxes: Dict[str, str] = {}

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

            "year_ok":
            "The year of the recommended version of the article (indicated on the 'Edit Article' page) is good. You can find this year by clicking the 'Edit article' tab above.",

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
def getPostprintRecommendation(art: Article, printable: bool = False, quiet: bool = True):
    db, auth = current.db, current.auth
    recommendationDiv = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))

    recomm = db.get_last_recomm(art.id)

    if not recomm:
        recommendationDiv.append("NO RECOMMENDATION") # type: ignore
        return recommendationDiv

    whoDidIt = common_small_html.getRecommAndReviewAuthors(recomm=recomm, with_reviewers=False, linked=not (printable), fullURL=True)

    amICoRecommender = db((db.t_press_reviews.recommendation_id == recomm.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0

    contributors: List[int] = []
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
        editRecommendationLink = common_tools.URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id), scheme=True)

        minimal_number_of_corecommenders = 0

        if len(contributors) >= minimal_number_of_corecommenders:
            sendRecommendationLink = common_tools.URL(c="recommender_actions", f="recommend_article", vars=dict(recommId=recomm.id), scheme=True)
            if recomm.recommendation_comments is not None:
                if len(recomm.recommendation_comments) > 50:
                    # recommender's button allowing recommendation submission, provided there are co-recommenders
                    isRecommendationTooShort = False
            else:
                isRecommendationTooShort = True
        else:
            # otherwise button for adding co-recommender(s)
            addContributorLink = common_tools.URL(c="recommender", f="add_contributor", vars=dict(recommId=recomm.id), scheme=True)

        # recommender's button allowing cancellation
        cancelSubmissionLink = common_tools.URL(c="recommender_actions", f="do_cancel_press_review", vars=dict(recommId=recomm.id), scheme=True)

    recommendationText = ""
    if len(recomm.recommendation_comments or "") > 2:
        recommendationText = WIKI(recomm.recommendation_comments or "", safe_mode='')

    validateRecommendationLink = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable):
        if art.status == "Pre-recommended":
            validateRecommendationLink = common_tools.URL(c="manager_actions", f="do_recommend_article", vars=dict(articleId=art.id), scheme=True)

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
    recommendationDiv.append(XML(current.response.render("components/postprint_recommendation.html", componentVars))) # type: ignore

    return recommendationDiv
