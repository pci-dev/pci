import json
import datetime


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
              {
                "published": "2023-06-19T00:00:00.000Z",
                "doi": "10.24072/pci.microbiol.100007",
                "type": "editorial-decision"
              }
            ],
            "inputs": [
                article_as_docmaps(v0)
            ]
          },
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": "Anonymous"
                },
                "role": "author"
              }
            ],
            "outputs": [
              {
                "published": "2023-04-04T00:00:00.000Z",
                "doi": "10.24072/pci.microbiol.100007",
                "type": "review"
              }
            ],
            "inputs": [
              {
                "published": "2023-01-13T00:00:00.000Z",
                "doi": "10.1101/2023.01.13.523754",
                "type": "preprint"
              }
            ]
          },
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": "Johannes Schweichhart"
                },
                "role": "author"
              }
            ],
            "outputs": [
              {
                "published": "2023-06-18T00:00:00.000Z",
                "doi": "10.24072/pci.microbiol.100007",
                "type": "review"
              }
            ],
            "inputs": [
                article_as_docmaps(v0)
            ]
          },
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
              {
                "published": "2023-07-04T00:00:00.000Z",
                "doi": "10.24072/pci.microbiol.100007",
                "type": "reply"
              }
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
              {
                "published": "2023-08-02T00:00:00.000Z",
                "doi": "10.24072/pci.microbiol.100007",
                "type": "editorial-decision"
              }
            ],
            "inputs": [
                article_as_docmaps(v2)
            ]
          },
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": "Anonymous"
                },
                "role": "author"
              }
            ],
            "outputs": [
              {
                "published": "2023-08-02T00:00:00.000Z",
                "doi": "10.24072/pci.microbiol.100007",
                "type": "review"
              }
            ],
            "inputs": [
                article_as_docmaps(v2)
            ]
          },
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": "Johannes Schweichhart"
                },
                "role": "author"
              }
            ],
            "outputs": [
              {
                "published": "2023-08-01T00:00:00.000Z",
                "doi": "10.24072/pci.microbiol.100007",
                "type": "review"
              }
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
              {
                "published": "2023-08-08T00:00:00.000Z",
                "doi": "10.24072/pci.microbiol.100007",
                "type": "reply"
              }
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
              {
                "published": "2023-08-29T00:00:00.000Z",
                "doi": "10.24072/pci.microbiol.100007",
                "type": "editorial-decision"
              }
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
