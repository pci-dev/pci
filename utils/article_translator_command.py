import argparse

from models.article import Article
from app_modules.article_translator import ArticleTranslator


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='Translator',
        description='Use deep_translator to translate text (Deepl and Google Translate)'
    )

    parser.add_argument('article_id', type=int)
    parser.add_argument('force', type=lambda x: (x if str(x).lower() == 'true' else False))
    parser.add_argument('public', type=lambda x: (x if str(x).lower() == 'true' else False), nargs="?", default=None)
    args = parser.parse_args()

    article_id = int(args.article_id)
    force = bool(args.force)
    public = None if args.public == None else bool(args.public)
    
    article = Article.get_by_id(article_id)

    if not article:
        raise Exception('Article not found')

    ArticleTranslator.run_article_translation_for_default_langs(article, force, public)
