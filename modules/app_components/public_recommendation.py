# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Literal, Optional, Union
from models.article import Article
from models.recommendation import Recommendation
from re import sub
from dateutil.relativedelta import *
from collections import OrderedDict

from gluon.html import *
from gluon.contrib.markdown import WIKI # type: ignore
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon.sqlhtml import *

from app_modules import common_small_html
from app_modules import common_tools
from app_modules.common_small_html import md_to_html

from app_components import article_components
from app_modules import emailing
from app_modules.common_tools import URL
from app_modules.schema_org import SchemaOrg

myconf = AppConfig(reload=True)

pciRRactivated = myconf.get("config.registered_reports", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

########################################################################################################################################################################
## Public recommendation
######################################################################################################################################################################
def getArticleAndFinalRecommendation(art: Article,
                                     finalRecomm: Recommendation,
                                     printable: bool,
                                     fullURL: bool = True):
    db = current.db

    headerContent: Dict[str, Any] = dict()

    recomm_altmetric = ""

    articleInfosCard = article_components.get_article_infos_card(
            art, printable,
            with_version=pciRRactivated,
            with_cover_letter=False, submitted_by=False, keywords=True)

    headerContent.update([("articleInfosCard", articleInfosCard)])

    isStage2 = art.art_stage_1_id is not None
    stage1Link = None
    stage2List: Optional[List[Union[DIV, Literal['']]]] = None
    if pciRRactivated and art.art_stage_1_id is not None:
        urlArticle = URL(c="articles", f="rec", vars=dict(id=art.art_stage_1_id))
        stage1Link = common_small_html.mkRepresentArticleLightLinked(art.art_stage_1_id, urlArticle)
    elif pciRRactivated and not isStage2:
        stage2Articles: List[Article] = db((db.t_articles.art_stage_1_id == art.id) & (db.t_articles.status == "Recommended")).select()
        stage2List = []
        for art_st_2 in stage2Articles:
            urlArticle = URL(c="articles", f="rec", vars=dict(id=art_st_2.id))
            stage2List.append(common_small_html.mkRepresentArticleLightLinked(art_st_2.id, urlArticle))

    if finalRecomm.recommendation_doi:
        recomm_altmetric = XML(
            """
                <div class='altmetric-embed pci2-altmetric'  data-badge-type='donut' data-badge-popover="right" data-hide-no-mentions='true' data-doi='%s'></div>
            """
            % sub(r"doi: *", "", finalRecomm.recommendation_doi)
        )


    cite = common_small_html.build_citation(art, finalRecomm)

    if art.already_published:
        info = ""
        funding = ""
    else:
        info = DIV(
            SPAN(
                B("Conflict of interest:", _class="pci2-main-color-text"),
                BR(),
                SPAN("The recommender in charge of the evaluation of the article and the reviewers declared that they have no conflict of interest ",
                "(as defined in ", A("the code of conduct of PCI",  _href="../about/ethics"), ") ",
                "with the authors or with the content of the article. ",
                "The authors declared that they comply with the PCI rule of having no financial conflicts of interest in relation to the content of the article." \
                        if not pciRRactivated else ""
                ),
            ),
            _class="pci-conflict-of-interest-note",
        )

        funding = DIV(
            SPAN(
                B("Funding:", _class="pci2-main-color-text"),
                BR(),
                SPAN(art.funding)
            ) if art.funding else "",
            _class="pci-funding",
        ) if not pciRRactivated else ""

    whoDidRecomm = common_small_html.getRecommAndReviewAuthors(
            recomm=finalRecomm,
            with_reviewers=True, linked=True,
            fullURL=fullURL,
            this_recomm_only=True,
            orcid_exponant=True
            )

    # PDF (if any)
    pdf_query = db(db.t_pdf.recommendation_id == finalRecomm.id).select(db.t_pdf.id, db.t_pdf.pdf)
    pdfUrl = None
    pdfLink = None

    if len(pdf_query) > 0:
        pdfUrl = URL("articles", "rec", vars=dict(articleId=art.id, asPDF=True), scheme=fullURL)
        pdfLink = A(SPAN(current.T("PDF recommendation"), " ", IMG(_alt="pdf", _src=URL("static", "images/application-pdf.png"))), _href=pdfUrl, _class="btn btn-info pci-public",)

    recommendationPdfLink = None
    if finalRecomm.recommender_file:
        recommendationPdfLink = A(
            I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
            current.T("Download recommender's annotations (PDF)"),
            _href=URL("default", "download", args=finalRecomm.recommender_file, scheme=fullURL),
            _style="font-weight: bold; margin-top: 15px; margin-bottom: 5px; display:block",
        )
    article_upload_time = art.upload_timestamp.strftime("posted %d %B %Y") if art.upload_timestamp else ""
    article_validation_time = art.validation_timestamp.strftime(", validated %d %B %Y") if art.validation_timestamp else ""
    if pciRRactivated: article_validation_time = ""
    recomm_post_time = finalRecomm.last_change.strftime("posted %d %B %Y") if finalRecomm.last_change else ""
    recomm_validation_time = finalRecomm.validation_timestamp.strftime(", validated %d %B %Y") if finalRecomm.validation_timestamp else ""

    headerContent.update(
        [
            ("recommTitle", md_to_html(finalRecomm.recommendation_title) if ((finalRecomm.recommendation_title or "") != "") else current.T("Recommendation"),),
            ("recommAuthor", whoDidRecomm),
            (
                "recommDateinfos",
                (
                    I(f"Submission: {article_upload_time}{article_validation_time}") if not art.already_published else "",
                    BR() if not art.already_published else "",
                    I(f"Recommendation: {recomm_post_time}{recomm_validation_time}"),
                ),
            ),
            ("recomm_altmetric", recomm_altmetric),
            ("cite", cite),
            ("info", info),
            ("funding", funding),
            ("recommText", WIKI(finalRecomm.recommendation_comments or "", safe_mode=False)),
            ("pdfLink", pdfLink),
            ("printable", printable),
            ("recommendationPdfLink", recommendationPdfLink),
            ("pciRRactivated", pciRRactivated),
            ("isStage2", isStage2),
            ("stage1Link", stage1Link),
            ("stage2List", stage2List),
        ]
    )

    # Get METADATA (see next function)
    recommMetadata = getRecommendationMetadata(art, finalRecomm, pdfUrl, Recommendation.get_doi_id(finalRecomm))
    schema_org = SchemaOrg(art).to_script_tag()

    headerHtml = XML(current.response.render("components/last_recommendation.html", headerContent))
    return dict(headerHtml=headerHtml, recommMetadata=recommMetadata, schema_org=schema_org)


######################################################################################################################################################################
def getRecommendationMetadata(art: Article, lastRecomm: Recommendation, pdfLink: Optional[str], citeNum: Optional[str]):
    desc = "A recommendation of: " + (art.authors or "") + " " + (md_to_html(art.title).flatten() or "") + " " + (art.doi or "")
    whoDidItMeta = common_small_html.getRecommAndReviewAuthors(recomm=lastRecomm, with_reviewers=False, linked=False, as_list=True)

    # META headers
    myMeta: OrderedDict[str, Any] = OrderedDict()
    myMeta["citation_title"] = lastRecomm.recommendation_title
    if len(whoDidItMeta) > 0:
        # Trick for multiple entries (see globals.py:464)
        for wdi in whoDidItMeta:
            myMeta["citation_author_%s" % wdi] = OrderedDict([("name", "citation_author"), ("content", wdi)])
    myMeta["citation_journal_title"] = myconf.take("app.description")
    myMeta["citation_publication_date"] = (lastRecomm.last_change.date()).strftime("%Y/%m/%d")
    myMeta["citation_online_date"] = (lastRecomm.last_change.date()).strftime("%Y/%m/%d")
    myMeta["citation_journal_abbrev"] = myconf.take("app.name")
    myMeta["citation_issn"] = current.db.config[1].issn
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
def getPublicReviewRoundsHtml(articleId: int):
    db= current.db

    recomms = db((db.t_recommendations.article_id == articleId)).select(orderby=~db.t_recommendations.id)

    recommRound = len(recomms)
    reviewRoundsHtml = DIV()

    for recomm in recomms:
        roundNumber = recommRound

        lastChanges = ""
        validationDate = ""
        recommendationText = ""
        preprintVersion = recomm.ms_version
        preprintDoi = ""
        isLastRecomm = False
        if recomms[0].id == recomm.id:
            isLastRecomm = True
        else:
            lastChanges = SPAN(I("posted ", recomm.last_change.strftime(DEFAULT_DATE_FORMAT))) if recomm.last_change else ""
            validationDate = SPAN(I(", validated ", recomm.validation_timestamp.strftime(DEFAULT_DATE_FORMAT))) if recomm.validation_timestamp else ""
            recommendationText = WIKI(recomm.recommendation_comments or "", safe_mode=False)
            preprintDoi = SPAN(common_small_html.mkDOI(recomm.doi), BR()) if ((recomm.doi or "") != "") else ""

        reviewsList = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Review completed")).select(orderby=db.t_reviews.id)
        reviwesPreparedData = []

        count_anon = 0
        for review in reviewsList:
            if review.anonymously:
                count_anon += 1
                reviewer_number = common_tools.find_reviewer_number(review, count_anon)
                reviewAuthorAndDate = SPAN(
                    current.T("Reviewed by") + " " + current.T("anonymous reviewer %s"%(reviewer_number)) + (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT) if review.last_change else "")
                )

            else:
                reviewAuthorAndDate = SPAN(
                    current.T("Reviewed by"),
                    " ", common_small_html.mkUser(review.reviewer_id, linked=True, orcid_exponant=True),
                    (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT) if review.last_change else ""),
                )

            reviewText = None
            if review.review:
                if len(review.review) > 2:
                    reviewText = WIKI(review.review, safe_mode=False)

            pdfLink = None
            if review.review_pdf:
                pdfLink = A(
                    I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
                    current.T("Download the review (PDF file)"),
                    _href=URL("default", "download", args=review.review_pdf, scheme=True),
                    _style="font-weight: bold; margin-bottom: 5px; display:block",
                )

            reviwesPreparedData.append(dict(authorAndDate=reviewAuthorAndDate, text=reviewText, pdfLink=pdfLink, id=review.id))

        authorsReply = None
        authorsReplyDate = None
        if (recomm.reply is not None and len(recomm.reply) > 0):
            authorsReply = DIV(WIKI(recomm.reply, safe_mode=False), _class="pci-bigtext")

        authorsReplyPdfLink = None
        if recomm.reply_pdf:
            authorsReplyPdfLink = A(
                I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
                current.T("Download author's reply (PDF file)"),
                _href=URL("default", "download", args=recomm.reply_pdf, scheme=True),
                _style="font-weight: bold; margin-bottom: 5px; display:block",
            )

        authorsReplyTrackChangeFileLink = None
        if recomm.track_change:
            authorsReplyTrackChangeFileLink = A(
                I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
                current.T("Download tracked changes file"),
                _href=URL("default", "download", args=recomm.track_change, scheme=True),
                _style="font-weight: bold; margin-bottom: 5px; display:block",
            )
        if (recomm.reply is not None and len(recomm.reply) > 0) or recomm.reply_pdf is not None or recomm.track_change is not None:
            authorsReplyDate = nextRound.recommendation_timestamp.strftime(DEFAULT_DATE_FORMAT) \
                if not isLastRecomm else None
        nextRound = recomm # iteration is last first; last round (final reco) has no author's reply

        recommendationPdfLink = None
        if recomm.recommender_file:
            recommendationPdfLink = A(
                I(_class="glyphicon glyphicon-save-file", _style="color: #ccc; margin-right: 5px; font-size: 18px"),
                current.T("Download recommender's annotations (PDF)"),
                _href=URL("default", "download", args=recomm.recommender_file, scheme=True),
                _style="font-weight: bold; margin-bottom: 5px; display:block",
            )

        recommAuthors = common_small_html.getRecommAndReviewAuthors(
                        recomm=recomm,
                        with_reviewers=False, linked=True,
                        fullURL=True,
                        this_recomm_only=True,
                        orcid_exponant=True
                        )
        recommAuthors = SPAN(recommAuthors)
        recommRound -= 1

        componentVars = dict(
            isLastRecomm=isLastRecomm or False,
            roundNumber=roundNumber,
            preprintVersion=preprintVersion,
            recommAuthors=recommAuthors,
            lastChanges=lastChanges,
            validationDate=validationDate,
            recommendationText=recommendationText,
            preprintDoi=preprintDoi,
            reviewsList=reviwesPreparedData,
            authorsReply=authorsReply,
            authorsReplyDate=authorsReplyDate,
            authorsReplyPdfLink=authorsReplyPdfLink,
            recommendationPdfLink=recommendationPdfLink,
            authorsReplyTrackChangeFileLink=authorsReplyTrackChangeFileLink,
        )

        reviewRoundsHtml.append(XML(current.response.render("components/public_review_rounds.html", componentVars)))

    return reviewRoundsHtml


######################################################################################################################################################################
def getRecommCommentListAndForm(articleId: int, parentId: Optional[int] = None):
    auth, db, response, session = current.auth, current.db, current.response, current.session

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
            emailing.send_new_comment_alert(articleId)
            redirect(URL(c="articles", f="rec", vars=dict(id=articleId, comments=True)))
        elif commentForm.errors:
            response.flash = current.T("Form has errors", lazy=False)

    # Get comments tree
    commentsTree = DIV()
    commentsQy = db((db.t_comments.article_id == articleId) & (db.t_comments.parent_id == None)).select(orderby=db.t_comments.comment_datetime)
    if len(commentsQy) > 0:
        for comment in commentsQy:
            commentsTree.append(getCommentsTreeHtml(comment.id))
    else:
        commentsTree.append(DIV(SPAN(current.T("No user comments yet")), _style="margin-top: 15px"))

    componentVars = dict(isLoggedIn=isLoggedIn, scrollToCommentForm=scrollToCommentForm, commentForm=commentForm, commentsTree=commentsTree,)

    return XML(response.render("components/comments_tree_and_form.html", componentVars))


def getCommentsTreeHtml(commentId):
    auth, db, response = current.auth, current.db, current.response
    comment = db.t_comments[commentId]
    childrenDiv = []
    children = db(db.t_comments.parent_id == comment.id).select(orderby=db.t_comments.comment_datetime)

    for child in children:
        childrenDiv.append(getCommentsTreeHtml(child.id))

    replyToLink = ""
    if auth.user:
        replyToLink = A(current.T("Reply..."), _href=URL(c="articles", f="rec", vars=dict(articleId=comment.article_id, comments=True, replyTo=comment.id),), _style="margin: 0",)

    componentVars = dict(
        userLink=common_small_html.mkUser_U(comment.user_id, linked=True),
        commentDate=str(comment.comment_datetime),
        commentText=WIKI(comment.user_comment) or "",
        replyToLink=replyToLink,
        childrenDiv=childrenDiv,
    )
    return XML(response.render("components/comments_tree.html", componentVars))
