import json
import requests
import uuid


def index():
    request.function = "post_form" # zap header in layout.html
    return post_form()


def post_form():
    form = SQLFORM.factory(
        Field("json_ld", label=T("COAR json+ld"), type="text",
            default=json.dumps(request_endorsement, indent=4)
                        .replace('_UUID_', str(uuid.uuid4()))),
    )
    form.element(_type="submit")["_value"] = T("Send to inbox")
    form.element(_name="json_ld").attributes.update(dict(
        _style="""
            font-family:monospace;
            cursor:default;
            /*min-height: inherit;*/
        """,
        _rows=20,
    ))
    status = ""
    form.insert(0, PRE(status, _name="status"))

    if form.process(keepvalues=True).accepted:
        try:
            data = json.loads(form.vars.json_ld)
            post(data)
        except requests.HTTPError as e:
            status = f"{e.response.text}"
        except Exception as e:
            status = f"{e.__class__.__name__}: {e}"

        form.element(_name="status", replace=PRE(status or "request sent"))

        form.element(_name="json_ld")["_disabled"] = 1
        url = URL("test_coar", "?")
        form.element(_type="submit").attributes.update(dict(
            _value="Back",
            _onclick= f'window.location.replace("{url}"); return false;'))


    response.flash = None
    response.view = "default/myLayout.html"
    return dict(
        form=form,
        titleIcon="envelope",
        pageTitle="COAR post form",
    )


def post(data):
    target = URL("coar_notify", "inbox", scheme=True, host=True)
    res = requests.post(
            target,
            json=data,
            headers={"Content-Type": "application/ld+json"},
            auth=basic_auth,
    )
    res.raise_for_status()


from gluon.contrib.appconfig import AppConfig
conf = AppConfig()
basic_auth = conf.get("config.basic_auth", None)
if basic_auth: basic_auth = tuple(basic_auth.split(":"))


from app_modules.coar_notify import COARNotifier

request_endorsement = \
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
  "id": "urn:uuid:_UUID_",
  "object": {
    "id": "https://hal.halpreprod.archives-ouvertes.fr/hal-01153368",
    "ietf:cite-as": "https://hal.halpreprod.archives-ouvertes.fr/hal-01153368v2",
    "type": "sorg:AboutPage",
    "ietf:item": {
      "id": "https://hal.halpreprod.archives-ouvertes.fr/hal-01153368v2/file/ArditiLobrySariDispersal.pdf",
      "mediaType": "application/pdf",
      "type": [
        "Article",
        "sorg:ScholarlyArticle"
      ]
    }
  },
  "origin": {
    "id": "https://research-organisation.org/repository",
    "inbox": COARNotifier.base_url + "coar_notify/inbox",
    "type": "Service"
  },
  "target": {
    "id": "https://overlay-journal.com/system",
    "inbox": COARNotifier.base_url + "coar_notify/inbox",
    "type": "Service"
  },
  "type": [
    "Offer",
    "coar-notify:EndorsementAction"
  ]
}

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
  "type": "Reject"
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
