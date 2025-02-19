from datetime import datetime, timedelta
from time import sleep
from typing import List
from app_modules.crossref_api import CrossrefAPI
from gluon import current
from models.article import Article
from app_modules import emailing


def main():
    articles = Article.get_all_articles_without_article_published_doi()
    print(f"Number of article without published article DOI: {len(articles)}")

    count = process_request_all_api(articles)    
    print(f"Fetch DOI from API finished: {count} published article DOI added")

    count = search_in_crossref(articles)
    print(f"Search in yesterday updated work in Crossref finished: {count} published article DOI added")


def search_in_crossref(articles: List[Article]):
    count = 0

    yesterday = (datetime.now() - timedelta(1)).date()

    preprint_dois: List[str] = []
    for article in articles:
        if article.doi:
            preprint_dois.append(article.doi)

    try:
        article_dois = CrossrefAPI().get_published_article_doi_since(preprint_dois, yesterday)
    except Exception as e:
        print(f"Error to search in Crossref API since {yesterday}: {e}")
        return
    
    if len(article_dois) == 0:
        return 0

    for article in articles:
        if not article.doi:
            continue

        preprint_doi = article.doi.strip()
        article_doi = article_dois.get(preprint_doi)

        if article_doi:
            current.db(current.db.t_articles.id == article.id).update(doi_of_published_article=article_doi)
            current.db.commit()
            count += 1
            if 'pcjournal' in article_doi:
                emailing.send_message_to_recommender_and_reviewers(article.id)

            print(f"Published article DOI found for article {article.id}: {article_doi}")

    return count


def process_request_all_api(articles: List[Article]):
    count = 0

    for article in articles:
        try:
            doi = Article.get_or_set_doi_published_article(article)
            
            if doi:
                current.db.commit()
                
                count += 1
                if 'pcjournal' in doi:
                    emailing.send_message_to_recommender_and_reviewers(article.id)
                    
                print(f"Published article DOI found for article {article.id}: {doi}")

        except Exception as e:
            print(f"Error to check API for {article.id} with doi {article.doi}: {e}")
            
        finally:
            sleep(0.1)
    
    return count

if __name__ == "__main__":
    main()
