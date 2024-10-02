from models.article import Article

if __name__ == '__main__':

    articles = Article.get_all()

    for article in articles:
        Article.update_alert_date(article)
