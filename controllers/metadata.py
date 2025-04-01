import json
import datetime

from app_modules.common_small_html import mkUser
from models.review import ReviewState


def recommendation():
    recommId = request.vars.id
    recomm = db.t_recommendations[recommId]

    if not recomm:
        raise HTTP(400, f"no such recommendation: {recommId}")

    response.headers.update({
        "Content-Type": "application/json",
    })

    pci_description = db.cfg.description

    article = db.t_articles[recomm.article_id]

    article_publication_date = article.article_year
    article_doi = article.doi

    def article_as_docmaps(version, typ="preprint"):
        return {
            "published": publication_date(version),
            "doi": article_doi,
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
            "doi": recomm.recommendation_doi,
            "type": typ,
        }

    authors = [
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


    return json.dumps([
  {
    "type": "docmap",
    "id": URL("metadata", f"recommendation-{recomm.recommendation_doi}", scheme=True),
    "publisher": {
      "name": pci_description,
      "url": "https://github.com/docmaps-project/docmaps/tree/main/packages/ts-etl"
    },
    "created": publication_date(recomm),
    "updated": publication_date(recomm),
    "first-step": "_:b0",
    "steps": {
            "_:b0": {
        "inputs": [],
        "actions": [
          {
            "participants": authors,
            "outputs": [
                article_as_docmaps(v1)
            ],
            "inputs": []
          }
        ],
        "assertions": [
          {
            "status": "catalogued",
            "item": article_doi,
          }
        ],
        "next-step": "_:b1"
      },
            "_:b1": {
        "actions": [
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": "Strub, Caroline"
                },
                "role": "author"
              }
            ],
            "outputs": [
                recommendation_as_docmaps(v0, "editorial-decision")
            ],
            "inputs": [
                article_as_docmaps(v0)
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
                recommendation_as_docmaps(v0, "review")
            ],
            "inputs": [
                article_as_docmaps(v0)
            ]
          }

          for reviewer in reviewers(v0)
        ],
        "assertions": [
          {
            "status": "reviewed",
            "item": article_doi,
          }
        ],
        "inputs": [],
        "previous-step": "_:b0",
        "next-step": "_:b2"
      },
            "_:b2": {
        "inputs": [
            article_as_docmaps(v1)
            ],
        "actions": [
          {
            "participants": authors,
            "outputs": [
                article_as_docmaps(v2)
            ],
            "inputs": []
          },
          {
            "participants": authors,
            "outputs": [
                recommendation_as_docmaps(v0, "reply")
            ],
            "inputs": []
          }
        ],
        "assertions": [
          {
            "status": "catalogued",
            "item": article_doi,
          }
        ],
        "previous-step": "_:b1",
        "next-step": "_:b3"
      },
            "_:b3": {
        "actions": [
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": "Strub, Caroline"
                },
                "role": "author"
              }
            ],
            "outputs": [
                recommendation_as_docmaps(v2, "editorial-decision")
            ],
            "inputs": [
                article_as_docmaps(v2)
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
                recommendation_as_docmaps(v1, "review")
            ],
            "inputs": [
                article_as_docmaps(v1)
            ]
          }

          for reviewer in reviewers(v1)
        ],
        "assertions": [
          {
            "status": "reviewed",
            "item": article_doi,
          }
        ],
        "inputs": [],
        "previous-step": "_:b2",
        "next-step": "_:b4"
      },
            "_:b4": {
        "inputs": [
            article_as_docmaps(v2)
            ],
        "actions": [
          {
            "participants": authors,
            "outputs": [
                recommendation_as_docmaps(v3, "reply")
            ],
            "inputs": []
          },
          {
            "participants": authors,
            "outputs": [
                article_as_docmaps(v3)
            ],
            "inputs": [
                article_as_docmaps(v2)
            ]
          },
        ],
        "assertions": [
          {
            "status": "reviewed",
            "item": article_doi,
          }
        ],
        "previous-step": "_:b3",
        "next-step": "_:b5"
      },
            "_:b5": {
        "actions": [
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": "Strub, Caroline"
                },
                "role": "author"
              }
            ],
            "outputs": [
                recommendation_as_docmaps(v3, "editorial-decision")
            ],
            "inputs": [
                article_as_docmaps(v3, "journal-article")
            ]
          }
        ],
        "assertions": [
          {
            "status": "reviewed",
            "item": article_doi,
          }
        ],
        "inputs": [],
        "previous-step": "_:b4",
        "next-step": "_b6"
      },
            "_:b6": {
        "inputs": [
                article_as_docmaps(v3)
            ],
        "actions": [
          {
            "participants": authors,
            "outputs": [
                article_as_docmaps(v3, "journal-article")
            ],
            "inputs": []
          }
        ],
        "assertions": [
          {
            "status": "published",
            "item": "10.24072/pcjournal.321"
          }
        ],
        "previous-step": "_:b5"
      },
         },
    "@context": "https://w3id.org/docmaps/context.jsonld"
  }
]
)
