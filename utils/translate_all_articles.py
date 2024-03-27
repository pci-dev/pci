from time import sleep
from app_modules.article_translator import ArticleTranslator
from models.article import Article, ArticleStatus, TranslatedFieldType
from gluon import current

# To launch script:
# python web2py.py -M -S {APP_NAME} -R applications/pci/utils/translate_all_articles.py

def missing_translations(article: Article):
    missing_translated_title = article.translated_title is None or missing_default_lang(article, TranslatedFieldType.TITLE)
    missing_translated_abstract = article.translated_abstract is None or missing_default_lang(article, TranslatedFieldType.ABSTRACT)
    missing_translated_keywords = article.translated_keywords is None or missing_default_lang(article, TranslatedFieldType.KEYWORDS)

    return missing_translated_title or missing_translated_abstract or missing_translated_keywords


def missing_default_lang(article: Article, field: TranslatedFieldType):
    for lang in ArticleTranslator.DEFAULT_TARGET_LANG:
        if not Article.already_translated(article, field, lang):
            return True
    return False


def main():
    articles_to_translate = Article.get_by_status([
        ArticleStatus.RECOMMENDED,
        ArticleStatus.AWAITING_CONSIDERATION,
        ArticleStatus.UNDER_CONSIDERATION,
        ArticleStatus.AWAITING_REVISION,
        ArticleStatus.PRE_REVISION,
        ArticleStatus.PRE_RECOMMENDED,
        ArticleStatus.SCHEDULED_SUBMISSION_PENDING,
        ArticleStatus.PENDING_SURVEY
    ], current.db.t_articles.id)

    nb_articles_total = len(articles_to_translate)

    articles_to_translate = list(filter(missing_translations, articles_to_translate))
    nb_articles_to_translate = len(articles_to_translate)

    print(f"# Number of articles to translate : {nb_articles_to_translate}/{nb_articles_total}")
    print(f"# {nb_articles_total - nb_articles_to_translate} articles already translated.")
    print("-----", end="\n\n")

    i = 1
    for article in articles_to_translate:
        print(f"{i}/{nb_articles_to_translate} Traduction for article ID {article.id}: {article.title}", end="")
        ArticleTranslator.run_article_translation_for_default_langs(article, public=True)
        current.db.commit()
        print('-> Added!')
        sleep(1)
        i += 1


if __name__ == "__main__":
    current.session.disable_trigger_setPublishedDoi = True
    main()
    current.session.disable_trigger_setPublishedDoi = None
