from models.article import Article

if __name__ == '__main__':

    articles = Article.get_all()

    for article in articles:
        try:
            Article.update_alert_date(article)
            Article.update_current_step(article)
            print(article.id, end=", ", flush=True)
        except Exception as e:
            print(f"Error for article: {e}")
            continue
