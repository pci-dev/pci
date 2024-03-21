import json
import requests
import pytest

import uuid
uid = lambda: str(uuid.uuid4())

_uid = uid()

def test_request_endorsement():
    data = json.loads(request_endorsement)
    data["id"] = _uid
    post(data)

def test_cancel_endorsement_request():
    data = json.loads(cancel_endorsement_request)
    data["id"] = uid()
    data["object"]["id"] = _uid
    post(data)

def test_resubmit_endorsement():
    data = json.loads(request_endorsement)
    data["id"] = uid()

    prev_url = data["object"]["ietf:cite-as"]
    data["context"] = { "id": prev_url }

    data["object"]["ietf:cite-as"] = "https://hal.inrae.fr/hal-02630042v2"

    with pytest.raises(Exception) as e:
        post(data)
        assert "not awaiting revision" in str(e.value)


def post(data):
    target = "http://localhost:8000/pci/coar_notify/inbox"
    res = requests.post(
            target,
            json=data,
            headers={"Content-Type": "application/ld+json"},
    )
    res.raise_for_status()


request_endorsement = """
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://purl.org/coar/notify"
  ],
  "actor": {
    "id": "mailto:denis.bourguet@inrae.fr",
    "name": "Denis Bourguet",
    "type": "Person"
  },
  "id": "urn:uuid:0370c0fb-bb78-4a9b-87f5-bed307a509dd",
  "object": {
    "id": "https://hal.inrae.fr/hal-02630042",
    "ietf:cite-as": "https://hal.inrae.fr/hal-02630042v1",
    "type": "sorg:AboutPage",
    "url": {
      "id": "https://hal.inrae.fr/hal-02630042v1/file/Bourguet%20Lieux%20Communs%202016.pdf",
      "mediaType": "application/pdf",
      "type": [
        "Article",
        "sorg:ScholarlyArticle"
      ]
    }
  },
  "origin": {
    "id": "https://research-organisation.org/repository",
    "inbox": "http://localhost:8000/coar_notify/inbox/",
    "type": "Service"
  },
  "target": {
    "id": "https://overlay-journal.com/system",
    "inbox": "http://localhost:8000/coar_notify/inbox/",
    "type": "Service"
  },
  "type": [
    "Offer",
    "coar-notify:EndorsementAction"
  ]
}
"""

cancel_endorsement_request = """
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://purl.org/coar/notify"
  ],
  "actor": {
    "id": "https://some-organisation.org",
    "name": "Some Organisation",
    "type": "Organization"
  },
  "id": "urn:uuid:46956915-e3fe-4528-8789-1d325a356e4f",
  "object": {
    "id": "urn:uuid:0370c0fb-bb78-4a9b-87f5-bed307a509dd",
    "object": "https://some-organisation.org/resource/0021",
    "type": "Offer"
  },
  "origin": {
    "id": "https://some-organisation.org",
    "inbox": "https://some-organisation.org/inbox/",
    "name": "Some Organisation",
    "type": "Organization"
  },
  "target": {
    "id": "https://generic-service.com/system",
    "inbox": "https://generic-service.com/system/inbox/",
    "type": "Service"
  },
  "type": "Undo"
}
"""

acknowledge_and_reject = """
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://purl.org/coar/notify"
  ],
  "actor": {
    "id": "https://generic-service.com",
    "name": "Generic Service",
    "type": "Service"
  },
  "context": {
    "id": "https://some-organisation.org/resource/0021",
    "ietf:cite-as": "https://doi.org/10.4598/12123487",
    "type": "Document"
  },
  "id": "urn:uuid:668f26e0-2c8d-4117-a0d2-ee713523bcb1",
  "inReplyTo": "urn:uuid:0370c0fb-bb78-4a9b-87f5-bed307a509dd",
  "object": {
    "id": "urn:uuid:0370c0fb-bb78-4a9b-87f5-bed307a509dd",
    "object": "https://some-organisation.org/resource/0021",
    "type": "Offer"
  },
  "origin": {
    "id": "https://generic-service.com/system",
    "inbox": "https://generic-service.com/system/inbox/",
    "type": "Service"
  },
  "target": {
    "id": "https://some-organisation.org",
    "name": "Some Organisation",
    "type": "Organization"
  },
  "type": "TentativeReject"
}
"""

acknowledge_and_tentative_accept = """
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://purl.org/coar/notify"
  ],
  "actor": {
    "id": "https://generic-service.com",
    "name": "Generic Service",
    "type": "Service"
  },
  "context": {
    "id": "https://some-organisation.org/resource/0021",
    "ietf:cite-as": "https://doi.org/10.4598/12123487",
    "type": "Document"
  },
  "id": "urn:uuid:4fb3af44-d4f8-4226-9475-2d09c2d8d9e0",
  "inReplyTo": "urn:uuid:0370c0fb-bb78-4a9b-87f5-bed307a509dd",
  "object": {
    "id": "urn:uuid:0370c0fb-bb78-4a9b-87f5-bed307a509dd",
    "object": "https://some-organisation.org/resource/0021",
    "type": "Offer"
  },
  "origin": {
    "id": "https://generic-service.com/system",
    "inbox": "https://generic-service.com/system/inbox/",
    "type": "Service"
  },
  "target": {
    "id": "https://some-organisation.org",
    "name": "Some Organisation",
    "type": "Organization"
  },
  "type": "TentativeAccept"
}
"""
