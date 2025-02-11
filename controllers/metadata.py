import json

def recommendation():
    recommId = request.vars.id
    recomm = db.t_recommendations[recommId]

    if not recomm:
        raise HTTP(400, f"no such recommendation: {recommId}")

    response.headers.update({
        "Content-Type": "application/json",
    })

    return json.dumps([
  {
    "type": "docmap",
    "id": URL('articles', 'rec', scheme=True, vars=dict(recommId=recomm.id)),
    "publisher": {
      "name": "Inferred from Crossref",
      "url": "https://github.com/docmaps-project/docmaps/"
    },
    "created": "2025-02-11T23:08:47.393Z",
    "updated": "2025-02-11T23:08:47.393Z",
    "first-step": "_:b0",
    "steps": {
      "_:b0": {
        "inputs": [],
        "actions": [
          {
            "participants": [
              {
                "actor": {
                  "type": "person",
                  "name": "Perrodin, Catherine"
                },
                "role": "author"
              },
              {
                "actor": {
                  "type": "person",
                  "name": "Verzat, Colombine"
                },
                "role": "author"
              },
              {
                "actor": {
                  "type": "person",
                  "name": "Bendor, Daniel"
                },
                "role": "author"
              }
            ],
            "outputs": [
              {
                "published": "2020-01-28T00:00:00.000Z",
                "doi": "10.1101/2020.01.28.922773",
                "type": "preprint"
              }
            ],
            "inputs": []
          }
        ],
        "assertions": [
          {
            "status": "catalogued",
            "item": "10.1101/2020.01.28.922773"
          }
        ]
      }
    },
    "@context": "https://w3id.org/docmaps/context.jsonld"
  }
]
)
