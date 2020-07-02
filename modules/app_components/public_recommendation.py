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
            ("recommText", WIKI(finalRecomm.recommendation_comments, safe_mode=False or "")),
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
            recommendationText = WIKI(recomm.recommendation_comments, safe_mode=False) or ""
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
                reviewText = WIKI(review.review, safe_mode=False)

            pdfLink = None
            if review.review_pdf:
                pdfLink = DIV(
                    A(current.T("Download the review (PDF file)"), _href=URL("default", "download", args=review.review_pdf), _style="margin-bottom: 64px;",),
                    _class="pci-bigtext margin",
                )

            reviwesPreparedData.append(dict(authorAndDate=reviewAuthorAndDate, text=reviewText, pdfLink=pdfLink))

        authorsReply = None
        if recomm.reply:
            authorsReply = DIV(WIKI(recomm.reply, safe_mode=False), _class="pci-bigtext")

        authorsReplyPdfLink = None
        if recomm.reply_pdf:
            authorsReplyPdfLink = (
                DIV(
                    A(current.T("Download author's reply (PDF file)"), _href=URL("default", "download", args=recomm.reply_pdf), _style="margin-bottom: 64px;",),
                    _class="pci-bigtext margin",
                ),
            )

        recommRound -= 1

        componentVars = dict(
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

        reviewRoundsHtml.append(XML(response.render("components/public_review_rounds.html", componentVars)))

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

    componentVars = dict(isLoggedIn=isLoggedIn, scrollToCommentForm=scrollToCommentForm, commentForm=commentForm, commentsTree=commentsTree,)

    return XML(response.render("components/comments_tree_and_form.html", componentVars))


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

    componentVars = dict(
        userLink=common_small_html.mkUser_U(auth, db, comment.user_id, linked=True),
        commentDate=str(comment.comment_datetime),
        commentText=WIKI(comment.user_comment) or "",
        replyToLink=replyToLink,
        childrenDiv=childrenDiv,
    )
    return XML(response.render("components/comments_tree.html", componentVars))
