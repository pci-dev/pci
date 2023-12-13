from time import sleep
from typing import Optional, TypedDict, cast
import uuid

from models.article import Article, TranslatedFieldDict, TranslatedFieldType
from app_modules.lang import Lang
from app_modules.translator import Translator

class ArticleTranslationDict(TypedDict, total=False):
    abstract: str
    title: str
    keywords: str


class ArticleTranslator(Translator):
    
    _article: Article


    def __init__(self, lang: Lang, article: Article):
        super().__init__(lang)
        self._article = article


    def run_article_translation(self):
        data_to_translate = self._build_data_to_translate(self._article)
        if not data_to_translate:
            return
        
        data_translated = self._translate_article_data(data_to_translate)

        self._save_translations(self._article, TranslatedFieldType.ABSTRACT, data_translated)
        self._save_translations(self._article, TranslatedFieldType.TITLE, data_translated)
        self._save_translations(self._article, TranslatedFieldType.KEYWORDS, data_translated)


    def _translate_article_data(self, data_to_translate: ArticleTranslationDict) -> ArticleTranslationDict:
        data_translated = ArticleTranslationDict()
        data_to_translate_hash = ArticleTranslationDict()
        text = ''
        text_translated = ''

        for key, value in data_to_translate.items():
            hash = uuid.uuid4().hex
            data_to_translate_hash[key] = hash

            text += f"\n{hash}\n{str(value)}"

        text_translated = self.translate(text)

        keys = list(data_to_translate.keys())
        for i in range(len(keys)):
            key = keys[i]
            hash = cast(str, data_to_translate_hash[key])
            next_hash = None
            if i + 1 < len(keys):
                next_hash = cast(str, data_to_translate_hash[keys[i + 1]])

            value = self._parse(text_translated, hash, next_hash)
            if value:
                data_translated[key] = value.strip()

        return data_translated
    

    def _parse(self, text: str, start_keyword: str, end_keyword: Optional[str]):
        lines = text.split('\n')

        start_index = -1
        end_index = -1

        for i, line in enumerate(lines):
            if line.strip() == start_keyword:
                start_index = i
            if end_keyword and line.strip() == end_keyword:
                end_index = i
                break

        if end_index == -1:
            end_index = len(lines)

        if start_index >= 0:
            return '\n'.join(lines[start_index+1:end_index])


    def _save_translations(self, article: Article, field: TranslatedFieldType, data_translated: ArticleTranslationDict):
        field_name = str(field.name.lower())

        if field_name not in data_translated:
            Article.delete_translation(article, field, self._lang)
            return
        
        translation = TranslatedFieldDict({
            'lang': self._lang.value.code,
            'content': data_translated[field_name],
            'automated': True
        })

        Article.add_or_update_translation(article, field, translation)


    def _build_data_to_translate(self, article: Article):
        data_to_translate = ArticleTranslationDict()
        if article.abstract and not Article.already_translated(article, TranslatedFieldType.ABSTRACT, self._lang):
            data_to_translate['abstract'] = article.abstract
        if article.title and not Article.already_translated(article, TranslatedFieldType.TITLE, self._lang):
            data_to_translate['title'] = article.title
        if article.keywords and not Article.already_translated(article, TranslatedFieldType.KEYWORDS, self._lang):
            data_to_translate['keywords'] = article.keywords
        return data_to_translate


    @staticmethod
    def run_article_translation_for_default_langs(article: Article):
        for lang in ArticleTranslator.DEFAULT_TARGET_LANG:
            translator = ArticleTranslator(lang, article)
            translator.run_article_translation()
            sleep(1)
