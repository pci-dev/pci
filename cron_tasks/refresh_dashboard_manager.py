from models.article import Article, ArticleStep
from app_modules.common_tools import log


def main():
    # articles with step containing "Since X days"
    articles = Article.get_by_step(
        [
            ArticleStep.SUBMISSION_AWAITING_COMPLETION,
            ArticleStep.SUBMISSION_PENDING_VALIDATION,
            ArticleStep.EVALUATION_AND_DECISION_UNDERWAY,
            ArticleStep.AWAITING_REVISION,
        ]
    )

    info(
        f"Articles that needs to have their alert date and current step refreshed: {[article.id for article in articles]}",
    )

    for article in articles:
        try:
            Article.update_alert_date(article)
            Article.update_current_step(article)
        except Exception as e:
            info(f"Error to refresh for article {article.id}: {e}")
            continue

    info("Dashboard manager refreshed!")


def info(msg: str):
    log("refresh_dashboard_manager.py", msg)


if __name__ == "__main__":
    main()
