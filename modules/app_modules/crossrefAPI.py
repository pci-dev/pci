from typing import Any, List, Optional

from app_modules.httpClient import HttpClient

class CrossrefAPI:

    BASE_URL = "https://api.crossref.org"
    
    http_client = HttpClient(default_headers={'accept': 'application/json'})

    def _get_work(self, doi: str):
        doi = self._clean_doi(doi)

        url = f"{self.BASE_URL}/works/{doi}"

        response = self.http_client.get(url)
        if response.ok:
            return response.json() # type: ignore


    def get_published_article_doi(self, preprint_doi: str):
        from app_modules.common_tools import sget
        
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
                return self._set_doi_like_url(doi)


    def _set_doi_like_url(self, doi: str):
        if not doi.startswith("http"):
            doi = f"https://doi.org/{doi}"
        return doi


    def _clean_doi(self, doi: str):
        doi = doi.strip()
        doi = doi.replace("https://", "").replace("http://", "").replace("doi.org/", "")
        return doi
