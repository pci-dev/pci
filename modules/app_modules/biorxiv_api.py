from time import sleep
from typing import Any, List, Optional
from app_modules.httpClient import HttpClient


class BiorxivAPI:

    BASE_URL = "https://api.biorxiv.org"

    _http_client = HttpClient(default_headers={"accept": "application/json"})

    servers = ("biorxiv", "medrxiv")


    def get_published_article_doi(self, preprint_doi: str):
        from app_modules.common_tools import url_to_doi_id, doi_to_url

        doi = url_to_doi_id(preprint_doi)

        if not doi.startswith("10.1101/"):
            return
        
        for server in self.servers:
            details = self._get_details(doi, server)
            if not details:
                continue

            collection: List[Any] = details.get("collection")
            if not collection:
                continue

            article_doi = self._get_article_doi(collection)
            if article_doi:
                return doi_to_url(article_doi)
            
            sleep(0.25)


    def _get_article_doi(self, collection: List[Any]):
        collection.sort(key=lambda d: d.get("version"), reverse=True)

        for doc in collection:
            published: Optional[str] = doc.get("published")
            if not published or published.lower().strip() == "na":
                continue
            else:
                return published


    def _get_details(self, doi: str, server: str):
        url = f"{self.BASE_URL}/details/{server}/{doi}"

        response = self._http_client.get(url)

        if response.ok:
            return response.json()  # type: ignore
