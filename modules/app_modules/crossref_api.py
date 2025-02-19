from datetime import date
from time import sleep
from app_modules.httpClient import HttpClient
from typing import Any, Dict, List, Optional

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


    def get_published_article_doi_since(self, preprint_doi_url: List[str], start_date: date):
        ''' Return dict where keys are preprint doi url and values journal doi url'''

        from app_modules.common_tools import url_to_doi_id, doi_to_url

        preprint_dois = [url_to_doi_id(d) for d in preprint_doi_url]
        works = self._get_works_article_journal_newer_than(start_date)

        journal_dois: Dict[str, str] = {}

        for preprint_doi in preprint_dois:
            for work in works:
                journal_doi: Optional[str] = work.get('DOI')
                if not journal_doi:
                    continue
                
                references: Optional[List[Any]] = work.get('reference')
                if not references:
                    continue

                for reference in references:
                    reference_doi: Optional[str] = reference.get('DOI')
                    if not reference_doi:
                        continue
                    
                    if preprint_doi in reference_doi:
                        journal_dois[doi_to_url(preprint_doi)] = doi_to_url(journal_doi)
                    
        return journal_dois


    def _get_works_article_journal_newer_than(self, start_date: date):
        from app_modules.common_tools import sget

        pub_date = start_date.isoformat()

        cursor_size = 1000

        cursor = "*"
        url = f"{self.BASE_URL}/works?rows={cursor_size}&select=DOI,reference,type&filter=type:journal-article,from-update-date:{pub_date},relation.type:has-preprint"

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
    
