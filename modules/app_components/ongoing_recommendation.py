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


########################################################################################################################################################################
def getRecommStatusHeader(auth, db, response, art, controller_name, request, userDiv, printable, quiet=True):
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

    recomms = db(db.t_recommendations.article_id == art.id).select(orderby=~db.t_recommendations.id)
    nbRecomms = len(recomms)

    if userDiv:
        statusDiv = DIV(common_small_html.mkStatusBigDivUser(auth, db, art.status, printable), _class="pci2-flex-center pci2-full-width",)
    else:
        statusDiv = DIV(common_small_html.mkStatusBigDiv(auth, db, art.status, printable), _class="pci2-flex-center pci2-full-width")

    myTitle = DIV(IMG(_src=URL(r=request, c="static", f="images/small-background.png")), DIV(statusDiv, _class="pci2-flex-grow"), _class="pci2-flex-row",)

    # author's button allowing article edition
    allowEditArticle = False
    if ((art.user_id == auth.user_id) and (art.status in ("Pending", "Awaiting revision"))) and not (quiet):
        allowEditArticle = True

    # manager buttons
    allowManageRecomms = False
    if nbRecomms > 0 and auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (quiet):
        allowManageRecomms = True

    back2 = URL(re.sub(r".*/([^/]+)$", "\\1", request.env.request_uri), scheme=scheme, host=host, port=port)

    allowManageRequest = False
    manageRecommendersButton = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (quiet):
        allowManageRequest = True
        manageRecommendersButton = manager_module.mkSuggestedRecommendersManagerButton(art, back2, auth, db)

    componentVars = dict(
        statusTitle=myTitle,
        allowEditArticle=allowEditArticle,
        allowManageRecomms=allowManageRecomms,
        allowManageRequest=allowManageRequest,
        manageRecommendersButton=manageRecommendersButton,
        articleId=art.id,
        printableUrl=URL(c=controller_name, f="recommendations", vars=dict(articleId=art.id, printable=True), user_signature=True),
        printable=printable,
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
                SPAN(current.T("Click here before starting the evaluation process"), _class="buttontext btn btn-success pci-recommender"),
                _href=URL(c="recommender", f="accept_new_article_to_recommend", vars=dict(articleId=art.id), user_signature=True),
                _class="button",
            ),
        ]
        amISugg = db((db.t_suggested_recommenders.article_id == art.id) & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)).count()
        if amISugg > 0:
            # suggested recommender's button for declining recommendation
            btsAccDec.append(
                A(
                    SPAN(current.T("No, thanks, I decline this suggestion"), _class="buttontext btn btn-warning pci-recommender"),
                    _href=URL(c="recommender_actions", f="decline_new_article_to_recommend", vars=dict(articleId=art.id), user_signature=True),
                    _class="button",
                ),
            )
        myButtons.append(DIV(btsAccDec, _class="pci2-flex-grow pci2-flex-center", _style="margin:10px"))

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

            recommenderName = common_small_html.getRecommAndReviewAuthors(
                auth, db, recomm=recomm, with_reviewers=False, linked=not (printable), host=host, port=port, scheme=scheme
            )

            recommStatus = None
            reviewCount = 0
            acceptedReviewCount = 0
            completedReviewCount = 0

            reviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state != "Declined") & (db.t_reviews.review_state != "Cancelled")).select(
                orderby=db.t_reviews.id
            )

            for review in reviews:
                reviewCount += 1
                if review.review_state == "Under consideration":
                    acceptedReviewCount += 1
                if review.review_state == "Completed":
                    acceptedReviewCount += 1
                    completedReviewCount += 1


            if acceptedReviewCount >= 2:
                reviewInvitationsAcceptedClass = "step-done"

            if completedReviewCount >= 2:
                reviewsStepDoneClass = "step-done"

            if recomm.recommendation_state == "Rejected" or recomm.recommendation_state == "Recommended" or recomm.recommendation_state == "Revision":
                recommendationStepClass = "step-done"
                recommStatus = recomm.recommendation_state

            if (roundNumber == totalRecomm and art.status in ("Rejected", "Recommended", "Awaiting revision")) or (roundNumber < totalRecomm and recomm.reply is not None):
                managerDecisionDoneClass = "step-done"

            if recommStatus == "Revision" and managerDecisionDoneClass == "step-done":
                managerDecisionDoneStepClass = "progress-step-div"
            else:
                managerDecisionDoneStepClass = "progress-last-step-div"

            if (roundNumber < totalRecomm) and (recomm.reply is not None) and (len(recomm.reply) > 0):
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
                acceptedReviewCount=acceptedReviewCount,
                reviewsStepDoneClass=reviewsStepDoneClass,
                completedReviewCount=completedReviewCount,
                recommendationStepClass=recommendationStepClass,
                recommStatus=recommStatus,
                managerDecisionDoneClass=managerDecisionDoneClass,
                managerDecisionDoneStepClass=managerDecisionDoneStepClass,
                authorsReplyClass=authorsReplyClass,
                authorsReplyClassStepClass=authorsReplyClassStepClass,
                totalRecomm=totalRecomm,
                recommendationLink=recommendationLink,
            )
            recommendationDiv.append(XML(response.render("components/recommendation_process_for_submitter.html", componentVars)))

            roundNumber += 1

    else:
        managerDecisionDoneStepClass = "progress-last-step-div"

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
            acceptedReviewCount=acceptedReviewCount,
            reviewsStepDoneClass=reviewsStepDoneClass,
            completedReviewCount=completedReviewCount,
            recommendationStepClass=recommendationStepClass,
            recommStatus=recommStatus,
            managerDecisionDoneClass=managerDecisionDoneClass,
            managerDecisionDoneStepClass=managerDecisionDoneStepClass,
            totalRecomm=totalRecomm,
        )

        recommendationDiv.append(XML(response.render("components/recommendation_process_for_submitter.html", componentVars)))

    return dict(
        roundNumber=totalRecomm,
        isRecommAvalaibleToSubmitter=(managerDecisionDoneClass == "step-done"),
        content=recommendationDiv
    ) 


########################################################################################################################################################################
# Preprint recommendation process
########################################################################################################################################################################
def getRecommendationProcess(auth, db, response, art, printable=False, quiet=True, scheme=False, host=False, port=False):
    recommendationRounds = DIV("", _class=("pci-article-div-printable" if printable else "pci-article-div"))

    ###NOTE: recommendations counting
    recomms = db(db.t_recommendations.article_id == art.id).select(orderby=~db.t_recommendations.id)
    nbRecomms = len(recomms)

    ###NOTE: here start recommendations display
    iRecomm = 0
    roundNb = nbRecomms + 1
    for recomm in recomms:
        iRecomm += 1
        roundNb -= 1
        nbCompleted = 0
        nbOnGoing = 0
        whoDidIt = common_small_html.getRecommAndReviewAuthors(auth, db, recomm=recomm, with_reviewers=False, linked=not (printable), host=host, port=port, scheme=scheme)

        amICoRecommender = db((db.t_press_reviews.recommendation_id == recomm.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0
        # Am I a reviewer?
        amIReviewer = (
            db((db.t_recommendations.article_id == art.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_reviews.reviewer_id == auth.user_id)).count() > 0
        )
        # During recommendation, no one is not allowed to see last (unclosed) recommendation
        hideOngoingRecomm = ((art.status == "Under consideration") or (art.status.startswith("Pre-"))) and not (recomm.is_closed)  # (iRecomm==1)
        #  ... unless he/she is THE recommender
        if auth.has_membership(role="recommender") and (recomm.recommender_id == auth.user_id or amICoRecommender):
            hideOngoingRecomm = False
        # or a manager, provided he/she is reviewer
        if auth.has_membership(role="manager") and (art.user_id != auth.user_id) and (amIReviewer is False):
            hideOngoingRecomm = False

        authorsReply = None
        if (recomm.reply is not None) and (len(recomm.reply) > 0):
            authorsReply = DIV(WIKI(recomm.reply or "", safe_mode=False))

        authorsReplyPdfLink = None
        if recomm.reply_pdf:
            authorsReplyPdfLink = A(current.T("Download author's reply (PDF file)"), _href=URL("default", "download", args=recomm.reply_pdf, scheme=scheme, host=host, port=port))

        authorsReplyTrackChangeFileLink = None
        if recomm.track_change:
            authorsReplyTrackChangeFileLink = A(
                current.T("Download tracked changes file"), _href=URL("default", "download", args=recomm.track_change, scheme=scheme, host=host, port=port)
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
                if recommenderOwnReviewState.review_state == "Completed":
                    recommReviewFilledOrNull = True  # Yes, his/her review is completed

        reviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state != "Declined") & (db.t_reviews.review_state != "Cancelled")).select(
            orderby=db.t_reviews.id
        )

        for review in reviews:
            if review.review_state == "Under consideration":
                existOngoingReview = True
                nbOnGoing += 1
            if review.review_state == "Completed":
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
            if (review.reviewer_id == auth.user_id) and (review.review_state in ("Under consideration", "Completed")):
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
            if auth.has_membership(role="recommender") and (recomm.recommender_id == auth.user_id) and recommReviewFilledOrNull:
                hideOngoingReview = False
            # ... or he/she is A CO-recommender and he/she already filled his/her own review ...
            if auth.has_membership(role="recommender") and amICoRecommender and recommReviewFilledOrNull:
                hideOngoingReview = False
            # ... or a manager, unless submitter or reviewer
            if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not amIReviewer:
                hideOngoingReview = False

            if auth.has_membership(role="recommender") and (recomm.recommender_id == auth.user_id) and review.review_state == "Ask for review":
                reviewVars.update([("showReviewRequest", True)])

            if (review.reviewer_id == auth.user_id) and (review.reviewer_id != recomm.recommender_id) and (art.status == "Under consideration") and not (printable):
                if review.review_state == "Pending":
                    # reviewer's buttons in order to accept/decline pending review
                    reviewVars.update([("showInvitationButtons", True)])
                elif review.review_state == "Ask for review" or review.review_state == "Declined by recommender":
                    # reviewer's buttons in order to accept/decline pending review
                    reviewVars.update([("showPendingAskForReview", True)])
                    if review.review_state == "Declined by recommender":
                        reviewVars.update([("declinedByRecommender", True)])

            elif review.review_state == "Pending" or review.review_state == "Declined by recommender":
                hideOngoingReview = True

            # reviewer's buttons in order to edit/complete pending review
            if (review.reviewer_id == auth.user_id) and (review.review_state == "Under consideration") and (art.status == "Under consideration") and not (printable):
                reviewVars.update([("showEditButtons", True)])

            if not (hideOngoingReview):
                # display the review
                if review.anonymously:
                    reviewVars.update([("authors", SPAN(current.T("anonymous reviewer"), (", " + review.last_change.strftime("%Y-%m-%d %H:%M") if review.last_change else ""),),)])
                else:
                    reviewer = db(db.auth_user.id == review.reviewer_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
                    if reviewer is not None:
                        reviewVars.update(
                            [
                                (
                                    "authors",
                                    SPAN(
                                        common_small_html.mkUser(auth, db, review.reviewer_id, linked=True),
                                        (", " + review.last_change.strftime("%Y-%m-%d %H:%M") if review.last_change else ""),
                                    ),
                                )
                            ]
                        )

                if len(review.review or "") > 2:
                    reviewVars.update([("text", WIKI(review.review, safe_mode=False))])

                if review.review_pdf:
                    pdfLink = A(
                        current.T("Download the review (PDF file)"),
                        _href=URL("default", "download", args=review.review_pdf, scheme=scheme, host=host, port=port),
                        _style="margin-bottom: 64px;",
                    )
                    reviewVars.update([("pdfLink", pdfLink)])

            reviewsList.append(reviewVars)

        # Reommendation label
        if recomm.recommendation_state == "Recommended":
            if recomm.recommender_id == auth.user_id:
                recommendationLabel = current.T("Your recommendation")
            else:
                recommendationLabel = current.T("Recommendation")
        else:
            if recomm.recommender_id == auth.user_id:
                recommendationLabel = current.T("Your decision")
            elif recomm.is_closed:
                recommendationLabel = current.T("Decision")
            else:
                recommendationLabel = ""

        # Recommender buttons
        editRecommendationLink = None
        editRecommendationDisabled = None
        editRecommendationButtonText = None
        if not (recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == "Under consideration") and not (printable):
            # recommender's button for recommendation edition
            if (nbCompleted >= 2 and nbOnGoing == 0) or roundNb > 1:
                editRecommendationDisabled = False
                editRecommendationButtonText = current.T("Write or edit your decision / recommendation")
                editRecommendationLink = URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id))
            else:
                editRecommendationDisabled = True
                editRecommendationButtonText = current.T("Write your decision / recommendation")
                editRecommendationLink = URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id))

        recommendationPdfLink = None
        if hideOngoingRecomm is False and recomm.recommender_file:
            recommendationPdfLink = A(
                current.T("Download recommender's annotations (PDF)"),
                _href=URL("default", "download", args=recomm.recommender_file, scheme=scheme, host=host, port=port),
                _style="margin-bottom: 64px;",
            )

        inviteReviewerLink = None
        showSearchingForReviewersButton = None
        showRemoveSearchingForReviewersButton = None
        if not (recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == "Under consideration"):
            inviteReviewerLink = URL(c="recommender", f="reviewers", vars=dict(recommId=recomm.id))
            showSearchingForReviewersButton = not art.is_searching_reviewers
            showRemoveSearchingForReviewersButton = art.is_searching_reviewers

        recommendationText = ""
        if len(recomm.recommendation_comments or "") > 2:
            recommendationText = WIKI(recomm.recommendation_comments or "", safe_mode=False) if (hideOngoingRecomm is False) else ""

        componentVars = dict(
            recommId=recomm.id,
            printable=printable,
            roundNumber=roundNb,
            nbRecomms=nbRecomms,
            lastChanges=None,
            authorsReply=authorsReply,
            authorsReplyPdfLink=authorsReplyPdfLink,
            authorsReplyTrackChangeFileLink=authorsReplyTrackChangeFileLink,
            editAuthorsReplyLink=editAuthorsReplyLink,
            recommendationAuthor=I(current.T("by "), B(whoDidIt), SPAN(", " + recomm.last_change.strftime("%Y-%m-%d %H:%M") if recomm.last_change else "")),
            manuscriptDoi=SPAN(current.T("Manuscript:") + " ", common_small_html.mkDOI(recomm.doi)) if (recomm.doi) else SPAN(""),
            recommendationVersion=SPAN(" " + current.T("version") + " ", recomm.ms_version) if (recomm.ms_version) else SPAN(""),
            recommendationTitle=H3(recomm.recommendation_title or "") if (hideOngoingRecomm is False) else "",
            recommendationLabel=recommendationLabel,
            recommendationText=recommendationText,
            recommendationPdfLink=recommendationPdfLink,
            inviteReviewerLink=inviteReviewerLink,
            editRecommendationButtonText=editRecommendationButtonText,
            editRecommendationLink=editRecommendationLink,
            editRecommendationDisabled=editRecommendationDisabled,
            reviewsList=reviewsList,
            showSearchingForReviewersButton=showSearchingForReviewersButton,
            showRemoveSearchingForReviewersButton=showRemoveSearchingForReviewersButton,
        )
        recommendationRounds.append(XML(response.render("components/recommendation_process.html", componentVars)))

    # Manager button
    managerButton = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable):
        if art.status == "Pending":
            managerButton = DIV(
                A(
                    SPAN(current.T("Validate this submission"), _class="buttontext btn btn-success pci-manager"),
                    _href=URL(c="manager_actions", f="do_validate_article", vars=dict(articleId=art.id), user_signature=True),
                    _title=current.T("Click here to validate this request and start recommendation process"),
                ),
                _class="pci-EditButtons-centered",
            )
        elif art.status == "Pre-recommended":
            managerButton = DIV(
                A(
                    SPAN(current.T("Validate this recommendation"), _class="buttontext btn btn-success pci-manager"),
                    _href=URL(c="manager_actions", f="do_recommend_article", vars=dict(articleId=art.id), user_signature=True),
                    _title=current.T("Click here to validate recommendation of this article"),
                ),
                _class="pci-EditButtons-centered",
            )
        elif art.status == "Pre-revision":
            managerButton = DIV(
                A(
                    SPAN(current.T("Validate this decision"), _class="buttontext btn btn-info pci-manager"),
                    _href=URL(c="manager_actions", f="do_revise_article", vars=dict(articleId=art.id), user_signature=True),
                    _title=current.T("Click here to validate revision of this article"),
                ),
                _class="pci-EditButtons-centered",
            )
        elif art.status == "Pre-rejected":
            managerButton = DIV(
                A(
                    SPAN(current.T("Validate this rejection"), _class="buttontext btn btn-info pci-manager"),
                    _href=URL(c="manager_actions", f="do_reject_article", vars=dict(articleId=art.id), user_signature=True),
                    _title=current.T("Click here to validate the rejection of this article"),
                ),
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

    contributors = []
    contrQy = db((db.t_press_reviews.recommendation_id == recomm.id)).select(orderby=db.t_press_reviews.id)
    for contr in contrQy:
        contributors.append(contr.contributor_id)

    editRecommendationLink = None
    sendRecommendationLink = None
    isRecommendationTooShort = True
    addContributorLink = None
    cancelSubmissionLink = None
    if (recomm.recommender_id == auth.user_id) and (art.status == "Under consideration") and not (recomm.is_closed) and not (printable):
        # recommender's button allowing recommendation edition
        editRecommendationLink = URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id), user_signature=True)

        # (gab) minimal_number_of_corecommenders is not defiend ! => set it to 0
        minimal_number_of_corecommenders = 0

        if len(contributors) >= minimal_number_of_corecommenders:
            sendRecommendationLink = URL(c="recommender_actions", f="recommend_article", vars=dict(recommId=recomm.id), user_signature=True)
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
        recommendationAuthor=I(current.T("by "), B(whoDidIt), SPAN(", " + recomm.last_change.strftime("%Y-%m-%d %H:%M") if recomm.last_change else "")),
        recommendationDoi=SPAN(current.T("Recommendation: "), common_small_html.mkDOI(recomm.recommendation_doi)) if (recomm.recommendation_doi) else "",
        manuscriptDoi=SPAN(current.T("Manuscript: "), common_small_html.mkDOI(recomm.doi)) if (recomm.doi) else "",
        recommendationTitle=H3(recomm.recommendation_title or "") if (recomm.recommendation_title or "") != "" else "",
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
