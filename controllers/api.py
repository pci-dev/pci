# -*- coding: utf-8 -*-

from typing import Any
from app_modules.common_small_html import doi_to_url
from app_modules.utils import run
from app_modules.utils import json

response.headers['Content-Type'] = 'application/json'


def index():
    response.headers['Content-Type'] = 'text/html'

    return menu([
        "pci",
        "version",
        "issn",
        "all/pci",
        "all/issn",
        "coar_inboxes",
    ])


def version():
    ver = run(f"git describe --tags --long --dirty=+").strip().split('-')
    sha = ver[-1][1:]
    inc = int(ver[-2])
    tag = "-".join(ver[:-2])
    if inc: tag += f"+{inc}"
    if "+" in sha: tag += "*"

    return json({
        "version": { "hash": sha, "tag": tag }
    })


def pci():
    return json(_pci())

def _pci():
    return ({
        "theme": db.cfg.description.replace("Peer Community in ", ""),
    })


def coar_inbox():
    return json({
        "url": URL("coar_notify", "inbox", scheme=True),
        "theme": _pci().get("theme"),
    })


def issn():
    return json({
        "issn": db.cfg.issn
    })


def coar_inboxes():
    exclude = [ 'rr' ]
    hosts = filter(lambda h: h not in exclude, pci_hosts())
    return json({
        host: res.get("theme")
            for host, res in call_all(hosts, "pci")
    })


def all():
    endpoint = request.args[0] if request.args else None

    if endpoint is None: return error("usage: api/all/<endpoint>")
    if endpoint == "all": return error("recursive call on all")

    if endpoint == "coar_inbox":
        hosts = filter(lambda h: h != "rr", pci_hosts())
    else:
        hosts = pci_hosts()

    return json({
        host: res for host, res in call_all(hosts, endpoint)
    })


def recommendations():
    from models.recommendation import Recommendation, RecommendationState
    from models.article import Article, ArticleStatus
    from app_modules.common_tools import URL
    from models.user import User

    recomms = Recommendation.get_all([RecommendationState.RECOMMENDED])
    articles = Article.get_by_status([ArticleStatus.RECOMMENDED])

    els: list[Any] = []

    for recom in recomms:
        article = list(filter(lambda a: a.id == recom.article_id, articles))
        if len(article) == 1:
            article = article[0]

            el: Any = {
                "recommendation": {
                    "url": URL("articles", f"rec?id={recom.article_id}", scheme=True),
                    "doi": doi_to_url(recom.recommendation_doi or ""),
                    "recommender": User.get_name(recom.recommender_id),
                    "co-recommenders": [
                        User.get_name(coreco.contributor_id)
                            for coreco in Recommendation.get_co_recommenders(recom.id)
                    ],
                },
                "article": {
                    "doi": recom.article_id.doi,
                    "published_doi": recom.article_id.doi_of_published_article,
                },
            }

            els.append(el)
    
    return json(els)


# internals

def pci_hosts(conf_key="host"):
    return read_confs(conf_key, cleanup="s:[.].*::")


def read_confs(key, cleanup=""):
    return run(f"""sh -c "
        cd ..
        cat PCI*/private/appconfig.ini \\
        | egrep '^{key} = ' \\
        | sed  's:{key} = ::; {cleanup}'
        " """
        ).strip().split('\n')


def menu(items):
    return "<br>\n".join(map(str, [
        A(x, _href=URL(x)) for x in items
    ]))


def error(mesg, status=400):
    response.status = status
    return json({"error": mesg})


import requests

basic_auth = db.conf.get("config.basic_auth")
if basic_auth: basic_auth = tuple(basic_auth.split(":"))


def api_call(host, endpoint):
    api_url = f"https://{host}/api/" \
            if host != "localhost" else f"http://{host}:8000/pci/api/"

    try:
        return requests.get(
            api_url + endpoint
            , auth=basic_auth
            , verify=False
        ).json()

    except Exception as err:
        return { "error": f"{type(err).__name__}: {err}" }


from multiprocessing.pool import ThreadPool

def call_all(hosts, endpoint):
    return ThreadPool().map(
        lambda host: [host, api_call(host, endpoint)],
        hosts
    )
