# -*- coding: utf-8 -*-

import gc
import os
import pytz, datetime
from re import sub, match
from copy import deepcopy
import datetime
from datetime import timedelta
from dateutil.relativedelta import *
from collections import OrderedDict

import io
from PIL import Image

from gluon import current, IS_IN_DB
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail
from gluon.sqlhtml import *

from app_modules import common_small_html
from app_modules import common_html
from app_modules import common_tools

from app_components import article_components

myconf = AppConfig(reload=True)


########################################################################################################################################################################
## Public recommendation
######################################################################################################################################################################
def getArticleAndFinalRecommendation(auth, db, response, art, finalRecomm, printable, with_cover_letter=False, fullURL=True):
    if fullURL:
        scheme = myconf.take("alerts.scheme")
        host = myconf.take("alerts.host")
        port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    else:
        scheme = False
        host = False
        port = False

    headerContent = dict()

    recomm_altmetric = ""

    articleInfosCard = article_components.getArticleInfosCard(auth, db, response, art, printable, with_cover_letter=False, submittedBy=False)

    headerContent.update([("articleInfosCard", articleInfosCard)])

    # Last recommendation
    finalRecomm = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=~db.t_recommendations.id).last()
    citeNum = ""
    citeRef = None
    if finalRecomm.recommendation_doi:
        recomm_altmetric = XML(
            """
                <div class='altmetric-embed pci2-altmetric'  data-badge-type='donut' data-badge-popover="right" data-hide-no-mentions='true' data-doi='%s'></div>
            """
            % sub(r"doi: *", "", finalRecomm.recommendation_doi)
        )

        citeNumSearch = re.search("([0-9]+$)", finalRecomm.recommendation_doi, re.IGNORECASE)
        if citeNumSearch:
            citeNum = citeNumSearch.group(1)
        citeRef = common_small_html.mkDOI(finalRecomm.recommendation_doi)

    if citeRef:
        citeUrl = citeRef
    else:
        citeUrl = URL(c="articles", f="rec", vars=dict(id=art.id), host=host, scheme=scheme, port=port)
        citeRef = A(citeUrl, _href=citeUrl)  # + SPAN(' accessed ', datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))

    recommAuthors = common_small_html.getRecommAndReviewAuthors(auth, db, article=art, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)
    cite = DIV(
        SPAN(
            B("Cite this recommendation as:", _class="pci2-main-color-text"),
            BR(),
            SPAN(recommAuthors),
            " ",
            finalRecomm.last_change.strftime("(%Y)"),
            " ",
            finalRecomm.recommendation_title,
            ". ",
            I(myconf.take("app.description") + ", " + (citeNum or "") + ". "),
            citeRef,
        ),
        _class="pci-citation",
    )

    whoDidRecomm = common_small_html.getRecommAndReviewAuthors(auth, db, recomm=finalRecomm, with_reviewers=True, linked=True, host=host, port=port, scheme=scheme)

    # PDF (if any)
    pdf_query = db(db.t_pdf.recommendation_id == finalRecomm.id).select(db.t_pdf.id, db.t_pdf.pdf)
    pdfUrl = None
    pdfLink = None

    if len(pdf_query) > 0:
        pdfUrl = URL("articles", "rec", vars=dict(articleId=art.id, asPDF=True), host=host, scheme=scheme, port=port)
        pdfLink = A(SPAN(current.T("PDF recommendation"), " ", IMG(_alt="pdf", _src=URL("static", "images/application-pdf.png"))), _href=pdfUrl, _class="btn btn-info pci-public",)

    headerContent.update(
        [
            ("recommTitle", finalRecomm.recommendation_title if ((finalRecomm.recommendation_title or "") != "") else current.T("Recommendation"),),
            ("recommAuthor", whoDidRecomm),
            (
                "recommDateinfos",
                (
                    I(art.upload_timestamp.strftime("Submitted: %d %B %Y")) if art.upload_timestamp else "",
                    ", ",
                    I(finalRecomm.last_change.strftime("Recommended: %d %B %Y")) if finalRecomm.last_change else "",
                ),
            ),
            ("recomm_altmetric", recomm_altmetric),
            ("cite", cite),
            ("recommText", WIKI(finalRecomm.recommendation_comments or "")),
            ("pdfLink", pdfLink),
            ("printable", printable),
        ]
    )

    # Get METADATA (see next function)
    recommMetadata = getRecommendationMetadata(auth, db, art, finalRecomm, pdfLink, citeNum, scheme, host, port)

    headerHtml = XML(response.render("components/last_recommendation.html", headerContent))
    return dict(headerHtml=headerHtml, recommMetadata=recommMetadata)


######################################################################################################################################################################
def getRecommendationMetadata(auth, db, art, lastRecomm, pdfLink, citeNum, scheme, host, port):
    desc = "A recommendation of: " + (art.authors or "") + " " + (art.title or "") + " " + (art.doi or "")
    whoDidItMeta = common_small_html.getRecommAndReviewAuthors(auth, db, recomm=lastRecomm, with_reviewers=False, linked=False, as_list=True)

    # META headers
    myMeta = OrderedDict()
    myMeta["citation_title"] = lastRecomm.recommendation_title
    if len(whoDidItMeta) > 0:
        # Trick for multiple entries (see globals.py:464)
        for wdi in whoDidItMeta:
            myMeta["citation_author_%s" % wdi] = OrderedDict([("name", "citation_author"), ("content", wdi)])
    myMeta["citation_journal_title"] = myconf.take("app.description")
    myMeta["citation_publication_date"] = (lastRecomm.last_change.date()).strftime("%Y/%m/%d")
    myMeta["citation_online_date"] = (lastRecomm.last_change.date()).strftime("%Y/%m/%d")
    myMeta["citation_journal_abbrev"] = myconf.take("app.name")
    myMeta["citation_issn"] = myconf.take("app.issn")
    myMeta["citation_volume"] = "1"
    myMeta["citation_publisher"] = "Peer Community In"
    if lastRecomm.recommendation_doi:
        myMeta["citation_doi"] = sub(r"doi: *", "", lastRecomm.recommendation_doi)  # for altmetrics
    if citeNum:
        myMeta["citation_firstpage"] = citeNum
    myMeta["citation_abstract"] = desc
    if pdfLink:
        myMeta["citation_pdf_url"] = pdfLink

    # myMeta['og:title'] = lastRecomm.recommendation_title
    # myMeta['description'] = desc

    # Dublin Core fields
    myMeta["DC.title"] = lastRecomm.recommendation_title
    if len(whoDidItMeta) > 0:
        myMeta["DC.creator"] = " ; ".join(whoDidItMeta)  # syntax follows: http://dublincore.org/documents/2000/07/16/usageguide/#usinghtml
    myMeta["DC.issued"] = lastRecomm.last_change.date()
    # myMeta['DC.date'] = lastRecomm.last_change.date()
    myMeta["DC.description"] = desc
    myMeta["DC.publisher"] = myconf.take("app.description")
    myMeta["DC.relation.ispartof"] = myconf.take("app.description")
    if lastRecomm.recommendation_doi:
        myMeta["DC.identifier"] = myMeta["citation_doi"]
    if citeNum:
        myMeta["DC.citation.spage"] = citeNum
    myMeta["DC.language"] = "en"
    myMeta["DC.rights"] = "(C) %s, %d" % (myconf.take("app.description"), lastRecomm.last_change.date().year)

    return myMeta


######################################################################################################################################################################
def getPublicReviewRoundsHtml(auth, db, response, articleId):
    recomms = db((db.t_recommendations.article_id == articleId)).select(orderby=~db.t_recommendations.id)

    recommRound = len(recomms)
    reviewRoundsHtml = DIV()

    indentationLeft = 0
    for recomm in recomms:
        roundNumber = recommRound

        lastChanges = ""
        recommendationText = ""
        preprintDoi = ""
        isLastRecomm = False
        if recomms[0].id == recomm.id:
            isLastRecomm = True
        else:
            lastChanges = SPAN(I(recomm.last_change.strftime("%Y-%m-%d") + " ")) if recomm.last_change else ""
            recommendationText = WIKI(recomm.recommendation_comments) or ""
            preprintDoi = DIV(I(current.T("Preprint DOI:") + " "), common_small_html.mkDOI(recomm.doi), BR()) if ((recomm.doi or "") != "") else ""

        reviewsList = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Completed")).select(orderby=db.t_reviews.id)
        reviwesPreparedData = []

        for review in reviewsList:
            if review.anonymously:
                reviewAuthorAndDate = SPAN(
                    current.T("Reviewed by") + " " + current.T("anonymous reviewer") + (", " + review.last_change.strftime("%Y-%m-%d %H:%M") if review.last_change else "")
                )

            else:
                reviewAuthorAndDate = SPAN(
                    current.T("Reviewed by"),
                    " ",
                    common_small_html.mkUser(auth, db, review.reviewer_id, linked=True),
                    (", " + review.last_change.strftime("%Y-%m-%d %H:%M") if review.last_change else ""),
                )

            reviewText = None
            if len(review.review) > 2:
                reviewText = WIKI(review.review)

            pdfLink = None
            if review.review_pdf:
                pdfLink = DIV(
                    A(current.T("Download the review (PDF file)"), _href=URL("default", "download", args=review.review_pdf), _style="margin-bottom: 64px;",),
                    _class="pci-bigtext margin",
                )

            reviwesPreparedData.append(dict(authorAndDate=reviewAuthorAndDate, text=reviewText, pdfLink=pdfLink))

        authorsReply = None
        if recomm.reply:
            authorsReply = DIV(WIKI(recomm.reply), _class="pci-bigtext")

        authorsReplyPdfLink = None
        if recomm.reply_pdf:
            authorsReplyPdfLink = (
                DIV(
                    A(current.T("Download author's reply (PDF file)"), _href=URL("default", "download", args=recomm.reply_pdf), _style="margin-bottom: 64px;",),
                    _class="pci-bigtext margin",
                ),
            )

        recommRound -= 1

        snippetVars = dict(
            indentationLeft=indentationLeft,
            isLastRecomm=isLastRecomm or False,
            roundNumber=roundNumber,
            lastChanges=lastChanges,
            recommendationText=recommendationText,
            preprintDoi=preprintDoi,
            reviewsList=reviwesPreparedData,
            authorsReply=authorsReply,
            authorsReplyPdfLink=authorsReplyPdfLink,
        )

        indentationLeft += 16

        reviewRoundsHtml.append(XML(response.render("components/public_review_rounds.html", snippetVars)))

    return reviewRoundsHtml


######################################################################################################################################################################
def getRecommCommentListAndForm(auth, db, response, session, articleId, with_reviews=False, parentId=None):
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

    isLoggedIn = False
    scrollToCommentForm = False

    if auth.user_id is not None:
        isLoggedIn = True

    # Create New Comment Form
    commentForm = None
    if isLoggedIn:
        if parentId is not None:
            # Scroll to comment form if 'replyTo' se in request.vars (see jquery in 'components/comments_tree_and_form.html')
            scrollToCommentForm = True
            fields = ["parent_id", "user_comment"]
        else:
            fields = ["user_comment"]

        db.t_comments.user_id.default = auth.user_id
        db.t_comments.user_id.readable = False
        db.t_comments.user_id.writable = False
        db.t_comments.article_id.default = articleId
        db.t_comments.article_id.writable = False
        db.t_comments.parent_id.default = parentId
        db.t_comments.parent_id.writable = False

        commentForm = SQLFORM(db.t_comments, fields=fields, showid=False)

        if commentForm.process().accepted:
            session.flash = current.T("Comment saved", lazy=False)
            redirect(URL(c="articles", f="rec", vars=dict(id=articleId, comments=True, reviews=with_reviews)))
        elif commentForm.errors:
            response.flash = current.T("Form has errors", lazy=False)

    # Get comments tree
    commentsTree = DIV()
    commentsQy = db((db.t_comments.article_id == articleId) & (db.t_comments.parent_id == None)).select(orderby=db.t_comments.comment_datetime)
    if len(commentsQy) > 0:
        for comment in commentsQy:
            commentsTree.append(getCommentsTreeHtml(auth, db, response, comment.id, with_reviews))
    else:
        commentsTree.append(DIV(SPAN(current.T("No user comments yet")), _style="margin-top: 15px"))

    snippetVars = dict(isLoggedIn=isLoggedIn, scrollToCommentForm=scrollToCommentForm, commentForm=commentForm, commentsTree=commentsTree,)

    return XML(response.render("components/comments_tree_and_form.html", snippetVars))


######################################################################################################################################################################
def getCommentsTreeHtml(auth, db, response, commentId, with_reviews=False):
    comment = db.t_comments[commentId]
    childrenDiv = []
    children = db(db.t_comments.parent_id == comment.id).select(orderby=db.t_comments.comment_datetime)

    for child in children:
        childrenDiv.append(getCommentsTreeHtml(auth, db, response, child.id, with_reviews))

    replyToLink = ""
    if auth.user:
        replyToLink = A(
            current.T("Reply..."),
            _href=URL(c="articles", f="rec", vars=dict(articleId=comment.article_id, comments=True, reviews=with_reviews, replyTo=comment.id),),
            _style="margin: 0",
        )

    snippetVars = dict(
        userLink=common_small_html.mkUser_U(auth, db, comment.user_id, linked=True),
        commentDate=str(comment.comment_datetime),
        commentText=WIKI(comment.user_comment) or "",
        replyToLink=replyToLink,
        childrenDiv=childrenDiv,
    )
    return XML(response.render("components/comments_tree.html", snippetVars))


########################################################################################################################################################################
## On going recommendation
########################################################################################################################################################################
def getRecommStatusHeader(auth, db, response, art, controller_name, request, userDiv, printable, quiet=True):
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

    allowManageRequest = False
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (quiet):
        allowManageRequest = True

    snippetVars = dict(
        statusTitle=myTitle,
        allowEditArticle=allowEditArticle,
        allowManageRecomms=allowManageRecomms,
        allowManageRequest=allowManageRequest,
        articleId=art.id,
        printableUrl=URL(c=controller_name, f="recommendations", vars=dict(articleId=art.id, printable=True), user_signature=True),
        printable=printable,
    )

    return XML(response.render("components/recommendation_header.html", snippetVars))


######################################################################################################################################################################
def getRecommendationTopButtons(auth, db, art, printable=False, with_comments=False, quiet=True, scheme=False, host=False, port=False):

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
                _class="pci-EditButtons",
            )
        )  # author's button allowing cancellation

    myContents.append(myButtons)

    return myContents


########################################################################################################################################################################
def getRecommendationProcess(auth, db, response, art, printable=False, with_comments=False, quiet=True, scheme=False, host=False, port=False):
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
            authorsReply = DIV(WIKI(recomm.reply or ""))

        authorsReplyPdfLink = None
        if recomm.reply_pdf:
            authorsReplyPdfLink = A(current.T("Download author's reply (PDF file)"), _href=URL("default", "download", args=recomm.reply_pdf, scheme=scheme, host=host, port=port))

        authorsReplyTrackChangeFileLink = None
        if recomm.track_change:
            authorsReplyTrackChangeFileLink = A(
                current.T("Download tracked changes file"), _href=URL("default", "download", args=recomm.track_change, scheme=scheme, host=host, port=port)
            )

        editAuthorsReplyLink = None
        if (art.user_id == auth.user_id) and (art.status == "Awaiting revision") and not (printable) and not (quiet) and (iRecomm == 1):
            editAuthorsReplyLink = URL(c="user", f="edit_reply", vars=dict(recommId=recomm.id), user_signature=True)

        # Check for reviews
        existOngoingReview = False
        reviewsList = []

        reviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state != "Declined") & (db.t_reviews.review_state != "Cancelled")).select(
            orderby=db.t_reviews.id
        )
        for review in reviews:
            if review.review_state == "Under consideration":
                existOngoingReview = True
            if review.review_state == "Completed":
                nbCompleted += 1
            if review.review_state == "Under consideration":
                nbOnGoing += 1
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

        for review in reviews:
            # No one is allowd to see ongoing reviews ...
            hideOngoingReview = True
            reviewVars = dict(id=review.id, showInvitationButtons=False, showEditButtons=False, authors=None, text=None, reviewPdfUrl=None)
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

            if (review.reviewer_id == auth.user_id) and (review.reviewer_id != recomm.recommender_id) and (art.status == "Under consideration") and not (printable) and not (quiet):
                if review.review_state == "Pending":
                    # reviewer's buttons in order to accept/decline pending review
                    reviewVars.update([("showInvitationButtons", True)])

            elif review.review_state == "Pending":
                hideOngoingReview = True

            if (
                (review.reviewer_id == auth.user_id)
                and (review.review_state == "Under consideration")
                and (art.status == "Under consideration")
                and not (printable)
                and not (quiet)
            ):
                # reviewer's buttons in order to edit/complete pending review
                reviewVars.update([("showEditButtons", True)])

            if not (hideOngoingReview):
                # display the review
                if review.anonymously:
                    reviewVars.update(
                        [
                            (
                                "authors",
                                SPAN(
                                    current.T("Reviewed by"),
                                    " ",
                                    current.T("anonymous reviewer"),
                                    (", " + review.last_change.strftime("%Y-%m-%d %H:%M") if review.last_change else ""),
                                ),
                            )
                        ]
                    )
                else:
                    reviewer = db(db.auth_user.id == review.reviewer_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
                    if reviewer is not None:
                        reviewVars.update(
                            [
                                (
                                    "authors",
                                    SPAN(
                                        current.T("Reviewed by"),
                                        " ",
                                        common_small_html.mkUser(auth, db, review.reviewer_id, linked=True),
                                        (", " + review.last_change.strftime("%Y-%m-%d %H:%M") if review.last_change else ""),
                                    ),
                                )
                            ]
                        )

                if len(review.review or "") > 2:
                    reviewVars.update([("text", WIKI(review.review))])

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
        if not (recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == "Under consideration") and not (printable) and not (quiet):
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
        if not (recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == "Under consideration"):
            inviteReviewerLink = URL(c="recommender", f="reviewers", vars=dict(recommId=recomm.id))

        recommendationText = ""
        if len(recomm.recommendation_comments or "") > 2:
            recommendationText = WIKI(recomm.recommendation_comments or "") if (hideOngoingRecomm is False) else ""

        componentVars = dict(
            printable=printable,
            roundNumber=roundNb,
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
        )
        recommendationRounds.append(XML(response.render("components/recommendation_process.html", componentVars)))

    # Manager button
    managerButton = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable) and not (quiet):
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
def getPostprintRecommendation(auth, db, response, art, printable=False, with_comments=False, quiet=True, scheme=False, host=False, port=False):
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
    if (recomm.recommender_id == auth.user_id) and (art.status == "Under consideration") and not (recomm.is_closed) and not (printable) and not (quiet):
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
        recommendationText = WIKI(recomm.recommendation_comments or "")

    validateRecommendationLink = None
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable) and not (quiet):
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
