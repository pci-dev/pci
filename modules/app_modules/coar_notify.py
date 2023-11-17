import logging

import datetime
import functools
import io
import json
import re
import typing
import uuid

import requests

from gluon import current
from gluon.contrib.appconfig import AppConfig
from app_modules.common_small_html import mkLinkDOI

__all__ = ["COARNotifier"]

logger = logging.getLogger(__name__)

myconf = AppConfig(reload=True)

try:
 import rdflib
 ACTIVITYSTREAMS = rdflib.Namespace("https://www.w3.org/ns/activitystreams#")
 LDP = rdflib.Namespace("http://www.w3.org/ns/ldp#")
except:
 rdflib = None


@functools.lru_cache()
def _get_requests_session() -> requests.Session:
    """Get a requests Session to be used for sending notifications.

    The result is cached on first call using `functools.lru_cache()`

    For now, this method only provides for a custom User-Agent string so that remote
    services can identify the sender in logs."""
    session = requests.Session()
    session.headers["User-Agent"] = f"pci ({myconf['coar_notify']['base_url'].strip()})"
    return session


class COARNotifyException(Exception):
    """Base exception from which all other COAR Notify exceptions derive."""
    message = "COAR Notify exception"


class COARNotifyParseException(COARNotifyException):
    message = "Couldn't parse message body."


class COARNotifyNoUniqueSubjectException(COARNotifyException):
    message = (
        "Exactly one resource in notification body must be an Activity Streams "
        "Announce instance."
    )


class COARNotifyMissingOrigin(COARNotifyException):
    message = "The Announcement is missing an activitystreams:origin property"


class COARNotifyMissingTarget(COARNotifyException):
    message = "The Announcement is missing an activitystreams:target property"


class COARNotifyMissingOriginInbox(COARNotifyException):
    message = "The origin is missing an ldp:inbox URI property"


class COARNotifyMissingTargetInbox(COARNotifyException):
    message = "The target is missing an ldp:inbox URI property"


class COARNotifier:
    """Handles sending and recording COAR Notify notifications.

    COAR Notify allows services to communicate review- and endorsement-related
    information between themselves.

    This is a demonstrator, which sends all outbound notifications to a pre-configured
    Linked Data Notifications (LDN) inbox. The inbox implementation in
    :module:`controllers.coar_notify` is unauthenticated.

    See https://notify.coar-repositories.org/ for details of the COAR Notify community
    conventions.
    """
    def __init__(self, db):
        self.db = db

    @functools.cached_property
    def base_url(self):
        return myconf["coar_notify"]["base_url"].strip()

    @functools.cached_property
    def inbox_url(self):
        return myconf["coar_notify"]["inbox_url"].strip()

    @property
    def enabled(self):
        try:
            return bool(self.inbox_url) and rdflib
        except KeyError:
            return False

    def send_notification(self, notification, article):
        """Send a notification to the target inbox (article.doi HTTP header).

        This method handles adding the generic bits of the notification (i.e. the
        @context, id, origin and target.
        """
        target_inbox = get_target_inbox(article)

        notification = self.add_base_notification_properties(notification, target_inbox)
        self._send_notification(notification, target_inbox)

    def add_base_notification_properties(self, notification, target_inbox):
        return {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://purl.org/coar/notify",
            ],
            "id": f"urn:uuid:{str(uuid.uuid4())}",
            "origin": {
                "id": self.base_url + "coar_notify/",
                "inbox": self.base_url + "coar_notify/inbox/",
                "type": ["Service"],
            },
            "target": {
                "id": re.sub("(http[s]?://[^/]+/).*", "\\1", target_inbox),
                "inbox": target_inbox,
                "type": ["Service"],
            },
            **notification,
        }

    def _send_notification(self, notification, target_inbox):
        serialized_notification = json.dumps(notification, indent=2)
        session = _get_requests_session()

        try:
            response = session.post(
                target_inbox,
                data=serialized_notification,
                headers={"Content-Type": "application/ld+json"},
            )
        except requests.exceptions.MissingSchema:
            http_status = 418 # no target_inbox found in Link header
        except requests.exceptions.RequestException as e:
            # Repurpose Cloudflare's unofficial status codes
            # https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#Cloudflare
            if isinstance(e, requests.exceptions.ConnectionError):
                http_status = 521  # Web Server Is Down
            elif isinstance(e, requests.exceptions.ConnectTimeout):
                http_status = 522  # Connection Timed Out
            elif isinstance(e, requests.exceptions.ReadTimeout):
                http_status = 524  # A Timeout Occurred
            elif isinstance(e, requests.exceptions.SSLError):
                http_status = 525  # SSL Handshake Failed
            else:
                http_status = 520  # Web Server Returned an Unknown Error
            logger.exception("Request exception when POSTing COAR Notification")
        else:
            http_status = response.status_code

        self.record_notification(
            body=io.BytesIO(serialized_notification.encode()),
            direction="Outbound",
            http_status=http_status,
        )

    def _review_as_jsonld(self, review):
        recommendation = self.db.t_recommendations[review.recommendation_id]
        article = self.db.t_articles[recommendation.article_id]
        return {
            "id": f"{self.base_url}articles/rec?articleId={article.id}#review-{review.id}",
            "type": ["Document", "sorg:Review"],
        }

    def _recommendation_as_jsonld(self, recommendation):
        article = self.db.t_articles[recommendation.article_id]
        return {
            "id": f"{self.base_url}articles/rec?articleId={article.id}",
            "type": ["Page", "sorg:WebPage"],
            "ietf:cite-as": mkLinkDOI(recommendation.recommendation_doi),
        }

    def _article_as_jsonld(self, article):
        return {
            "id": article_cite_as(article),
            "ietf:cite-as": article_cite_as(article),
            "type": "sorg:AboutPage",
        }

    def _article_as_jsonld_using_pci_ref_to_article(self, article):
        return {
            "id": f"{self.base_url}articles/rec?articleId={article.id}#article-{article.id}",
            "ietf:cite-as": article_cite_as(article),
            "type": "sorg:AboutPage",
        }

    def _user_as_jsonld(self, user, user_email=None):
        return {
            "id": f"{self.base_url}public/user_public_page?userId={user.id}" \
                    if user else user_email,
            "type": ["Person"],
            "name": f"{user.first_name} {user.last_name}" \
                    if user else user_email,
        }

    def review_completed(self, review):
        """Notify that a review has been completed for an article.

        This implements Step 3 of Scenario 1 from COAR Notify. See
        https://notify.coar-repositories.org/scenarios/1/ for more information.
        """
        if not self.enabled:
            return

        recommendation = self.db.t_recommendations[review.recommendation_id]
        reviewer = self.db.auth_user[review.reviewer_id]
        article = self.db.t_articles[recommendation.article_id]
        notification = {
            "type": ["Announce", "coar-notify:ReviewAction"],
            "context": self._article_as_jsonld(article),
            "object": self._review_as_jsonld(review),
            "actor": {} if review.anonymously else \
                    self._user_as_jsonld(reviewer, review.reviewer_details),
        }
        self.send_notification(notification, article)

    def article_endorsed(self, recommendation):
        """Notify that an article has received an endorsement via a recommendation.

        This implements Step 5 of Scenario 3 from COAR Notify. See
        https://notify.coar-repositories.org/scenarios/1/ for more information.
        """
        if not self.enabled:
            return

        article = self.db.t_articles[recommendation.article_id]
        recommender = self.db.auth_user[recommendation.recommender_id]
        notification = {
            "type": ["Announce", "coar-notify:EndorsementAction"],
            "context": self._article_as_jsonld(article),
            "object": self._recommendation_as_jsonld(recommendation),
            "actor": self._user_as_jsonld(recommender, recommendation.recommender_details),
        }
        self.send_notification(notification, article)

    def send_acknowledge_and_tentative_accept(self, article):
        if not article.coar_notification_id: return
        if article.coar_notification_closed: return

        send_ack(self, "Accept", article)

    def send_acknowledge_and_reject(self, article):
        if not article.coar_notification_id: return
        if article.coar_notification_closed: return

        send_ack(self, "Reject", article)

        article.coar_notification_closed = True
        article.update_record()


    def record_notification(
        self,
        *,
        body: io.BytesIO,
        body_format: str = "json-ld",
        http_status: int = None,
        direction: typing.Literal["Inbound", "Outbound"],
        base: str = None,
    ) -> None:
        """Records a notification in the database for logging purposes.

        This method does some validation:

        * ensures that the notification can be parsed into RDF
        * ensures that it contains a single activitystreams:Announce
        * ensures that there is an origin and a target, and that both have an ldp:inbox

        body can either be a JSON-LD-style dictionary, or a BytesIO.
        base, if specified, provides the base URL for resolving absolute URLs
        """
        if isinstance(body, dict):
            bb = json.dumps(body)
            b = bytes(bb, "utf8")
        else:
            bb = body.read()
            body.seek(0)
            b = body

        graph = rdflib.Graph()

        try:
            graph.parse(b, format=body_format, base=base or "https://invalid/")
        except Exception as e:
            raise COARNotifyParseException from e

        body = (
            body if body_format == "json-ld" and isinstance(body, dict)
            else json.loads(bb) if body_format == "json-ld"
            else json.loads(graph.serialize(
                    format="json-ld", auto_compact=True))["@graph"]
        )

        if direction == "Outbound":
            validate_outbound_notification(graph)

        inbox_url = body \
                ["target" if direction == "Outbound" else "origin"] \
                ["inbox"]

        self.db.t_coar_notification.insert(
            created=datetime.datetime.now(tz=datetime.timezone.utc),
            rdf_type=get_notification_type(graph),
            body=json.dumps(body),
            direction=direction,
            inbox_url=inbox_url,
            http_status=http_status,
            coar_id=body["id"],
        )

#

def send_ack(self, typ: typing.Literal["Accept", "Reject"], article):
    origin_req = get_origin_request(article)
    target_inbox = origin_req["origin"]["inbox"]
    origin_object = origin_req["object"]["id"]
    notification = {
          "type": f"Tentative{typ}",
          "object": {
            "id": article.coar_notification_id,
            "object": origin_object,
            "type": "Offer"
          },
          "inReplyTo": article.coar_notification_id,
          "actor": {
            "id": self.base_url,
            "type": "Service",
            #"name": "PCI coar Service",
          },
          #"context": {
          #  "id": "https://some-organisation.org/resource/0021",
          #  "ietf:cite-as": "https://doi.org/10.4598/12123487",
          #  "type": "Document"
          #},
        }

    notification = self.add_base_notification_properties(notification, target_inbox)
    self._send_notification(notification, target_inbox)


def get_origin_request(article):
    db = current.db
    return json.loads(
        db(db.t_coar_notification.coar_id == article.coar_notification_id)
        .select().first()
        .body
    )


def validate_outbound_notification(graph):
    subjects = list(graph.subjects(rdflib.RDF.type, ACTIVITYSTREAMS.Announce))
    subjects += list(graph.subjects(rdflib.RDF.type, ACTIVITYSTREAMS.TentativeAccept))
    subjects += list(graph.subjects(rdflib.RDF.type, ACTIVITYSTREAMS.TentativeReject))
    if len(subjects) != 1:
        raise COARNotifyNoUniqueSubjectException
    subject = subjects[0]

    origin = graph.value(subject, ACTIVITYSTREAMS.origin)
    target = graph.value(subject, ACTIVITYSTREAMS.target)

    if not origin:
        raise COARNotifyMissingOrigin
    if not target:
        raise COARNotifyMissingTarget

    origin_inbox = graph.value(origin, LDP.inbox)
    target_inbox = graph.value(target, LDP.inbox)

    if not isinstance(origin_inbox, rdflib.URIRef):
        raise COARNotifyMissingOriginInbox
    if not isinstance(target_inbox, rdflib.URIRef):
        raise COARNotifyMissingTargetInbox


def get_notification_type(graph):
    return " ".join(typ.fragment
            for typ in graph.objects(predicate=rdflib.RDF.type)
            if typ not in (ACTIVITYSTREAMS.Service)
    )


def get_target_inbox(article):
    for _ in range(5):
        inbox = _get_target_inbox(article)

        if inbox: break

    return inbox


def _get_target_inbox(article):
    """Grab the inbox url from the Link entry (if any) provided by the repo
    We expect a HEAD request to adhere to https://www.w3.org/TR/ldn/#discovery
    """

    try:
        resp = requests.head(article.doi, timeout=5, allow_redirects=True)
        inbox = resp.links['http://www.w3.org/ns/ldp#inbox']['url']
        return inbox
    except:
        return ""


def article_cite_as(article):
    inbox = get_target_inbox(article)
    if ".hal." in inbox:
        article_doi = re.sub('v[0-9]+/?$', '', article.doi)
        return article_doi + f"v{article.ms_version}"
    else:
        return article.doi
