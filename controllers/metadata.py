import json
import datetime
from app_modules.common_tools import url_to_doi_id
from gluon import HTTP

from app_modules import crossref as _crossref

from app_modules.common_small_html import mkUser, URL
from app_modules.httpClient import HttpClient
from models.review import ReviewState, Review
from models.article import Article
from models.recommendation import Recommendation
from typing import cast, Any

from gluon.storage import Storage
from gluon import current

response = current.response
request = current.request
db = current.db

def parse_args(request: ...):
    article_id = request.vars.article_id or request.vars.id

    try:
        article = Article.get_by_id(article_id)
        assert article
    except:
        raise HTTP(400, f"no such article: {article_id}")

    recomm = Article.get_final_recommendation(article)

    if not recomm:
        raise HTTP(400, f"no recommendation for article: {article_id}")

    return article, recomm


def crossref():
    _, recomm = parse_args(request)

    response.headers.update({
        "Content-Type": "text/xml",
    })

    return _crossref.RecommendationXML.build(recomm).content


def docmaps():
    article, recomm = parse_args(request)

    response.headers.update({
        "Content-Type": "application/ld+json",
    })

    pci_description = cast(str, db.cfg.description) # type: ignore

    return json.dumps([{
    "type": "docmap",
    "id": URL("metadata", f"recommendation?article_id={article.id}", scheme=True),
    "publisher": {
      "name": pci_description,
      "url": URL("about", "|", scheme=True).replace("|", ""),
    },
    "created": publication_date(recomm.validation_timestamp),
    "updated": publication_date(recomm.validation_timestamp),
    "first-step": "_:b0",
    "steps": steps(article),
    "@context": "https://w3id.org/docmaps/context.jsonld"
  }])


def article_as_docmaps(version: Recommendation | Any, typ: str = "preprint") -> dict[str, str]:
    return {
        "published": publication_date(version.recommendation_timestamp),
        "doi": version.doi or "MISSING",
        "type": typ,
    }


def publication_date(timestamp: datetime.datetime | None):
    if timestamp is None:
        return 'MISSING!'
    
    return datetime.datetime.strftime(
            timestamp,
            "%Y-%m-%dT%H:%M:%S%Z",
    )


def recommendation_as_docmaps(version: Recommendation, typ: str) -> dict[str, str]:
    timestamp = version.validation_timestamp if typ != "reply" \
            else version.recommendation_timestamp
    return {
        "published": publication_date(timestamp),
        "doi": version.recommendation_doi or 'MISSING',
        "type": typ,
    }


def authors_as_docmaps(article: Article) -> list[dict[str, Any]]:
    if article.authors is None:
        return []
        
    return [
        {
            "actor": {
              "type": "person",
              "name": author,
            },
            "role": "author"
        }

        for author in article.authors.split(", ")
    ]


def reviews(version: Recommendation):
    reviews = Review.get_by_recommendation_id(version.id, review_states=[ReviewState.REVIEW_COMPLETED])
    return [
        Storage(
            reviewer=mkUser(review.reviewer_id).flatten() # type: ignore
                        if not review.anonymously else "Anonymous reviewer",
            proxy=Storage(
                validation_timestamp=review.last_change,
                recommendation_doi=version.recommendation_doi,
            )
        )
        for review in reviews
    ]


def get_crossref_publication_date(article: Article):
    try:
        if article.doi_of_published_article is None:
            raise
        
        doi = url_to_doi_id(article.doi_of_published_article)
        xref = HttpClient().get(f"https://api.crossref.org/works/{doi}").json() # type: ignore
        published = xref["message"]["published"]["date-parts"][0]
        return datetime.datetime(*published)
    except:
        return article.last_status_change


def steps(article: Article):
    authors = authors_as_docmaps(article)
    rounds = Recommendation.get_by_article_id(article.id, db.t_recommendations.validation_timestamp)

    init_r = rounds[0]
    last_r = rounds[-1]

    recommender_name = cast(str, mkUser(last_r.recommender_id).flatten()) # type: ignore

    init_r.recommendation_timestamp = article.validation_timestamp

    b0: dict[str, Any] = {
            "_:b0": {
        "inputs": [],
        "actions": [
          {
            "participants": authors,
            "outputs": [
                article_as_docmaps(init_r)
            ],
            "inputs": []
          }
        ],
        "assertions": [
          {
            "status": "catalogued",
            "item": init_r.doi,
          }
        ],
        "next-step": "_:b1"
      },
    }

    reviewed: dict[str, Any] = {
            f"_:b{round_nb*2 + 1}": {

        "actions": [
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": recommender_name,
                },
                "role": "author"
              }
            ],
            "outputs": [
                recommendation_as_docmaps(rnd, "editorial-decision")
            ],
            "inputs": [
                article_as_docmaps(rnd)
            ]
          },
          ] + [
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": review.reviewer, # type: ignore
                },
                "role": "author"
              }
            ],
            "outputs": [
                recommendation_as_docmaps(review.proxy, "review") # type: ignore
            ],
            "inputs": [
                article_as_docmaps(rnd)
            ]
          }

          for review in reviews(rnd)
        ],
        "assertions": [
          {
            "status": "reviewed",
            "item": rnd.doi,
          }
        ],
        "inputs": [],
        "previous-step": f"_:b{round_nb*2}",
        "next-step": f"_:b{round_nb*2 + 2}"
      }

      for round_nb, rnd in enumerate(rounds)
    }

    catalogued: dict[str, Any] = {
            f"_:b{round_nb*2 + 2}": {

        "inputs": [
            article_as_docmaps(rnd)
            ],
        "actions": [
          {
            "participants": authors,
            "outputs": [
                article_as_docmaps(rounds[round_nb + 1])
            ],
            "inputs": []
          },
          {
            "participants": authors,
            "outputs": [
                recommendation_as_docmaps(rounds[round_nb + 1], "reply")
            ],
            "inputs": []
          }
        ],
        "assertions": [
          {
            "status": "catalogued",
            "item": rnd.doi,
          }
        ],
        "previous-step": f"_:b{round_nb*2 + 1}",
        "next-step": f"_:b{round_nb*2 + 3}"
        }

        for round_nb, rnd in enumerate(rounds[:-1])
    }

    class published_proxy:
        recommendation_timestamp = get_crossref_publication_date(article)
        doi = article.doi_of_published_article

    final: dict[str, Any] = {
            f"_:b{len(rounds)*2}": {

        "inputs": [
                article_as_docmaps(last_r)
            ],
        "actions": [
          {
            "participants": authors,
            "outputs": [
                article_as_docmaps(published_proxy, "journal-article")
            ],
            "inputs": []
          }
        ],
        "assertions": [
          {
            "status": "published",
            "item": published_proxy.doi
          }
        ],
        "previous-step": f"_:b{len(rounds)*2 -1}"
      },

    } if "10.24072/pcjournal" in str(article.doi_of_published_article) else {}

    override_outputs_dates(
            last_r.validation_timestamp,
            [reviewed, catalogued])

    ret: dict[str, Any] = {}
    ret.update(b0)
    ret.update(reviewed)
    ret.update(catalogued)
    ret.update(final)

    return ret


def override_outputs_dates(timestamp: datetime.datetime | None, items: list[dict[str, Any]]):
    for it in items:
      for item in it.values():
        for action in item["actions"]:
          for output in action["outputs"]:
              if output["type"] == "preprint":
                  continue
              output["published"] = publication_date(timestamp)
