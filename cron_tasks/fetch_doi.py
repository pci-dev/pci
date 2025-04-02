from time import sleep
from typing import List
from gluon import current
from models.article import Article
from app_modules import emailing


def main():
    articles = Article.get_all_articles_without_article_published_doi()
    print(f"Number of article without published article DOI: {len(articles)}")

    count = process_request_all_api(articles)    
    print(f"Fetch DOI from API finished: {count} published article DOI added")


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
            sleep(0.25)
    
    return count

if __name__ == "__main__":
    main()
