from enum import Enum
import html
from typing import List, Optional, cast
from gluon import current
from gluon.contrib.appconfig import AppConfig
from gluon.globals import Response, Request, Session
from gluon.html import A, BUTTON, DIV, FORM, HR, I, INPUT, LABEL, OPTION, P, SELECT, TEXTAREA, URL, XML
from gluon.http import redirect
from gluon.tools import Auth
from app_modules.lang import DEFAULT_LANG, Lang, LangItem
from app_modules.article_translator import ArticleTranslator
from models.article import Article, TranslatedFieldType, TranslatedFieldDict
from pydal.base import DAL
from app_modules import common_tools
from app_modules import common_small_html
from app_modules.translator import Translator


db = cast(DAL, current.db)
response = cast(Response, current.response)
request = cast(Request, current.request)
session = cast(Session, current.session)
auth = cast(Auth, current.auth)
config = AppConfig()

scheme = config.take("alerts.scheme")
host = config.take("alerts.host")
port = config.take("alerts.port", cast=lambda v: common_tools.takePort(v))


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
    
    done_button = BUTTON(current.T("Back"), _class="btn btn-default", _onclick="window.history.back();", _style="margin: auto")
        
    response.view = 'default/myLayout.html'
    return dict(
            form=form,
            myBackButton=common_small_html.mkBackButton(),
            myFinalScript=common_tools.get_script("article_translations.js"),
            pageTitle=english_field.capitalize() + "'s translations",
            confirmationScript = common_small_html.confirmationDialog('Are you sure?'),
            myAcceptBtn=done_button)


def edit_all_article_translations():
    article_id = int(request.vars["article_id"])

    article = Article.get_by_id(db, article_id)
    if not article:
        session.flash = "Article not found"
        return redirect(URL('default','index'))
    
    if article.user_id != auth.user_id and not auth.has_membership(role="manager"):
        session.flash = "Forbidden"
        return redirect(URL('default','index'))
    
    form = DIV(
        _generate_all_form(article)
    )

    done_button = BUTTON(current.T("Back"), _class="btn btn-default", _onclick="window.history.back();", _style="margin: auto")

    response.view = 'default/myLayout.html'
    return dict(
            form=form,
            myBackButton=common_small_html.mkBackButton(),
            myFinalScript=common_tools.get_script("article_translations.js"),
            pageTitle="Translations",
            confirmationScript = common_small_html.confirmationDialog('Are you sure?'),
            myAcceptBtn=done_button)


@auth.requires_login()
def add_or_edit_article_fields_translations():
    article_id = int(request.vars["article_id"])
    lang = Lang.get_lang_by_code(request.vars["lang"])
    action = AddNewLanguageAction(request.vars["action"])
    title = str(request.vars["title"] or '')
    abstract = str(request.vars["abstract"] or '')
    keywords = str(request.vars["keywords"] or '')
    public = bool(request.vars["public"])

    article = Article.get_by_id(db, article_id)
    if not article:
        response.flash = "Article not found"
        return

    title_value = _add_or_edit_field_translation(article, TranslatedFieldType.TITLE, lang, action, title, public)
    abstract_value = _add_or_edit_field_translation(article, TranslatedFieldType.ABSTRACT, lang, action, abstract, public)
    keywords_value = _add_or_edit_field_translation(article, TranslatedFieldType.KEYWORDS, lang, action, keywords, public)

    title_new_value = Article.get_translation(article, TranslatedFieldType.TITLE, lang)
    abstract_new_value = Article.get_translation(article, TranslatedFieldType.ABSTRACT, lang)
    keywords_new_value = Article.get_translation(article, TranslatedFieldType.KEYWORDS, lang)

    if title_new_value and abstract_new_value and keywords_new_value:
        if not title_new_value['automated'] or not abstract_new_value['automated'] or not keywords_new_value['automated']:
            if title_new_value['automated']:
                title_new_value['automated'] = False
                Article.add_or_update_translation(article, TranslatedFieldType.TITLE, title_new_value)
            if abstract_new_value['automated']:
                abstract_new_value['automated'] = False
                Article.add_or_update_translation(article, TranslatedFieldType.ABSTRACT, abstract_new_value)
            if keywords_new_value['automated']:
                keywords_new_value['automated'] = False
                Article.add_or_update_translation(article, TranslatedFieldType.KEYWORDS, keywords_new_value)

    if title_value or abstract_value or keywords_value:
        return _generate_all_field_lang_form(article, lang)


@auth.requires_login()
def add_or_edit_article_field_translation():
    article_id = int(request.vars["article_id"])
    translated_field = TranslatedFieldType(request.vars["field"])
    lang = Lang.get_lang_by_code(request.vars["lang"])
    action = AddNewLanguageAction(request.vars["action"])
    translation = str(request.vars["translation"] or '')
    public = bool(request.vars["public"])

    article = Article.get_by_id(db, article_id)
    if not article:
        response.flash = "Article not found"
        return

    translation_value = _add_or_edit_field_translation(article, translated_field, lang, action, translation, public)

    if translation_value:
        is_textarea = translated_field == TranslatedFieldType.ABSTRACT
        return _generate_lang_form(article, translated_field, translation_value, is_textarea)


def _add_or_edit_field_translation(article: Article, translated_field: TranslatedFieldType, lang: Lang, action: 'AddNewLanguageAction', translation: str, public: bool):
    if not translated_field:
        response.flash = "Translated field not found"
        return

    if article.user_id != auth.user_id and not auth.has_membership(role="manager"):
        response.flash = "Forbidden"
        return
    
    existing_translation = Article.get_translation(article, translated_field, lang)
    exists_translation = existing_translation != None

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
        
        if exists_translation:
            old_content = html.unescape(existing_translation["content"])
            new_content = html.unescape(translation)
            automated = AddNewLanguageAction.CHECK != action and old_content == new_content
        else:
            automated = False
        
        new_translation: TranslatedFieldDict = {
            'automated': automated,
            'content': translation,
            'lang': lang.value.code,
            'public': public
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

    return translation_value


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


def delete_all_translation():
    article_id = int(request.vars["article_id"])
    lang = Lang.get_lang_by_code(request.vars["lang"])

    article = Article.get_by_id(db, article_id)
    if not article:
        response.flash = "Article not found"
        return
    
    if article.user_id != auth.user_id and not auth.has_membership(role="manager"):
        response.flash = "Forbidden"
        return
    
    Article.delete_translation(article, TranslatedFieldType.TITLE, lang)
    Article.delete_translation(article, TranslatedFieldType.ABSTRACT, lang)
    Article.delete_translation(article, TranslatedFieldType.KEYWORDS, lang)
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


def _generate_all_form(article: Article):
    form: List[DIV] = []
    english_field_title = TranslatedFieldType.get_corresponding_english_field(TranslatedFieldType.TITLE)
    english_field_abstract = TranslatedFieldType.get_corresponding_english_field(TranslatedFieldType.ABSTRACT)
    english_field_keywords = TranslatedFieldType.get_corresponding_english_field(TranslatedFieldType.KEYWORDS)

    form.append(_generate_english_form(article, english_field_title, False, TranslatedFieldType.TITLE, True))
    form.append(_generate_english_form(article, english_field_abstract, True, TranslatedFieldType.ABSTRACT, False))
    form.append(_generate_english_form(article, english_field_keywords, False, TranslatedFieldType.KEYWORDS, False))
    form.append(HR())

    form.append(_generate_lang_selector_all_field(article))
    form.append(HR())

    lang_form: List[FORM] = []
    abstract_translations = Article.get_all_translations(article, TranslatedFieldType.ABSTRACT)
    if abstract_translations:
        for abstract_translation in abstract_translations:
            lang = Lang.get_lang_by_code(abstract_translation["lang"])
            fields = _generate_all_field_lang_form(article, lang)
            if fields:
                lang_form.append(fields)
    
    form.append(DIV(*lang_form, _id="lang-form-list"))
    return DIV(*form)
    

def _generate_lang_selector_all_field(article: Article):
    url_generate = cast(str,
               URL(c="article_translations",
                   f="add_or_edit_article_fields_translations",
                   vars=dict(article_id=article.id, action=AddNewLanguageAction.GENERATE.value),
                   user_signature=True,
                   host=host,
                   scheme=scheme,
                   port=port)
               )

    url_write = cast(str,
               URL(c="article_translations",
                   f="add_or_edit_article_fields_translations",
                   vars=dict(article_id=article.id, action=AddNewLanguageAction.WRITE.value),
                   user_signature=True,
                   host=host,
                   scheme=scheme,
                   port=port)
               )
    
    return FORM(
        LABEL('Add translation', _class="control-label col-sm-3", _for="lang-selector", _style="font-size: 17px"),
        DIV(
            _get_lang_select_input(),
            BUTTON("Write", _id="write-translation", _class="btn btn-default", _disabled=True),
            BUTTON("Generate", _id="generate-translation", _class="btn btn-success", _link=url_generate, _disabled=True),
            DIV(
                LABEL(TranslatedFieldType.get_corresponding_english_field(TranslatedFieldType.TITLE).capitalize(), _class="control-label", _for="title-new-translation"),
                INPUT(_id="title-new-translation", _type='text', _class="string form-control", _name="title-new-translation"),
                LABEL(TranslatedFieldType.get_corresponding_english_field(TranslatedFieldType.ABSTRACT).capitalize(), _class="control-label", _for="abstract-new-translation"),
                TEXTAREA(_id="abstract-new-translation", _class="form-control text", _name="abstract-new-translation"),
                LABEL(TranslatedFieldType.get_corresponding_english_field(TranslatedFieldType.KEYWORDS).capitalize(), _class="control-label", _for="keywords-new-translation"),
                INPUT(_id="keywords-new-translation", _type='text', _class="string form-control", _name="keywords-new-translation"),
                BUTTON("Save", _id="save-all-translation", _class="btn btn-primary", _disabled=True, _link=url_write),
                _id="write-tranlation-block", _style="display: none"
            ),
            _class="col-sm-9"
        ),
        _class="form-group")


def _generate_lang_selector(article: Article, translated_field: TranslatedFieldType, is_textarea: bool):
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
            _get_lang_select_input(),
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


def _get_lang_select_input():
    lang_list = [lang.value for lang in Lang if lang != DEFAULT_LANG]
    lang_list = sorted(lang_list, key=lambda lang: lang.english_name)

    lang_generation_supported = [lang.value for lang in Translator.get_all_supported_langs()]
    lang_options: List[OPTION] = [OPTION('')]
    for lang in lang_list:
        if lang in lang_generation_supported:
            lang_options.append(OPTION(_build_lang_name(lang) + ' - Generation supported', _value=lang.code))
        else:
            lang_options.append(OPTION(_build_lang_name(lang), _value=lang.code))

    return SELECT(lang_options, _id="lang-selector", _class="generic-widget form-control")


def _build_lang_name(lang: LangItem):
    lang_name = lang.english_name
    if lang.name:
        lang_name += f" ({lang.name})"
    return lang_name


def _generate_all_field_lang_form(article: Article, lang: Lang):
    title = Article.get_translation(article, TranslatedFieldType.TITLE, lang)
    abstract = Article.get_translation(article, TranslatedFieldType.ABSTRACT, lang)
    keywords = Article.get_translation(article, TranslatedFieldType.KEYWORDS, lang)

    if not abstract:
        return
    
    title_content = title['content'] if title else ''
    abstract_content = abstract['content'] if abstract else ''
    keywords_content = keywords['content'] if keywords else ''

    inputs: List[DIV] = []
    inputs.append(LABEL(TranslatedFieldType.get_corresponding_english_field(TranslatedFieldType.TITLE).capitalize(), _for=f"title-{lang.value.code}", _class="control-label"))
    inputs.append(INPUT(_id=f"title-{lang.value.code}", _value=title_content, _type='text', _class="string form-control", _name=f"title-{lang.value.code}"))
    inputs.append(LABEL(TranslatedFieldType.get_corresponding_english_field(TranslatedFieldType.ABSTRACT).capitalize(), _for=f"title-{lang.value.code}", _class="control-label"))
    inputs.append(TEXTAREA(abstract_content, _id=f"abstract-{lang.value.code}", _class="form-control text", _name=f"abstract-{lang.value.code}"))
    inputs.append(LABEL(TranslatedFieldType.get_corresponding_english_field(TranslatedFieldType.KEYWORDS).capitalize(), _for=f"title-{lang.value.code}", _class="control-label"))
    inputs.append(INPUT(_id=f"keywords-{lang.value.code}", _value=keywords_content, _type='text', _class="string form-control", _name=f"keywords-{lang.value.code}"))

    save_url = cast(str,
                        URL(c="article_translations",
                            f="add_or_edit_article_fields_translations",
                            vars=dict(article_id=article.id, action=AddNewLanguageAction.WRITE.value, lang=lang.value.code),
                            user_signature=True,
                            host=host,
                            scheme=scheme,
                            port=port)
                    )
    
    check_url = cast(str,
                        URL(c="article_translations",
                            f="add_or_edit_article_fields_translations",
                            vars=dict(article_id=article.id, action=AddNewLanguageAction.CHECK.value, lang=lang.value.code),
                            user_signature=True,
                            host=host,
                            scheme=scheme,
                            port=port)
                    )
    
    delete_url = cast(str,
                        URL(c="article_translations",
                            f="delete_all_translation",
                            vars=dict(article_id=article.id, lang=lang.value.code),
                            user_signature=True,
                            host=host,
                            scheme=scheme,
                            port=port)
                    )
    
    checkbox = DIV(
        INPUT(_type="checkbox", _id=f"checkbox-public-{lang.value.code}", value=abstract['public']),
        LABEL("Show translation on recommendation page", _for=f"checkbox-show-{lang.value.code}"),
        _style="margin-top: 5px; margin-left: 2px"
    )

    buttons: List[DIV] = []
    buttons.append(checkbox)

    if abstract["automated"]:
        buttons.append(DIV(
            P("If is checked, the author endorse the responsibiblity of this translation and the following statement will be published with the translation \"This is an author verified version. The authors endorse the responsibility of its content.\""),
            P("Else the following statement will be displayed: \"This is a version automatically generated. The authors and PCI decline all responsibility concerning its content.\""),
            _class="well", _style="font-size: 13px; margin-bottom: 5px; margin-top: 10px"))
        buttons.append(A("Mark checked", _class="btn btn-success lang-form-save-all-button", _link=check_url))
    buttons.append(A("Save", _class="btn btn-primary lang-form-save-all-button", _link=save_url))
    buttons.append(A("Delete", _class="btn btn-danger lang-form-delete-all-button", _link=delete_url))

    return FORM(
                _generate_lang_label(lang, abstract),
                DIV(
                    *inputs,
                    *buttons,
                    HR(),
                    _class="col-sm-9"
                ),
                _class="form-group", _style="margin-bottom: 10px", _id=f"translation-{lang.value.code}"
            )


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
    
    check_url = cast(str,
                        URL(c="article_translations",
                            f="add_or_edit_article_field_translation",
                            vars=dict(article_id=article.id, field=translated_field.value, action=AddNewLanguageAction.CHECK.value, lang=lang.value.code, is_textarea=str(is_textarea).lower()),
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
    
    checkbox = DIV(
        INPUT(_type="checkbox", _id=f"checkbox-public-{lang.value.code}", value=translation_value['public']),
        LABEL("Show translation on recommendation page", _for=f"checkbox-show-{lang.value.code}"),
        _style="margin-top: 5px; margin-left: 2px"
    )

    buttons: List[DIV] = []
    buttons.append(checkbox)

    if translation_value["automated"] and translated_field == TranslatedFieldType.ABSTRACT:
        buttons.append(DIV(
            P("If is checked, the author endorse the responsibiblity of this translation and the following statement will be published with the translation \"This is an author verified version. The authors endorse the responsibility of its content.\""),
            P("Else the following statement will be displayed: \"This is a version automatically generated. The authors and PCI decline all responsibility concerning its content.\""),
            _class="well", _style="font-size: 13px; margin-bottom: 5px; margin-top: 10px"))
        buttons.append(A("Mark checked", _class="btn btn-success lang-form-save-button", _link=check_url))
    buttons.append(A("Save", _class="btn btn-primary lang-form-save-button", _link=save_url))
    buttons.append(A("Delete", _class="btn btn-danger lang-form-delete-button", _link=delete_url))

    return FORM(
                _generate_lang_label(lang, translation_value),
                DIV(
                    input,
                    *buttons,
                    HR(),
                    _class="col-sm-9"
                ),
                _class="form-group", _style="margin-bottom: 10px", _id=f"translation-{lang.value.code}"
            )


def _generate_english_form(article: Article, english_field: str, is_textarea: bool, id_prefix: Optional[TranslatedFieldType] = None, show_lang_label: bool = True):
    english_value = cast(str, getattr(article, english_field))
    lang_en = DEFAULT_LANG

    id = lang_en.value.code
    if id_prefix:
        id = f"{id_prefix.name.lower()}-{id}"

    if is_textarea:
        input = DIV(XML(english_value), _id=id, _name=id, _class="well", _style="margin-bottom: 0px")
    else:
        input = INPUT(_id=id, _value=english_value, _type='text', _class="string form-control", _name=id, _disabled=True)
    
    if show_lang_label:
        lang_label = LABEL(lang_en.value.english_name, _class="control-label col-sm-3", _for=id, _style="font-size: 17px")
    else:
        lang_label = ''        

    if id_prefix:
        field_label = LABEL(TranslatedFieldType.get_corresponding_english_field(id_prefix).capitalize(), _class="control-label")
    else:
        field_label = ''

    return FORM(
            lang_label,
            DIV(field_label,
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
        return LABEL(label_text, I('Automated translation', _style="color: #d9534f; margin-left: 5px"), _class=label_class, _for=label_for, _style=style)
    else:
        return LABEL(label_text, I('Author version', _style="color: #0275d8; margin-left: 5px"), _class=label_class, _for=label_for, _style=style)

class AddNewLanguageAction(Enum):
    WRITE = 'write'
    GENERATE = 'generate'
    CHECK = 'check'
