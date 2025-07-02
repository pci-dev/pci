from app_modules.common_tools import doi_to_url
from app_modules.crossref import get_decision_doi
from app_modules.httpClient import HttpClient
from models.article import Article, ArticleStatus
from gluon import current
from models.recommendation import Recommendation

db = current.db

if __name__ == '__main__':
    http_client = HttpClient()
    failed = 0

    articles = Article.get_by_status([ArticleStatus.RECOMMENDED], order_by=~db.t_articles.last_status_change)
    for article in articles:
        if failed >= 5:
            print(f"{failed} failed ! Stop script")
            exit(0)

        if article.show_all_doi:
            continue

        first_recommendation = Recommendation.get_by_article_id(article.id, order_by=db.t_recommendations.id)[0]
        doi = get_decision_doi(first_recommendation, 1)
        url = doi_to_url(doi)
        response = http_client.get(url)
        if response.status_code == 200: # type: ignore
            article.show_all_doi = True
            article.update_record() # type: ignore
            db.commit()
            print(article.id)
            failed = 0
        else:
            failed += 1

print("End !")
