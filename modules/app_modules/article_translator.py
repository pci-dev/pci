from time import sleep
from typing import Optional, TypedDict, cast
import uuid
import subprocess
from gluon import current
from gluon.html import A, URL
from gluon.sqlhtml import SQLFORM

from models.article import Article, TranslatedFieldDict, TranslatedFieldType
from app_modules.lang import Lang
from app_modules.translator import Translator

class ArticleTranslationDict(TypedDict, total=False):
    abstract: str
    title: str
    keywords: str


class ArticleTranslator(Translator):
    
    _article: Article
    _public: Optional[bool]

    def __init__(self, lang: Lang, article: Article, public: Optional[bool] = False):
        super().__init__(lang)
        self._article = article
        self._public = public


    def run_article_translation(self, force: bool = False):
        data_to_translate = self._build_data_to_translate(force)
        if not data_to_translate:
            return
        
        data_translated = self._translate_article_data(data_to_translate)

        self._save_translations(TranslatedFieldType.ABSTRACT, data_translated)
        self._save_translations(TranslatedFieldType.TITLE, data_translated)
        self._save_translations(TranslatedFieldType.KEYWORDS, data_translated)

        self._clean_translation()


    def run_field_article_translation(self, field: TranslatedFieldType):
        data_to_translate = ArticleTranslationDict()
        self._build_field_data_to_translate(data_to_translate, field)

        if not data_to_translate:
            return

        data_translated = self._translate_article_data(data_to_translate)

        self._save_translations(field, data_translated)


    def _clean_translation(self):
        if not self._article.abstract:
            Article.delete_translation(self._article, TranslatedFieldType.ABSTRACT, self._lang)
        if not self._article.title:
            Article.delete_translation(self._article, TranslatedFieldType.TITLE, self._lang)
        if not self._article.keywords:
            Article.delete_translation(self._article, TranslatedFieldType.KEYWORDS, self._lang)
        

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
        for i, key in enumerate(keys):
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


    def _save_translations(self, field: TranslatedFieldType, data_translated: ArticleTranslationDict):
        field_name = str(TranslatedFieldType.get_corresponding_english_field(field))

        if field_name not in data_translated:
            return
        
        translation = TranslatedFieldDict({
            'lang': self._lang.value.code,
            'content': data_translated[field_name],
            'automated': True,
            'public': self._public
        })

        Article.add_or_update_translation(self._article, field, translation)


    def _build_data_to_translate(self, force: bool = False):
        data_to_translate = ArticleTranslationDict()

        self._build_field_data_to_translate(data_to_translate, TranslatedFieldType.ABSTRACT, force)
        self._build_field_data_to_translate(data_to_translate, TranslatedFieldType.TITLE, force)
        self._build_field_data_to_translate(data_to_translate, TranslatedFieldType.KEYWORDS, force)

        return data_to_translate


    def _build_field_data_to_translate(self, data_to_translate: ArticleTranslationDict, translated_field: TranslatedFieldType, force: bool = False):
        field = str(TranslatedFieldType.get_corresponding_english_field(translated_field))
        field_value = str(getattr(self._article, field))

        if field_value:
            already_translated = Article.already_translated(self._article, translated_field, self._lang) and not force
            manual_translation = Article.already_translated(self._article, translated_field, self._lang, manual=True)

            if not already_translated and not manual_translation :
                data_to_translate[field] = field_value


    @staticmethod
    def run_article_translation_for_default_langs(article: Article, force: bool = False, public: Optional[bool] = None):
        for lang in ArticleTranslator.DEFAULT_TARGET_LANG:
            translator = ArticleTranslator(lang, article, public)
            translator.run_article_translation(force)
            sleep(1)


    @staticmethod
    def launch_article_translation_for_default_langs_process(article_id: int, force: bool = False, public: Optional[bool] = None):
        app_name = current.request.application
        
        cmd = [
            'python3',
            'web2py.py',
            '-M', 
            '-S', 
            app_name, 
            '-R', 
            f'applications/{app_name}/utils/article_translator_command.py',
            '-A', 
            str(article_id),
            str(force)
        ]

        if public != None:
            cmd.append(str(public))
        
        subprocess.Popen(cmd)

    
    @staticmethod
    def add_edit_translation_buttons(article: Article, article_form: SQLFORM):
        if not Article.current_user_has_edit_translation_right(article):
            return
        
        style = "margin: 0px"
        button_class = "btn btn-default"
        
        title_url = cast(str, URL(c="article_translations", f="edit_all_article_translations", vars=dict(article_id=article.id),  user_signature=True))
        abstract_url = cast(str, URL(c="article_translations", f="edit_all_article_translations", vars=dict(article_id=article.id),  user_signature=True))
        keywords_url = cast(str, URL(c="article_translations", f="edit_all_article_translations", vars=dict(article_id=article.id),  user_signature=True))

        title_row = article_form.element(_id="t_articles_title__row")
        if title_row:
            title_row.components[1].append(A("Edit title translations", _class=button_class, _style=style, _href=title_url))
        
        abstract_row = article_form.element(_id="t_articles_abstract__row")
        if abstract_row:
            abstract_row.components[1].append(A("Edit abstract translations", _class=button_class, _style=style, _href=abstract_url))

        keywords_row = article_form.element(_id="t_articles_keywords__row")
        if keywords_row:
            keywords_row.components[1].append(A("Edit keywords translations", _class=button_class, _style=style, _href=keywords_url))
