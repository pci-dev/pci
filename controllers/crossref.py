from app_modules import crossref
from app_modules.clockss import send_to_clockss
from app_modules.common_tools import URL
from gluon import PRE, current
from models.article import Article


auth = current.auth
request = current.request
db = current.db
response = current.response
T = current.T
session = current.session

is_admin = auth.has_membership(role="administrator")

def index():
    request.function = "post_form" # zap header in layout.html
    return post_form()


@auth.requires(is_admin)
def post_form():
    try:
        article_id = int(request.vars.article_id)
    except:
        return error("article_id: no such parameter")

    article = Article.get_by_id(article_id)
    if not article:
        return error("article: no such article")

    recommendation = Article.get_last_recommendation(article_id)
    if not recommendation :
        return error("article: no recommendation yet")

    if not recommendation.recommendation_title:
        return error("recommendation: no title (not recommended)")

    disable_form = False

    batch_id = crossref.get_filename_article(recommendation)

    if f"article_xml;{batch_id}" in request.vars:
        recommendation_xml = crossref.CrossrefXML.from_request(request)

        post_response = crossref.post_and_forget(article, recommendation_xml)
        if not post_response:
            try:
                send_to_clockss(article, recommendation)
            except Exception as e:
                response.flash = f"{e}"

        crossref_status = post_response or "request sent"
        disable_form = True
        response.flash = "Send to Crossref & Clockss"
    else:
        recommendation_xml = crossref.CrossrefXML.build(article)
        crossref_status = ""

    response.view = "controller/crossref.html"
    return dict(
        get_status_url=URL("crossref", f"get_status_response?article_id={article_id}"),
        crossref_status=crossref_status,
        back_url=URL("manager", f"recommendations?articleId={recommendation.article_id}"),
        disable_form=disable_form,
        recommendation_xml=recommendation_xml,
        titleIcon="envelope",
        pageTitle="Crossref post form",
    )


@auth.requires(is_admin)
def get_status_response():
    article_id = request.vars.article_id

    try:
        article = Article.get_by_id(article_id)
        assert article
    except:
        return f"error: no such article_id={article_id}"

    recommendation_xml = crossref.CrossrefXML.build(article)
    status = recommendation_xml.get_status()

    return status


@auth.requires(is_admin)
def get_status():
    article_id = request.vars.article_id

    try:
        article = Article.get_by_id(article_id)
        assert article
    except:
        return f"error: no such article_id={article_id}"

    recommendation_xml = crossref.CrossrefXML.build(article)
    status = recommendation_xml.get_status()
    return (
        3 if status.startswith("error:") else
        2 if crossref.QUEUED in status else
        1 if crossref.FAILED in status else
        0
    )


def error(message: str):
    response.view = "default/myLayout.html"
    return dict(
        form=PRE(message),
        titleIcon="envelope",
        pageTitle="Crossref post error",
    )
