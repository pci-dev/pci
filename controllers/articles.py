# -*- coding: utf-8 -*-

from app_modules.helper import *

from app_components import article_components
from app_components import public_recommendation

from app_modules import old_common
from app_modules import common_tools

pciRRactivated = myconf.get("config.registered_reports", default=False)
######################################################################################################################################################################
def index():
    redirect(request.home)


######################################################################################################################################################################
# Recommendations of an article (public)
def rec():
    articleId = request.vars.get("articleId") or request.vars.get("id")
    printable = request.vars.get("printable") == "True"
    with_comments = not printable
    as_pdf = request.vars.get("asPDF") == "True"

    if not articleId:
        session.flash = T("No parameter id (or articleId)")
        redirect(request.home)

    # Remove "reviews" vars from url
    if "reviews" in request.vars:
        redirect(URL(c="articles", f="rec", vars=dict(id=articleId)))

    if not articleId.isdigit():
        session.flash = T("Article id must be a digit")
        redirect(request.home)

    art = db.t_articles[articleId]

    if art == None:
        session.flash = T("No such article: id=") + articleId
        redirect(request.home)

    if art.status != "Recommended":
        session.flash = T("Access denied: item not recommended yet")
        redirect(request.home)

    if as_pdf:
        pdfQ = db((db.t_pdf.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == art.id)).select(db.t_pdf.id, db.t_pdf.pdf)
        if len(pdfQ) > 0:
            redirect(URL("default", "download", args=pdfQ[0]["pdf"]))
        else:
            session.flash = T("Unavailable")
            redirect(redirect(request.env.http_referer))

    # Set Page title
    finalRecomm = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()
    if not finalRecomm:
        session.flash = T("Item not recommended yet")
        redirect(request.home)

    response.title = finalRecomm.recommendation_title
    response.title = common_tools.getShortText(response.title, 64)

    nbRecomms = db((db.t_recommendations.article_id == art.id)).count()
    nbRevs = db((db.t_recommendations.article_id == art.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id)).count()
    nbReviews = nbRevs + (nbRecomms - 1)

    # Recommendation Header and Metadata
    recommendationHeader = public_recommendation.getArticleAndFinalRecommendation(auth, db, response, art, finalRecomm, printable)
    recommHeaderHtml = recommendationHeader["headerHtml"]
    recommMetadata = recommendationHeader["recommMetadata"]

    if len(recommMetadata) > 0:
        response.meta = recommMetadata

    reviewRounds = DIV(public_recommendation.getPublicReviewRoundsHtml(auth, db, response, art.id))

    commentsTreeAndForm = None
    if with_comments:
        # Get user comments list and form
        commentsTreeAndForm = public_recommendation.getRecommCommentListAndForm(auth, db, response, session, art.id, request.vars["replyTo"])

    if printable:
        printableClass = "printable"
        response.view = "default/wrapper_printable.html"
    else:
        printableClass = ""
        response.view = "default/wrapper_normal.html"

    viewToRender = "controller/articles/public_article_recommendation.html" #xxx
    return dict(
        viewToRender=viewToRender,
        withComments=with_comments,
        printableUrl=URL(c="articles", f="rec", vars=dict(articleId=articleId, printable=True), user_signature=True),
        currentUrl=URL(c="articles", f="rec", vars=dict(articleId=articleId), host=host, scheme=scheme, port=port),
        shareButtons=True,
        nbReviews=nbReviews,
        pciRRactivated=pciRRactivated,
        recommHeaderHtml=recommHeaderHtml,
        reviewRounds=reviewRounds,
        commentsTreeAndForm=commentsTreeAndForm,
        printableClass=printableClass,
        myBackButton=common_small_html.mkBackButton(),
    )


######################################################################################################################################################################
def tracking():
    tracking = True # myconf.get("config.tracking", default=False)
    if tracking is False:
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    else:
        article_list = DIV(_class="pci2-articles-list")

        query_already_published_articles = db(db.t_articles.already_published == False).select(orderby=~db.t_articles.last_status_change)

        for article in query_already_published_articles:
            article_html_card = article_components.getArticleTrackcRowCard(auth, db, response, article)
            if article_html_card:
                article_list.append(article_html_card)

        response.view = "default/gab_list_layout.html"
        resu = dict(
            pageHelp=getHelp(request, auth, db, "#Tracking"),
            titleIcon="tasks",
            pageTitle=getTitle(request, auth, db, "#TrackingTitle"),
            customText=getText(request, auth, db, "#TrackingText"),
            grid=DIV(article_list, _class="pci2-flex-center"),
        )
        return resu


######################################################################################################################################################################
def pub_reviews():
    tracking = True # myconf.get("config.tracking", default=False)
    if tracking is False:
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    elif "articleId" in request.vars:
        articleId = request.vars["articleId"]
    elif "id" in request.vars:
        articleId = request.vars["id"]
    else:
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    # NOTE: check id is numeric!
    if not articleId.isdigit():
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))

    art = db.t_articles[articleId]
    myContents = None
    if art is None:
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    elif art.status != "Cancelled":
        session.flash = T("Unavailable")
        redirect(redirect(request.env.http_referer))
    else:
        myContents = DIV(old_common.reviewsOfCancelled(auth, db, art))

    response.view = "default/myLayout.html"
    resu = dict(
        titleIcon="eye-open",
        pageTitle=getTitle(request, auth, db, "#TrackReviewsTitle"),
        pageHelp=getHelp(request, auth, db, "#TrackReviews"),
        customText=getText(request, auth, db, "#TrackReviewsText"),
        grid=myContents,
    )
    return resu
