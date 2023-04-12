import io
import rdflib

pci_notif = b"""
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://purl.org/coar/notify"
  ],
  "id": "urn: uuid:ab19e043-81b1-4ba8-9f63-607c56c3407c",
  "origin": {
    "id": "http://localhost:8000/pci/coar_notify/",
    "inbox": "http://localhost:8000/pci/coar_notify/inbox/",
    "type": [ "Service" ]
  },
  "target": {
    "inbox": "http://localhost:8000/pci/coar_notify/inbox",
    "type": [ "Service" ]
  },
  "type": [
    "Announce",
    "coar-notify:ReviewAction"
  ],
  "context": {
    "id": "http://localhost:8000/pci/articles/rec?articleId=1#article-1",
    "ietf:cite-as": "https://doi.org/10.1038/nature.2014.14583",
    "type": "sorg:AboutPage"
  },
  "object": {
    "id": "http://localhost:8000/pci/articles/rec?articleId=1#review-1",
    "type": [ "Document", "sorg:Review" ]
  },
  "actor": {
    "id": "http://localhost:8000/pci/public/user_public_page?userId=6",
    "type": [ "Person" ],
    "name": "reviewer dude"
  }
}
"""

def test_pci_notif_parse():

    graph = rdflib.Graph()
    graph.parse(
            io.BytesIO(pci_notif),
            format="json-ld",
            base="http://127.0.0.1:8000/pci/coar_notify/inbox"
    )
