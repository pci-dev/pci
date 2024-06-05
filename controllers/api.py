# -*- coding: utf-8 -*-

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

    return json({
        "version": { "hash": sha, "tag": tag }
    })


def pci():
    return json({
        "theme": db.cfg.description.replace("Peer Community in ", ""),
    })


def coar_inbox():
    return json({
        "url": URL("coar_notify", "inbox", scheme=True),
    })


def issn():
    return json({
        "issn": db.cfg.issn
    })


def coar_inboxes():
    hosts = filter(lambda h: h != 'rr', pci_hosts())
    return json({
        host: res.get("theme")
            for host, res in call_all(hosts, "pci")
    })


def all():
    endpoint = request.args[0] if request.args else None

    if endpoint is None: return error("usage: api/all/<endpoint>")
    if endpoint == "all": return error("recursive call on all")

    return json({
        host: res for host, res in call_all(pci_hosts(), endpoint)
    })


def recommendations():
    from app_modules.common_small_html import mkLinkDOI
    from models.recommendation import Recommendation, RecommendationState
    recomms = Recommendation.get_all([RecommendationState.RECOMMENDED])
    return json([
        {
            "recommendation": {
                "url": URL("articles", f"rec?id={recom.article_id}", scheme=True),
                "doi": mkLinkDOI(recom.recommendation_doi),
                "recommender": User.get_name(recom.recommender_id),
                "co-recommenders": [
                    User.get_name(coreco.contributor_id)
                        for coreco in Recommendation.get_co_recommenders(recom)
                ],
            },
            "article": {
                "doi": recom.article_id.doi,
                "published_doi": recom.article_id.doi_of_published_article,
            },
        }
        for recom in recomms if recom.article_id.status == "Recommended"
    ])


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
    api_url = f"https://{host}.peercommunityin.org/api/" \
            if host != "localhost" else f"http://{host}:8000/pci/api/"

    try:
        return requests.get(
            api_url + endpoint
            , auth=basic_auth
        ).json()

    except Exception as err:
        return { "error": f"{type(err).__name__}: {err}" }


from multiprocessing.pool import ThreadPool

def call_all(hosts, endpoint):
    return ThreadPool().map(
        lambda host: [host, api_call(host, endpoint)],
        hosts
    )
