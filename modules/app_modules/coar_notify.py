import uuid

import json

import functools
import requests

from gluon.contrib.appconfig import AppConfig

__all__ = ["COARNotifier"]

myconf = AppConfig(reload=True)


@functools.lru_cache()
def _get_requests_session() -> requests.Session:
    """Get a requests Session to be used for sending notifications.

    The result is cached on first call using `functools.lru_cache()`

    For now, this method only provides for a custom User-Agent string so that remote
    services can identify the sender in logs."""
    session = requests.Session()
    session.headers["User-Agent"] = f"pci ({myconf['coar_notify']['base_url'].strip()})"
    return session


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
            return bool(self.inbox_url)
        except KeyError:
            return False

    def send_notification(self, notification):
        """Send a notification to the pre-configured external inbox.

        This method handles adding the generic bits of the notification (i.e. the
        @context, id, origin and target.
        """
        session = _get_requests_session()

        # Add the base properties for the notification, including the JSON-LD context.
        notification = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "http://purl.org/coar/notify",
            ],
            "id": f"urn:uuid:{str(uuid.uuid4())}",
            "origin": {
                "id": self.base_url,
                "inbox": self.base_url + "coar_notify/inbox/",
                "type": ["Service"],
            },
            "target": {
                "inbox": self.inbox_url,
                "type": ["Service"],
            },
            **notification,
        }

        response = session.post(
            inbox_url,
            data=json.dumps(notification, indent=2),
            headers={"Content-Type": "application/ld+json"},
        )

        print(response)

    def _review_as_jsonld(self, review):
        recommendation = self.db.t_recommendations[review.recommendation_id]
        article = self.db.t_articles[recommendation.article_id]
        return {
            "id": f"{self.base_url}articles/rec?articleId={article.id}#review-{review.id}",
            "type": ["Document", "sorg:Review"],
            "coar-notify:reviews": self._article_as_jsonld(article),
        }

    def _recommendation_as_jsonld(self, recommendation):
        article = self.db.t_articles[recommendation.article_id]
        return {
            "id": f"{self.base_url}articles/rec?articleId={article.id}",
            "coar-notify:endorses": self._article_as_jsonld(article),
            "type": ["Page", "sorg:WebPage"],
        }

    def _article_as_jsonld(self, article):
        return {
            "id": f"{self.base_url}articles/rec?articleId={article.id}#article-{article.id}",
            "ietf:cite-as": article.doi,
        }

    def _user_as_jsonld(self, user):
        return {
            "id": f"{self.base_url}public/user_public_page?userId={user.id}",
            "type": ["Person"],
            "name": f"{user.first_name} {user.last_name}",
        }

    def review_completed(self, review):
        """Notify that a review has been completed for an article.

        This implements Step 3 of Scenario 1 from COAR Notify. See
        https://notify.coar-repositories.org/scenarios/1/ for more information.
        """
        reviewer = self.db.auth_user[review.reviewer_id]
        notification = {
            "type": ["Announce", "coar-notify:ReviewSuccess"],
            "actor": {} if review.anonymously else self._user_as_jsonld(reviewer),
            "object": self._review_as_jsonld(review),
        }
        self.send_notification(notification)

    def article_endorsed(self, recommendation):
        """Notify that an article has received an endorsement via a recommendation.

        This implements Step 5 of Scenario 3 from COAR Notify. See
        https://notify.coar-repositories.org/scenarios/1/ for more information.
        """
        recommender = self.db.auth_user[recommendation.recommender_id]
        notification = {
            "type": ["Announce", "coar-notify:EndorsementSuccess"],
            "actor": self._user_as_jsonld(recommender),
            "object": self._recommendation_as_jsonld(recommendation),
        }
        self.send_notification(notification)
