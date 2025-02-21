from time import sleep
from app_modules.httpClient import HttpClient
from typing import Any, List, Optional

class CrossrefAPI:

    BASE_URL = "https://api.crossref.org"

    _http_client = HttpClient(default_headers={'accept': 'application/json'})
    
    def _get_work(self, doi: str):
        from app_modules.common_tools import url_to_doi_id

        doi = url_to_doi_id(doi)

        url = f"{self.BASE_URL}/works/{doi}"

        response = self._http_client.get(url)
        if response.ok:
            return response.json() # type: ignore


    def get_published_article_doi_method_1(self, preprint_doi: str):
        from app_modules.common_tools import sget, doi_to_url
        
        work = self._get_work(preprint_doi)
        if not work:
            return
        
        relations: Optional[List[Any]] = sget(work, 'message', 'relation', 'is-preprint-of')
        if not relations:
            return
        
        for relation in relations:
            if 'id' not in relation:
                continue

            if 'id-type' not in relation or relation['id-type'] != "doi":
                continue 
            
            doi = str(relation['id'])
            if doi:
                return doi_to_url(doi)


    def get_published_article_doi_method_2(self, preprint_doi: str):
        from app_modules.common_tools import doi_to_url, sget, url_to_doi_id

        doi = url_to_doi_id(preprint_doi)

        items = self._get_items(doi)

        relation_type_priority = ('doi', 'other')

        for work in items:
            journal_doi: Optional[str] = work.get('DOI')
            if not journal_doi:
                continue
            
            relations: Optional[List[Any]] = sget(work, 'relation', 'has-preprint')
            if not relations:
                continue

            for type in relation_type_priority:
                for relation in relations:
                    relation_doi: Optional[str] = relation.get('id')
                    relation_type: Optional[str] = relation.get('id-type')
                    if not relation_doi or not relation_type:
                        continue

                    if relation_type.strip().lower() == type:
                        if doi in relation_doi:
                            return doi_to_url(journal_doi)


    def _get_items(self, doi: str):
        from app_modules.common_tools import sget

        cursor_size = 1000

        cursor = "*"
        url = f"{self.BASE_URL}/works?rows={cursor_size}&select=DOI,relation,type&filter=type:journal-article,relation.type:has-preprint,relation.object:{doi}"
        works: List[Any] = []

        while True:
            response = self._http_client.get(f"{url}&cursor={cursor}")
            if not response.ok:
                break

            data = response.json() # type: ignore
            items: Optional[List[Any]] = sget(data, 'message', 'items')
            if not items:
                break

            works.extend(items)

            if len(items) != cursor_size:
                break
            
            cursor = sget(data, 'message', 'next-cursor')
            if not cursor:
                break

            sleep(0.1)
        
        return works
    
