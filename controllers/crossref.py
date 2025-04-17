from app_modules import crossref
from app_modules.clockss import send_to_clockss
from app_modules.common_tools import URL
from gluon import PRE, current
from models.article import Article
from models.recommendation import Recommendation

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

    crossref_status = get_crossref_status(recommendation)
    disable_form = False

    batch_id = crossref.get_filename_article(recommendation)

    if f"article_xml;{batch_id}" in request.vars:
        recommendation_xml = crossref.CrossrefXML.from_request(request)
        status = crossref.post_and_forget(article, recommendation_xml)

        if not status:
            try:
                send_to_clockss(article, recommendation)
            except Exception as e:
                response.flash = f"{e}"

        crossref_status = status or "request sent"
        disable_form = True
    else:
        recommendation_xml = crossref.crossref_recommendations_xml(article)


    response.view = "controller/crossref.html"
    return dict(
        crossref_status=crossref_status,
        back_url=URL("manager", f"recommendations?articleId={recommendation.article_id}"),
        disable_form=disable_form,
        recommendation_xml=recommendation_xml,
        titleIcon="envelope",
        pageTitle="Crossref post form",
    )



@auth.requires(is_admin)
def get_status():
    recomm_id = request.vars.recomm_id

    try:
        recomm = Recommendation.get_by_id(recomm_id)
        assert recomm
    except:
        return f"error: no such recomm_id={recomm_id}"

    status = crossref.get_status(recomm)
    return (
        3 if status.startswith("error:") else
        2 if crossref.QUEUED in status else
        1 if crossref.FAILED in status else
        0
    )


def get_crossref_status(recomm: Recommendation):
    status = crossref.get_status(recomm)
    if status.startswith("error:") \
    or crossref.QUEUED in status:
        return status

    if crossref.FAILED in status:
        return "error: " + crossref.FAILED + "\n\n" + status
    else:
        return "success"


def error(message: str):
    response.view = "default/myLayout.html"
    return dict(
        form=PRE(message),
        titleIcon="envelope",
        pageTitle="Crossref post error",
    )
