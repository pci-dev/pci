import argparse

from gluon import current

from models.article import Article
from app_modules.article_translator import ArticleTranslator

parser = argparse.ArgumentParser(
    prog='Translator',
    description='Use deep_translator to translate text (Deepl and Google Translate)'
)

parser.add_argument('article_id', type=int)
args = parser.parse_args()

article_id = int(args.article_id)


def main(article_id: int):
    article = Article.get_by_id(current.db, article_id)

    if not article:
        raise Exception('Article not found')

    ArticleTranslator.run_article_translation_for_default_langs(article)


main(article_id)
