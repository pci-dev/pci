# -*- coding: utf-8 -*-
import os
from re import sub
from dateutil.relativedelta import *

import io

from gluon import current, IS_IN_DB
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.sqlhtml import *

from app_modules import common_tools
from app_modules import common_small_html

from controller_modules import manager_module

myconf = AppConfig(reload=True)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

########################################################################################################################################################################
def getRecommStatusHeader(auth, db, response, art, controller_name, request, userDiv, printable, quiet=True):
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

    recomms = db(db.t_recommendations.article_id == art.id).select(orderby=~db.t_recommendations.id)
    nbRecomms = len(recomms)

    if userDiv:
        statusDiv = DIV(
            common_small_html.mkStatusBigDivUser(auth, db, art.status, printable),
            _class="pci2-flex-center pci2-full-width",
        )
    else:
        statusDiv = DIV(common_small_html.mkStatusBigDiv(auth, db, art.status, printable), _class="pci2-flex-center pci2-full-width")


    myTitle = DIV(
        IMG(_src=URL(r=request, c="static", f="images/small-background.png")),
        DIV(statusDiv, _class="pci2-flex-grow"),
        _class="pci2-flex-row",
    )

    # author's button allowing article edition
    allowEditArticle = False
    if ((art.user_id == auth.user_id) and (art.status in ("Pending", "Awaiting revision"))) and not (quiet):
        allowEditArticle = True

    # manager buttons
    allowManageRecomms = False
    if (nbRecomms > 0 or art.status == "Under consideration") and auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (quiet):
        allowManageRecomms = True

    back2 = URL(re.sub(r".*/([^/]+)$", "\\1", request.env.request_uri), scheme=scheme, host=host, port=port)

    allowManageRequest = False
    manageRecommendersButton = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (quiet):
        allowManageRequest = True
        manageRecommendersButton = manager_module.mkSuggestedRecommendersManagerButton(art, back2, auth, db)

    printableUrl = None
    if auth.has_membership(role="manager"):
        printableUrl = URL(c="manager", f="article_emails", vars=dict(articleId=art.id, printable=True), user_signature=True)

    recommenderSurveyButton = None
    if len(recomms) > 0 and auth.user_id == recomms[-1].recommender_id:
        printableUrl = URL(c="recommender", f="article_reviews_emails", vars=dict(articleId=art.id), user_signature=True)
        recommenderSurveyButton = True

    componentVars = dict(
        statusTitle=myTitle,
        allowEditArticle=allowEditArticle,
        allowManageRecomms=allowManageRecomms,
        allowManageRequest=allowManageRequest,
        manageRecommendersButton=manageRecommendersButton,
        articleId=art.id,
        printableUrl=printableUrl,
        printable=printable,
        pciRRactivated=pciRRactivated,
        recommenderSurveyButton=recommenderSurveyButton
    )

    return XML(response.render("components/recommendation_header.html", componentVars))


######################################################################################################################################################################
def getRecommendationTopButtons(auth, db, art, printable=False, quiet=True, scheme=False, host=False, port=False):

    myContents = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))
    ###NOTE: recommendations counting
    recomms = db(db.t_recommendations.article_id == art.id).select(orderby=~db.t_recommendations.id)
    nbRecomms = len(recomms)
    myButtons = DIV()

    if (
        len(recomms) == 0
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
                _href=URL(c="recommender", f="accept_new_article_to_recommend", vars=dict(articleId=art.id), user_signature=True),
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
                    _href=URL(c="recommender_actions", f="decline_new_article_to_recommend", vars=dict(articleId=art.id), user_signature=True),
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
        and (art.status not in ("Cancelled", "Rejected", "Pre-recommended", "Recommended"))
        and not (printable)
        and not (quiet)
    ):
        myButtons.append(
            DIV(
                A(
                    SPAN(current.T("I wish to cancel my submission"), _class="buttontext btn btn-warning pci-submitter"),
                    _href=URL(c="user_actions", f="do_cancel_article", vars=dict(articleId=art.id), user_signature=True),
                    _title=current.T("Click here in order to cancel this submission"),
                ),
                _class="pci-EditButtons pci2-flex-grow pci2-flex-center",
                _id="cancel-submission-button",
            )
        )  # author's button allowing cancellation

    myContents.append(myButtons)

    return myContents


########################################################################################################################################################################
def getRecommendationProcessForSubmitter(auth, db, response, art, printable, scheme=False, host=False, port=False):
    recommendationDiv = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))

    submissionValidatedClassClass = "step-default"
    havingRecommenderClass = "step-default"
    reviewInvitationsAcceptedClass = "step-default"
    reviewsStepDoneClass = "step-default"
    recommendationStepClass = "step-default"
    managerDecisionDoneClass = "step-default"

    if not (art.status == "Pending"):
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
            authorsReplyDate = (recomm.author_last_change or recomm.last_change).strftime("%d %B %Y")

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

            if completedReviewCount == acceptedReviewCount:
                reviewsStepDoneClass = "step-done"

            if recomm.recommendation_state == "Rejected" or recomm.recommendation_state == "Recommended" or recomm.recommendation_state == "Revision":
                recommendationStepClass = "step-done"
                recommStatus = recomm.recommendation_state

            if (roundNumber == totalRecomm and art.status in ("Rejected", "Recommended", "Awaiting revision")) or (roundNumber < totalRecomm and (((recomm.reply is not None) and (len(recomm.reply) > 0)) or (recomm.reply_pdf is not None))):
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
                recommendationLink = URL(c="articles", f="rec", vars=dict(id=art.id), user_signature=True)

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
            authorsReplyDate=authorsReplyDate,
            managerDecisionDoneClass=managerDecisionDoneClass,
            managerDecisionDoneStepClass=managerDecisionDoneStepClass,
            totalRecomm=totalRecomm,
            uploadDate=uploadDate,
        )

        recommendationDiv.append(XML(response.render("components/recommendation_process_for_submitter.html", componentVars)))

    return dict(roundNumber=totalRecomm, isRecommAvalaibleToSubmitter=(managerDecisionDoneClass == "step-done"), content=recommendationDiv)


########################################################################################################################################################################
# Preprint recommendation process (rounds, recomms, reviews, author's reply)
########################################################################################################################################################################
def getRecommendationProcess(auth, db, response, art, printable=False, quiet=True, scheme=False, host=False, port=False):
    recommendationRounds = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))

    ###NOTE: recommendations counting
    recomms = db(db.t_recommendations.article_id == art.id).select(orderby=~db.t_recommendations.id)
    nbRecomms = len(recomms)

    amIEngagedInStage2Process = False
    if pciRRactivated and art.art_stage_1_id is None:
        authCpt = 0
        # if currentUser is reviewer of a related stage 2
        authCpt += db(
            (db.t_articles.art_stage_1_id == art.id)
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.id == db.t_reviews.recommendation_id)
            & (db.t_reviews.reviewer_id == auth.user_id)
            & (db.t_reviews.review_state != "Willing to review")
        ).count()
        # if currentUser is reviewer of a related stage 2
        authCpt += db(
            (db.t_articles.art_stage_1_id == art.id) & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommender_id == auth.user_id)
        ).count()
        # if currentUser is reviewer of a related stage 2
        if art.status == "Recommended":
            authCpt += 1
        amIEngagedInStage2Process = authCpt > 0

    if pciRRactivated and art.status == "Recommended":
        amIEngagedInStage2Process = True

    isScheduledSubmission = False
    if scheduledSubmissionActivated and art.doi is None and art.scheduled_submission_date is not None:
        isScheduledSubmission = True

    isPendingRecommenderAcceptation = db(
          (db.t_recommendations.article_id == art.id)
        & (db.t_recommendations.id == db.t_reviews.recommendation_id)
        & (db.t_reviews.reviewer_id == auth.user_id)
        & (db.t_reviews.review_state == "Willing to review")
    ).count() > 0

    ###NOTE: here start recommendations display
    amIinRecommenderList = False
    amIinCoRecommenderList = False
    iRecomm = 0
    roundNb = nbRecomms + 1
    for recomm in recomms:
        iRecomm += 1
        roundNb -= 1
        nbCompleted = 0
        nbOnGoing = 0
        whoDidIt = common_small_html.getRecommAndReviewAuthors(auth, db, recomm=recomm, with_reviewers=False, linked=not (printable),
                        host=host, port=port, scheme=scheme,
                        this_recomm_only=True,
                        )

        # Am I a recommender?
        if recomm.recommender_id == auth.user_id:
            amIinRecommenderList = True
        # Am I a co recommender?
        amICoRecommender = db((db.t_press_reviews.recommendation_id == recomm.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0
        if amICoRecommender:
            amIinCoRecommenderList = True
        # Am I a reviewer?
        amIReviewer = (
            db((db.t_recommendations.article_id == art.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_reviews.reviewer_id == auth.user_id)).count() > 0
        )
        # During recommendation, no one is not allowed to see last (unclosed) recommendation
        hideOngoingRecomm = ((art.status == "Under consideration") or (art.status.startswith("Pre-"))) and not (recomm.is_closed)  # (iRecomm==1)
        #  ... unless he/she is THE recommender
        if auth.has_membership(role="recommender") and (recomm.recommender_id == auth.user_id or amICoRecommender):
            hideOngoingRecomm = False
        # or a manager
        if auth.has_membership(role="manager") and (art.user_id != auth.user_id):
            hideOngoingRecomm = False

        authorsReply = None
        authorsReplyDate = None
        if (recomm.reply is not None) and (len(recomm.reply) > 0):
            authorsReply = DIV(WIKI(recomm.reply or "", safe_mode=False))
            authorsReplyDate = (recomm.author_last_change or recomm.last_change).strftime(DEFAULT_DATE_FORMAT+ " %H:%M")

        authorsReplyPdfLink = None
        if recomm.reply_pdf:
            authorsReplyPdfLink = A(
                I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
                current.T("Download author's reply (PDF file)"),
                _href=URL("default", "download", args=recomm.reply_pdf, scheme=scheme, host=host, port=port),
                _style="font-weight: bold; margin-bottom: 5px; display:block",
            )

        authorsReplyTrackChangeFileLink = None
        if recomm.track_change:
            authorsReplyTrackChangeFileLink = A(
                I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
                current.T("Download tracked changes file"),
                _href=URL("default", "download", args=recomm.track_change, scheme=scheme, host=host, port=port),
                _style="font-weight: bold; margin-bottom: 5px; display:block",
            )

        editAuthorsReplyLink = None
        if (art.user_id == auth.user_id) and (art.status == "Awaiting revision") and not (printable) and (iRecomm == 1):
            editAuthorsReplyLink = URL(c="user", f="edit_reply", vars=dict(recommId=recomm.id), user_signature=True)

        # Check for reviews
        existOngoingReview = False
        reviewsList = []

        # If the recommender is also a reviewer, did he/she already completed his/her review?
        recommReviewFilledOrNull = False  # Let's say no by default
        # Get reviews states for this case
        recommenderOwnReviewStates = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.reviewer_id == recomm.recommender_id)).select(db.t_reviews.review_state)
        if len(recommenderOwnReviewStates) == 0:
            # The recommender is not also a reviewer
            recommReviewFilledOrNull = True  # He/she is allowed to see other's reviews
        else:
            # The recommender is also a reviewer
            for recommenderOwnReviewState in recommenderOwnReviewStates:
                if recommenderOwnReviewState.review_state == "Review completed":
                    recommReviewFilledOrNull = True  # Yes, his/her review is completed

        reviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state != "Declined manually") & (db.t_reviews.review_state != "Declined") & (db.t_reviews.review_state != "Cancelled")).select(
            orderby=db.t_reviews.id
        )

        for review in reviews:
            if review.review_state == "Awaiting review":
                existOngoingReview = True
                nbOnGoing += 1
            if review.review_state == "Review completed":
                nbCompleted += 1

            # No one is allowd to see ongoing reviews ...
            hideOngoingReview = True
            reviewVars = dict(
                id=review.id,
                showInvitationButtons=False,
                showReviewRequest=False,
                showPendingAskForReview=False,
                declinedByRecommender=False,
                showEditButtons=False,
                authors=None,
                text=None,
                pdfLink=None,
            )
            # ... but:
            # ... the author for a closed decision/recommendation ...
            if (art.user_id == auth.user_id) and (recomm.is_closed or art.status == "Awaiting revision"):
                hideOngoingReview = False
            # ...  the reviewer himself once accepted ...
            if (review.reviewer_id == auth.user_id) and (review.review_state in ("Awaiting review", "Review completed")):
                hideOngoingReview = False
            # ...  a reviewer himself once the decision made up ...
            if (
                (amIReviewer)
                and (recomm.recommendation_state in ("Recommended", "Rejected", "Revision"))
                and recomm.is_closed
                and (art.status in ("Under consideration", "Recommended", "Rejected", "Awaiting revision"))
            ):
                hideOngoingReview = False
            # ... or he/she is THE recommender and he/she already filled his/her own review ...
            if auth.has_membership(role="recommender") and (recomm.recommender_id == auth.user_id or amICoRecommender) and recommReviewFilledOrNull:
                hideOngoingReview = False
            # ... or he/she is A CO-recommender and he/she already filled his/her own review ...
            if auth.has_membership(role="recommender") and amICoRecommender and recommReviewFilledOrNull:
                hideOngoingReview = False
            # ... or a manager, unless submitter
            if auth.has_membership(role="manager") and not (art.user_id == auth.user_id):
                hideOngoingReview = False

            # ... or if engaged in stage 2 process (pci RR)
            if review.review_state == "Review completed" and amIEngagedInStage2Process:
                hideOngoingReview = False

            if auth.has_membership(role="recommender") and (recomm.recommender_id == auth.user_id or amICoRecommender) and (review.review_state == "Willing to review") and (art.status == "Under consideration"):
                reviewVars.update([("showReviewRequest", True)])

            if (review.reviewer_id == auth.user_id) and (review.reviewer_id != recomm.recommender_id) and (art.status == "Under consideration") and not (printable):
                if review.review_state == "Awaiting response":
                    # reviewer's buttons in order to accept/decline pending review
                    reviewVars.update([("showInvitationButtons", True)])
                elif review.review_state == "Willing to review" or review.review_state == "Declined by recommender":
                    # reviewer's buttons in order to accept/decline pending review
                    reviewVars.update([("showPendingAskForReview", True)])
                    if review.review_state == "Declined by recommender":
                        reviewVars.update([("declinedByRecommender", True)])

            elif review.review_state == "Awaiting response" or review.review_state == "Declined by recommender":
                hideOngoingReview = True

            if (recomm.recommender_id != auth.user_id and amICoRecommender == False) and review.review_state == "Willing to review":
                reviewVars.update([("showReviewRequest", False)])
                hideOngoingReview = True
                
            if auth.has_membership(role="manager")  and review.review_state == "Willing to review":
                reviewVars.update([("showReviewRequest", True)])
                hideOngoingReview = False

            if (review.reviewer_id == auth.user_id) and review.review_state == "Willing to review":
                reviewVars.update([("showReviewRequest", False)])
                hideOngoingReview = False

            # reviewer's buttons in order to edit/complete pending review
            if (review.reviewer_id == auth.user_id) and (review.review_state == "Awaiting review") and (art.status == "Under consideration") and not (printable):
                reviewVars.update([("showEditButtons", True)])

            if not (hideOngoingReview):
                # display the review
                if review.anonymously:
                    reviewVars.update(
                        [
                            (
                                "authors",
                                SPAN(
                                    current.T("anonymous reviewer"),
                                    (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review.last_change else ""),
                                ),
                            )
                        ]
                    )
                else:
                    reviewVars.update(
                        [
                            (
                                "authors",
                                SPAN(
                                    review.reviewer_details.replace('<span>', '').split('</span>')[0] if review.reviewer_details else \
                                    common_small_html.mkUser(auth, db, review.reviewer_id, linked=True),
                                    (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review.last_change else ""),
                                ),
                            )
                        ]
                    )

                if len(review.review or "") > 2:
                    reviewVars.update([("text", WIKI(review.review, safe_mode=False))])

                if review.review_pdf:
                    pdfLink = A(
                        I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
                        current.T("Download the review (PDF file)"),
                        _href=URL("default", "download", args=review.review_pdf, scheme=scheme, host=host, port=port),
                        _style="font-weight: bold; margin-bottom: 5px; display:block",
                    )
                    reviewVars.update([("pdfLink", pdfLink)])

            reviewsList.append(reviewVars)

        # Reommendation label
        if recomm.recommendation_state == "Recommended":
            if recomm.recommender_id == auth.user_id:
                recommendationLabel = current.T("Your recommendation")
            elif amICoRecommender:
                recommendationLabel = current.T("Your co-recommendation")
            elif auth.has_membership(role="manager"):
                recommendationLabel = current.T("Decision")
            else:
                recommendationLabel = current.T("Recommendation")
        else:
            if recomm.recommender_id == auth.user_id:
                recommendationLabel = current.T("Your decision")
            elif amICoRecommender:
                recommendationLabel = current.T("Your co-decision")
            elif recomm.is_closed:
                recommendationLabel = current.T("Decision")
            else:
                recommendationLabel = current.T("Decision")

        # Recommender buttons
        editRecommendationLink = None
        editRecommendationDisabled = None
        editRecommendationButtonText = None
        if not (recomm.is_closed) and (recomm.recommender_id == auth.user_id or amICoRecommender) and (art.status == "Under consideration") and not (printable):
            # recommender's button for recommendation edition
            editRecommendationButtonText = current.T("Write or edit your decision / recommendation")
            editRecommendationLink = URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id))
            if pciRRactivated:
                pass
            elif (nbCompleted >= 2 and nbOnGoing == 0) or roundNb > 1:
                pass
            else:
                editRecommendationDisabled = True
                editRecommendationButtonText = current.T("Write your decision / recommendation")

        recommendationPdfLink = None
        if hideOngoingRecomm is False and recomm.recommender_file:
            recommendationPdfLink = A(
                I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
                current.T("Download recommender's annotations (PDF)"),
                _href=URL("default", "download", args=recomm.recommender_file, scheme=scheme, host=host, port=port),
                _style="font-weight: bold; margin-bottom: 5px; display:block",
            )
        
        def mk_link(role, action, rev):
            return URL(c=role+"_actions", f=action+"_review_request", vars=dict(reviewId=rev["id"]))

        role = ("manager" if auth.has_membership(role="manager") else
                "recommender" if auth.has_membership(role="recommender") else
                None)

        for rev in reviewsList:
            if rev["showReviewRequest"] and role:
                rev.update([
                    ("acceptReviewRequestLink", mk_link(role, "accept", rev)),
                    ("rejectReviewRequestLink", mk_link(role, "decline", rev)),
                ])

        inviteReviewerLink = None
        showSearchingForReviewersButton = None
        showRemoveSearchingForReviewersButton = None
        if not (recomm.is_closed) and (recomm.recommender_id == auth.user_id or amICoRecommender or auth.has_membership(role="manager")) and (art.status == "Under consideration"):
            inviteReviewerLink = URL(c="recommender", f="reviewers", vars=dict(recommId=recomm.id))
            showSearchingForReviewersButton = not art.is_searching_reviewers
            showRemoveSearchingForReviewersButton = art.is_searching_reviewers

        recommendationText = ""
        if len(recomm.recommendation_comments or "") > 2:
            recommendationText = WIKI(recomm.recommendation_comments or "", safe_mode=False) if (hideOngoingRecomm is False) else ""

        componentVars = dict(
            articleId=art.id,
            recommId=recomm.id,
            printable=printable,
            roundNumber=roundNb,
            nbRecomms=nbRecomms,
            lastChanges=None,
            authorsReply=authorsReply,
            authorsReplyDate=authorsReplyDate,
            authorsReplyPdfLink=authorsReplyPdfLink,
            authorsReplyTrackChangeFileLink=authorsReplyTrackChangeFileLink,
            editAuthorsReplyLink=editAuthorsReplyLink,
            recommendationAuthor=I(current.T("by "), B(whoDidIt), SPAN(", " + recomm.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if recomm.last_change else "")),
            manuscriptDoi=SPAN(current.T("Manuscript:") + " ", common_small_html.mkDOI(recomm.doi)) if (recomm.doi) else SPAN(""),
            recommendationVersion=SPAN(" " + current.T("version:") + " ", recomm.ms_version) if (recomm.ms_version) else SPAN(""),
            recommendationTitle=H4(recomm.recommendation_title or "", _style="font-weight: bold; margin-top: 5px; margin-bottom: 20px") if (hideOngoingRecomm is False) else "",
            recommendationLabel=recommendationLabel,
            recommendationText=recommendationText,
            recommendationStatus=recomm.recommendation_state,
            recommendationPdfLink=recommendationPdfLink,
            inviteReviewerLink=inviteReviewerLink,
            editRecommendationButtonText=editRecommendationButtonText,
            editRecommendationLink=editRecommendationLink,
            editRecommendationDisabled=editRecommendationDisabled,
            reviewsList=reviewsList,
            showSearchingForReviewersButton=showSearchingForReviewersButton,
            showRemoveSearchingForReviewersButton=showRemoveSearchingForReviewersButton,
            scheduledSubmissionActivated=scheduledSubmissionActivated,
            isScheduledSubmission=isScheduledSubmission,
            isArticleSubmitter=(art.user_id == auth.user_id),
        )

        recommendationRounds.append(XML(response.render("components/recommendation_process.html", componentVars)))

        # show only current round if user is pending RecommenderAcceptation
        if roundNb == nbRecomms and isPendingRecommenderAcceptation:
            break

    # Manager button
    managerButton = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable):
        if amIinRecommenderList or amIinCoRecommenderList:
            managerButton = DIV(
                B(current.T("Note: you also served as the Recommender for this submission, please ensure that another member of the Managing Board performs the validation")),
                _class="pci2-flex-center"
            )
        else:
            send_back_button =  A(
                SPAN(current.T("Send back this decision to the recommender"), _class="buttontext btn btn-danger pci-manager"),
                _href=URL(c="manager_actions", f="do_send_back_decision", vars=dict(articleId=art.id), user_signature=True),
                _title=current.T("Click here to send back this decision to the recommender"),
            )

            if art.status == "Pending":
                managerButton = DIV(
                    A(
                        SPAN(current.T("Validate this submission"), _class="buttontext btn btn-success pci-manager"),
                        _href=URL(c="manager_actions", f="do_validate_article", vars=dict(articleId=art.id), user_signature=True),
                        _title=current.T("Click here to validate this request and start recommendation process"),
                    ),
                    _class="pci-EditButtons-centered",
                )
            elif art.status == "Pre-recommended" or art.status == "Pre-recommended-private":
                managerButton = DIV(
                    A(
                        SPAN(current.T("Validate this recommendation"), _class="buttontext btn btn-success pci-manager"),
                        _href=URL(c="manager_actions", f="do_recommend_article", vars=dict(articleId=art.id), user_signature=True),
                        _title=current.T("Click here to validate recommendation of this article"),
                    ),
                    send_back_button,
                    _class="pci-EditButtons-centered",
                )
            elif art.status == "Pre-revision":
                managerButton = DIV(
                    A(
                        SPAN(current.T("Validate this decision"), _class="buttontext btn btn-info pci-manager"),
                        _href=URL(c="manager_actions", f="do_revise_article", vars=dict(articleId=art.id), user_signature=True),
                        _title=current.T("Click here to validate revision of this article"),
                    ),
                    send_back_button,
                    _class="pci-EditButtons-centered",
                )
            elif art.status == "Pre-rejected":
                managerButton = DIV(
                    A(
                        SPAN(current.T("Validate this rejection"), _class="buttontext btn btn-info pci-manager"),
                        _href=URL(c="manager_actions", f="do_reject_article", vars=dict(articleId=art.id), user_signature=True),
                        _title=current.T("Click here to validate the rejection of this article"),
                    ),
                    send_back_button,
                    _class="pci-EditButtons-centered",
                )

    return DIV(recommendationRounds, managerButton or "")


######################################################################################################################################
# Postprint recommendation process
######################################################################################################################################
def getPostprintRecommendation(auth, db, response, art, printable=False, quiet=True, scheme=False, host=False, port=False):
    recommendationDiv = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))

    ###NOTE: recommendations counting
    recomm = db(db.t_recommendations.article_id == art.id).select(orderby=~db.t_recommendations.id).last()

    ###NOTE: here start recommendations display
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
    if (recomm.recommender_id == auth.user_id or amICoRecommender) and (art.status == "Under consideration") and not (recomm.is_closed) and not (printable):
        # recommender's button allowing recommendation edition
        editRecommendationLink = URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id), user_signature=True)

        # (gab) minimal_number_of_corecommenders is not defiend ! => set it to 0
        minimal_number_of_corecommenders = 0

        if len(contributors) >= minimal_number_of_corecommenders:
            sendRecommendationLink = URL(c="recommender_actions", f="recommend_article", vars=dict(recommId=recomm.id), user_signature=True)
            if recomm.recommendation_comments is not None:
                if len(recomm.recommendation_comments) > 50:
                    # recommender's button allowing recommendation submission, provided there are co-recommenders
                    isRecommendationTooShort = False
            else:
                isRecommendationTooShort = True
        else:
            # otherwise button for adding co-recommender(s)
            addContributorLink = URL(c="recommender", f="add_contributor", vars=dict(recommId=recomm.id), user_signature=True)

        # recommender's button allowing cancellation
        cancelSubmissionLink = URL(c="recommender_actions", f="do_cancel_press_review", vars=dict(recommId=recomm.id), user_signature=True)

    # (gab) why this ???
    # if myRound and (recomm.is_closed or art.status == "Awaiting revision" or art.user_id != auth.user_id):
    showRecommendation = False
    if recomm.is_closed or art.status == "Awaiting revision" or art.user_id != auth.user_id:
        showRecommendation = True

    recommendationText = ""
    if len(recomm.recommendation_comments or "") > 2:
        recommendationText = WIKI(recomm.recommendation_comments or "", safe_mode=False)

    validateRecommendationLink = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable):
        if art.status == "Pre-recommended":
            validateRecommendationLink = URL(c="manager_actions", f="do_recommend_article", vars=dict(articleId=art.id), user_signature=True)

    componentVars = dict(
        printable=printable,
        showRecommendation=True,
        recommendationAuthor=I(current.T("by "), B(whoDidIt), SPAN(", " + recomm.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if recomm.last_change else "")),
        recommendationDoi=SPAN(current.T("Recommendation: "), common_small_html.mkDOI(recomm.recommendation_doi)) if (recomm.recommendation_doi) else "",
        manuscriptDoi=SPAN(current.T("Manuscript: "), common_small_html.mkDOI(recomm.doi)) if (recomm.doi) else "",
        recommendationTitle=H4(recomm.recommendation_title or "", _style="font-weight: bold; margin-top: 5px; margin-bottom: 20px")
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
