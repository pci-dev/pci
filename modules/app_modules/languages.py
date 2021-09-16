import gluon.languages
from gluon.cfs import getcfs
from gluon.languages import clear_cache, safe_eval
from pydal._compat import to_native
from pydal.contrib.portalocker import read_locked

"""
Divert web2py language files mechanism to use file default_RR.py
instead of the usual default.py, pretending it's still default.py

>>> use_language_file("default_RR.py")
"""

def _read_dict(filename, _filename):
    lang_text = read_locked(_filename).replace(b'\r\n', b'\n')
    clear_cache(filename)
    return safe_eval(to_native(lang_text)) or {}

def use_language_file(language_filename):
    def read_dict(filename):
        _filename = filename.replace("default.py", language_filename)
        return getcfs('lang:' + filename, _filename, lambda: _read_dict(filename, _filename))

    gluon.languages.read_dict = read_dict
