from configparser import ConfigParser
from os import path

from py4web.utils.auth import Auth
from py4web.utils.mailer import Mailer

from .modules.app_modules.coar_notify import COARNotifier
from .modules.app_modules.common_tools import takePort
from py4web import DAL, Session, Translator
from .settings import CONFIG_PATH, T_FOLDER, DEFAULT_DKIM_KEY_PATH

T = Translator(T_FOLDER)

config = ConfigParser()
config.read(CONFIG_PATH)

db = DAL(
    config.get("db", "uri"),
    pool_size=config.get("db", "pool_size"),
    migrate_enabled=config.getboolean("db", "migrate"),
    migrate=config.getboolean("db", "migrate"),
    check_reserved=["all"],
)

session = Session()

auth = Auth(session,
            db,
            use_username=False,
            login_expiration_time=10800,
            define_tables=True)

coar = COARNotifier()
is_rr = config.getboolean("config", "registered_reports", fallback=False)

appName = config.get("app", "name")
scheme = config.get("alerts", "scheme")
host = config.get("alerts", "host")
port = takePort(config.get("alerts", "port"))
pdf_max_size = config.getint("config", "pdf_max_size", fallback=10)
scheduledSubmissionActivated = config.getboolean("config", "scheduled_submissions", fallback=False)
postprint = config.getboolean("config", "postprint", fallback=False)

# # -------------------------------------------------------------------------
# # configure email
# # -------------------------------------------------------------------------
mail = Mailer(
server=config.get("smtp", "server"),
sender=config.get("smtp", "sender"),
login=config.get("smtp", "login"),
tls=config.getboolean("smtp", "tls", fallback=True),
ssl=config.getboolean("smtp", "ssl", fallback=False)
)

dkim_key_path = config.get("dkim", "key", fallback=DEFAULT_DKIM_KEY_PATH)
if path.exists(dkim_key_path):
    class dkim:
        key = open(dkim_key_path).read()
        selector = config.get("dkim", "selector", fallback="s1024")

    mail.settings.dkim = dkim
    mail.settings.list_unsubscribe = config.get("contacts", "contact")

auth.sender = mail
