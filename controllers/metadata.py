import json
import datetime

from app_modules.common_small_html import mkUser
from models.review import ReviewState


def recommendation():
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

    response.headers.update({
        "Content-Type": "application/json",
    })

    pci_description = db.cfg.description

    return json.dumps([{
    "type": "docmap",
    "id": URL("metadata", f"recommendation-{recomm.recommendation_doi}", scheme=True),
    "publisher": {
      "name": pci_description,
      "url": "https://github.com/docmaps-project/docmaps/tree/main/packages/ts-etl"
    },
    "created": publication_date(recomm),
    "updated": publication_date(recomm),
    "first-step": "_:b0",
    "steps": steps(article),
    "@context": "https://w3id.org/docmaps/context.jsonld"
  }])


def article_as_docmaps(version, typ="preprint"):
    return {
        "published": publication_date(version),
        "doi": version.doi,
        "type": typ,
    }


def publication_date(version):
    return datetime.datetime.strftime(
            version.validation_timestamp,
            "%Y-%m-%dT%H:%M:%S%Z",
    )


def recommendation_as_docmaps(version, typ):
    return {
        "published": publication_date(version),
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


def reviewers(version):
    reviews = db(
            (db.t_reviews.recommendation_id == version.id)
        &   (db.t_reviews.review_state == ReviewState.REVIEW_COMPLETED.value)
    ).select()
    return [

        mkUser(review.reviewer_id).flatten()
        if not review.anonymously else "Anonymous reviewer"

        for review in reviews
    ]


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
                  "name": reviewer,
                },
                "role": "author"
              }
            ],
            "outputs": [
                recommendation_as_docmaps(rnd, "review")
            ],
            "inputs": [
                article_as_docmaps(rnd)
            ]
          }

          for reviewer in reviewers(rnd)
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
        recommendation_timestamp = last_r.validation_timestamp
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

    ret = {}
    ret.update(b0)
    ret.update(reviewed)
    ret.update(catalogued)
    ret.update(final)

    return ret
