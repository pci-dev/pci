# -*- coding: utf-8 -*-

from app_modules.helper import *

from app_components import article_components
from app_components import public_recommendation

from app_modules import common_small_html, old_common
from app_modules import common_tools
from app_modules import common_small_html
from gluon import redirect # type: ignore
from models.article import Article

from gluon import current
from gluon.http import redirect # type: ignore
from models.article import Article, ArticleStatus

auth = current.auth
request = current.request
db = current.db
response = current.response
T = current.T
session = current.session

pciRRactivated = myconf.get("config.registered_reports", default=False)

request = current.request
session = current.session
T = current.T
db = current.db
response = current.response


######################################################################################################################################################################
def index():
    redirect(request.home)


######################################################################################################################################################################
# Recommendations of an article (public)
def rec():
    if request.vars.get("articleId"):
        article_id = request.vars.get("articleId")
        request.vars.pop("articleId")
        request.vars.id = article_id
        return redirect(URL(c="articles", f="rec", args=request.args, vars=request.vars), how=301)

    article_id_str = str(request.vars.get("id"))
    printable = str(request.vars.get("printable")) == "True"
    with_comments = not printable
    as_pdf = str(request.vars.get("asPDF")) == "True"

    if not article_id_str:
        session.flash = T("No parameter id (or articleId)")
        return redirect(request.home)

    try:
        articleId = int(article_id_str)
        assert articleId > 0
    except:
        session.flash = T("Article id must be a positive number")
        return redirect(request.home)

    # Remove "reviews" vars from url
    if "reviews" in request.vars:
        return redirect(URL(c="articles", f="rec", vars=dict(id=articleId)))

    art = Article.get_by_id(articleId)

    if art == None:
        session.flash = T("No such article: id=") + articleId
        return redirect(request.home)

    if art.status != ArticleStatus.RECOMMENDED.value:
        session.flash = T("Access denied: item not recommended yet")
        return redirect(request.home)

    if as_pdf:
        pdfQ = db((db.t_pdf.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == art.id)).select(db.t_pdf.id, db.t_pdf.pdf)
        if len(pdfQ) > 0:
            return redirect(URL("default", "download", args=pdfQ[0]["pdf"]))
        else:
            session.flash = T("Unavailable")
            return redirect(request.env.http_referer)

    # Set Page title
    finalRecomm = Article.get_final_recommendation(art)
    if not finalRecomm:
        session.flash = T("Item not recommended yet")
        return redirect(request.home)

    if handle_rec_signposting(finalRecomm):
        return ""

    if finalRecomm.recommendation_title:
        response.title = finalRecomm.recommendation_title
        response.title = common_tools.getShortText(response.title, 64)

    nbRecomms = int(db((db.t_recommendations.article_id == art.id)).count())
    nbRevs = int(db((db.t_recommendations.article_id == art.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id)).count())
    nbReviews = nbRevs + (nbRecomms - 1)

    # Recommendation Header and Metadata
    recommendationHeader = public_recommendation.getArticleAndFinalRecommendation(art, finalRecomm, printable)
    recommHeaderHtml = recommendationHeader["headerHtml"]
    recommMetadata = recommendationHeader["recommMetadata"]
    dublin_core = recommendationHeader["dublin_core"]

    if len(recommMetadata) > 0:
        response.meta = recommMetadata

    reviewRounds = DIV(public_recommendation.getPublicReviewRoundsHtml(art))

    commentsTreeAndForm = None
    if with_comments:
        commentsTreeAndForm = public_recommendation.getRecommCommentListAndForm(art.id, request.vars["replyTo"])

    if printable:
        printableClass = "printable"
        response.view = "default/wrapper_printable.html"
    else:
        printableClass = ""
        response.view = "default/wrapper_normal.html"

    viewToRender = "controller/articles/public_article_recommendation.html"
    return dict(
        viewToRender=viewToRender,
        withComments=with_comments,
        printableUrl=URL(c="articles", f="rec", vars=dict(id=articleId, printable=True), user_signature=True),
        currentUrl=URL(c="articles", f="rec", vars=dict(id=articleId), scheme=True),
        shareButtons=True,
        nbReviews=nbReviews,
        pciRRactivated=pciRRactivated,
        recommHeaderHtml=recommHeaderHtml,
        reviewRounds=reviewRounds,
        commentsTreeAndForm=commentsTreeAndForm,
        printableClass=printableClass,
        myBackButton=common_small_html.mkBackButton(),
        dublinCore=dublin_core
    )


def handle_rec_signposting(recomm: Recommendation):
    if request.method == 'HEAD':
        article_id = recomm.article_id

        response.headers = { "link": ", ".join([
            '<' + URL("metadata", f"{target}?article_id={article_id}", scheme=True)
            + f'>; rel="describedby" {opts}'

            for target, opts in [
                ("docmaps", 'type="application/ld+json" profile="https://w3id.org/docmaps/context.jsonld"'),
                ("crossref", 'type="application/xml" profile="http://www.crossref.org/schema/4.3.7"'),
            ]
        ])}
        return True


######################################################################################################################################################################
def tracking():
    article_list = DIV(_class="pci2-articles-list")

    query_already_published_articles = db(db.t_articles.already_published == False).select(orderby=~db.t_articles.last_status_change)

    for article in query_already_published_articles:
        article_html_card = article_components.getArticleTrackcRowCard(article)
        if article_html_card:
            article_list.append(article_html_card) # type: ignore

    response.view = "default/gab_list_layout.html"
    resu = dict(
        pageHelp=getHelp("#Tracking"),
        titleIcon="tasks",
        pageTitle=getTitle("#TrackingTitle"),
        customText=getText("#TrackingText"),
        grid=DIV(article_list, _class="pci2-flex-center"),
    )
    return resu


######################################################################################################################################################################
def pub_reviews():
    if "articleId" in request.vars:
        articleId = request.vars["articleId"]
    elif "id" in request.vars:
        articleId = request.vars["id"]
    else:
        session.flash = T("Unavailable")
        return redirect(request.env.http_referer)
    # NOTE: check id is numeric!
    if not str(articleId).isdigit():
        session.flash = T("Unavailable")
        return redirect(request.env.http_referer)

    art = db.t_articles[articleId]
    myContents = None
    if art is None:
        session.flash = T("Unavailable")
        return redirect(request.env.http_referer)
    elif art.status != "Cancelled":
        session.flash = T("Unavailable")
        return redirect(request.env.http_referer)
    else:
        myContents = DIV(old_common.reviewsOfCancelled(art))

    response.view = "default/myLayout.html"
    resu = dict(
        titleIcon="eye-open",
        pageTitle=getTitle("#TrackReviewsTitle"),
        pageHelp=getHelp("#TrackReviews"),
        customText=getText("#TrackReviewsText"),
        grid=myContents,
    )
    return resu
