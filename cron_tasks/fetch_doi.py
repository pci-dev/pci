from time import sleep
from gluon import current
from models.article import Article
from app_modules import emailing


def main():
    articles = Article.get_all_articles_without_article_published_doi()
    print(f"Number of article without published article DOI: {len(articles)}")

    count = 0

    for article in articles:
        try:
            doi = Article.get_or_set_doi_published_article(article)
            current.db.commit()
            
            if doi:
                count += 1
                emailing.send_message_to_recommender_and_reviewers(article.id)
                print(f"Published article DOI found for article {article.id}: {doi}")

        except Exception as e:
            print(f"Error to check API for {article.id} with doi {article.doi}: {e}")
            
        finally:
            sleep(0.1)
    
    print(f"Fetch DOI finished: {count} published article DOI added")
    


if __name__ == "__main__":
    main()
