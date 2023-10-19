# -*- coding: utf-8 -*-

from typing import Set, cast
from app_modules.coar_notify import COARNotifier
from app_modules.images import RESIZE
from pydal.validators import IS_IN_SET
from gluon.tools import Auth, Service, PluginManager, Mail
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Recaptcha2
from gluon.storage import Storage # for db.get_last_recomms()
from pydal.objects import OpRow
from pydal import Field

from gluon.custom_import import track_changes

track_changes(True)

from app_modules.helper import *

from app_modules import emailing
from app_modules import common_tools
from app_modules import common_small_html
from app_modules.country import Country
from app_modules.orcid import ORCID_NUMBER_FIELD_TYPE, ORCID_NUMBER_LENGTH_WITH_HYPHEN, OrcidValidator

from models.review import ReviewDuration, ReviewState, Review

from controller_modules import recommender_module


# -------------------------------------------------------------------------
# This scaffolding model makes your app work on Google App Engine too
# File is released under public domain and you can use without limitations
# -------------------------------------------------------------------------

if request.global_settings.web2py_version < "2.14.1":
    raise HTTP(500, "Requires web2py 2.13.3 or newer")

# -------------------------------------------------------------------------
# if SSL/HTTPS is properly configured and you want all HTTP requests to
# be redirected to HTTPS, uncomment the line below:
# -------------------------------------------------------------------------
# request.requires_https()

# -------------------------------------------------------------------------
# helper for redirects to / - usage: redirect(request.home)
request.home = URL("../..")

# -------------------------------------------------------------------------
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
myconf = AppConfig(reload=True)
appName = myconf.take("app.name")
scheme = myconf.take("alerts.scheme")
host = myconf.take("alerts.host")
port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
pdf_max_size = int(myconf.get("config.pdf_max_size", default=10))

scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)
pciRRactivated = myconf.get("config.registered_reports", default=False)

from os import symlink, path
def create_symlink(filename):
    base = current.request.folder
    target = base + "/languages/default.py"
    if not path.exists(target):
        symlink(filename, target)

if pciRRactivated:
    create_symlink("default_RR.py")
else:
    create_symlink("default_base.py")


if not request.env.web2py_runtime_gae:
    # ---------------------------------------------------------------------
    # if NOT running on Google App Engine use SQLite or other DB
    # ---------------------------------------------------------------------
    db = DAL(
        myconf.get("db.uri"),
        pool_size=myconf.get("db.pool_size"),
        migrate_enabled=myconf.get("db.migrate"),
        check_reserved=["all"],
        lazy_tables=True,
    )
else:
    # ---------------------------------------------------------------------
    # connect to Google BigTable (optional 'google:datastore://namespace')
    # ---------------------------------------------------------------------
    db = DAL("google:datastore+ndb")
    # ---------------------------------------------------------------------
    # store sessions and tickets there
    # ---------------------------------------------------------------------
    session.connect(request, response, db=db)
    # ---------------------------------------------------------------------
    # or store session in Memcache, Redis, etc.
    # from gluon.contrib.memdb import MEMDB
    # from google.appengine.api.memcache import Client
    # session.connect(request, response, db = MEMDB(Client()))
    # ---------------------------------------------------------------------


# ----------------------------- Configuration -----------------------------
db.define_table(
    "config",
    Field(
        "allow_submissions",
        type="boolean",
        default=True,
        label=T("Allow Submissions"),
    ),
    Field(
        "issn",
        type="string",
        label=T("This PCI's ISSN"),
    ),
    Field(
        "allowed_upload_filetypes",
        type="list:string",
        label=T("Allowed upload filetypes"),
    ),
)
cfg = db.config[1]

cfg.host = host.split(".")[0]

db.cfg = cfg
db.conf = myconf
# -------------------------------------------------------------------------
from app_modules import helper
helper.issn = cfg.issn
# -------------------------------------------------------------------------


allowed_upload_filetypes = ["pdf", "docx", "odt"]

if cfg.allowed_upload_filetypes:
    allowed_upload_filetypes = cfg.allowed_upload_filetypes
else:
    cfg.update_record(
        allowed_upload_filetypes=allowed_upload_filetypes)

allowed_review_filetypes = "pdf" if not pciRRactivated else allowed_upload_filetypes

upload_file_contraints = lambda extensions=allowed_upload_filetypes: [
        IS_LENGTH(pdf_max_size * 1048576, error_message="The file size is over " + str(pdf_max_size) + "MB."),
        IS_EMPTY_OR(IS_FILE(extension=extensions)),
]

email_options = {"Email to authors", "Email to reviewers"}
# -------------------------------------------------------------------------
# by default give a view/generic.extension to all actions from localhost
# none otherwise. a pattern can be 'controller/function.extension'
# -------------------------------------------------------------------------
response.generic_patterns = ["*"] if request.is_local else []
# -------------------------------------------------------------------------
# choose a style for forms
# -------------------------------------------------------------------------
response.formstyle = myconf.get("forms.formstyle")  # or 'bootstrap3_stacked' or 'bootstrap2' or other
response.form_label_separator = myconf.get("forms.separator") or ""

# -------------------------------------------------------------------------
# (optional) optimize handling of static files
# -------------------------------------------------------------------------
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'

# -------------------------------------------------------------------------
# (optional) static assets folder versioning
# -------------------------------------------------------------------------
# response.static_version = '0.0.0'

# -------------------------------------------------------------------------
# Here is sample code if you need for
# - email capabilities
# - authentication (registration, login, logout, ... )
# - authorization (role based authorization)
# - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
# - old style crud actions
# (more options discussed in gluon/tools.py)
# -------------------------------------------------------------------------

# host names must be a list of allowed host names (glob syntax allowed)
auth = Auth(db, host_names=myconf.get("host.names"))
service = Service()
plugins = PluginManager()

auth.settings.expiration = 10800  # 3h in seconds
auth.settings.host = host
# auth.settings.keep_session_onlogin=False
# auth.settings.logout_next = ''

# -------------------------------------------------------------------------
from gluon import current
current.auth = auth
current.db = db

# -------------------------------------------------------------------------
db.define_table(
    "t_thematics",
    Field("id", type="id"),
    Field("keyword", type="string", requires=IS_NOT_EMPTY(), label=T("Keyword")),
    format="%(keyword)s",
    singular=T("Keyword"),
    plural=T("Keywords"),
    migrate=False,
)


# -------------------------------------------------------------------------
# create all tables needed by auth if not custom tables
# -------------------------------------------------------------------------
auth.settings.extra_fields["auth_user"] = [
    Field("orcid", type=ORCID_NUMBER_FIELD_TYPE, label="ORCID number", requires=OrcidValidator(), maxlength=ORCID_NUMBER_LENGTH_WITH_HYPHEN),
    Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
    Field("picture_data", type="blob"),
    Field("laboratory", type="string", label=SPAN(T("Department")) + SPAN(" * ", _style="color:red;"), requires=IS_NOT_EMPTY()),
    Field("institution", type="string", label=SPAN(T("Institution")) + SPAN(" * ", _style="color:red;"), requires=IS_NOT_EMPTY()),
    Field("city", type="string", label=SPAN(T("City")) + SPAN(" * ", _style="color:red;"), requires=IS_NOT_EMPTY()),
    Field(
        "country",
        type="string",
        label=SPAN(T("Country")) + SPAN(" * ", _style="color:red;"),
        requires=IS_IN_SET([country.value for country in Country]),
        represent=lambda t, r: t if t else "",
    ),
    Field(
        "thematics",
        type="list:string",
        label=SPAN(T("Thematic fields")) + SPAN(" * ", _style="color:red;"),
        requires=[IS_IN_DB(db, db.t_thematics.keyword, "%(keyword)s", multiple=True), IS_NOT_EMPTY()],
        widget=SQLFORM.widgets.checkboxes.widget,
    ),
    Field("cv", type="text", length=2097152, label=SPAN(T("Areas of expertise")) + SPAN(" * ", _style="color:red;"), requires=IS_NOT_EMPTY()),
    Field("keywords", type="string", length=1024, label=SPAN(T("Keywords")) + SPAN(" * ", _style="color:red;"), requires=IS_NOT_EMPTY()),
    Field("email_options", type="list:string", label=SPAN(T("Opt in/out of being cc'ed")), 
          requires=[IS_EMPTY_OR(IS_IN_SET(email_options, multiple=True))], 
          widget=SQLFORM.widgets.checkboxes.widget, default=list(email_options)
    ),
    Field("website", type="string", length=4096, label=SPAN(T("Link to your website, profile page, google scholar profile or any other professional website")) + SPAN(" * ", _style="color:red;"), requires=IS_NOT_EMPTY()),
    Field(
        "alerts",
        type="string",
        label=DIV(
            SPAN(T("Do you wish to receive the PCI newsletter")) + SPAN(" * ", _style="color:red;"),
            BR(),
            SPAN(
                "if you are interested to act as recommender and/or as reviewer, we suggest you to receive the newletter once a week",
                _style="font-weight: normal; font-style: italic; color: #333",
            ),
        ),
        requires=IS_IN_SET(("Never", "Weekly", "Every two weeks", "Monthly"), zero=None),
        default="Weekly",
    ),
    Field("last_alert", type="datetime", label=T("Last alert"), writable=False, readable=False),
    Field("registration_datetime", type="datetime", default=request.now, label=T("Registration date & time"), writable=False, readable=False),
    Field(
        "ethical_code_approved",
        type="boolean",
        default=False,
        label=SPAN(
            SPAN(" * ", _style="color:red;"),
            SPAN(
                T("I agree to comply with the "),
                A(T("General Terms of Use"), _target="_blank", _href=URL("about", "gtu")),
                SPAN(" and the "),
                A(T("code of conduct"), _target="_blank", _href=URL("about", "ethics")),
            ),
        ),
        requires=IS_NOT_EMPTY(),
    ),
    Field("recover_email", label=T("Recover e-mail address"), unique=True, type="string", writable=False, readable=False),
    Field("recover_email_key", label=T("Recover e-mail key"), unique=True, type="string", writable=False, readable=False),
]
auth.define_tables(username=False, signature=False, migrate=False)
db.auth_user._singular = T("User")
db.auth_user._plural = T("Users")
db.auth_membership._singular = T("User role")
db.auth_membership._plural = T("User roles")
db.auth_user.first_name.label = SPAN(T("First name(s)")) + SPAN(" * ", _style="color:red;")
# db.auth_user.first_name.requires=IS_NOT_EMPTY()
db.auth_user.last_name.label = SPAN(T("Last name")) + SPAN(" * ", _style="color:red;")
# db.auth_user.last_name.requires=IS_NOT_EMPTY()
db.auth_user.email.label = SPAN(T("E-mail")) + SPAN(" * ", _style="color:red;")
# db.auth_user.email.requires=IS_NOT_EMPTY()
db.auth_user.registration_key.label = T("Registration key")
db.auth_user.registration_key.writable = db.auth_user.registration_key.readable = auth.has_membership(role="administrator")
db.auth_user.registration_key.requires = IS_IN_SET(("", "blocked"))
db.auth_user._format = "%(last_name)s, %(first_name)s"
db.auth_group._format = "%(role)s"
db.auth_user.password.label = SPAN(T("Password")) + SPAN(" * ", _style="color:red;")

def mail_queue_update_pending(sets, fields):
    old_email = cast(str, db.auth_user(sets.query).email)
    new_email = cast(str, fields.get('email'))

    if new_email and len(new_email) > 0 and old_email != new_email:
        db((db.mail_queue.dest_mail_address == old_email) & (db.mail_queue.sending_status == 'pending')).update(dest_mail_address=new_email)

db.auth_user._before_update.append(mail_queue_update_pending)

# -------------------------------------------------------------------------
# configure email
# -------------------------------------------------------------------------
mail = auth.settings.mailer
mail.settings.server = myconf.get("smtp.server")
# mail.settings.server = 'logging' if request.is_local else myconf.get('smtp.server')
mail.settings.sender = myconf.get("smtp.sender")
mail.settings.login = myconf.get("smtp.login")
mail.settings.tls = myconf.get("smtp.tls") or True
mail.settings.ssl = myconf.get("smtp.ssl") or False

default_dkim_key_path = "/var/www/peercommunityin/DKIM-peercommunityin.org.key"
dkim_key_path = myconf.get("dkim.key", default=default_dkim_key_path)
if path.exists(dkim_key_path):
    class dkim:
        key = open(dkim_key_path).read()
        selector = myconf.get("dkim.selector", default="s1024")

    mail.settings.dkim = dkim
    mail.settings.list_unsubscribe = myconf.take("contacts.contact")

# -------------------------------------------------------------------------
# configure auth policy
# -------------------------------------------------------------------------
auth.settings.registration_requires_verification = True  # WARNING set to True in production
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True  # WARNING set to True in production
auth.settings.create_user_groups = False
auth.settings.showid = False
if myconf.get("captcha.private"):
    # auth.settings.captcha = Recaptcha(request, myconf.get('captcha.public'), myconf.get('captcha.private'), use_ssl=True) # DEPRECATED
    try:
        auth.settings.captcha = Recaptcha2(request, myconf.get("captcha.public"), myconf.get("captcha.private"))
    except:
        pass
    auth.settings.login_captcha = False
    auth.settings.register_captcha = None
    auth.settings.retrieve_username_captcha = False
    auth.settings.retrieve_password_captcha = None
auth.messages.email_sent = "A request of confirmation has been sent to your e-mail address. Please confirm you e-mail address before trying to login."
auth.messages.verify_email_subject = "%s: validate your registration" % myconf.get("app.longname")
auth.messages.verify_email = (
    """
Welcome %(username)s! 

To complete your registration with the """
    + myconf.get("app.longname")
    + """ website, please click on the following link and enter your login and password:
%(link)s

Thanks for signing up!
Yours sincerely,
The Managing Board of """
    + myconf.get("app.longname")
    + """

"""
    + myconf.get("app.longname")
    + """ is one of the communities of the parent project Peer Community In... .
It is a community of researchers in """
    + myconf.get("app.thematics")
    + """ dedicated to both 1) the review and recommendation of preprints publicly available in preprint servers (such as bioRxiv) and 2) the recommendation of postprints published in traditional journals. 
This project was driven by a desire to establish a free, transparent and public recommendation system for reviewing and identifying remarkable articles. 
More information can be found on the website of """
    + myconf.get("app.longname")
    + """: """
    + URL(c="default", f="index", scheme=scheme, host=host, port=port)
)


# db.auth_user._after_insert.append(lambda f, id: newUser(f, id))
db.auth_user._before_update.append(lambda s, f: newRegistration(s, f))


def newRegistration(s, f):
    o = s.select().first()
    # handle missing "registration_key" on password reset and account not confirmed
    if "registration_key" not in f.keys():
        f["registration_key"] = ""
    if o.registration_key != "" and f["registration_key"] == "" and (o["recover_email_key"] is None or o["recover_email_key"] == ""):
        emailing.send_new_user(session, auth, db, o.id)
        emailing.send_admin_new_user(session, auth, db, o.id)
    return None


db.auth_membership._after_insert.append(lambda f, id: newMembership(f, id))


def newMembership(f, membershipId):
    emailing.send_new_membreship(session, auth, db, membershipId)


db.auth_user._after_insert.append(lambda f, i: insUserThumb(f, i))
db.auth_user._after_update.append(lambda s, f: updUserThumb(s, f))


def insUserThumb(f, i):
    common_small_html.makeUserThumbnail(auth, db, i, size=(150, 150))
    return None


def updUserThumb(s, f):
    o = s.select().first()
    common_small_html.makeUserThumbnail(auth, db, o.id, size=(150, 150))
    return None


appContactLink=A(myconf.take("contacts.managers"), _href="mailto:" + myconf.take("contacts.managers"))
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)


db.define_table(
    "help_texts",
    Field("id", type="id"),
    Field("hashtag", type="string", length=128, label=T("Hashtag"), default="#"),
    Field("lang", type="string", length=10, label=T("Language"), default="default"),
    Field("contents", type="text", length=1048576, label=T("Contents")),
    sequence_name='public.help_texts_id_seq',
    format="%(hashtag)s",
    migrate=False,
)


db.define_table(
    "t_status_article",
    Field("status", type="string", length=50, label=T("Status"), writable=False, requires=IS_NOT_EMPTY()),
    Field("color_class", type="string", length=50, default="default", requires=IS_NOT_EMPTY()),
    Field("explaination", type="text", label=T("Explaination")),
    Field("priority_level", type="text", length=1, requires=IS_IN_SET(("A", "B", "C"))),
    format="%(status)s",
    migrate=False,
)
# in-memory dict
statusArticles = dict()
for sa in db(db.t_status_article).select():
    statusArticles[sa["status"]] = T(sa["status"])

db.data_choices = (
    "None of the results are based on data",
    "All or part of the results presented in this preprint are based on data",
)

db.script_choices = (
    "No script (e.g. for statistical analysis, like R scripts) was used to obtain or analyze the results",
    "Scripts were used to obtain or analyze the results",
)

db.code_choices = (
    "No codes (e.g. codes for original programs or software) were used in this study",
    "Codes have been used in this study",
)

def widget(**kwargs):
    return lambda field, value, kwargs=kwargs: SQLFORM.widgets[field.type].widget(field, value, **kwargs)

db.define_table(
    "t_articles",
    Field("id", type="id"),
    Field("anonymous_submission", type="boolean", default=False, label=(
        T("I wish an anonymous submission (submitter concealed from reviewers)") if pciRRactivated else
        XML("I wish an anonymous submission (see " +
            "<a target='_blank' href='%s/guide_for_authors#h_7928466772121619502443551'>requirements</a>)" %
                URL(c="/..", f="help", scheme=scheme, host=host, port=port))
    )),
    Field("has_manager_in_authors", type="boolean", label=T("One or more authors of this article are members of the %s Managing Board" % appName), default=False),
    Field("title", type="string", length=1024, label=T("Title"), requires=[IS_NOT_EMPTY(), IS_LENGTH(1024, 0)], comment="use asterix (*) to get italics"),
    Field("authors", type="string", length=4096, label=T("Authors"), requires=[IS_NOT_EMPTY(), IS_LENGTH(4096, 0)], represent=lambda t, r: ("") if (r.anonymous_submission) else (t)),
    Field("article_year", type="integer", label=T("Year"), requires=IS_NOT_EMPTY()),
    Field("article_source", type="string", length=1024, label=T("Source (journal, year, volume, pages)"), requires=IS_EMPTY_OR(IS_LENGTH(1024, 0))),
    Field("doi", type="string", label=T("Most recent DOI (or URL)"), length=512, unique=False, represent=lambda text, row: common_small_html.mkDOI(text), requires=IS_EMPTY_OR(IS_URL(mode='generic',allowed_schemes=['http', 'https'],prepend_scheme='https')), comment=SPAN(T("URL must start with http:// or https://"), BR(), T("Note: for Stage 1 submissions, please make sure the link points exclusively to the manuscript file (and not to the broader project folder), and that any other links to supplementary materials, appendices, data, code, etc. are all within the manuscript file") if pciRRactivated else "")),
    Field("preprint_server", type="string", length=512, requires=[IS_NOT_EMPTY(), IS_LENGTH(512, 0)], label=
        T("Name of the server or open archive where your report has been deposited (eg OSF, Zenodo, arXiv, bioRxiv, HAL...)")
            if pciRRactivated else
        T("Name of the preprint server or open archive (eg bioRxiv, Zenodo, arXiv, HAL, OSF prepints...) where your preprint has been posted")
    ),
    Field("ms_version", type="string", length=1024, label=SPAN(T("Most recent version of the manuscript"), T(' (e.g. 1)')), default="",
        requires=[IS_NOT_EMPTY(), IS_INT_IN_RANGE(1, 101)] if not pciRRactivated else IS_NOT_EMPTY()),
    Field("picture_rights_ok",  widget=widget(_type="hidden") if not pciRRactivated else "",type="boolean", label=T("Picture right")),
    Field("uploaded_picture", type="upload", label=T("Picture"), requires=RESIZE(500,500) if pciRRactivated else [RESIZE(500,500), IS_NOT_EMPTY(error_message=T("Please upload a picture"))]),
    Field("abstract", type="text", length=2097152, label=T("Abstract"), requires=IS_NOT_EMPTY()),
    Field("results_based_on_data", type="string", label="", requires=IS_IN_SET(db.data_choices), widget=SQLFORM.widgets.radio.widget,),
    Field("data_doi", 
        type="list:string",
        requires=IS_LIST_OF(IS_EMPTY_OR(IS_URL(mode='generic',allowed_schemes=['http', 'https'],prepend_scheme='https'))),
        label=SPAN(T("Indicate the full web address (DOI or URL) giving public access to these data (if you have any problems with the deposit of your data, please contact "), appContactLink, ")"),
        length=512,
        comment=T("You should fill this box only if you chose 'All or part of the results presented in this preprint are based on data'. URL must start with http:// or https://")
    ),
    Field("scripts_used_for_result", type="string", label="", requires=IS_IN_SET(db.script_choices), widget=SQLFORM.widgets.radio.widget,),
    Field("scripts_doi", 
        type="list:string",
        requires=IS_LIST_OF(IS_EMPTY_OR(IS_URL(mode='generic',allowed_schemes=['http', 'https'],prepend_scheme='https'))),
        label=SPAN(T("Indicate the full web address (DOI or URL) giving public access to these scripts (if you have any problems with the deposit of your scripts, please contact "), appContactLink, ")"),
        length=512,
        comment=T("You should fill this box only if you chose 'Scripts were used to obtain or analyze the results'. URL must start with http:// or https://")
    ),
    Field("codes_used_in_study", type="string", label="", requires=IS_IN_SET(db.code_choices), widget=SQLFORM.widgets.radio.widget,),
    Field("codes_doi",
        type="list:string",
        requires=IS_LIST_OF(IS_EMPTY_OR(IS_URL(mode='generic',allowed_schemes=['http', 'https'],prepend_scheme='https'))),
        label=SPAN(T("Indicate the full web address (DOI, SWHID or URL) giving public access to these codes (if you have any problems with the deposit of your codes, please contact "), appContactLink, ")"),
        length=512,
        comment=T("You should fill this box only if you chose 'Codes have been used in this study'. URL must start with http:// or https://")
    ),
    Field("upload_timestamp", type="datetime", default=request.now, label=T("Submission date")),
    Field("is_scheduled", type="boolean", default=False, label=T("Is this a scheduled submission?"), readable=False, writable=False),
    Field("validation_timestamp", type="datetime", label=T("Validation date")),
    Field("user_id", type="reference auth_user", ondelete="RESTRICT", label=T("Submitter")),
    Field("status", type="string", length=50, default="Pending", label=T("Article status")),
    Field("last_status_change", type="datetime", default=request.now, label=T("Last status change")),
    Field("request_submission_change", type="boolean", default=False, label=T("Ask submitter to edit submission")),
    Field("funding", type="string", length=1024, label=T("Fundings"), requires=[IS_NOT_EMPTY(), IS_LENGTH(1024, 0)], comment="Indicate in this box the origin of the funding of your study. If your study has not been supported by particular funding, please indicate \"The authors declare that they have received no specific funding for this study\"."),
    Field("keywords", type="string", length=4096, label=T("Keywords"), requires=IS_EMPTY_OR(IS_LENGTH(4096, 0))),
    Field(
        "thematics",
        type="list:string",
        label=T("Thematic fields"),
        requires=[IS_IN_DB(db, db.t_thematics.keyword, "%(keyword)s", multiple=True), IS_NOT_EMPTY()],
        widget=SQLFORM.widgets.checkboxes.widget,
    ),
    Field("already_published", type="boolean", label=T("Postprint"), default=False),
    Field("doi_of_published_article", type="string", label=T("DOI of published article"), length=512, unique=False, represent=lambda text, row: common_small_html.mkDOI(text), requires=IS_EMPTY_OR(IS_URL(mode='generic',allowed_schemes=['http', 'https'],prepend_scheme='https')), comment=T("URL must start with http:// or https://")),
    Field(
        "cover_letter",
        type="text",
        length=2097152,
        label=T("Cover letter (for the initial submission only, not for resubmissions)") if not pciRRactivated else T("Cover letter"),
        writable=False,
        readable=False,
        comment=T("You can indicate anything you want in the box, but be aware that all recommenders, invited reviewers and reviewers will be able to read the cover letter."),
    ),
    Field(
        "suggest_reviewers",
        type="list:string",
        label=T("Suggested reviewers - Suggest up to 10 reviewers (provide names and Email addresses). (Optional)"),
        length=20000,
        comment=SPAN(
            T(" No need for them to be recommenders of %s. Please do not suggest reviewers for whom there might be a conflict of interest. Reviewers are not allowed to review preprints written by close colleagues (with whom they have published in the last four years, with whom they have received joint funding in the last four years, or with whom they are currently writing a manuscript, or submitting a grant proposal), or by family members, friends, or anyone for whom bias might affect the nature of the review - " % appName),
            A("see the code of conduct", _href="../about/ethics", _target="_blank"),
        ),
    ),
    Field(
        "competitors",
        type="list:string",
        label=T("Opposed reviewers - Suggest up to 5 people not to invite as reviewers. (Optional)"),
        length=20000,
        comment=SPAN(T("e.g. John Doe [john@doe.com]")),
    ),
    Field(
        "parallel_submission",
        type="boolean",
        label=T("Parallel submission"),
        default=False,
        writable=parallelSubmissionAllowed,
        readable=parallelSubmissionAllowed,
        represent=lambda p, r: SPAN("//", _class="pci-parallelSubmission") if p else "",
    ),
    Field("is_searching_reviewers", type="boolean", label=T("Open to reviewers"), default=False),
    # PCI RR
    Field("report_stage", type="string", label=T("Is this a Stage 1 or Stage 2 submission?"), requires=IS_EMPTY_OR(IS_IN_SET(("STAGE 1", "STAGE 2")))),
    Field("art_stage_1_id", type="reference t_articles", ondelete="CASCADE", label=T("Related stage 1 report")),
    Field("sub_thematics", requires=IS_EMPTY_OR(IS_LENGTH(512, 0)),length=512, type="string", label=T("Sub-field")),
    Field("record_url_version", requires=IS_EMPTY_OR(IS_LENGTH(512, 0)),length=512, type="string", label=T("Version of record URL (if different from above; e.g., if the VOR file is difficult to read but it is the version-tracked document showing track changes, or if the DOI refers to a whole repository rather than the file in it that is being submitted)")),
    Field("record_id_version", requires=IS_EMPTY_OR(IS_LENGTH(512, 0)),length=512, type="string", label=T("Version of record unique identifier (e.g., GitHub commit identifier)")),

    Field("scheduled_submission_date", type="date", label=T("Scheduled submission date"), requires=IS_EMPTY_OR(IS_DATE(format=T('%Y-%m-%d'), error_message='must be a valid date: YYYY-MM-DD'))),
    Field("auto_nb_recommendations", type="integer", label=T("Rounds of reviews")),
    Field("submitter_details", type="text", length=512, label=T("Article submitter"), readable=False, writable=False),
    format="%(title)s (%(authors)s)",
    singular=T("Article"),
    plural=T("Articles"),
    migrate=True,
)
db.t_articles.uploaded_picture.represent = lambda text, row: (IMG(_src=URL("static", "uploads", args=text), _width=100)) if (text is not None and text != "") else ("")
db.t_articles.authors.represent = lambda t, r: "[undisclosed]" if (r.anonymous_submission and r.status != "Recommended") else (t)
db.t_articles.upload_timestamp.writable = False
db.t_articles.last_status_change.writable = False
db.t_articles.auto_nb_recommendations.writable = False
db.t_articles.auto_nb_recommendations.readable = False
db.t_articles.user_id.requires = IS_EMPTY_OR(IS_IN_DB(db, db.auth_user.id, "%(last_name)s, %(first_name)s"))
db.t_articles.status.requires = IS_IN_SET(statusArticles)
db.t_articles._after_insert.append(lambda s, i: newArticle(s, i))
db.t_articles._before_update.append(lambda s, f: deltaStatus(s, f))


def deltaStatus(s, f):
    if "status" in f:
        o = s.select().first()
        recomm = db.get_last_recomm(o.id)

        if f.status == "Awaiting revision" and o.status != f.status:
            f.request_submission_change = True

        if o.already_published:  # POSTPRINTS
            if o.status != f["status"]:
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_recommender_postprint_status_changed(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])

        else:  # PREPRINTS
            if f.status in ["Cancelled", "Rejected", "Not considered"]:
                emailing.delete_all_reminders_from_article_id(db, o.id)

            if o.status == "Pending" and f["status"] == "Awaiting consideration":
                emailing.send_to_suggested_recommenders(session, auth, db, o["id"])
                emailing.send_to_submitter(session, auth, db, o["id"], f["status"], response=response)
                # create reminders
                emailing.create_reminder_for_submitter_new_suggested_recommender_needed(session, auth, db, o["id"])
                # emailing.create_reminder_for_submitter_cancel_submission(session, auth, db, o["id"])
                emailing.create_reminder_for_suggested_recommenders_invitation(session, auth, db, o["id"])
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])

            elif o.status == "Pre-submission" and f["status"] == "Pending":
                emailing.send_to_managers(session, auth, db, o["id"], "Resubmission")
                # create reminders
                emailing.create_reminder_for_submitter_suggested_recommender_needed(session, auth, db, o["id"])

            elif o.status == "Pending" and f["status"] == "Pre-submission":
                # delete reminders
                emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterSuggestedRecommenderNeeded", o["id"])
            
            elif o.status == "Pending" and f["status"] == "Not considered":
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])

            elif o.status == "Awaiting consideration" and f["status"] == "Not considered":
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])

            elif o.status == "Awaiting consideration" and f["status"] == "Under consideration":
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_submitter(session, auth, db, o["id"], f["status"], response=response)
                emailing.send_to_suggested_recommenders_not_needed_anymore(session, auth, db, o["id"])
                emailing.send_to_thank_recommender_preprint(session, auth, db, o["id"])
                # create reminders
                emailing.create_reminder_for_recommender_reviewers_needed(session, auth, db, o["id"])
                # delete reminders
                emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterSuggestedRecommenderNeeded", o["id"])
                emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterNewSuggestedRecommenderNeeded", o["id"])
                # emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterCancelSubmission", o["id"])
                emailing.delete_reminder_for_suggested_recommenders(db, "#ReminderSuggestedRecommenderInvitation", o["id"])

            elif o.status == "Awaiting revision" and f["status"] == "Under consideration":
                emailing.send_to_recommender_status_changed(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                # create reminders
                emailing.create_reminder_for_recommender_revised_decision_soon_due(session, auth, db, o["id"])
                emailing.create_reminder_for_recommender_revised_decision_due(session, auth, db, o["id"])
                emailing.create_reminder_for_recommender_revised_decision_over_due(session, auth, db, o["id"])
                # delete reminders
                emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterRevisedVersionWarning", o["id"])
                emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterRevisedVersionNeeded", o["id"])

            elif o.status == "Under consideration" and (f["status"].startswith("Pre-")):
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])
                emailing.send_to_recommender_status_changed(session, auth, db, o["id"], f["status"])
                # delete reminders
                emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderReviewersNeeded", o["id"])
                emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderDecisionSoonDue", o["id"])
                emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderDecisionDue", o["id"])
                emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderDecisionOverDue", o["id"])
                emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderRevisedDecisionSoonDue", o["id"])
                emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderRevisedDecisionDue", o["id"])
                emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderRevisedDecisionOverDue", o["id"])

            elif o.status in ("Pending", "Awaiting consideration", "Under consideration", "Scheduled submission pending", "Scheduled submission under consideration") and f["status"] == "Cancelled":
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_recommender_status_changed(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])
                emailing.send_to_reviewers_article_cancellation(session, auth, db, o["id"], f["status"])
                emailing.send_to_submitter(session, auth, db, o["id"], f["status"], response=response)

            elif o.status in ("Pending", "Awaiting consideration", "Under consideration") and f["status"] == "Scheduled submission pending":
                articleId = o.id
                emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterScheduledSubmissionSoonDue", articleId)
                emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterScheduledSubmissionDue", articleId)
                emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterScheduledSubmissionOverDue", articleId)
                emailing.send_to_recommender_preprint_submitted(session, auth, db, o["id"])
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])

            elif o.status == "Scheduled submission pending" and f["status"] == "Scheduled submission under consideration":
                emailing.send_to_recommender_preprint_validated(session, auth, db, o["id"])
                emailing.create_reminder_for_recommender_validated_scheduled_submission(session, auth, db, o["id"])
                emailing.create_reminder_for_recommender_validated_scheduled_submission_late(session, auth, db, o["id"])

            elif o.status == "Scheduled submission under consideration" and f["status"] == "Under consideration":
                emailing.send_to_reviewers_preprint_submitted(session, auth, db, o["id"])
                emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderPreprintValidatedScheduledSubmission", o["id"])
                emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderPreprintValidatedScheduledSubmissionLate", o["id"])

            elif o.status != f["status"]:
                if o["status"].startswith("Pre-") and f["status"] == "Under consideration": return
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_recommender_status_changed(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])
                
                if f["status"] == "Not considered":
                    emailing.send_to_submitter(session, auth, db, o["id"], f["status"], response=response)

                if f["status"] == "Rejected" and isScheduledTrack(o):
                    recommender_module.cancel_scheduled_reviews(session, auth, db, o["id"])

                if f["status"] in ("Awaiting revision", "Rejected", "Recommended", "Recommended-private"):
                    if not o.is_scheduled:
                        emailing.send_to_submitter(session, auth, db, o["id"], f["status"], response=response)
                    emailing.send_decision_to_reviewers(session, auth, db, o["id"], f["status"])
                    lastRecomm = db((db.t_recommendations.article_id == o.id) & (db.t_recommendations.is_closed == False)).select(db.t_recommendations.ALL)
                    for lr in lastRecomm:
                        lr.is_closed = True
                        lr.update_record()
                        # delete reminders
                        emailing.delete_all_reminders_from_recommendation_id(db, lr.id)

                if f["status"] in ("Recommended", "Recommended-private"):
                    # delete reminders
                    print("RECOMMENDED")
                    emailing.delete_all_reminders_from_article_id(db, o["id"])

                if o["status"] == "Pre-revision" and f["status"] == "Awaiting revision":
                    # create reminders
                    emailing.create_reminder_for_submitter_revised_version_warning(session, auth, db, o["id"])
                    emailing.create_reminder_for_submitter_revised_version_needed(session, auth, db, o["id"])
    return None


def newArticle(s, articleId):
    if s.status == "Pending-survey": # pciRRactivated only
        return

    if s.already_published is False:
        emailing.send_to_managers(session, auth, db, articleId, "Pending")
        emailing.send_to_submitter_acknowledgement_submission(session, auth, db, articleId)
        emailing.create_reminder_for_submitter_suggested_recommender_needed(session, auth, db, articleId)

    return None


db.define_table(
    "t_recommendations",
    Field("id", type="id"),
    Field("article_id", type="reference t_articles", ondelete="RESTRICT", label=T("Article")),
    Field("doi", type="string", length=512, label=T("Manuscript DOI (or URL) for the round"), represent=lambda text, row: common_small_html.mkDOI(text)),
    Field("ms_version", type="string", length=1024, label=T("Manuscript version for the round"), default=""),
    Field("recommender_id", type="reference auth_user", ondelete="RESTRICT", label=T("Recommender")),
    Field("recommendation_title", type="string", length=1024, label=T("Recommendation title"), comment="use asterix (*) to get italics"),
    Field("recommendation_comments", type="text", length=2097152, label=T("Recommendation"), default=""),
    Field("recommendation_doi", type="string", length=512, label=T("Recommendation DOI"), represent=lambda text, row: common_small_html.mkDOI(text)),
    Field(
        "recommendation_state",
        type="string",
        length=50,
        label=T("Recommendation state"),
        requires=IS_EMPTY_OR(IS_IN_SET(("Ongoing", "Recommended", "Rejected", "Revision", "Awaiting revision"))),
    ),
    Field("recommendation_timestamp", type="datetime", default=request.now, label=T("Recommendation start"), writable=False, requires=IS_NOT_EMPTY()),
    Field("validation_timestamp", type="datetime", label=T("Validation date")),
    Field("last_change", type="datetime", default=request.now, label=T("Last change"), writable=False),
    Field("is_closed", type="boolean", label=T("Closed"), default=False),
    Field("no_conflict_of_interest", type="boolean", label=T("I/we declare that I/we have no conflict of interest with the authors or the content of the article")),
    Field("reply", type="text", length=2097152, label=T("Author's Reply"), default=""),
    Field(
        "reply_pdf",
        type="upload",
        uploadfield="reply_pdf_data",
        label=T("Author's Reply as PDF"),
        requires=upload_file_contraints("pdf"),
    ),
    Field("reply_pdf_data", type="blob"),  # , readable=False),
    Field(
        "track_change",
        type="upload",
        uploadfield="track_change_data",
        label=T("Tracked changes document (eg. PDF or Word file)"),
        requires=upload_file_contraints(),
    ),
    Field("track_change_data", type="blob", readable=False),
    Field(
        "recommender_file",
        type="upload",
        uploadfield="recommender_file_data",
        label=T("Recommender's annotations (PDF)"),
        requires=upload_file_contraints(),
    ),
    Field("recommender_file_data", type="blob", readable=False),
    Field("recommender_details", type="text", length=512, label=T("Recommender details"), readable=False, writable=False),
    format=lambda row: recommender_module.mkRecommendationFormat(auth, db, row),
    singular=T("Recommendation"),
    plural=T("Recommendations"),
    migrate=False,
)
db.t_recommendations.recommender_id.requires = IS_IN_DB(
    db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == "recommender")),
    db.auth_user.id,
    "%(first_name)s %(last_name)s %(email)s",
)
db.t_recommendations._after_insert.append(lambda s, i: newRecommendation(s, i))
db.t_recommendations._before_update.append(lambda s, i: setRecommendationDoi(s, i))
db.t_recommendations._before_update.append(lambda s, i: recommendationUpdated(s, i)) \
        if COARNotifier(db).enabled else None

def get_last_recomm(articleId):
    return db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.id).last()

db.get_last_recomm = get_last_recomm

def newRecommendation(s, recomm):
    article = db.t_articles[recomm.article_id]
    if pciRRactivated:
        emailing.alert_managers_recommender_action_needed(session, auth, db, "#ManagersRecommenderAgreedAndNeedsToTakeAction", recomm.id)

    if article.already_published:
        emailing.send_to_thank_recommender_postprint(session, auth, db, recomm)

    if isScheduledTrack(article):
        # "send" future message as soon as we have a {{recommenderPerson}}
        emailing.send_to_submitter_scheduled_submission_open(auth, db, article)


def recommendationUpdated(s, updated_recommendation):
    original_recommendation = s.select().first()

    if not original_recommendation: return # on delete user

    if (
        not original_recommendation.is_closed
        and updated_recommendation.get('is_closed')
        and updated_recommendation.get('recommendation_state') == "Recommended"
    ):
        # COAR notification
        coar_notifier = COARNotifier(db)
        for review in db(
                (db.t_recommendations.article_id == original_recommendation.article_id)
              & (db.t_reviews.recommendation_id == db.t_recommendations.id)
              & (db.t_reviews.review_state == 'Review completed')
        ).select(db.t_reviews.ALL):
            coar_notifier.review_completed(review)
        coar_notifier.article_endorsed(updated_recommendation)


def setRecommendationDoi(s, _recomm):
    recomm = s.select().first()

    if not recomm: return # on delete user

    if pciRRactivated:
        emailing.delete_reminder_for_managers(db, ["#ManagersRecommenderAgreedAndNeedsToTakeAction", 
                                                   "#ManagersRecommenderReceivedAllReviewsNeedsToTakeAction"], recomm.id)
        if db.t_articles[recomm.article_id].report_stage != "STAGE 2":
            return

    if (not recomm.recommendation_doi
        or hasattr(_recomm, "recommendation_doi") and
        not _recomm.recommendation_doi
    ):
        _recomm.recommendation_doi = common_tools.generate_recommendation_doi(recomm.article_id)


def get_last_recomms():
    lastRecomms = db.executesql("""
        SELECT * FROM t_recommendations
        WHERE id in (SELECT max(id) FROM t_recommendations GROUP BY article_id)
        AND recommendation_state = 'Recommended'
        ;
    """, as_dict=True)
    return { recomm['article_id']: Storage(recomm) for recomm in lastRecomms }


db.get_last_recomms = get_last_recomms


db.pending_scheduled_submissions_query = (
    db.t_articles.status.belongs(("Scheduled submission pending",))
    & (db.t_articles.id == db.t_recommendations.article_id)
    & (db.t_recommendations.recommender_id == auth.user_id)
)


db.define_table(
    "t_pdf",
    Field("id", type="id"),
    Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field(
        "pdf", type="upload", uploadfield="pdf_data", label=T("PDF"), requires=upload_file_contraints()
    ),
    Field("pdf_data", type="blob"),
    singular=T("PDF file"),
    plural=T("PDF files"),
    migrate=False,
)

db.review_duration_choices = (ReviewDuration.TWO_WEEK.value, ReviewDuration.THREE_WEEK.value, ReviewDuration.FOUR_WEEK.value, ReviewDuration.FIVE_WEEK.value, ReviewDuration.SIX_WEEK.value, ReviewDuration.SEVEN_WEEK.value, ReviewDuration.EIGHT_WEEK.value)
db.review_duration_scheduled_track = ReviewDuration.FIVE_WORKING_DAY.value
db.review_duration_requires = IS_IN_SET(db.review_duration_choices
        + ((db.review_duration_scheduled_track,) if pciRRactivated else ())
)
db.review_duration_default = Review.get_default_review_duration()

db.define_table(
    "t_reviews",
    Field("id", type="id"),
    Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field("reviewer_id", type="reference auth_user", ondelete="RESTRICT", label=T("Reviewer")),
    Field("anonymously", type="boolean", label=T("Anonymously"), default=False),
    Field("anonymous_agreement", type="boolean", label=T('In the event that authors submit their article to a journal once recommended by PCI, I agree that my name may be passed on in confidence to that journal.')),
    Field("no_conflict_of_interest", type="boolean", label=T("I declare that I have no conflict of interest with the authors or the content of the article")),
    Field(
        "review_state",
        type="string",
        length=50,
        label=T("Review status"),
        requires=IS_EMPTY_OR(IS_IN_SET(("Awaiting response", "Awaiting review", "Willing to review", "Declined by recommender", "Declined", "Declined manually", "Review completed", "Cancelled"))),
        writable=False,
    ),
    Field("review_duration", type="text", label=T("Review duration"), default=db.review_duration_default, requires=db.review_duration_requires),
    Field("review", type="string", length=2097152, label=T("Review as text")),
    Field(
        "review_pdf",
        type="upload",
        uploadfield="review_pdf_data",
        label=T("AND/OR Upload review as PDF") if not pciRRactivated else (
                T("AND/OR Upload review document(s) (one or more ") +
                f"{', '.join(allowed_upload_filetypes)}). " +
                T("Multiple files can be selected for upload and will be downloadable all at once as a zip.")),
        requires=upload_file_contraints(allowed_review_filetypes),
    ),
    Field("review_pdf_data", type="blob", readable=False),
    Field("acceptation_timestamp", type="datetime", label=T("Acceptation timestamp"), writable=False),
    Field("last_change", type="datetime", default=request.now, label=T("Last change"), writable=False),
    Field("emailing", type="text", length=2097152, label=T("Emails sent"), readable=False, writable=False),
    Field("quick_decline_key", type="text", length=512, label=T("Quick decline key"), readable=False, writable=False),
    Field("reviewer_details", type="text", length=512, label=T("Reviewer details"), readable=False, writable=False),
    Field("suggested_reviewers_send", type="boolean", label=T("Suggested reviewers send")),
    Field("due_date", type="datetime", label=("Due date")),
    singular=T("Review"),
    plural=T("Reviews"),
    migrate=False,
)
db.t_reviews.reviewer_id.requires = IS_EMPTY_OR(IS_IN_DB(db, db.auth_user.id, "%(last_name)s, %(first_name)s"))
db.t_reviews.recommendation_id.requires = IS_IN_DB(db, db.t_recommendations.id, "%(doi)s")
db.t_reviews._before_update.append(lambda s, f: reviewDone(s, f))
db.t_reviews._before_update.append(lambda s, f: updateReviewerDetails(f))
db.t_reviews._after_insert.append(lambda s, row: reviewSuggested(s, row))
db.auth_user._before_delete.append(lambda s: setReviewerDetails(s.select().first()))
db.auth_user._before_delete.append(lambda s: setRecommenderDetails(s.select().first()))
db.auth_user._before_delete.append(lambda s: setArticleSubmitter(s.select().first()))
db.auth_user._before_delete.append(lambda s: setCoRecommenderDetails(s.select().first()))

def setReviewerDetails(user):
    db(db.t_reviews.reviewer_id == user.id).update(
        reviewer_details = common_small_html.mkUserWithMail(auth, db, user.id)
                                .flatten()
    )

def setRecommenderDetails(user):
    db(db.t_recommendations.recommender_id == user.id).update(
        recommender_details = common_small_html.mkUserWithMail(auth, db, user.id)
                                .flatten()
    )

def setArticleSubmitter(user):
    db(db.t_articles.user_id == user.id).update(
        submitter_details = common_small_html.mkUserWithMail(auth, db, user.id)
                                .flatten()
    )

def setCoRecommenderDetails(user):
    db(db.t_press_reviews.contributor_id == user.id).update(
        contributor_details = common_small_html.mkUserWithMail(auth, db, user.id)
                                .flatten()
    )

def updateReviewerDetails(row):
    if hasattr(row, "reviewer_id") and hasattr(row, "reviewer_details"):
        if row.reviewer_id and row.reviewer_details:
            row.reviewer_details = None


from app_modules.emailing import isScheduledTrack

def notify_submitter(review):
    recomm = db.t_recommendations[review.recommendation_id]
    article = db.t_articles[recomm.article_id]

    if pciRRactivated and isScheduledTrack(article):
        nb_reviews = recomm.t_reviews.count()
        if nb_reviews == 1:
            pass



def reviewSuggested(s, row):
    reviewId = row["id"]
    recommendationId = row["recommendation_id"]
    recomm = db.t_recommendations[recommendationId]
    article = db.t_articles[recomm.article_id]
    rev = db.t_reviews[reviewId]
    revwr = db.t_recommendations[rev.recommendation_id]

    notify_submitter(row)

    try:
        rev_recomm_mail = db.auth_user[revwr.recommender_id]["email"]
    except:
        rev_recomm_mail = None
    try:
        recomm_mail = db.auth_user[recomm.recommender_id]["email"]
    except:
        recomm_mail = None

    if rev_recomm_mail is not None:
        if row["review_state"] == "Willing to review":
            emailing.send_to_recommenders_pending_review_request(session, auth, db, row["id"])
        elif row["review_state"] == "Awaiting review":
            emailing.send_to_thank_reviewer_acceptation(session, auth, db, row["id"])
            emailing.send_to_admin_2_reviews_under_consideration(session, auth, db, row["id"], manual_insert=True)
            if isScheduledTrack(article):
                emailing.create_reminder_for_reviewer_scheduled_review_coming_soon(session, auth, db, row)
            # create reminder
            emailing.create_reminder_for_reviewer_review_soon_due(session, auth, db, row["id"])
            emailing.create_reminder_for_reviewer_review_due(session, auth, db, row["id"])
            emailing.create_reminder_for_reviewer_review_over_due(session, auth, db, row["id"])
        else:
            if recomm_mail is not None:
                # renew reminder
                emailing.delete_reminder_for_recommender(db, "#ReminderRecommenderNewReviewersNeeded", row["recommendation_id"], force_delete=True)
                emailing.create_reminder_for_recommender_new_reviewers_needed(session, auth, db, row["recommendation_id"])
                # delete reminder
                emailing.delete_reminder_for_recommender(db, "#ReminderRecommenderReviewersNeeded", row["recommendation_id"])
                emailing.delete_reminder_for_recommender(db, "#ReminderRecommenderRevisedDecisionSoonDue", row["recommendation_id"])
                emailing.delete_reminder_for_recommender(db, "#ReminderRecommenderRevisedDecisionDue", row["recommendation_id"])
                emailing.delete_reminder_for_recommender(db, "#ReminderRecommenderRevisedDecisionOverDue", row["recommendation_id"])
                if pciRRactivated:
                    emailing.delete_reminder_for_managers(db, ["#ManagersRecommenderAgreedAndNeedsToTakeAction"], row["recommendation_id"])
    return None


def reviewDone(s, f):
    if not hasattr(f, "review_state"): return

    o = cast(Review, s.select().first())
    reviewId = o["id"]
    rev = db.t_reviews[reviewId]
    recomm = db.t_recommendations[rev.recommendation_id]
    no_of_completed_reviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Review completed")).count()
    no_of_accepted_invites =  db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state.belongs("Awaiting review", "Review completed"))).count()
    last_recomm_reminder_mail = db((db.mail_queue.sending_status == "pending") & (db.mail_queue.recommendation_id == recomm.id)
    & (db.mail_queue.mail_template_hashtag == "#ReminderRecommender2ReviewsReceivedCouldMakeDecision")
    & (db.mail_queue.sending_date >= (request.now + timedelta(days=7)))).select().first()
    not_enough_reviewer_mail = db((db.mail_queue.sending_status == "pending") & (db.mail_queue.recommendation_id == recomm.id)
                                    & (db.mail_queue.mail_template_hashtag == "#ManagersRecommenderNotEnoughReviewersNeedsToTakeAction")).count()

    if f["review_state"] == "Review completed":
        no_of_completed_reviews += 1
    try:
        recomm_mail = db.auth_user[recomm.recommender_id]["email"]
    except:
        recomm_mail = None
    if recomm_mail is not None:
        if pciRRactivated:
            if no_of_accepted_invites < 2 and recomm.recommendation_state == "Ongoing" and not_enough_reviewer_mail == 0:
                emailing.alert_managers_recommender_action_needed(session, auth, db, "#ManagersRecommenderNotEnoughReviewersNeedsToTakeAction", recomm.id)
            elif no_of_accepted_invites >= 2:
                emailing.delete_reminder_for_managers(db, ["#ManagersRecommenderNotEnoughReviewersNeedsToTakeAction"], recomm.id)
            elif no_of_completed_reviews >= 2 and no_of_completed_reviews == no_of_accepted_invites and recomm.recommendation_state == "Ongoing":
                emailing.alert_managers_recommender_action_needed(session, auth, db, "#ManagersRecommenderReceivedAllReviewsNeedsToTakeAction", recomm.id)
                   
        if no_of_completed_reviews >= 2 and no_of_completed_reviews < no_of_accepted_invites and recomm.recommendation_state == "Ongoing" and last_recomm_reminder_mail is None:
            emailing.create_reminder_recommender_could_make_decision(session, auth, db, recomm.id)
        if o["review_state"] == "Awaiting review" and f['review_state'] in ["Cancelled", "Declined", "Declined manually"] and no_of_accepted_invites - no_of_completed_reviews == 1:
            emailing.delete_reminder_for_recommender(db, "#ReminderRecommender2ReviewsReceivedCouldMakeDecision", recomm.id)

        if o.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value and o.review_state != f["review_state"]:
            emailing.delete_reminder_for_recommender(db, "#ReminderRecommenderAcceptationReview", o.recommendation_id, review=o)

        if o.review_state == ReviewState.AWAITING_RESPONSE.value and f["review_state"] == ReviewState.NEED_EXTRA_REVIEW_TIME.value:
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewInvitationRegisteredUser"], o.id)
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerInvitationNewRoundRegisteredUser"], o.id)
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewInvitationNewUser"], o.id)
            
        if o.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value and f["review_state"] == ReviewState.AWAITING_REVIEW.value:
            emailing.create_reminder_for_reviewer_review_soon_due(session, auth, db, o["id"])
            emailing.create_reminder_for_reviewer_review_due(session, auth, db, o["id"])
            emailing.create_reminder_for_reviewer_review_over_due(session, auth, db, o["id"])

            emailing.delete_reminder_for_recommender(db, "#ReminderRecommenderNewReviewersNeeded", o.recommendation_id)
            emailing.send_to_admin_2_reviews_under_consideration(session, auth, db, o.id)

        if o["review_state"] in ["Awaiting response", "Cancelled", "Declined", "Declined manually"] and f["review_state"] == "Awaiting review":
            emailing.send_to_recommenders_review_considered(session, auth, db, o["id"])
            emailing.send_to_thank_reviewer_acceptation(session, auth, db, o["id"])
            emailing.send_to_admin_2_reviews_under_consideration(session, auth, db, o["id"])
            # create reminder
            emailing.create_reminder_for_reviewer_review_soon_due(session, auth, db, o["id"])
            emailing.create_reminder_for_reviewer_review_due(session, auth, db, o["id"])
            emailing.create_reminder_for_reviewer_review_over_due(session, auth, db, o["id"])

            if o["review_state"] == "Awaiting response":
                # delete reminder
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewInvitationNewUser"], o["id"])
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewInvitationRegisteredUser"], o["id"])
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerInvitationNewRoundRegisteredUser"], o["id"])
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewInvitationRegisteredUserReturningReviewer"], o["id"])
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewInvitationRegisteredUserNewReviewer"], o["id"])
                emailing.delete_reminder_for_recommender(db, "#ReminderRecommenderNewReviewersNeeded", o["recommendation_id"])

        elif o["review_state"] == "Willing to review" and f["review_state"] == "Awaiting review":
            emailing.send_to_reviewer_review_request_accepted(session, auth, db, o["id"], f)
            emailing.send_to_admin_2_reviews_under_consideration(session, auth, db, o["id"])
            # create reminder
            emailing.create_reminder_for_reviewer_review_soon_due(session, auth, db, o["id"])
            emailing.create_reminder_for_reviewer_review_due(session, auth, db, o["id"])
            emailing.create_reminder_for_reviewer_review_over_due(session, auth, db, o["id"])

        elif o["review_state"] == "Willing to review" and \
             f["review_state"] in [
                 "Declined by recommender",
                 "Declined manually",
                 "Cancelled",
                 "Declined",
             ]:
            if f["review_state"] == "Cancelled":
                emailing.create_cancellation_for_reviewer(session, auth, db, o["id"])
            emailing.send_to_reviewer_review_request_declined(session, auth, db, o["id"], f)

        elif o["review_state"] == "Review completed" and f["review_state"] == "Awaiting review":
            emailing.send_to_reviewer_review_reopened(session, auth, db, o["id"], f)


        elif o["review_state"] == "Awaiting response" and \
             f["review_state"] in [
                 "Declined by recommender",
                 "Declined manually",
                 "Cancelled",
                 "Declined",
             ]:
            if f["review_state"] == "Cancelled":
                emailing.create_cancellation_for_reviewer(session, auth, db, o["id"])
            if f["review_state"] == "Declined":
                emailing.send_to_recommenders_review_declined(session, auth, db, o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewInvitationNewUser"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewInvitationRegisteredUser"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerInvitationNewRoundRegisteredUser"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewInvitationRegisteredUserReturningReviewer"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewInvitationRegisteredUserNewReviewer"], o["id"])

        # remove reminders if review declined or canceled
        # irrespective of previous state
        # (was): elif o["review_state"] == "Awaiting review" and \
        elif \
             f["review_state"] in [
                 "Declined by recommender",
                 "Declined manually",
                 "Cancelled",
                 "Declined",
             ]:
            if f["review_state"] == "Cancelled":
                emailing.create_cancellation_for_reviewer(session, auth, db, o["id"])
            # delete reminder
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewSoonDue"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewDue"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewOverDue"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderScheduledReviewComingSoon"], o["id"])

        if o["reviewer_id"] is not None and o["review_state"] in ["Awaiting review", "Awaiting response"] and f["review_state"] == "Review completed":
            emailing.send_to_recommenders_review_completed(session, auth, db, o["id"])
            emailing.send_to_thank_reviewer_done(session, auth, db, o["id"], f)  # args: session, auth, db, reviewId, newForm
            emailing.send_to_admin_all_reviews_completed(session, auth, db, o["id"])
            # create reminder
            emailing.create_reminder_for_recommender_decision_soon_due(session, auth, db, o["id"])
            emailing.create_reminder_for_recommender_decision_due(session, auth, db, o["id"])
            emailing.create_reminder_for_recommender_decision_over_due(session, auth, db, o["id"])
            # delete reminder
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewSoonDue"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewDue"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewOverDue"], o["id"])
            emailing.delete_reminder_for_reviewer(db, ["#ReminderScheduledReviewComingSoon"], o["id"])

            if o["review_state"] == "Awaiting response":
                # delete reminder
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewInvitationNewUser"], o["id"])
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerReviewInvitationRegisteredUser"], o["id"])
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewerInvitationNewRoundRegisteredUser"], o["id"])
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewInvitationRegisteredUserReturningReviewer"], o["id"])
                emailing.delete_reminder_for_reviewer(db, ["#ReminderReviewInvitationRegisteredUserNewReviewer"], o["id"])
                emailing.delete_reminder_for_recommender(db, "#ReminderRecommenderNewReviewersNeeded", o["recommendation_id"])
        
        if no_of_completed_reviews >= 2 and o["review_state"] in ["Willing to review", "Awaiting response"] and f["review_state"] == "Awaiting review":
            emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderDecisionSoonDue", recomm["article_id"])
            emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderDecisionDue", recomm["article_id"])
            emailing.delete_reminder_for_recommender_from_article_id(db, "#ReminderRecommenderDecisionOverDue", recomm["article_id"])

    return None


db.define_table(
    "t_suggested_recommenders",
    Field("id", type="id"),
    Field("article_id", type="reference t_articles", ondelete="RESTRICT", label=T("Article")),
    Field("suggested_recommender_id", type="reference auth_user", ondelete="RESTRICT", label=T("Suggested recommender")),
    Field("email_sent", type="boolean", default=False, label=T("E-mail sent")),
    Field("declined", type="boolean", default=False, label=T("Declined")),
    Field("emailing", type="text", length=2097152, label=T("Emails history"), readable=False, writable=False),
    singular=T("Suggested recommender"),
    plural=T("Suggested recommenders"),
    migrate=False,
)
db.t_suggested_recommenders.suggested_recommender_id.requires = IS_EMPTY_OR(
    IS_IN_DB(
        db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == "recommender")),
        db.auth_user.id,
        "%(last_name)s, %(first_name)s",
    )
)

db.t_suggested_recommenders._after_insert.append(lambda f, i: appendSuggRecommender(f, i))
db.t_suggested_recommenders._before_delete.append(lambda s: deleteSuggRecommender(s))
db.t_suggested_recommenders._before_update.append(lambda s, f: declineSuggRecommender(s, f))


def appendSuggRecommender(f, i):
    a = db.t_articles[f.article_id]

    emailing.delete_reminder_for_submitter(db, "#ReminderSubmitterSuggestedRecommenderNeeded", a.id)
    # note: do NOT delete #ReminderSubmitterNewSuggestedRecommenderNeeded

    if a and a["status"] == "Awaiting consideration":
        # BUG : resend to all send to all
        emailing.send_to_suggested_recommender(session, auth, db, a["id"], f["suggested_recommender_id"])
        emailing.create_reminder_for_suggested_recommender_invitation(session, auth, db, a["id"], f["suggested_recommender_id"])


def deleteSuggRecommender(s):
    sugg_recomm = s.select().first()
    article = db.t_articles[sugg_recomm.article_id]
    emailing.delete_reminder_for_one_suggested_recommender(db, "#ReminderSuggestedRecommenderInvitation", article["id"], sugg_recomm["suggested_recommender_id"])


def declineSuggRecommender(s, f):
    o = s.select().first()
    sugg_recomm = o['suggested_recommender_id']
    article = o['article_id']
    o['declined'] = o['declined'] if 'declined' in o.keys() else False
    f['declined'] = f['declined'] if 'declined' in f.keys() else False
    if o['declined'] is False and f['declined'] is True:
        emailing.delete_reminder_for_one_suggested_recommender(db, "#ReminderSuggestedRecommenderInvitation", article, sugg_recomm)
    if o['declined'] is True and f['declined'] is False:
        emailing.create_reminder_for_suggested_recommender_invitation(session, auth, db, article, sugg_recomm)

db.define_table(
    "t_excluded_recommenders",
    Field("id", type="id"),
    Field("article_id", type="reference t_articles", ondelete="RESTRICT", label=T("Article")),
    Field("excluded_recommender_id", type="reference auth_user", ondelete="RESTRICT", label=T("Excluded recommender")),
    singular=T("Excluded recommender"),
    plural=T("Excluded recommenders"),
    migrate=False,
)
db.t_excluded_recommenders.excluded_recommender_id.requires = IS_EMPTY_OR(
    IS_IN_DB(
        db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == "recommender")),
        db.auth_user.id,
        "%(last_name)s, %(first_name)s",
    )
)

db.define_table(
    "t_press_reviews",
    Field("id", type="id"),
    Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field("contributor_id", type="reference auth_user", ondelete="RESTRICT", label=T("Contributor")),
    Field("contributor_details", type="text", length=512, label=T("Co-Recommender details"), readable=False, writable=False),
    singular=T("Co-recommendation"),
    plural=T("Co-recommendations"),
    migrate=False,
)
db.t_press_reviews.contributor_id.requires = IS_IN_DB(
    db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == "recommender")),
    db.auth_user.id,
    "%(last_name)s, %(first_name)s",
)
db.t_press_reviews.recommendation_id.requires = IS_IN_DB(db, db.t_recommendations.id, "%(doi)s")

# WARNING: not to be triggered at each new round
db.t_press_reviews._after_insert.append(lambda s, i: newPressReview(s, i))


def newPressReview(s, i):
    emailing.send_to_one_corecommender(session, auth, db, i)


db.t_press_reviews._before_delete.append(lambda s: delPressReview(s))


def delPressReview(s):
    pr = s.select().first()
    emailing.send_to_delete_one_corecommender(session, auth, db, pr.id)


db.define_table(
    "t_comments",
    Field("id", type="id"),
    Field("article_id", type="reference t_articles", ondelete="CASCADE", label=T("Article")),
    Field("parent_id", type="reference t_comments", ondelete="CASCADE", label=T("Reply to")),
    Field("user_id", type="reference auth_user", ondelete="RESTRICT", label=T("Author")),
    Field("user_comment", type="text", length=65536, label=T("Comment"), requires=IS_NOT_EMPTY()),
    Field("comment_datetime", type="datetime", default=request.now, label=T("Date & time"), writable=False),
    migrate=False,
    singular=T("Comment"),
    plural=T("Comments"),
    format=lambda row: row.user_comment[0:100],
)

db.define_table(
    "mail_templates",
    Field("id", type="id"),
    Field("hashtag", type="string", length=128, label=T("Hashtag"), default="#"),
    Field("lang", type="string", length=10, label=T("Language"), default="default"),
    Field("subject", type="string", length=256, label=T("Subject")),
    Field("contents", type="text", length=1048576, label=T("Contents")),
    Field("description", type="string", length=512, label=T("Description")),
    format="%(hashtag)s",
    migrate=False,
)

db.define_table(
    "mail_queue",
    Field("id", type="id"),
    Field("removed_from_queue", type="boolean", label=T("Unscheduled"), default=False),
    Field("sending_status", type="string", length=128, label=T("Sending status"), default="in queue"),
    Field("sending_attempts", type="integer", label=T("Sending attempts"), default=0),
    Field("sending_date", type="datetime", label=T("Sending date"), default=request.now),
    Field("dest_mail_address", type="string", label=T("Dest e-mail")),
    Field("cc_mail_addresses", type="list:string", label=T("CC e-mails")),
    Field("bcc_mail_addresses", type="list:string", label=T("BCC e-mails")),
    Field("replyto_addresses", type="list:string", label=T("Reply-to")),
    Field("mail_subject", type="string", length=256, label=T("Subject")),
    Field("mail_content", type="text", length=1048576, label=T("Contents")),
    Field("user_id", type="reference auth_user", ondelete="CASCADE", label=T("Sender")),
    Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field("article_id", type="reference t_articles", ondelete="CASCADE", label=T("Article")),
    Field("review_id", type="reference t_reviews", ondelete="CASCADE", label=T("Review")),
    Field("mail_template_hashtag", type="string", length=128, label=T("Template hashtag"), writable=False),
    Field("reminder_count", type="integer", label=T("Reminder count"), default=0),
    Field("sender_name", type="string", label=T("Sender name")),
    migrate=False,
)

db.define_table(
    "tweets",
    Field("id", type="id"),
    Field("post_id", type="integer"),
    Field("text_content", type="text"),
    Field("thread_position", type="integer"),
    Field("article_id", type="reference t_articles", ondelete="CASCADE", label=T("Article")),
    Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field("parent_id", type="reference tweets", ondelete="CASCADE", label=T("Tweet parent")),
)

db.define_table(
    "toots",
    Field("id", type="id"),
    Field("post_id", type="integer"),
    Field("text_content", type="text"),
    Field("thread_position", type="integer"),
    Field("article_id", type="reference t_articles", ondelete="CASCADE", label=T("Article")),
    Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field("parent_id", type="reference toots", ondelete="CASCADE", label=T("Toot parent")),
)

def _Field_CC(default):
    return Field(
            "cc",
            label=T("CC"),
            widget=SQLFORM.widgets.string.widget,
            type="list:string",
            length=250,
            #requires=IS_EMPTY_OR(IS_LIST_OF_EMAILS(error_message=T("invalid e-mail!"))),
            filter_in=lambda l: IS_LIST_OF_EMAILS.split_emails.findall(l[0]) if l else l,
            represent=lambda v, r: XML(', '.join([x.xml() for x in (v or [])])),
            default=default,
            writable=True,
        )

Field.CC = _Field_CC

##-------------------------------- PCI RR ---------------------------------
db.TOP_guidelines_choices = (
    "YES",
    "NO: LEGAL AND/OR ETHICAL RESTRICTIONS WILL PREVENT PUBLIC ARCHIVING OF AT LEAST SOME OF THE ABOVE [INSERT DETAILS]",
    "NO: BARRIERS OTHER THAN LEGAL OR ETHICAL RESTRICTIONS PREVENT ARCHIVING OF AT LEAST SOME OF THE ABOVE [INSERT DETAILS] -- Note: there is a risk of desk rejection in this case because the submission will likely fail to meet TOP guidelines",
)


db.define_table(
    "t_report_survey",
    # Field("stage_number", type="string", label=T("Is this a Stage 1 or Stage 2 submission?"), default=False, requires=IS_IN_SET(("STAGE 1", "STAGE 2"))),
    Field("article_id", type="reference t_articles", ondelete="CASCADE", label=T("Article")),
    Field(
        "q1",
        type="string", length=1024,
        label=T("1. Does the submission include a complete Stage 1 report for regular review or a Stage 1 RR snapshot for scheduled review?"),
        requires=IS_EMPTY_OR(IS_IN_SET(("COMPLETE STAGE 1 REPORT FOR REGULAR REVIEW", "RR SNAPSHOT FOR SCHEDULED REVIEW"))),
    ),
    Field(
        "q1_1",
        type="string",
        length=1024,
        label=T(
            "2. Enter the URL for the Stage 1 snapshot (if applicable)"
        ),
        requires=IS_EMPTY_OR(IS_LENGTH(1024, 0))
    ),
    Field(
        "q1_2",
        type="string",
        label=T(
            "3. Please indicate the status of your scheduled submission"
        ),
        requires=IS_EMPTY_OR(IS_IN_SET((
            "I AM SUBMITTING A STAGE 1 SNAPSHOT AND THE FULL MANUSCRIPT IS NOT YET READY FOR REVIEW",
            "I PREVIOUSLY SUBMITTED A STAGE 1 SNAPSHOT AND THE FULL MANUSCRIPT IS NOW READY FOR REVIEW"
        ))),
    ),
    Field(
        "q2",
        type="string",
        label=T(
            "4. Does the Stage 1 report or snapshot propose a regular RR that is intended to produce a single Stage 2 publication, or does it propose a programmatic RR that is intended to produce multiple Stage 2 publications?"
        ),
        requires=IS_EMPTY_OR(IS_IN_SET(("REGULAR RR", "PROGRAMMATIC RR"))),
    ),
    Field(
        "q3",
        type="string",
        label=T("5. Is the Stage 1 report or snapshot already published (e.g. at a repository) or is it currently being archived privately?"),
        requires=IS_EMPTY_OR(IS_IN_SET(("FULLY PUBLIC", "PRIVATE"))),
    ),
    Field(
        "q4",
        type="boolean",
        label=T("6. If submitting a RR snapshot, the authors confirm that they have used the PCI RR snapshot template and adhered to all requirements stated in the template"),
        default=False,
    ),
    # Field(
    #     "q5",
    #     type="string",
    #     length=2000,
    #     label=T(
    #         "5. Please provide an accessible URL to the Stage 1 report or Stage 1 snapshot. The link can be a private, view-only URL, but must not include any access restrictions (e.g. login barriers)"
    #     ),
    # ),
    # Need name
    Field(
        "q6",
        type="string",
        label=SPAN(
            T("7. If the authors are submitting a full Stage 1 report (rather than a Stage 1 snapshot), and the report describes at least one "),
            I(T("quantitative ")),
            T("study that tests hypotheses or predictions, please confirm that the report also contains a Study Design Template as outlined in "),
            A("Section 2.16 of the Guide to Authors. ", _href=URL(c="help", f="guide_for_authors#h_27513965735331613309625021"), _target="_blank"),
            T(
                "The inclusion of the Study Design Template is required for full Stage 1 reports that involve quantitative hypothesis-testing, and is optional (albeit strongly encouraged) for all other research modes."
            ),
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "YES - THE RESEARCH INVOLVES AT LEAST SOME QUANTITATIVE HYPOTHESIS-TESTING AND THE REPORT INCLUDES A STUDY DESIGN TEMPLATE",
                    "YES - EVEN THOUGH THE RESEARCH DOESN’T INVOLVE ANY QUANTITATIVE HYPOTHESIS-TESTING, THE REPORT NEVERTHELESS INCLUDES A STUDY DESIGN TEMPLATE",
                    "NO - THE REPORT DOES NOT INCLUDE ANY QUANTITATIVE STUDIES THAT TEST HYPOTHESES OR PREDICTIONS. NO STUDY DESIGN TEMPLATE IS INCLUDED.",
                    "N/A - THE SUBMISSION IS A STAGE 1 SNAPSHOT, NOT A STAGE 1 REPORT",
                )
            )
        ),
        widget=SQLFORM.widgets.radio.widget,
    ),
    Field(
        "q7",
        type="string",
        label=SPAN(
            T("8. Putting aside any preliminary results reported in the Stage 1 report, select which of the following scenarios applies to the data that will be the focus of the "),
            SPAN("proposed", _style="text-decoration: underline"),
            T(" research to be conducted "),
            SPAN("after", _style="text-decoration: underline"),
            T(" Stage 1 in-principle acceptance (IPA):"),
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "No part of the data or evidence that will be used to answer the research question yet exists and no part will be generated until after IPA [Level 6]",
                    "ALL of the data or evidence that will be used to answer the research question already exist, but are currently inaccessible to the authors and thus unobservable prior to IPA (e.g. held by a gatekeeper) [Level 5]",
                    "At least some of the data/evidence that will be used to answer the research question already exists AND is accessible in principle to the authors (e.g. residing in a public database or with a colleague), BUT the authors certify that they have not yet accessed any part of that data/evidence [Level 4]",
                    "At least some data/evidence that will be used to the answer the research question has been previously accessed by the authors (e.g. downloaded or otherwise received), but the authors certify that they have not yet observed ANY part of the data/evidence [Level 3]",
                    "At least some data/evidence that will be used to answer the research question has been accessed and partially observed by the authors, but the authors certify that they have not yet observed the key variables within the data that will be used to answer the research question AND they have taken additional steps to maximise bias control and rigour (e.g. conservative statistical threshold; recruitment of a blinded analyst; robustness testing, multiverse/specification analysis, or other approach) [Level 2]",
                    "At least some of the data/evidence that will be used to the answer the research question has been accessed and observed by the authors, including key variables, but the authors certify that they have not yet performed ANY of their preregistered analyses, and in addition they have taken stringent steps to reduce the risk of bias [Level 1]",
                    "At least some of the data/evidence that will be used to the answer the research question has been accessed and observed by the authors, including key variables, AND the authors have already conducted (and know the outcome of) at least some of their preregistered analyses [Level 0]",
                )
            )
        ),
        widget=SQLFORM.widgets.radio.widget,
    ),
    Field(
        "q8",
        type="string",
        length=1024,
        label=T(
            "9. Suggested reviewers. Suggest up to 5 reviewers that you recommend. In making these suggestions, the authors confirm that none of the authors have collaborated, published, or held joint research funding with any of these potential reviewers in the last 5 years."
        ),
        requires=IS_EMPTY_OR(IS_LENGTH(1024, 0))
    ),
    Field(
        "q9",
        type="string",
        length=1024,
        label=T(
            "10. Opposed reviewers. Choose up to 5 reviewers that you oppose. You do NOT need provide a reason for the opposition. PCI RR confirms that specifically-named opposed reviewers will not be invited to review the report or RR snapshot."
        ),
        requires=IS_EMPTY_OR(IS_LENGTH(1024, 0))
    ),
    Field(
        "q10",
        type="date",
        label=SPAN(
            T("11. ONLY for Stage 1 RR Snapshots submitted for Scheduled Review:"),
            BR(),
            T("Choose a "),
            SPAN("weekday no sooner than 6 weeks from today", _style="text-decoration: underline"),
            T(
                " by which the full manuscript will be submitted if the RR snapshot is invited to the next stage. Saturdays and Sundays are not eligible submission dates. Authors may submit their Stage 1 report no earlier than one week in advance of this date. Please note that (1) authors must submit the Stage 1 report for evaluation "
            ),
            SPAN("no later", _style="text-decoration: underline"),
            T(
                " than this date to preserve the timeline of scheduled review, and (2) where authors submit earlier than this date, the manuscript will probably not be reviewed earlier than scheduled. This deadline, once selected, cannot be extended and if authors fail to submit by the deadline, the scheduled review process will be cancelled."
            ),
        ),
        requires=IS_EMPTY_OR(IS_DATE(format=T('%Y-%m-%d'), error_message='must be a valid date: YYYY-MM-DD')),
    ),
    Field(
        "q11",
        type="string",
        label=T("12. Are all necessary approvals, such as ethics or regulatory permissions, in place for the proposed research?"),
        requires=IS_EMPTY_OR(IS_IN_SET(("YES", "NO - PROVIDE DETAILS"))),
    ),
    Field(
        "q11_details",
        type="text",
        label=T("12a. details"),
        length=2000,
    ),
    Field(
        "q12",
        type="string",
        label=T("13. Is all necessary support (e.g. funding, facilities) in place for the proposed research?"),
        requires=IS_EMPTY_OR(IS_IN_SET(("YES", "NO - PROVIDE DETAILS"))),
    ),
    Field(
        "q12_details",
        type="text",
        label=T("13a. details"),
        length=2000,
    ),
    Field(
        "q13",
        type="string",
        label=SPAN(
            SPAN(
                T(
                    "14. The TOP guidelines establish a series of modular standards for transparency and reproducibility in published research. Before completing next questions, authors should ensure that they are familiar with the "
                ),
                A("TOP policy requirements for PCI RR.", _href=URL("help", "top_guidelines"), _target="_blank"),
                _style="color: black",
            ),
            BR(),
            BR(),
            T(
                "The authors confirm that they will be able to make freely and publicly available ALL raw and processed data (anonymised where applicable), digital study materials, and analysis code that are necessary and sufficient to reproduce all data acquisition procedures, analyses, and data presentations in the Stage 2 manuscript."
            ),
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(db.TOP_guidelines_choices)
        ),
        widget=SQLFORM.widgets.radio.widget,
    ),
    Field(
        "q13_details",
        type="text",
        label=T("14a. details"),
        length=2000,
    ),
    Field(
        "q14",
        type="boolean",
        label=SPAN(
            T(
                "15. In the event of the submission achieving Stage 1 in-principle acceptance, the authors confirm that they agree to PCI RR registering the approved protocol on their behalf on the Open Science Framework (OSF) using OSF’s dedicated Stage 1 RR registration mechanism "
            ),
            A("https://osf.io/rr/", _href="https://osf.io/rr/", _target="_blank"),
            T(
                ". PCI RR will provide the corresponding author with the URL to this registered protocol in the Stage 1 in-principle acceptance letter, and authors must later include this URL in the Stage 2 manuscript. Note that PCI RR will register the protocol ONLY once the Stage 1 report is in-principle accepted, and not if it is rejected or withdrawn by authors prior to being awarded in-principle acceptance."
            ),
        ),
        default=False,
    ),
    Field(
        "q15",
        type="text",
        label=SPAN(
            T("16. For each author who currently has an account on the OSF ("),
            A("https://osf.io/", _href="https://osf.io/", _target="_blank"),
            T(
                "), in the text box below, please provide their name and the URL of their OSF home page. In the event of the Stage 1 report receiving in-principle acceptance, PCI RR will include these authors as contributors to the OSF registration. It is not required that all authors have an OSF account, but only authors with an OSF account will be included by PCI RR as contributors to the report on the OSF. At least ONE author must have an OSF account to ensure that the report is linked to at least one member of the authoring team. In the event of Stage 2 acceptance, authors without an OSF account will still be named as authors on the final article. List the names and URLs below in the following format, ensuring that each URL is live and valid."
            ),
        ),
        length=2000,
        default=T("[First name] [Surname], [URL]\n[First name] [Surname], [URL]\ne.g. John Doe, https://osf.io/pkm67/"),
    ),
    Field(
        "q16",
        type="string",
        label=T(
            "17. If the submission achieves Stage 1 in-principle acceptance, authors can instruct PCI RR to either make the registered Stage 1 manuscript immediately public on the OSF or instead register it under a private embargo for up to 4 years from the date of registration. If authors choose a private embargo, the embargo will be released and the registered protocol made public when any one of the following conditions are met: (a) submission of the Stage 2 manuscript for a regular RR, or the *FIRST* Stage 2 manuscript in a planned series of Stage 2 manuscripts linked to a programmatic RR; (b) withdrawal of the submission after in-principle acceptance and consequent triggering of a Withdrawn Registration; or (c) natural expiry of the embargo period. Please choose the authors’ preferred method of registration following Stage 1 in-principle acceptance."
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "MAKE PUBLIC IMMEDIATELY",
                    "UNDER PRIVATE EMBARGO",
                )
            )
        ),
    ),
    Field(
        "q17",
        type="string",
        label=T(
            "18. If choosing a private embargo please enter the duration of the embargo following in-principle acceptance. This can be specified either as a duration (e.g. “2 years”) or as a specific future date. The embargo period must be less than 4 years. Any entries that exceed this permissible maximum will be treated by PCI RR as “4 years”."
        ),
        length=128,
    ),
    Field(
        "q18",
        type="boolean",
        label=T(
            "19. The authors confirm that if they withdraw their report following Stage 1 in-principle acceptance then they agree to PCI RR (a) lifting any applicable private embargo on the registered Stage 1 protocol, thus making the protocol public on the OSF; and (b) publishing a short summary of the preregistered study, which will include the abstract of the Stage 1 submission, the URL of the registered Stage 1 protocol on the OSF, all Stage 1 reviews and decision letters, the PCI RR recommendation text, and a stated reason for the withdrawal."
        ),
        default=False,
    ),
    Field(
        "q19",
        type="boolean",
        label=T(
            "20. Should Stage 1 in-principle acceptance be forthcoming, authors will be asked to provide PCI RR with an estimated submission date for the completed Stage 2 manuscript (or manuscripts, in the case of programmatic RRs). This deadline can be readily altered in consultation with the recommenders (e.g. in case of delays requiring additional time to complete the research). However, in the event that the authors (a) fail to submit the Stage 2 manuscript within 6 months of the mutually agreed deadline, while also (b) becoming non-responsive during this period to enquiries from PCI RR, then the manuscript will be considered by PCI RR to be de facto withdrawn, triggering publication of a Withdrawn Registration. Please confirm the authors’ agreement to these conditions."
        ),
        default=False,
    ),
    Field(
        "q20",
        type="string",
        label=SPAN(
            T(
                "21. Should Stage 1 in-principle acceptance be forthcoming, would the authors like the current list of PCI RR-interested journals to be alerted? Doing so may (but is not guaranteed to) lead to one or more of these journals issuing an offer of Stage 1 in-principle acceptance. Answering YES to this question will result in PCI RR-interested journals having access to the author names, stated contact details, reviews and recommendation (if authors agree to publish this at the point of IPA -- see next question), and the URL to the Stage 1 report registered by PCI RR (even if preregistered under a private embargo). Authors must explicitly consent to permit PCI RR-interested journals to access this information, and PCI RR-interested journals are required to confirm that they will keep submissions confidential. Note that PCI RR-friendly journals will not be specifically alerted, and need not be, because PCI RR-friendly journals automatically offer IPA to any Stage 1 submission recommended by PCI RR without needing to inspect the content (subject to meeting any additional procedural requirements listed "
            ),
            A(T("here"), _href=URL("about", "pci_rr_friendly_journals"), _target="_blank"),
            T(")."),
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "YES - please alert PCI RR-interested journals in the event of IPA, as described above",
                    "NO",
                )
            )
        ),
    ),
    Field(
        "q21",
        type="string",
        label=T(
            "22. Should Stage 1 in-principle acceptance be forthcoming, would the authors prefer the Stage 1 recommendation and reviews to appear immediately on the PCI RR website along with a link to the Stage 1 report, or would they prefer to delay the publication of the Stage 1 recommendation and reviews until final Stage 2 acceptance (published all at once with the Stage 2 reviews)? This choice has no impact on automatic offers of publication by PCI RR-friendly journals, but electing to publish the Stage 1 reviews sooner may facilitate offers of IPA from PCI RR-interested journals due to the peer evaluations being accessible to those journal editors. Note that authors can exercise this choice regardless of whether they instruct PCI RR to register the Stage 1 manuscript publicly or under a private embargo. Where the authors choose to publish the Stage 1 reviews and recommendation at the point of IPA, but ALSO instruct PCI RR to register the report under a private embargo, then the URL to the Stage 1 report will still be published alongside the Stage 1 reviews and recommendation, but the Stage 1 report contained within the URL will be automatically accessible only to PCI RR, the authors, and the list of PCI RR-interested journals (if the authors answered YES to the previous question)."
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "PUBLISH STAGE 1 REVIEWS AT POINT OF IPA",
                    "PUBLISH STAGE 1 AND 2 REVIEWS TOGETHER FOLLOWING STAGE 2 ACCEPTANCE",
                )
            )
        ),
    ),
    Field(
        "q22",
        type="string",
        label=SPAN(
            T(
                "23. Would the authors like PCI RR to invite reviewers on the condition that the reviewers agree to waive anonymity and thereby sign their reviews? This option can be useful where the authors intend to eventually publish their RR in a PCI RR-friendly journal that requires reviews to be signed in order to automatically accept PCI RR recommendations (see "
            ),
            A("list of Journal Adopters", _href=URL("about", "pci_rr_friendly_journals"), _target="_blank"),
            T(
                "). Note that this choice will apply to both Stage 1 and (if applicable) Stage 2, and that applying this selection could increase the review time due to needing to recruit only reviewers who are willing to sign their reviews. Under the PCI RR open review policy, all reviews of accepted submissions are published, either signed or anonymous."
            ),
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "YES - ACCEPT SIGNED REVIEWS ONLY",
                    "NO - ACCEPT SIGNED AND ANONYMOUS REVIEWS",
                )
            )
        ),
    ),
    Field(
        "q23",
        type="string",
        label=T(
            "24. Please anticipate the approximate amount of time it will take to complete the research and submit a Stage 2 manuscript following Stage 1 in-principle acceptance. If the authors are submitting a programmatic RR then estimate this duration for each of the anticipated Stage 2 outputs (e.g. +12 months after IPA for Stage 2 RR.1, +18 months after IPA for Stage 2 RR.2, +24 months after IPA for Stage 2 RR.3, etc.)."
        ),
        length=128,
    ),
    Field(
        "q24",
        type="date",
        label=T(
            "25. Please enter the planned start date for the research (e.g. to commence data collection) and indicate whether this start date is flexible. If the date is not flexible, please explain the reasons for the lack of flexibility. If authors have an inflexible data collection start date and have not received in principle acceptance (IPA) before this date, they may begin collecting data but must adjust the bias-control level accordingly (e.g., if the initial submission was Level 6, it would then drop to Level 3, 2, or 1). There are several points to consider when dropping to a lower bias-control level. First, there is a greater risk of Stage 1 rejection if concerns with the study procedures raised in the Stage 1 review process can no longer be addressed due to data collection commencing and crucial parts of the methodology being immutable from that point forward. Second, the number of PCI RR-friendly journals that will automatically accept the Stage 2 RR may be reduced because adopting journals can set a minimum bias-control level that exceeds the requirements of PCI RR (for example, the submission would become ineligible for automatic acceptance in a PCI RR-friendly journal that sets a minimum requirement of Level 4 or higher). Third, as explained in the table, reducing the bias-control level increases the stringency of steps required to minimise bias and increase rigour (e.g., through the adoption of a more conservative statistical threshold, or blinded analyst, etc). Finally, it is essential that, despite the drop in bias-control level, the manuscript remains at Level 1 or higher: if authors begin to discover the conclusions (or likely conclusions) of the research prior to IPA then they would risk dropping to Level 0 and the manuscript would no longer be eligible for consideration at PCI RR."
        ),
        requires=IS_EMPTY_OR(IS_DATE(format=T('%Y-%m-%d'), error_message='must be a valid date: YYYY-MM-DD')),
    ),
    Field(
        "q24_1",
        type="string",
        label=T("25a. Date flexibility:"),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "FLEXIBLE",
                    "NOT FLEXIBLE",
                )
            )
        ),
    ),
    Field(
        "q24_1_details",
        type="text",
        label=T("25b. details"),
        length=2000,
    ),
    # Stage 2 questions
    Field("temp_art_stage_1_id", type="reference t_articles", ondelete="CASCADE", label=T("1. Please select the related stage 1 report:")),
    Field("tracked_changes_url",
        type="string",
        label=T("2. Please include below an accessible URL to the tracked-changes version of the Stage 2 manuscript, showing all textual changes between the current Stage 2 manuscript and the corresponding sections of the approved Stage 1 manuscript (e.g. Abstract, Introduction, Methods). All such differences, however minor must without exception be tracked. Please ensure that the tracked changes show both the addition and deletion of text (i.e. not just the final text but highlighted). This document will be shared with reviewers"),
        length=512, unique=False, represent=lambda text, row: common_small_html.mkDOI(text), comment=T("URL must start with http:// or https://")
    ),
    Field(
        "q25",
        type="boolean",
        label=T(
            "3. In addition to meeting conventional citation standards for published articles, where applicable, I confirm that any references to published data sets, software, program code, or other methods are cited in the manuscript."
        ),
        default=False,
    ),
    Field(
        "q26",
        type="string",
        label=SPAN(
            T("4. Have all raw and processed "),
            SPAN(T("study data"), _style="text-decoration: underline"),
            T(" that are necessary and sufficient to reproduce all analyses and data presentations been made freely and publicly available?"),
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    T("YES - All data are contained in manuscript"),
                    T(
                        "YES - Enter URL of the repository containing the data, ensuring that it contains sufficient README documentation to explain file definitions, file structures, and variable names (e.g. using a codebook)"
                    ),
                    T(
                        "NO - Please state the ethical or legal reasons why study data are not publicly archived and explain how the data supporting the reported results can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement."
                    ),
                )
            )
        ),
        widget=SQLFORM.widgets.radio.widget,
    ),
    Field(
        "q26_details",
        type="text",
        label=T("4a. details"),
        length=2000,
    ),
    Field(
        "q27",
        type="string",
        label=SPAN(
            T("5. Have all "),
            SPAN("digital materials", _style="text-decoration: underline"),
            T(
                " that are necessary and sufficient to reproduce all data acquisition procedures been made freely and publicly available? Such materials can include, but are not limited to, software code associated with data acquisition hardware, stimuli (e.g. images, videos), survey text, and digital or digitized questionnaires."
            ),
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "YES - All digital materials are contained in manuscript",
                    "YES - Enter URL of the repository containing the digital materials, ensuring that it contains sufficient README documentation to explain file definitions, file structures, and variable names (e.g. using a codebook)",
                    "NO - Please state the ethical or legal reasons why digital study materials are not publicly archived and explain how the materials can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement.",
                    "N/A - There are no digital study materials of any kind",
                )
            )
        ),
        widget=SQLFORM.widgets.radio.widget,
    ),
    Field(
        "q27_details",
        type="text",
        label=T("5a. details"),
        length=2000,
    ),
    Field(
        "q28",
        type="string",
        label=SPAN(
            T("6. Has all "),
            SPAN("analysis code", _style="text-decoration: underline"),
            T(" (where applicable) that would be necessary and sufficient to reproduce all data analyses been made freely and publicly available? "),
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "YES - All code is contained in manuscript",
                    "YES - Enter URL of the repository containing the analysis code/scripts",
                    "NO - Please state the ethical or legal reasons why analysis code is not publicly archived and explain how the materials can be obtained by readers. Please also confirm the page number in the manuscript that includes this statement.",
                    "N/A - No analysis code/scripts were used in any part of the data analysis",
                )
            )
        ),
        widget=SQLFORM.widgets.radio.widget,
    ),
    Field(
        "q28_details",
        type="text",
        label=T("6a. details"),
        length=2000,
    ),
    Field(
        "q29",
        type="boolean",
        label=T(
            '7. The authors confirm that the following statement is correct: "We report how we determined our sample size, all data exclusions (if any), all inclusion/exclusion criteria, whether inclusion/exclusion criteria were established prior to data analysis, all manipulations, and all measures in the study", elaborated as necessary in the main text.'
        ),
        default=False,
    ),
    Field(
        "q30",
        type="string",
        label=SPAN(
            T(
                "8. The Stage 2 manuscript must state the URL to the approved Stage 1 manuscript on the Open Science Framework (OSF). PCI RR registered the Stage 1 manuscript on behalf of the authors at the point of in-principle acceptance and provided the authors with the URL to this formal registration in the Stage 1 recommendation. If the authors are unable to find this URL then please contact the PCI RR Managing Board before proceeding further with the current submission."
            ),
            BR(),
            T(
                "Please insert the exact URL below and the page number where this URL is stated in the Stage 2 submission. If the authors elected for the accepted Stage 1 manuscript to be registered under a private embargo then please note that PCI RR will now release the embargo and make the protocol public before the Stage 2 manuscript is sent for in-depth review."
            ),
            BR(),
            T(
                "URL to the registered Stage 1 manuscript:"
            )
        ),
        length=512, unique=False, represent=lambda text, row: common_small_html.mkDOI(text), comment=T("URL must start with http:// or https://")
    ),
    Field(
        "q30_details",
        type="string",
        label=T("Page number in the Stage 2 manuscript where this URL is stated:"),
        length=256,
    ),
    Field(
        "q31",
        type="string",
        label=SPAN(
            T("9. If the authors are submitting a Stage 2 manuscript associated with a "),
            SPAN("programmatic", _style="text-decoration: underline"),
            T(
                " Stage 1 RR (in which multiple Stage 2 manuscripts are intended from a single Stage 1 report), please confirm that the Stage 2 manuscript includes a section that (a) states that the current manuscript is one part of this larger protocol; (b) cites all previously published Stage 2 manuscripts arising from the report, if any; and (c) notes which, if any, Stage 2 components arising from the protocol are either awaiting completion, have been rejected at Stage 2 by PCI RR, or have been formally withdrawn by the authors."
            ),
        ),
        requires=IS_EMPTY_OR(
            IS_IN_SET(
                (
                    "N/A - NOT A PROGRAMMATIC RR",
                    "CONFIRM",
                )
            )
        ),
    ),
    Field(
        "q32",
        type="boolean",
        label=T(
            "I agree to make my submission immediately viewable by PCI RR users in the \"Reports in need of reviewers\" section of the PCI RR website"
        ),
        default=False,
    ),
    migrate=False,
)


db.t_report_survey._after_update.append(lambda s, f: survey_updated(s.select().first()))

def survey_updated(survey):
    article = db.t_articles[survey.article_id]
    recomm = db.get_last_recomm(article.id)

    if not isScheduledTrack(article): return
    if not recomm: return

    # renew reminders and scheduled_submission_open "future" message
    # in case submission due date is changed by user

    for review in recomm.t_reviews.select():
        if not review.review_state == "Awaiting review": continue

        emailing.delete_reminder_for_reviewer(db, ["#ReminderScheduledReviewComingSoon"], review.id)
        emailing.create_reminder_for_reviewer_scheduled_review_coming_soon(session, auth, db, review)

    emailing.delete_reminder_for_submitter(db, "#SubmitterScheduledSubmissionOpen", article.id)
    emailing.send_to_submitter_scheduled_submission_open(auth, db, article)


from datetime import timedelta
db.full_upload_opening_offset = timedelta(weeks=1)


##---------------------- COAR Notify notifications -----------------------

db.define_table(
    "t_coar_notification",
    Field("id", type="id"),
    Field("created", type="datetime"),
    Field("rdf_type", type="string", label="Space-separated type URIs"),
    Field("body", type="string", label="JSON-LD serialization of notification body"),
    Field("direction", type="string", label="Inbound or Outbound"),
    Field("http_status", type="integer", label="HTTP Status for outboard messages"),
    Field("inbox_url", type="string", label="Remote inbox for notification"),
)


##-------------------------------- Views ---------------------------------

db.define_table(
    "v_article",
    db.t_articles,
    Field("submission_date", type="string", label=T("Submission date")),
    Field("recommender", type="string"),
    Field("reviewers", type="string"),
)

db.define_table(
    "v_article_id",
    Field("id", type="id"),
    Field("id_str", type="string"),
)

db.define_table(
    "v_last_recommendation",
    Field("id", type="id"),
    Field("last_recommendation", type="datetime", label=T("Last recommendation")),
    Field("days_since_last_recommendation", type="integer", label="Days since last recommendation"),
    # writable=False,
    migrate=False,
)

db.define_table(
    "v_suggested_recommenders",
    Field("id", type="id"),
    Field("suggested_recommenders", type="text", label=T("Suggested recommenders")),
    # writable=False,
    migrate=False,
)

db.define_table(
    "v_article_recommender",
    Field("id", type="id"),
    Field("recommender", type="text", label=T("Recommender")),
    Field("recommendation_id", type="id"),
    # writable=False,
    migrate=False,
)

db.define_table(
    "v_recommender_stats",
    Field("id", type="id", label=T("Recommender")),
    Field("total_invitations", type="text", label=T("Total invitations")),
    Field("total_accepted", type="text", label=T("Total accepted")),
    Field("total_completed", type="text", label=T("Total completed")),
    Field("current_invitations", type="text", label=T("Current invitations")),
    Field("current_assignments", type="text", label=T("Current assignments")),
    Field("awaiting_revision", type="text", label=T("Awaiting revision")),
    Field("requiring_action", type="text", label=T("Requiring action")),
    Field("requiring_reviewers", type="text", label=T("Requiring reviewers")),
    Field("required_reviews_completed", type="text", label=T("Required reviews completed")),
    Field("late_reviews", type="text", label=T("Late reviews")),
    Field("recommender_details", type="text", label=T("Recommender Details")),
    # writable=False,
    migrate=False,
)

db.define_table(
    "v_reviewers",
    Field("id", type="id"),
    Field("reviewers", type="text", label=T("Reviewers")),
    # writable=False,
    migrate=False,
)


db.define_table(
    "v_recommendation_contributors",
    Field("id", type="id"),
    Field("contributors", type="text", label=T("Co-recommenders")),
    # writable=False,
    migrate=False,
)


db.define_table(
    "v_roles",
    Field("id", type="id"),
    Field("roles", type="string", length=512, label=T("Roles")),
    # writable=False,
    migrate=False,
)

# -------------------------------------------------------------------------
# after defining tables, uncomment below to enable auditing
# -------------------------------------------------------------------------
# auth.enable_record_versioning(db)
