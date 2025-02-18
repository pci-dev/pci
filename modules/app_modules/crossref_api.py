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


    def get_published_article_doi(self, preprint_doi: str):
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
