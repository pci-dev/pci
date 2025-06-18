import os
from py4web.core import required_folder

# mode (default or development)
MODE = os.environ.get("PY4WEB_MODE")

# db settings
APP_FOLDER = os.path.dirname(__file__)
APP_NAME = os.path.split(APP_FOLDER)[-1]

# location where static files are stored:
STATIC_FOLDER = str(required_folder(APP_FOLDER, "static"))

# location where to store uploaded files:
UPLOAD_FOLDER = str(required_folder(APP_FOLDER, "uploads"))

# logger settings
LOGGERS = [
    "warning:stdout"
]  # syntax "severity:filename:format" filename can be stderr or stdout

# i18n settings
T_FOLDER = str(required_folder(APP_FOLDER, "languages"))

CONFIG_FOLDER = str(required_folder(APP_FOLDER, "private"))
CONFIG_PATH = os.path.join(CONFIG_FOLDER, "appconfig.ini")

DEFAULT_DKIM_KEY_PATH = os.path.join("var", "www", "peercommunityin", "DKIM-peercommunityin.org.key")
