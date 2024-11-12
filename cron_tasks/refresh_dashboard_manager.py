from models.article import Article, ArticleStep


if __name__ == "__main__":

    # articles with step containing "Since X days" 
    articles = Article.get_by_step(
        [
            ArticleStep.SUBMISSION_AWAITING_COMPLETION,
            ArticleStep.SUBMISSION_PENDING_VALIDATION,
            ArticleStep.EVALUATION_AND_DECISION_UNDERWAY,
            ArticleStep.AWAITING_REVISION,
        ]
    )

    print(f"Articles that needs to have their alert date and current step refreshed: {[article.id for article in articles]}")

    for article in articles:
        try:
            Article.update_alert_date(article)
            Article.update_current_step(article)
        except Exception as e:
            print(f"Error to refresh for article {article.id}: {e}")
            continue

    print("Dashboard manager refreshed!")
