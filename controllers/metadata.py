import json
import datetime
import requests

from app_modules.common_small_html import mkUser
from models.review import ReviewState

from gluon.storage import Storage


def parse_args(request):
    article_id = request.vars.article_id or request.vars.id

    try:
        article = db.t_articles[article_id]
        assert article
    except:
        raise HTTP(400, f"no such article: {article_id}")

    recomm = db(
        (db.t_recommendations.article_id == article.id)
        & (db.t_recommendations.recommendation_state == "Recommended")
    ).select().first()

    if not recomm:
        raise HTTP(400, f"no recommendation for article: {article_id}")

    return article, recomm


def recommendation():
    article, recomm = parse_args(request)

    response.headers.update({
        "Content-Type": "application/ld+json",
    })

    pci_description = db.cfg.description

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


def article_as_docmaps(version, typ="preprint"):
    return {
        "published": publication_date(version.recommendation_timestamp),
        "doi": version.doi,
        "type": typ,
    }


def publication_date(timestamp):
    return datetime.datetime.strftime(
            timestamp,
            "%Y-%m-%dT%H:%M:%S%Z",
    )


def recommendation_as_docmaps(version, typ):
    timestamp = version.validation_timestamp if typ != "reply" \
            else version.recommendation_timestamp
    return {
        "published": publication_date(timestamp),
        "doi": version.recommendation_doi,
        "type": typ,
    }


def authors_as_docmaps(article):
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


def reviews(version):
    reviews = db(
            (db.t_reviews.recommendation_id == version.id)
        &   (db.t_reviews.review_state == ReviewState.REVIEW_COMPLETED.value)
    ).select()
    return [
        Storage(
            reviewer=mkUser(review.reviewer_id).flatten()
                        if not review.anonymously else "Anonymous reviewer",
            proxy=Storage(
                validation_timestamp=review.last_change,
                recommendation_doi=version.recommendation_doi,
            )
        )
        for review in reviews
    ]


def get_crossref_publication_date(article):
    try:
        doi = article.doi_of_published_article.replace("https://doi.org/", "")
        xref = requests.get(f"https://api.crossref.org/works/{doi}").json()
        published = xref["message"]["published"]["date-parts"][0]
        return datetime.datetime(*published)
    except:
        return article.last_status_change


def steps(article):
    authors = authors_as_docmaps(article)

    rounds = db(db.t_recommendations.article_id == article.id) \
                .select(orderby=db.t_recommendations.validation_timestamp)

    init_r = rounds[0]
    last_r = rounds[-1]

    recommender_name = mkUser(last_r.recommender_id).flatten()

    init_r.recommendation_timestamp = article.validation_timestamp

    b0 = {
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

    reviewed = {
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
                  "name": review.reviewer,
                },
                "role": "author"
              }
            ],
            "outputs": [
                recommendation_as_docmaps(review.proxy, "review")
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

    catalogued = {
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

    final = {
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

    ret = {}
    ret.update(b0)
    ret.update(reviewed)
    ret.update(catalogued)
    ret.update(final)

    return ret


def override_outputs_dates(timestamp, items):
    for it in items:
      for item in it.values():
        for action in item["actions"]:
          for output in action["outputs"]:
              if output["type"] == "preprint":
                  continue
              output["published"] = publication_date(timestamp)
