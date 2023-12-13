from deep_translator import GoogleTranslator

from app_modules.lang import Lang


class Translator:
    
    DEFAULT_TARGET_LANG = [
        Lang.FR,
        Lang.ES,
        Lang.HI,
        Lang.ZH_CN,
        Lang.AR
    ]

    _lang: Lang


    def __init__(self, lang: Lang):
        self._lang = lang


    def translate(self, text: str):
        google_translator = GoogleTranslator(Lang.EN.value.code, self._lang.value.code)
        
        if GoogleTranslator.is_language_supported(google_translator, self._lang.value.code):
            data_translated = google_translator.translate(text)
        else:
            raise Exception('Language not supported')

        if not data_translated:
            raise Exception('Traduction failed')
        
        return data_translated
