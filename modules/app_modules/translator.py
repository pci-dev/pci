from abc import ABCMeta
from typing import Any, Dict, List, Optional
from attr import dataclass
from deep_translator import GoogleTranslator
from deep_translator.base import BaseTranslator

from app_modules.lang import Lang

@dataclass
class TranslatorConfig:
    engine_class: ABCMeta
    params: Dict[str, Any]

class Translator:
    
    DEFAULT_TARGET_LANG = [
        Lang.FR,
        Lang.ES,
        Lang.HI,
        Lang.ZH_CN,
        Lang.AR
    ]

    @staticmethod
    def get_translation_config(source: Lang, target: Lang):
        # The first in the list will be the first used if it supports the language.
        return [
            TranslatorConfig(GoogleTranslator, dict(source=source.value.code, target=target.value.code)),
        ]
    

    def __init__(self, lang: Lang):
        self._lang = lang
        self._translators = self._init_translators(lang)

        if len(self._translators) == 0:
            raise Exception('Language not supported')


    def translate(self, text: str):
        data_translated: Optional[str] = None

        i = 0
        while i < len(self._translators) and data_translated == None:
            try:
                engine = self._translators[i]
                data_translated = engine.translate(text)
            except Exception as e:
                print(e)
                continue
            finally:
                i += 1

        if not data_translated:
            raise Exception('Traduction failed')
        
        return data_translated


    @staticmethod
    def _init_translators(lang: Lang):
        translation_config = Translator.get_translation_config(Lang.EN, lang)
        translators: List[BaseTranslator] = []

        for config in translation_config:
            engine_class = config.engine_class

            if not issubclass(engine_class, BaseTranslator):
                raise Exception(f"Configuration error for translator. {engine_class} is not subclass of BaseTranslator")
            
            try:
                translator = engine_class(**config.params)
                if translator.is_language_supported(lang.value.code) or translator.is_language_supported(lang.value.english_name.lower()):
                    translators.append(translator)
            except:
                pass

        return translators
    

    @staticmethod
    def get_all_supported_langs():
        translators = Translator._init_translators(Lang.EN)
        supported_langs: List[Lang] = []

        for lang in Lang:
            for translator in translators:
                if translator.is_language_supported(lang.value.code) or translator.is_language_supported(lang.value.english_name.lower()):
                    supported_langs.append(lang)
                    break
        
        return supported_langs
