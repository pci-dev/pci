from datetime import datetime, timezone
from typing import Any
from app_modules.httpClient import HttpClient
from app_modules.mastodon import SocialNetwork
from models.post import Post, PostTable


class Bluesky(SocialNetwork):

    POST_MAX_LENGTH = 300
    BASE_URL = "https://bsky.social/xrpc"

    def __init__(self):
        super().__init__(self.POST_MAX_LENGTH, PostTable.BLUESKY_POSTS)

        self._general_handle = self.get_config("general_handle")
        self._general_app_password = self.get_config("general_app_password")

        self._specific_handle = self.get_config("specific_handle")
        self._specific_app_password = self.get_config("specific_app_password")


    def get_config(self, key: str) -> str:
        return self._myconf.get(f'social_bluesky.{key}') or ''


    def has_general_bluesky_config(self) -> bool:
         return len(self._general_handle) > 0 and len(self._general_app_password) > 0


    def has_specific_bluesky_config(self) -> bool:
        return len(self._specific_handle) > 0 and len(self._specific_app_password) > 0


    def send_post(self, article_id: int, recommendation_id: int, posts_text: list[str], specific_account: bool = True, general_account: bool = False):
        if general_account and self.has_general_bluesky_config():
            did = self._resolve_handler(self._general_handle)
            token = self._create_session(did, self._general_app_password)
            self._bluesky_post(article_id, recommendation_id, posts_text, did, token)

        if specific_account and self.has_specific_bluesky_config():
            did = self._resolve_handler(self._specific_handle)
            token = self._create_session(did, self._specific_app_password)
            self._bluesky_post(article_id, recommendation_id, posts_text, did, token)


    def _bluesky_post(self,  article_id: int, recommendation_id: int, posts_text: list[str], did: str, token: str):
        url = f"{self.BASE_URL}/com.atproto.repo.createRecord"
        collection = "app.bsky.feed.post"

        http_client = HttpClient({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

        parent_id: int | None = None
        root_post: Any | None = None
        parent_post: Any | None = None

        for i, post_text in enumerate(posts_text):
            payload: dict[str, Any] = {
                "collection": collection,
                "repo": did,
                "record": {
                    "$type": collection,
                    "text": post_text,
                    "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "langs": ["en-US"]
                }
            }

            if parent_post and root_post:
                payload["record"]["reply"] = {
                    "root": {
                        "uri": root_post["uri"],
                        "cid": root_post["cid"]
                    },
                    "parent": {
                        "uri": parent_post["uri"],
                        "cid": parent_post["cid"]
                    }
                }

            response = http_client.post(url, json=payload)
            bluesky_post = response.json() # type: ignore

            if response.status_code == 200: # type: ignore
                if not root_post:
                    root_post = bluesky_post
                post = Post(bluesky_post["cid"], post_text, i, article_id, recommendation_id, parent_id)
                parent_id = self._save_posts_in_db(post)
                parent_post = bluesky_post
            else:
                raise Exception(f"{bluesky_post["error"]}: {bluesky_post["message"]}")


    def _create_session(self, did: str, password: str):
        url = f"{self.BASE_URL}/com.atproto.server.createSession"
        http_client = HttpClient({"Content-Type": "application/json"})

        payload: dict[str, str] = {}
        payload["identifier"] = did
        payload["password"] = password

        response = http_client.post(url, json=payload)
        if response.status_code == 200: #type: ignore
            response = response.json() # type: ignore
            return str(response['accessJwt'])
        response.raise_for_status()
        raise


    def _resolve_handler(self, handle: str):
        url = f"{self.BASE_URL}/com.atproto.identity.resolveHandle?handle={handle}"
        http_client = HttpClient({"Content-Type": "application/x-www-form-urlencoded"})
        response = http_client.get(url)
        if response.status_code == 200: # type: ignore
            response = response.json() # type: ignore
            return str(response['did'])
        response.raise_for_status()
        raise






