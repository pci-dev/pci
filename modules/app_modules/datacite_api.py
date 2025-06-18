from .httpClient import HttpClient
from datetime import datetime
from typing import Any, List, Optional


class DataciteAPI:

    BASE_URL = "https://api.datacite.org"

    _http_client = HttpClient(default_headers={'accept': 'application/json'})


    def _get_associated_articles(self, doi: str):
        url = f"{self.BASE_URL}/dois/?query=types.resourceTypeGeneral:JournalArticle AND relatedIdentifiers.relatedIdentifier:{doi}"

        response = self._http_client.get(url)
        if response.ok:
            return response.json() # type: ignore


    def get_published_article_doi(self, preprint_doi: str):
        from app_modules.common_tools import sget, url_to_doi_id, doi_to_url

        preprint_doi = url_to_doi_id(preprint_doi)

        response = self._get_associated_articles(preprint_doi)

        if not response:
            return

        linked_article: Optional[Any] = None

        articles: List[Any] = response['data']
        for article in articles:
            has_preprint = self._is_preprint_of_article(preprint_doi, article)
            if not has_preprint:
                continue

            linked_article_updated: Optional[str] = None
            linked_article_created: Optional[str] = None

            if linked_article:
                linked_article_updated = sget(linked_article, 'attributes', 'updated')
                linked_article_created = sget(linked_article, 'attributes', 'created')

            article_updated: Optional[str] = sget(article, 'attributes', 'updated')
            article_created: Optional[str] = sget(article, 'attributes', 'created')

            if not linked_article_created and not linked_article_created:
                linked_article = article
                continue

            if linked_article_updated and article_updated:
                linked_article_updated_dt = datetime.strptime(linked_article_updated, "%Y-%m-%dT%H:%M:%SZ")
                article_updated_dt = datetime.strptime(article_updated, "%Y-%m-%dT%H:%M:%SZ")

                if article_updated_dt > linked_article_updated_dt:
                    linked_article = article
                    continue

            if linked_article_created and article_created:
                linked_article_created_dt = datetime.strptime(linked_article_created, "%Y-%m-%dT%H:%M:%SZ")
                article_created_dt = datetime.strptime(article_created, "%Y-%m-%dT%H:%M:%SZ")

                if article_created_dt > linked_article_created_dt:
                    linked_article = article
                    continue

        if linked_article:
            doi = sget(linked_article, 'attributes', 'doi')
            if doi:
                doi = doi_to_url(str(doi))
                return doi


    def _is_preprint_of_article(self, doi: str, article: ...):
        from app_modules.common_tools import sget

        related_works: Optional[List[Any]] = sget(article, 'attributes', 'relatedIdentifiers')
        if not related_works:
            return False

        for work in related_works:
            type: Optional[str] = work.get('resourceTypeGeneral')
            related_id_type: Optional[str] = work.get('relatedIdentifierType')
            related_id: Optional[str] = work.get('relatedIdentifier')

            if not type or not related_id or not related_id_type:
                continue

            if type.strip() != 'Preprint':
                continue

            if related_id.strip() != doi:
                continue

            if related_id_type.strip().upper() != 'DOI':
                continue

            return True

        return False







