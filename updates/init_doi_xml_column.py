from models.article import Article, ArticleStatus
from app_modules.article_translator import ArticleTranslator


if __name__ == '__main__':

    articles = Article.get_by_status([ArticleStatus.RECOMMENDED])



    ArticleTranslator.run_article_translation_for_default_langs(article, force, public)
