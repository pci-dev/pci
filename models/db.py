# -*- coding: utf-8 -*-

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
# app configuration made easy. Look inside private/appconfig.ini
# -------------------------------------------------------------------------
from gluon.contrib.appconfig import AppConfig

# -------------------------------------------------------------------------
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
myconf = AppConfig(reload=True)

if not request.env.web2py_runtime_gae:
    # ---------------------------------------------------------------------
    # if NOT running on Google App Engine use SQLite or other DB
    # ---------------------------------------------------------------------
    db = DAL(myconf.get('db.uri'),
             pool_size=myconf.get('db.pool_size'),
             migrate_enabled=myconf.get('db.migrate'),
             check_reserved=['all'])
else:
    # ---------------------------------------------------------------------
    # connect to Google BigTable (optional 'google:datastore://namespace')
    # ---------------------------------------------------------------------
    db = DAL('google:datastore+ndb')
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
response.generic_patterns = ['*'] if request.is_local else []
# -------------------------------------------------------------------------
# choose a style for forms
# -------------------------------------------------------------------------
response.formstyle = myconf.get('forms.formstyle')  # or 'bootstrap3_stacked' or 'bootstrap2' or other
response.form_label_separator = myconf.get('forms.separator') or ''

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

from gluon.tools import Auth, Service, PluginManager, Mail

# host names must be a list of allowed host names (glob syntax allowed)
auth = Auth(db, host_names=myconf.get('host.names'))
service = Service()
plugins = PluginManager()

# -------------------------------------------------------------------------
db.define_table('t_thematics',
	Field('id', type='id'),
	Field('keyword', type='string', requires=IS_NOT_EMPTY(), label=T('Keyword')),
	format='%(keyword)s',
	singular=T("Keyword"), 
	plural=T("Keywords"),
	migrate=False,
)

# -------------------------------------------------------------------------
# create all tables needed by auth if not custom tables
# -------------------------------------------------------------------------
auth.settings.extra_fields['auth_user'] = [
	Field('user_title', type='string', length=10, label=T('Title'), requires=IS_IN_SET(('', 'Dr.', 'Pr.', 'M.', 'Mrs.')), default=''),
	Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
	Field('picture_data', type='blob'),
	Field('laboratory', type='string', label=T('Laboratory')),
	Field('institution', type='string', label=T('Institution')),
	Field('city', type='string', label=T('City'), requires=IS_NOT_EMPTY()),
	Field('country', type='string', label=T('Country'), requires=IS_IN_SET(('Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Antigua and Barbuda', 'Argentina', 'Armenia', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados', 'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan', 'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 'Brazil', 'Brunei', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Cambodia', 'Cameroon', 'Canada', 'Cape Verde', 'Central African Republic', 'Chad', 'Chile', 'China', 'Colombia', 'Comoros', 'Congo', 'Costa Rica', "Côte d'Ivoire", 'Croatia', 'Cuba', 'Cyprus', 'Czech Republic', 'Denmark', 'Djibouti', 'Dominica', 'Dominican Republic', 'East Timor', 'Ecuador', 'Egypt', 'El Salvador', 'Equatorial Guinea', 'Eritrea', 'Estonia', 'Ethiopia', 'Fiji', 'Finland', 'France', 'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana', 'Greece', 'Grenada', 'Guatemala', 'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras', 'Hong Kong', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Israel', 'Italy', 'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kiribati', 'North Korea','South Korea', 'Kuwait', 'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Liechtenstein', 'Lithuania', 'Luxembourg', 'FYROM', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Mali', 'Malta', 'Marshall Islands', 'Mauritania', 'Mauritius', 'Mexico', 'Micronesia', 'Moldova', 'Monaco', 'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'Namibia', 'Nauru', 'Nepal', 'Netherlands', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 'Norway', 'Oman', 'Pakistan', 'Palau', 'Palestine', 'Panama', 'Papua New Guinea', 'Paraguay', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Puerto Rico', 'Qatar', 'Romania', 'Russia', 'Rwanda', 'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines', 'Samoa', 'San Marino', 'Sao Tome and Principe', 'Saudi Arabia', 'Senegal', 'Serbia and Montenegro', 'Seychelles', 'Sierra Leone', 'Singapore', 'Slovakia', 'Slovenia', 'Solomon Islands', 'Somalia', 'South Africa', 'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Swaziland', 'Sweden', 'Switzerland', 'Syria', 'Taiwan', 'Tajikistan', 'Tanzania', 'Thailand', 'Togo', 'Tonga', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan', 'Tuvalu', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States of America', 'Uruguay', 'Uzbekistan', 'Vanuatu', 'Vatican City', 'Venezuela', 'Vietnam', 'Yemen', 'Zambia', 'Zimbabwe'))),
	Field('thematics', type='list:string', label=T('Thematic fields'), requires=IS_EMPTY_OR(IS_IN_DB(db, db.t_thematics.keyword, '%(keyword)s', multiple=True)), widget=SQLFORM.widgets.checkboxes.widget),
	Field('alerts', type='list:string', label=T('Alert frequency'), requires=IS_EMPTY_OR(IS_IN_SET(('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'), multiple=True)), widget=SQLFORM.widgets.checkboxes.widget),
]
auth.define_tables(username=False, signature=False, migrate=False)
db.auth_user._format = '%(user_title)s %(first_name)s %(last_name)s (%(laboratory)s, %(institution)s, %(city)s, %(country)s)'
db.auth_group._format = '%(role)s'

# -------------------------------------------------------------------------
# configure email
# -------------------------------------------------------------------------
mail = auth.settings.mailer
mail.settings.server = myconf.get('smtp.server')
#mail.settings.server = 'logging' if request.is_local else myconf.get('smtp.server')
mail.settings.sender = myconf.get('smtp.sender')
mail.settings.login = myconf.get('smtp.login')
mail.settings.tls = myconf.get('smtp.tls') or False
mail.settings.ssl = myconf.get('smtp.ssl') or False

# -------------------------------------------------------------------------
# configure auth policy
# -------------------------------------------------------------------------
auth.settings.registration_requires_verification = True
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True
auth.settings.create_user_groups = False
auth.settings.showid = False


# -------------------------------------------------------------------------
db.define_table('t_status_article',
	Field('status', type='string', length=50, label=T('Status'), requires=IS_NOT_EMPTY()),
	Field('color_class', type='string', length=50, default='btn-default', requires=IS_NOT_EMPTY()),
	Field('explaination', type='text', label=T('Explaination')),
	format='%(status)s',
	migrate=False,
)


# in-memory dicts
statusArticles = dict()
for sa in db(db.t_status_article).select():
	statusArticles[sa['status']] = T(sa['status'])



db.define_table('t_articles',
	Field('id', type='id'),
	Field('title', type='string', length=1024, label=T('Title'), requires=IS_NOT_EMPTY()),
	Field('authors', type='string', length=4096, label=T('Authors'), requires=IS_NOT_EMPTY()),
	Field('doi', type='string', label=T('DOI'), represent=lambda text, row: mkDOI(text) ),
	Field('abstract', type='text', label=T('Abstract'), requires=IS_NOT_EMPTY()),
	Field('upload_timestamp', type='datetime', default=request.now, label=T('Submission date/time')),
	Field('user_id', type='reference auth_user', ondelete='RESTRICT', label=T('Submitter')),
	Field('status', type='string', length=50, default='Pending', label=T('Status')),
	Field('last_status_change', type='datetime', default=request.now, label=T('Last status change')),
	Field('thematics', type='list:string', label=T('Thematic fields'), requires=IS_IN_DB(db, db.t_thematics.keyword, '%(keyword)s', multiple=True), widget=SQLFORM.widgets.checkboxes.widget),
	Field('keywords', type='string', length=4096, label=T('Keywords')),
	Field('auto_nb_recommendations', type='integer', label=T('Number of recommendations'), default=0),
	format='%(title)s (%(authors)s)',
	singular=T("Article"), 
	plural=T("Articles"),
	migrate=False,
)
db.t_articles.upload_timestamp.writable = False
db.t_articles.last_status_change.writable = False
db.t_articles.auto_nb_recommendations.writable = False
db.t_articles.auto_nb_recommendations.readable = False
db.t_articles.user_id.requires = IS_IN_DB(db, db.auth_user.id)
db.t_articles.status.requires = IS_IN_SET(statusArticles)



db.define_table('t_recommendations',
	Field('id', type='id'),
	Field('article_id', type='reference t_articles', ondelete='RESTRICT', label=T('Article')),
	Field('doi', type='string', label=T('DOI'), represent=lambda text, row: mkDOI(text) ),
	Field('recommender_id', type='reference auth_user', ondelete='RESTRICT', label=T('Recommender')),
	Field('recommendation_comments', type='text', label=T('Recommendation comments'), default=''),
	Field('recommendation_timestamp', type='datetime', default=request.now, label=T('Recommendation start'), writable=False, requires=IS_NOT_EMPTY()),
	Field('last_change', type='datetime', default=request.now, label=T('Last change'), writable=False),
	Field('is_closed', type='boolean', label=T('Closed'), default=False),
	Field('reply', type='text', label=T('Reply'), default=''),
	singular=T("Recommendation"), 
	plural=T("Recommendations"),
	migrate=False,
	format=lambda row: mkRecommendationFormat(auth, db, row),
)
db.t_recommendations.recommender_id.requires = IS_IN_DB(db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == 'recommender')), db.auth_user.id, '%(user_title)s %(first_name)s %(last_name)s')



db.define_table('t_reviews',
	Field('id', type='id'),
	Field('recommendation_id', type='reference t_recommendations', ondelete='CASCADE', label=T('Recommendation')),
	Field('reviewer_id', type='reference auth_user', ondelete='RESTRICT', label=T('Reviewer')),
	Field('anonymously', type='boolean', label=T('Anonymously'), default=False),
	Field('review', type='text', label=T('Review')),
	Field('last_change', type='datetime', default=request.now, label=T('Last change'), writable=False),
	migrate=False,
)
db.t_reviews.reviewer_id.requires = IS_EMPTY_OR(IS_IN_DB(db, db.auth_user.id, '%(user_title)s %(first_name)s %(last_name)s'))
db.t_reviews.recommendation_id.requires = IS_IN_DB(db, db.t_recommendations.id, '%(doi)s')



db.define_table('t_suggested_recommenders',
	Field('id', type='id'),
	Field('article_id', type='reference t_articles', ondelete='RESTRICT', label=T('Article')),
	Field('suggested_recommender_id', type='reference auth_user', ondelete='RESTRICT', label=T('Suggested recommender')),
	migrate=False,
)
db.t_suggested_recommenders.suggested_recommender_id.requires = IS_EMPTY_OR(IS_IN_DB(db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == 'recommender')), db.auth_user.id, '%(last_name)s, %(first_name)s %(user_title)s'))




##-------------------------------- Views ---------------------------------
db.define_table('v_last_recommendation',
	Field('id', type='id'), 
	Field('last_recommendation', type='datetime', label=T('Last recommendation')),
	Field('days_since_last_recommendation', type='integer', label='Days since last recommendation'),
	writable=False,
	migrate=False,
)

db.define_table('v_suggested_recommenders',
	Field('id', type='id'),
	Field('suggested_recommenders', type='text', label=T('Suggested recommenders')),
	writable=False,
	migrate=False,
)

db.define_table('v_reviewers',
	Field('id', type='id'),
	Field('reviewers', type='text', label=T('Reviewers')),
	writable=False,
	migrate=False,
)
# -------------------------------------------------------------------------
# after defining tables, uncomment below to enable auditing
# -------------------------------------------------------------------------
#auth.enable_record_versioning(db)
