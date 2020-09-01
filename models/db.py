# -*- coding: utf-8 -*-

# import pprint
# pp = pprint.PrettyPrinter(indent=4)

from gluon.tools import Auth, Service, PluginManager, Mail
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Recaptcha2

from gluon.custom_import import track_changes

track_changes(True)

from app_modules.helper import *

from app_modules import emailing
from app_modules import common_tools
from app_modules import common_small_html

from controller_modules import recommender_module

# def pprint(*args): print args

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
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
myconf = AppConfig(reload=True)
scheme = myconf.take("alerts.scheme")
host = myconf.take("alerts.host")
port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

pdf_max_size = int(myconf.take("config.pdf_max_size") or 5)


if not request.env.web2py_runtime_gae:
    # ---------------------------------------------------------------------
    # if NOT running on Google App Engine use SQLite or other DB
    # ---------------------------------------------------------------------
    db = DAL(myconf.get("db.uri"), pool_size=myconf.get("db.pool_size"), migrate_enabled=myconf.get("db.migrate"), check_reserved=["all"], lazy_tables=True,)
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
    Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
    Field("picture_data", type="blob"),
    Field("laboratory", type="string", label=SPAN(T("Department")) + SPAN(" * ", _style="color:red;"), requires=IS_NOT_EMPTY()),
    Field("institution", type="string", label=SPAN(T("Institution")) + SPAN(" * ", _style="color:red;"), requires=IS_NOT_EMPTY()),
    Field("city", type="string", label=SPAN(T("City")) + SPAN(" * ", _style="color:red;"), requires=IS_NOT_EMPTY()),
    Field(
        "country",
        type="string",
        label=SPAN(T("Country")) + SPAN(" * ", _style="color:red;"),
        requires=IS_IN_SET(
            (
                "Afghanistan",
                "Albania",
                "Algeria",
                "Andorra",
                "Angola",
                "Antigua and Barbuda",
                "Argentina",
                "Armenia",
                "Australia",
                "Austria",
                "Azerbaijan",
                "Bahamas",
                "Bahrain",
                "Bangladesh",
                "Barbados",
                "Belarus",
                "Belgium",
                "Belize",
                "Benin",
                "Bhutan",
                "Bolivia",
                "Bosnia and Herzegovina",
                "Botswana",
                "Brazil",
                "Brunei",
                "Bulgaria",
                "Burkina Faso",
                "Burundi",
                "Cambodia",
                "Cameroon",
                "Canada",
                "Cape Verde",
                "Central African Republic",
                "Chad",
                "Chile",
                "China",
                "Colombia",
                "Comoros",
                "Congo",
                "Costa Rica",
                "Côte d'Ivoire",
                "Croatia",
                "Cuba",
                "Cyprus",
                "Czech Republic",
                "Denmark",
                "Djibouti",
                "Dominica",
                "Dominican Republic",
                "East Timor",
                "Ecuador",
                "Egypt",
                "El Salvador",
                "Equatorial Guinea",
                "Eritrea",
                "Estonia",
                "Ethiopia",
                "Fiji",
                "Finland",
                "France",
                "Gabon",
                "Gambia",
                "Georgia",
                "Germany",
                "Ghana",
                "Greece",
                "Grenada",
                "Guatemala",
                "Guinea",
                "Guinea-Bissau",
                "Guyana",
                "Haiti",
                "Honduras",
                "Hong Kong",
                "Hungary",
                "Iceland",
                "India",
                "Indonesia",
                "Iran",
                "Iraq",
                "Ireland",
                "Israel",
                "Italy",
                "Jamaica",
                "Japan",
                "Jordan",
                "Kazakhstan",
                "Kenya",
                "Kiribati",
                "North Korea",
                "South Korea",
                "Kuwait",
                "Kyrgyzstan",
                "Laos",
                "Latvia",
                "Lebanon",
                "Lesotho",
                "Liberia",
                "Libya",
                "Liechtenstein",
                "Lithuania",
                "Luxembourg",
                "FYROM",
                "Madagascar",
                "Malawi",
                "Malaysia",
                "Maldives",
                "Mali",
                "Malta",
                "Marshall Islands",
                "Mauritania",
                "Mauritius",
                "Mexico",
                "Micronesia",
                "Moldova",
                "Monaco",
                "Mongolia",
                "Montenegro",
                "Morocco",
                "Mozambique",
                "Myanmar",
                "Namibia",
                "Nauru",
                "Nepal",
                "Netherlands",
                "New Zealand",
                "Nicaragua",
                "Niger",
                "Nigeria",
                "Norway",
                "Oman",
                "Pakistan",
                "Palau",
                "Palestine",
                "Panama",
                "Papua New Guinea",
                "Paraguay",
                "Peru",
                "Philippines",
                "Poland",
                "Portugal",
                "Puerto Rico",
                "Qatar",
                "Romania",
                "Russia",
                "Rwanda",
                "Saint Kitts and Nevis",
                "Saint Lucia",
                "Saint Vincent and the Grenadines",
                "Samoa",
                "San Marino",
                "Sao Tome and Principe",
                "Saudi Arabia",
                "Senegal",
                "Serbia and Montenegro",
                "Seychelles",
                "Sierra Leone",
                "Singapore",
                "Slovakia",
                "Slovenia",
                "Solomon Islands",
                "Somalia",
                "South Africa",
                "Spain",
                "Sri Lanka",
                "Sudan",
                "Suriname",
                "Swaziland",
                "Sweden",
                "Switzerland",
                "Syria",
                "Taiwan",
                "Tajikistan",
                "Tanzania",
                "Thailand",
                "Togo",
                "Tonga",
                "Trinidad and Tobago",
                "Tunisia",
                "Turkey",
                "Turkmenistan",
                "Tuvalu",
                "Uganda",
                "Ukraine",
                "United Arab Emirates",
                "United Kingdom",
                "United States of America",
                "Uruguay",
                "Uzbekistan",
                "Vanuatu",
                "Vatican City",
                "Venezuela",
                "Vietnam",
                "Yemen",
                "Zambia",
                "Zimbabwe",
            )
        ),
        represent=lambda t, r: t if t else "",
    ),
    Field(
        "thematics",
        type="list:string",
        label=SPAN(T("Thematic fields")) + SPAN(" * ", _style="color:red;"),
        requires=IS_IN_DB(db, db.t_thematics.keyword, "%(keyword)s", multiple=True),
        widget=SQLFORM.widgets.checkboxes.widget,
    ),
    Field("cv", type="text", length=2097152, label=T("Educational and work background")),
    Field(
        "alerts",
        type="list:string",
        label=T("Alert frequency"),
        requires=IS_EMPTY_OR(IS_IN_SET(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"), multiple=True)),
        widget=SQLFORM.widgets.checkboxes.widget,
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
    ),
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

# -------------------------------------------------------------------------
# configure email
# -------------------------------------------------------------------------
mail = auth.settings.mailer
mail.settings.server = myconf.get("smtp.server")
# mail.settings.server = 'logging' if request.is_local else myconf.get('smtp.server')
mail.settings.sender = myconf.get("smtp.sender")
mail.settings.login = myconf.get("smtp.login")
mail.settings.tls = myconf.get("smtp.tls") or False
mail.settings.ssl = myconf.get("smtp.ssl") or False

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
    auth.settings.captcha = Recaptcha2(request, myconf.get("captcha.public"), myconf.get("captcha.private"))
    auth.settings.login_captcha = False
    auth.settings.register_captcha = None
    auth.settings.retrieve_username_captcha = False
    auth.settings.retrieve_password_captcha = None
auth.messages.email_sent = "A request of confirmation has been sent to your email address. Please confirm you email address before trying to login."
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
    # BUG: missing key "registration_key" error occurs when password reset and account not confirmed
    if o.registration_key != "" and f["registration_key"] == "":
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


applongname = myconf.take("app.longname")
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)


db.define_table(
    "help_texts",
    Field("id", type="id"),
    Field("hashtag", type="string", length=128, label=T("Hashtag"), default="#"),
    Field("lang", type="string", length=10, label=T("Language"), default="default"),
    Field("contents", type="text", length=1048576, label=T("Contents")),
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


db.define_table(
    "t_articles",
    Field("id", type="id"),
    Field("anonymous_submission", type="boolean", label=T("I wish an anonymous submission (submitter concealed to reviewers)"), default=False),
    Field("title", type="string", length=1024, label=T("Title"), requires=IS_NOT_EMPTY()),
    Field("authors", type="string", length=4096, label=T("Authors"), requires=IS_NOT_EMPTY(), represent=lambda t, r: ("") if (r.anonymous_submission) else (t)),
    Field("article_source", type="string", length=1024, label=T("Source (journal, year, volume, pages)")),
    Field("doi", type="string", label=T("Manuscript most recent DOI (or URL)"), length=512, unique=False, represent=lambda text, row: common_small_html.mkDOI(text)),
    Field("ms_version", type="string", length=1024, label=T("Manuscript most recent version"), default=""),
    Field("picture_rights_ok", type="boolean", label=T("I wish to add a small picture (png or jpeg format) for which no rights are required")),
    Field("uploaded_picture", type="upload", uploadfield="picture_data", label=T("Picture")),
    Field("picture_data", type="blob"),
    Field("abstract", type="text", length=2097152, label=T("Abstract"), requires=IS_NOT_EMPTY()),
    Field("upload_timestamp", type="datetime", default=request.now, label=T("Submission date")),
    Field("user_id", type="reference auth_user", ondelete="RESTRICT", label=T("Submitter")),
    Field("status", type="string", length=50, default="Pending", label=T("Article status")),
    Field("last_status_change", type="datetime", default=request.now, label=T("Last status change")),
    Field(
        "thematics",
        type="list:string",
        label=T("Thematic fields"),
        requires=[IS_IN_DB(db, db.t_thematics.keyword, "%(keyword)s", multiple=True), IS_NOT_EMPTY()],
        widget=SQLFORM.widgets.checkboxes.widget,
    ),
    Field("keywords", type="string", length=4096, label=T("Keywords")),
    Field("already_published", type="boolean", label=T("Postprint"), default=False),
    Field(
        "cover_letter",
        type="text",
        length=2097152,
        label=T("Cover letter"),
        writable=False,
        readable=False,
        comment=T(
            "Free text. Indicate in the box above whatever you want. Just be aware that after validation of the submission by the managing board every recommender, invited reviewers, and reviewers will be able to read the cover letter."
        ),
    ),
    Field("i_am_an_author", type="boolean", label=T("I am an author of the article and I am acting on behalf of all the authors")),
    Field(
        "is_not_reviewed_elsewhere",
        type="boolean",
        label=T(
            "This preprint has not been published or sent for review elsewhere. I agree not to submit this preprint to a journal before the end of the %s evaluation process (i.e. before its rejection or recommendation by %s), if it is sent out for review."
        )
        % (applongname, applongname),
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
    Field("auto_nb_recommendations", type="integer", label=T("Rounds of reviews"), default=0),
    format="%(title)s (%(authors)s)",
    singular=T("Article"),
    plural=T("Articles"),
    migrate=False,
)
db.t_articles.uploaded_picture.represent = lambda text, row: (IMG(_src=URL("default", "download", args=text), _width=100)) if (text is not None and text != "") else ("")
db.t_articles.authors.represent = lambda t, r: "[undisclosed]" if (r.anonymous_submission and r.status != "Recommended") else (t)
db.t_articles.upload_timestamp.writable = False
db.t_articles.last_status_change.writable = False
db.t_articles.auto_nb_recommendations.writable = False
db.t_articles.auto_nb_recommendations.readable = False
db.t_articles.user_id.requires = IS_EMPTY_OR(IS_IN_DB(db, db.auth_user.id, "%(last_name)s, %(first_name)s"))
db.t_articles.status.requires = IS_IN_SET(statusArticles)
db.t_articles._after_insert.append(lambda s, i: newArticle(s, i))
db.t_articles._after_insert.append(lambda f, i: insArticleThumb(f, i))
db.t_articles._before_update.append(lambda s, f: deltaStatus(s, f))
db.t_articles._after_update.append(lambda s, f: updArticleThumb(s, f))


def deltaStatus(s, f):
    # pprint(s,f)
    if "status" in f:
        o = s.select().first()
        # print(o.status + " --> " +f['status'])
        if o.already_published:  # POSTPRINTS
            # if o.status == 'Under consideration' and (f['status'].startswith('Pre-') or f['status']=='Cancelled'):
            # emailing.send_to_managers(session, auth, db, o['id'], f['status'])
            # emailing.send_to_recommender_postprint_status_changed(session, auth, db, o['id'], f['status'])
            # emailing.send_to_corecommenders(session, auth, db, o['id'], f['status'])
            # elif o.status == 'Pre-recommended' and f['status'] == 'Recommended':
            if o.status != f["status"]:
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_recommender_postprint_status_changed(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])

        else:  # PREPRINTS
            if o.status == "Pending" and f["status"] == "Awaiting consideration":
                emailing.send_to_suggested_recommenders(session, auth, db, o["id"])
                emailing.send_to_submitter(session, auth, db, o["id"], f["status"])
            elif o.status == "Awaiting consideration" and f["status"] == "Not considered":
                emailing.send_to_submitter(session, auth, db, o["id"], f["status"])
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
            elif o.status == "Awaiting consideration" and f["status"] == "Under consideration":
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_submitter(session, auth, db, o["id"], f["status"])
                emailing.send_to_suggested_recommenders_not_needed_anymore(session, auth, db, o["id"])
                emailing.send_to_thank_recommender_preprint(session, auth, db, o["id"])
            elif o.status == "Awaiting revision" and f["status"] == "Under consideration":
                emailing.send_to_recommender_status_changed(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
            elif o.status == "Under consideration" and (f["status"].startswith("Pre-")):
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])
                emailing.send_to_recommender_status_changed(session, auth, db, o["id"], f["status"])
            elif o.status in ("Pending", "Awaiting consideration", "Under consideration") and f["status"] == "Cancelled":
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_recommender_status_changed(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])
                emailing.send_to_reviewers_article_cancellation(session, auth, db, o["id"], f["status"])
                emailing.send_to_submitter(session, auth, db, o["id"], f["status"])
            elif o.status != f["status"]:
                emailing.send_to_managers(session, auth, db, o["id"], f["status"])
                emailing.send_to_recommender_status_changed(session, auth, db, o["id"], f["status"])
                emailing.send_to_corecommenders(session, auth, db, o["id"], f["status"])
                if f["status"] in ("Awaiting revision", "Rejected", "Recommended"):
                    emailing.send_decision_to_reviewers(session, auth, db, o["id"], f["status"])
                    emailing.send_to_submitter(session, auth, db, o["id"], f["status"])
                if f["status"] in ("Rejected", "Recommended", "Awaiting revision"):
                    lastRecomm = db((db.t_recommendations.article_id == o.id) & (db.t_recommendations.is_closed == False)).select(db.t_recommendations.ALL)
                    for lr in lastRecomm:
                        lr.is_closed = True
                        lr.update_record()
    return None


def newArticle(s, articleId):
    if s.already_published is False:
        emailing.send_to_managers(session, auth, db, articleId, "Pending")
    return None


def insArticleThumb(f, i):
    common_small_html.makeArticleThumbnail(auth, db, i, size=(150, 150))
    return None


def updArticleThumb(s, f):
    o = s.select().first()
    common_small_html.makeArticleThumbnail(auth, db, o.id, size=(150, 150))
    return None


db.define_table(
    "t_recommendations",
    Field("id", type="id"),
    Field("article_id", type="reference t_articles", ondelete="RESTRICT", label=T("Article")),
    Field("doi", type="string", length=512, label=T("Manuscript DOI (or URL) for the round"), represent=lambda text, row: common_small_html.mkDOI(text)),
    Field("ms_version", type="string", length=1024, label=T("Manuscript version for the round"), default=""),
    Field("recommender_id", type="reference auth_user", ondelete="RESTRICT", label=T("Recommender")),
    Field("recommendation_title", type="string", length=1024, label=T("Recommendation title")),
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
    Field("last_change", type="datetime", default=request.now, label=T("Last change"), writable=False),
    Field("is_closed", type="boolean", label=T("Closed"), default=False),
    Field("no_conflict_of_interest", type="boolean", label=T("I/we declare that I/we have no conflict of interest with the authors or the content of the article")),
    Field("reply", type="text", length=2097152, label=T("Author's Reply"), default=""),
    Field(
        "reply_pdf",
        type="upload",
        uploadfield="reply_pdf_data",
        label=T("Author's Reply as PDF"),
        requires=[IS_EMPTY_OR(IS_UPLOAD_FILENAME(extension="pdf")), IS_LENGTH(pdf_max_size * 1048576, error_message="The file size is over " + str(pdf_max_size) + "MB.")],
    ),
    Field("reply_pdf_data", type="blob"),  # , readable=False),
    Field(
        "track_change",
        type="upload",
        uploadfield="track_change_data",
        label=T("Tracked changes document (eg. PDF or Word file)"),
        requires=IS_LENGTH(pdf_max_size * 1048576, error_message="The file size is over " + str(pdf_max_size) + "MB."),
    ),
    Field("track_change_data", type="blob", readable=False),
    Field(
        "recommender_file",
        type="upload",
        uploadfield="recommender_file_data",
        label=T("Recommender's annotations (PDF)"),
        requires=[IS_LENGTH(pdf_max_size * 1048576, error_message="The file size is over " + str(pdf_max_size) + "MB."), IS_EMPTY_OR(IS_UPLOAD_FILENAME(extension="pdf"))],
    ),
    Field("recommender_file_data", type="blob", readable=False),
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
# db.t_recommendations._after_update.append(lambda s,f: closedRecommendation(s,f))


def newRecommendation(s, i):
    recomm = db.t_recommendations[i]
    if recomm:
        art = db.t_articles[recomm.article_id]
        if art:
            if art.already_published:
                emailing.send_to_thank_recommender_postprint(session, auth, db, i)
    return None


# def closedRecommendation(s,f):
# o = s.select().first()
# a = db.t_articles[o.article_id]
# if a.already_published and (o.recommendation_comments or '') != '':
# pass #TODO: warn co-recommenders
# return None


db.define_table(
    "t_pdf",
    Field("id", type="id"),
    Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field(
        "pdf", type="upload", uploadfield="pdf_data", label=T("PDF"), requires=IS_LENGTH(pdf_max_size * 1048576, error_message="The file size is over " + str(pdf_max_size) + "MB.")
    ),
    Field("pdf_data", type="blob"),
    singular=T("PDF file"),
    plural=T("PDF files"),
    migrate=False,
)


db.define_table(
    "t_resources",
    Field("id", type="id", readable=False, writable=False),
    Field("resource_rank", type="integer", label=T("Rank")),
    Field("resource_category", type="string", length=250, label=T("Category")),
    Field("resource_name", type="string", length=512, label=T("Name")),
    Field("resource_description", type="text", label=T("Description")),
    # Field('resource_url', type='string', length=512, label=T('URL'), requires=IS_EMPTY_OR(IS_URL())),
    Field(
        "resource_logo",
        type="upload",
        uploadfield="resource_logo_data",
        label=T("Logo"),
        comment=T("Small image (jpg, png, gif) as an illustration"),
        requires=IS_EMPTY_OR(IS_IMAGE(extensions=("JPG", "jpg", "jpeg", "PNG", "png", "GIF", "gif"))),
    ),
    Field("resource_logo_data", type="blob", readable=False),
    Field(
        "resource_document",
        type="upload",
        uploadfield="resource_document_data",
        comment=T("The document itself"),
        label=T("Document"),
        requires=IS_LENGTH(pdf_max_size * 1048576, error_message="The file size is over " + str(pdf_max_size) + "MB."),
    ),
    Field("resource_document_data", type="blob", readable=False),
    singular=T("Resource"),
    plural=T("Resources"),
    migrate=False,
)
db.t_resources.resource_logo.represent = lambda text, row: (IMG(_src=URL("default", "download", args=text), _width=100)) if (text is not None and text != "") else ("")
db.t_resources._after_insert.append(lambda f, i: insResourceThumb(f, i))
db.t_resources._after_update.append(lambda s, f: updResourceThumb(s, f))


def insResourceThumb(f, i):
    common_small_html.mkStatusDiv(auth, db, i, size=(150, 150))
    return None


def updResourceThumb(s, f):
    o = s.select().first()
    common_small_html.mkStatusDiv(auth, db, o.id, size=(150, 150))
    return None


db.define_table(
    "t_supports",
    Field("id", type="id", readable=False, writable=False),
    Field("support_rank", type="integer", label=T("Rank")),
    Field("support_category", type="string", length=250, label=T("Category")),
    Field("support_name", type="string", length=512, label=T("Name")),
    Field("support_url", type="string", length=512, label=T("URL"), requires=IS_EMPTY_OR(IS_URL())),
    Field("support_logo", type="upload", uploadfield="support_logo_data", label=T("Logo"), requires=IS_IMAGE(extensions=("JPG", "jpg", "jpeg", "PNG", "png", "GIF", "gif"))),
    Field("support_logo_data", type="blob", readable=False),
    singular=T("Support"),
    plural=T("Supports"),
    migrate=False,
)
db.t_supports.support_logo.represent = lambda text, row: (IMG(_src=URL("default", "download", args=text), _width=100)) if (text is not None and text != "") else ("")


db.define_table(
    "t_reviews",
    Field("id", type="id"),
    Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field("reviewer_id", type="reference auth_user", ondelete="RESTRICT", label=T("Reviewer")),
    Field("anonymously", type="boolean", label=T("Anonymously"), default=False),
    Field("no_conflict_of_interest", type="boolean", label=T("I declare that I have no conflict of interest with the authors or the content of the article")),
    Field(
        "review_state",
        type="string",
        length=50,
        label=T("Review status"),
        requires=IS_EMPTY_OR(IS_IN_SET(("Pending", "Under consideration", "Declined", "Completed", "Cancelled"))),
        writable=False,
    ),
    Field("review", type="text", length=2097152, label=T("Review as text")),
    Field(
        "review_pdf",
        type="upload",
        uploadfield="review_pdf_data",
        label=T("Review as PDF"),
        requires=[IS_LENGTH(pdf_max_size * 1048576, error_message="The file size is over " + str(pdf_max_size) + "MB."), IS_EMPTY_OR(IS_UPLOAD_FILENAME(extension="pdf"))],
    ),
    Field("review_pdf_data", type="blob", readable=False),
    Field("acceptation_timestamp", type="datetime", label=T("Acceptation timestamp"), writable=False),
    Field("last_change", type="datetime", default=request.now, label=T("Last change"), writable=False),
    Field("emailing", type="text", length=2097152, label=T("Emails sent"), readable=False, writable=False),
    singular=T("Review"),
    plural=T("Reviews"),
    migrate=False,
)
db.t_reviews.reviewer_id.requires = IS_EMPTY_OR(IS_IN_DB(db, db.auth_user.id, "%(last_name)s, %(first_name)s"))
db.t_reviews.recommendation_id.requires = IS_IN_DB(db, db.t_recommendations.id, "%(doi)s")
db.t_reviews._before_update.append(lambda s, f: reviewDone(s, f))
# db.t_reviews._after_insert.append(lambda s,i: reviewSuggested(s,i))
# db.t_reviews._after_update.append(lambda s,f: reviewDone(s,f))


def reviewDone(s, f):
    o = s.select().first()
    if o["review_state"] == "Pending" and f["review_state"] == "Under consideration":
        emailing.send_to_recommenders_review_considered(session, auth, db, o["id"])
        emailing.send_to_thank_reviewer_acceptation(session, auth, db, o["id"], f)
    elif o["review_state"] == "Completed" and f["review_state"] == "Under consideration":
        emailing.send_to_reviewer_review_reopened(session, auth, db, o["id"], f)
    elif o["review_state"] == "Pending" and f["review_state"] == "Declined":
        emailing.send_to_recommenders_review_declined(session, auth, db, o["id"])
    if o["reviewer_id"] is not None and o["review_state"] == "Under consideration" and f["review_state"] == "Completed":
        emailing.send_to_recommenders_review_completed(session, auth, db, o["id"])
        emailing.send_to_thank_reviewer_done(session, auth, db, o["id"], f)  # args: session, auth, db, reviewId, newForm
    return None


db.define_table(
    "t_suggested_recommenders",
    Field("id", type="id"),
    Field("article_id", type="reference t_articles", ondelete="RESTRICT", label=T("Article")),
    Field("suggested_recommender_id", type="reference auth_user", ondelete="RESTRICT", label=T("Suggested recommender")),
    Field("email_sent", type="boolean", default=False, label=T("Email sent")),
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

db.t_suggested_recommenders._after_insert.append(lambda f, i: appendRecommender(f, i))


def appendRecommender(f, i):
    a = db.t_articles[f.article_id]
    if a and a["status"] == "Awaiting consideration":
        emailing.send_to_suggested_recommenders(session, auth, db, a["id"])


db.define_table(
    "t_press_reviews",
    Field("id", type="id"),
    Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field("contributor_id", type="reference auth_user", ondelete="RESTRICT", label=T("Contributor")),
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
    Field("sending_status", type="string", length=128, label=T("Sending status"), default="in queue"),
    Field("sending_attempts", type="integer", label=T("Sending attempts"), default=0),
    Field("sending_date", type="datetime", label=T("Sending date"), default=request.now),
    Field("dest_mail_address", type="string", length=256, label=T("Dest email")),
    Field("user_id", type="reference auth_user", ondelete="RESTRICT", label=T("Sender")),
    # Field("recommendation_id", type="reference t_recommendations", ondelete="CASCADE", label=T("Recommendation")),
    Field("mail_subject", type="string", length=256, label=T("Subject")),
    Field("mail_content", type="text", length=1048576, label=T("Contents")),
    Field("mail_template_hashtag", type="string", length=128, label=T("Template hashtag"), writable=False),
    migrate=True,
)

##-------------------------------- Views ---------------------------------
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

