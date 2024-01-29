from enum import Enum
from typing import List, cast
from gluon import current
from gluon.contrib.appconfig import AppConfig
from gluon.globals import Response, Request, Session
from gluon.html import A, BUTTON, DIV, FORM, HR, INPUT, LABEL, OPTION, SELECT, SPAN, TEXTAREA, URL, XML
from gluon.http import redirect
from gluon.tools import Auth
from app_modules.lang import DEFAULT_LANG, Lang, LangItem
from app_modules.article_translator import ArticleTranslator
from models.article import Article, TranslatedFieldType, TranslatedFieldDict
from pydal.base import DAL
from app_modules import common_tools
from app_modules import common_small_html

db = cast(DAL, current.db)
response = cast(Response, current.response)
request = cast(Request, current.request)
session = cast(Session, current.session)
auth = cast(Auth, current.auth)
config = AppConfig()

scheme = config.take("alerts.scheme")
host = config.take("alerts.host")
port = config.take("alerts.port", cast=lambda v: common_tools.takePort(v))


@auth.requires_signature()
@auth.requires_login()
def edit_article_translations():
    article_id = int(request.vars["article_id"])
    translated_field = TranslatedFieldType(request.vars["field"])

    if not translated_field:
        session.flash = "Translated field not found"
        return redirect(URL('default','index'))

    article = Article.get_by_id(db, article_id)
    if not article:
        session.flash = "Article not found"
        return redirect(URL('default','index'))
    
    if article.user_id != auth.user_id and not auth.has_membership(role="manager"):
        session.flash = "Forbidden"
        return redirect(URL('default','index'))
        
    english_field = TranslatedFieldType.get_corresponding_english_field(translated_field)
    if not english_field:
        session.flash = "English value not found"
        return redirect(URL('default','index'))

    form = DIV(
        _generate_form(article, translated_field, english_field),
        _id="lang_form_group"
        )

    response.view = 'default/myLayout.html'
    return dict(
            form=form,
            myBackButton=common_small_html.mkBackButton(),
            myFinalScript=common_tools.get_script("article_translations.js"),
            pageTitle=english_field.capitalize() + "'s translations",
            confirmationScript = common_small_html.confirmationDialog('Are you sure?')
        )


@auth.requires_login()
def add_or_edit_article_field_translation():
    article_id = int(request.vars["article_id"])
    translated_field = TranslatedFieldType(request.vars["field"])
    lang = Lang.get_lang_by_code(request.vars["lang"])
    action = AddNewLanguageAction(request.vars["action"])
    translation = str(request.vars["translation"] or '')

    if not translated_field:
        response.flash = "Translated field not found"
        return

    article = Article.get_by_id(db, article_id)
    if not article:
        response.flash = "Article not found"
        return
    
    if article.user_id != auth.user_id and not auth.has_membership(role="manager"):
        response.flash = "Forbidden"
        return
    
    is_textarea = translated_field == TranslatedFieldType.ABSTRACT
    exists_translation = translation_value = Article.get_translation(article, translated_field, lang) != None

    if action == AddNewLanguageAction.GENERATE:
        try:
            ArticleTranslator(lang, article).run_field_article_translation(translated_field)
        except Exception:
            response.flash = f"Automatic translation not possible: {lang.value.english_name} not supported."
            return
    else:
        if len(translation) == 0:
            response.flash = 'Text input field empty'
            return
        
        new_translation: TranslatedFieldDict = {
            'automated': False,
            'content': translation,
            'lang': lang.value.code
        }
        Article.add_or_update_translation(article, translated_field, new_translation)

    translation_value = Article.get_translation(article, translated_field, lang)

    if not translation_value:
        response.flash = f"No translation for {translated_field.value} in {lang.value.english_name}"
        return

    if exists_translation:
        response.flash = f"Translation in {lang.value.english_name} updated"
    else:
        response.flash = f"Translation in {lang.value.english_name} added"

    return _generate_lang_form(article, translated_field, translation_value, is_textarea)


@auth.requires_login()
def delete_translation():
    article_id = int(request.vars["article_id"])
    translated_field = TranslatedFieldType(request.vars["field"])
    lang = Lang.get_lang_by_code(request.vars["lang"])

    if not translated_field:
        response.flash = "Translated field not found"
        return

    article = Article.get_by_id(db, article_id)
    if not article:
        response.flash = "Article not found"
        return
    
    if article.user_id != auth.user_id and not auth.has_membership(role="manager"):
        response.flash = "Forbidden"
        return
    
    Article.delete_translation(article, translated_field, lang)
    response.flash = f"Translation in {lang.value.english_name} deleted"


def _generate_form(article: Article, translated_field: TranslatedFieldType, english_field: str):
    translations_value = Article.get_all_translations(article, translated_field)
    is_textarea = translated_field == TranslatedFieldType.ABSTRACT

    form: List[DIV] = []
    form.append(_generate_english_form(article, english_field, is_textarea))
    form.append(HR())
    
    form.append(_generate_lang_selector(article, translated_field, is_textarea))
    form.append(HR())

    lang_form: List[FORM] = []
    if translations_value:
        for translation_value in translations_value:
            lang_form.append(_generate_lang_form(article, translated_field, translation_value, is_textarea))
    form.append(DIV(*lang_form, _id="lang-form-list"))

    return DIV(*form)


def _generate_lang_selector(article: Article, translated_field: TranslatedFieldType, is_textarea: bool):
    lang_list = [lang.value for lang in Lang if lang != DEFAULT_LANG]
    lang_list = sorted(lang_list, key=lambda lang: lang.english_name)
    lang_options = [OPTION(_build_lang_name(lang), _value=lang.code) for lang in lang_list]
    lang_options.insert(0, OPTION(''))

    url_generate = cast(str,
               URL(c="article_translations",
                   f="add_or_edit_article_field_translation",
                   vars=dict(article_id=article.id, field=translated_field.value, action=AddNewLanguageAction.GENERATE.value),
                   user_signature=True,
                   host=host,
                   scheme=scheme,
                   port=port)
               )
    
    url_write = cast(str,
               URL(c="article_translations",
                   f="add_or_edit_article_field_translation",
                   vars=dict(article_id=article.id, field=translated_field.value, action=AddNewLanguageAction.WRITE.value),
                   user_signature=True,
                   host=host,
                   scheme=scheme,
                   port=port)
               )
    
    if is_textarea:
        input = TEXTAREA(_id="new-translation", _class="form-control text", _name="new-translation")
    else:
        input = INPUT(_id="new-translation", _type='text', _class="string form-control", _name="new-translation")
    
    return FORM(
        LABEL('Add translation', _class="control-label col-sm-3", _for="lang-selector", _style="font-size: 17px"),
        DIV(
            SELECT(lang_options, _id="lang-selector", _class="generic-widget form-control"),
            BUTTON("Write", _id="write-translation", _class="btn btn-default", _disabled=True),
            BUTTON("Generate", _id="generate-translation", _class="btn btn-success", _link=url_generate, _disabled=True),
            DIV(
                input,
                BUTTON("Save", _id="save-translation", _class="btn btn-primary", _disabled=True, _link=url_write),
                _id="write-tranlation-block", _style="display: none"
            ),
            _class="col-sm-9"
        ),
    _class="form-group")


def _build_lang_name(lang: LangItem):
    lang_name = lang.english_name
    if lang.name:
        lang_name += f" ({lang.name})"
    return lang_name


def _generate_lang_form(article: Article, translated_field: TranslatedFieldType, translation_value: TranslatedFieldDict, is_textarea: bool):
    lang = Lang.get_lang_by_code(translation_value['lang'])

    if is_textarea:
        input = TEXTAREA(translation_value["content"], _id=lang.value.code, _class="form-control text", _name=lang.value.code)
    else:
        input = INPUT(_id=lang.value.code, _value=translation_value["content"], _type='text', _class="string form-control", _name=lang.value.code)

    save_url = cast(str,
                        URL(c="article_translations",
                            f="add_or_edit_article_field_translation",
                            vars=dict(article_id=article.id, field=translated_field.value, action=AddNewLanguageAction.WRITE.value, lang=lang.value.code, is_textarea=str(is_textarea).lower()),
                            user_signature=True,
                            host=host,
                            scheme=scheme,
                            port=port)
                    )
    
    delete_url = cast(str,
                        URL(c="article_translations",
                            f="delete_translation",
                            vars=dict(article_id=article.id, field=translated_field.value, lang=lang.value.code),
                            user_signature=True,
                            host=host,
                            scheme=scheme,
                            port=port)
                    )
        
    return FORM(
                _generate_lang_label(lang, translation_value),
                DIV(
                    input,
                    A("Save", _class="btn btn-primary lang-form-save-button", _link=save_url),
                    A("Delete", _class="btn btn-danger lang-form-delete-button", _link=delete_url),
                    _class="col-sm-9"
                ),
                _class="form-group", _style="margin-bottom: 10px", _id=f"translation-{lang.value.code}"
            )


def _generate_english_form(article: Article, english_field: str, is_textarea: bool):
    english_value = cast(str, getattr(article, english_field))
    lang_en = DEFAULT_LANG

    if is_textarea:
        input = DIV(XML(english_value), _id=lang_en.value.code, _name=lang_en.value.code, _class="well")
    else:
        input = INPUT(_id=lang_en.value.code, _value=english_value, _type='text', _class="string form-control", _name=lang_en.value.code, _disabled=True),
                
    return FORM(
            LABEL(lang_en.value.english_name, _class="control-label col-sm-3", _for=lang_en.value.code, _style="font-size: 17px"),
            DIV(
                input,
                _class="col-sm-9"
            ),
            _class="form-group"
        )
    

def _generate_lang_label(lang: Lang, translation_value: TranslatedFieldDict):
    label_text = _build_lang_name(lang.value)
    label_class = "control-label col-sm-3"
    label_for = lang.value.code
    style = "font-size: 17px"

    if translation_value['automated']:
        return LABEL(label_text, SPAN('Generated', _style="color: red; margin-left: 5px"), _class=label_class, _for=label_for, _style=style)
    else:
        return LABEL(label_text, _class=label_class, _for=label_for, _style=style)


class AddNewLanguageAction(Enum):
    WRITE = 'write'
    GENERATE = 'generate'
