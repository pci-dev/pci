from app_modules.httpClient import HttpClient
from app_modules.mastodon import SocialNetwork
from models.post import PostTable


class Bluesky(SocialNetwork):

    POST_MAX_LENGTH = 300

    def __init__(self):
        super().__init__(self.POST_MAX_LENGTH, PostTable.BLUESKY_POSTS)

        self._handle = "charcefe.bsky.social"
        self._app_password = "yr23-w64r-5e7x-cgoe"

        self._token = self._create_session()


    def send_post(self, article_id: int, recommendation_id: int, posts_text: list[str], specific_account: bool = True, general_account: bool = False):
        ...

    def _post(self):
        url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
        http_client = HttpClient({"Content-Type": "application/json", "Authorization": self._token})



    def _create_session(self):
        url = "https://bsky.social/xrpc/com.atproto.server.createSession"
        http_client = HttpClient({"Content-Type": "application/json"})
        payload: dict[str, str] = {}
        payload["identifier"] = self._resolve_handler()
        payload["password"] = self._app_password
        response = http_client.post(url, json=payload)
        if response.status_code == 200: #type: ignore
            response = response.json() # type: ignore
            return str(response.accessJwt)
        response.raise_for_status()
        raise


    def _resolve_handler(self):
        url = f"https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle={self._handle}"
        http_client = HttpClient({"Content-Type": "application/x-www-form-urlencoded"})
        response = http_client.get(url)
        if response.status_code == 200: # type: ignore
            response = response.json() # type: ignore
            return str(response.did)
        response.raise_for_status()
        raise






