# -*- coding: utf-8 -*-

import pprint
pp = pprint.PrettyPrinter(indent=4)

from gluon.tools import Auth, Service, PluginManager, Mail
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Recaptcha

from gluon.custom_import import track_changes; track_changes(True)
from common import *
from emailing import *
from helper import *

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

if not request.env.web2py_runtime_gae:
    # ---------------------------------------------------------------------
    # if NOT running on Google App Engine use SQLite or other DB
    # ---------------------------------------------------------------------
    db = DAL(myconf.get('db.uri'),
             pool_size=myconf.get('db.pool_size'),
             migrate_enabled=myconf.get('db.migrate'),
             check_reserved=['all'],
             lazy_tables=True,
         )
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
	Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
	Field('picture_data', type='blob'),
	Field('laboratory', type='string', label=T('Laboratory')),
	Field('institution', type='string', label=T('Institution')),
	Field('city', type='string', label=T('City')),
	Field('country', type='string', label=T('Country'), requires=IS_EMPTY_OR(IS_IN_SET(('Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Antigua and Barbuda', 'Argentina', 'Armenia', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados', 'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan', 'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 'Brazil', 'Brunei', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Cambodia', 'Cameroon', 'Canada', 'Cape Verde', 'Central African Republic', 'Chad', 'Chile', 'China', 'Colombia', 'Comoros', 'Congo', 'Costa Rica', "Côte d'Ivoire", 'Croatia', 'Cuba', 'Cyprus', 'Czech Republic', 'Denmark', 'Djibouti', 'Dominica', 'Dominican Republic', 'East Timor', 'Ecuador', 'Egypt', 'El Salvador', 'Equatorial Guinea', 'Eritrea', 'Estonia', 'Ethiopia', 'Fiji', 'Finland', 'France', 'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana', 'Greece', 'Grenada', 'Guatemala', 'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras', 'Hong Kong', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Israel', 'Italy', 'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kiribati', 'North Korea','South Korea', 'Kuwait', 'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Liechtenstein', 'Lithuania', 'Luxembourg', 'FYROM', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Mali', 'Malta', 'Marshall Islands', 'Mauritania', 'Mauritius', 'Mexico', 'Micronesia', 'Moldova', 'Monaco', 'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'Namibia', 'Nauru', 'Nepal', 'Netherlands', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 'Norway', 'Oman', 'Pakistan', 'Palau', 'Palestine', 'Panama', 'Papua New Guinea', 'Paraguay', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Puerto Rico', 'Qatar', 'Romania', 'Russia', 'Rwanda', 'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines', 'Samoa', 'San Marino', 'Sao Tome and Principe', 'Saudi Arabia', 'Senegal', 'Serbia and Montenegro', 'Seychelles', 'Sierra Leone', 'Singapore', 'Slovakia', 'Slovenia', 'Solomon Islands', 'Somalia', 'South Africa', 'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Swaziland', 'Sweden', 'Switzerland', 'Syria', 'Taiwan', 'Tajikistan', 'Tanzania', 'Thailand', 'Togo', 'Tonga', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan', 'Tuvalu', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States of America', 'Uruguay', 'Uzbekistan', 'Vanuatu', 'Vatican City', 'Venezuela', 'Vietnam', 'Yemen', 'Zambia', 'Zimbabwe')))),
	Field('thematics', type='list:string', label=T('Thematic fields'), requires=IS_EMPTY_OR(IS_IN_DB(db, db.t_thematics.keyword, '%(keyword)s', multiple=True)), widget=SQLFORM.widgets.checkboxes.widget),
	Field('cv', type='text', label=T('Educational and work background')),
	Field('alerts', type='list:string', label=T('Alert frequency'), requires=IS_EMPTY_OR(IS_IN_SET(('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'), multiple=True)), widget=SQLFORM.widgets.checkboxes.widget),
	Field('last_alert', type='datetime', label=T('Last alert'), writable=False, readable=False),
	Field('registration_datetime', type='datetime', default=request.now, label=T('Registration date & time'), writable=False, readable=False),

]
auth.define_tables(username=False, signature=False, migrate=False)
db.auth_user.first_name.label=T('Given name(s)')
db.auth_user.registration_key.label=T('Registration key')
db.auth_user.registration_key.writable = db.auth_user.registration_key.readable = auth.has_membership(role='administrator')
db.auth_user.registration_key.requires=IS_IN_SET(('','blocked'))
db.auth_user._format = '%(last_name)s, %(first_name)s'
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
auth.settings.registration_requires_verification = True #WARNING set to True in production
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True #WARNING set to True in production
auth.settings.create_user_groups = False
auth.settings.showid = False
if myconf.get('captcha.private'):
	auth.settings.captcha = Recaptcha(request, myconf.get('captcha.public'), myconf.get('captcha.private'), use_ssl=True)
	auth.settings.login_captcha = False
	auth.settings.register_captcha = None
	auth.settings.retrieve_username_captcha = False
	auth.settings.retrieve_password_captcha = None
auth.messages.verify_email_subject = '%s: validate your registration' % myconf.get('app.longname')
auth.messages.verify_email="""
Welcome %(username)s! 

To complete your registration with the """+myconf.get('app.longname')+""" website, please click on the following link and enter your login and password:
%(link)s

Thanks for signing up!
Yours sincerely,
The Managing Board of """+myconf.get('app.longname')+"""

"""+myconf.get('app.longname')+""" is the first community of the parent project Peer Community In…. 
It is a community of researchers in Evolutionary Biology dedicated to both 1) the review and recommendation of preprints publicly available in preprint servers (such as bioRxiv) and 2) the recommendation of postprints published in traditional journals. 
This project was driven by a desire to establish a free, transparent and public recommendation system for reviewing and identifying remarkable articles. 
More information can be found on the website of """+myconf.get('app.longname')+""": """+URL(c='default', f='index', scheme=True, host=True)

#db.auth_user._after_insert.append(lambda f, id: newUser(f, id))
db.auth_user._before_update.append(lambda s,f: newRegistration(s,f))
def newRegistration(s,f):
	o = s.select().first()
	if o.registration_key != '' and f['registration_key'] == '':
		do_send_mail_new_user(session, auth, db, o.id)
		do_send_mail_admin_new_user(session, auth, db, o.id)
	return None
		
db.auth_membership._after_insert.append(lambda f, id: newMembership(f, id))
def newMembership(f, membershipId):
	do_send_mail_new_membreship(session, auth, db, membershipId)

db.auth_user._after_insert.append(lambda f,i: insUserThumb(f,i))
db.auth_user._after_update.append(lambda s,f: updUserThumb(s,f))
def insUserThumb(f,i):
	makeUserThumbnail(auth, db, i, size=(150,150))
	return None
def updUserThumb(s,f):
	o = s.select().first()
	makeUserThumbnail(auth, db, o.id, size=(150,150))
	return None


db.define_table('help_texts',
	Field('id', type='id'),
	Field('hashtag', type='string', length=128, label=T('Hashtag'), default='#'),
	Field('lang', type='string', length=10, label=T('Language'), default='default'),
	Field('contents', type='text', length=1048576, label=T('Contents')),
	format='%(hashtag)s',
	migrate=False,
)


db.define_table('t_status_article',
	Field('status', type='string', length=50, label=T('Status'), writable=False, requires=IS_NOT_EMPTY()),
	Field('color_class', type='string', length=50, default='btn-default', requires=IS_NOT_EMPTY()),
	Field('explaination', type='text', label=T('Explaination')),
	Field('priority_level', type='text', length=1, requires=IS_IN_SET(('A', 'B', 'C'))),
	format='%(status)s',
	migrate=False,
)
# in-memory dict
statusArticles = dict()
for sa in db(db.t_status_article).select():
	statusArticles[sa['status']] = T(sa['status'])


db.define_table('t_articles',
	Field('id', type='id'),
	Field('title', type='string', length=1024, label=T('Title'), requires=IS_NOT_EMPTY()),
	Field('authors', type='string', length=4096, label=T('Authors'), requires=IS_NOT_EMPTY()),
	Field('article_source', type='string', length=1024, label=T('Source (journal, year, pages)')),
	Field('doi', type='string', label=T('DOI'), length=512, unique=True, represent=lambda text, row: mkDOI(text) ),
	Field('picture_rights_ok', type='boolean', label=T('I wish to add a small picture for which no rights are required')),
	Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
	Field('picture_data', type='blob'),
	Field('abstract', type='text', label=T('Abstract'), requires=IS_NOT_EMPTY()),
	Field('upload_timestamp', type='datetime', default=request.now, label=T('Submission date')),
	Field('user_id', type='reference auth_user', ondelete='RESTRICT', label=T('Submitter')),
	Field('status', type='string', length=50, default='Pending', label=T('Article status')),
	Field('last_status_change', type='datetime', default=request.now, label=T('Last status change')),
	Field('thematics', type='list:string', label=T('Thematic fields'), requires=[IS_IN_DB(db, db.t_thematics.keyword, '%(keyword)s', multiple=True), IS_NOT_EMPTY()], widget=SQLFORM.widgets.checkboxes.widget),
	Field('keywords', type='string', length=4096, label=T('Keywords')),
	Field('already_published', type='boolean', label=T('Already published'), default=False),
	Field('i_am_an_author', type='boolean', label=T('I am an author of the article and I am acting on behalf of all the authors')),
	Field('is_not_reviewed_elsewhere', type='boolean', label=T('This preprint has not been published and has not been sent for review elsewhere')),
	Field('auto_nb_recommendations', type='integer', label=T('Rounds of reviews'), default=0),
	format='%(title)s (%(authors)s)',
	singular=T("Article"), 
	plural=T("Articles"),
	migrate=False,
)
db.t_articles.uploaded_picture.represent = lambda text,row: (IMG(_src=URL('default', 'download', args=text), _width=100)) if (text is not None and text != '') else ('')
db.t_articles.upload_timestamp.writable = False
db.t_articles.last_status_change.writable = False
db.t_articles.auto_nb_recommendations.writable = False
db.t_articles.auto_nb_recommendations.readable = False
db.t_articles.user_id.requires = IS_EMPTY_OR(IS_IN_DB(db, db.auth_user.id, '%(last_name)s, %(first_name)s'))
db.t_articles.status.requires = IS_IN_SET(statusArticles)
db.t_articles._before_update.append(lambda s,f: deltaStatus(s,f))
db.t_articles._after_insert.append(lambda s,i: newArticle(s,i))
db.t_articles._after_insert.append(lambda f,i: insArticleThumb(f,i))
db.t_articles._after_update.append(lambda s,f: updArticleThumb(s,f))

def deltaStatus(s, f):
	if 'status' in f:
		o = s.select().first()
		if o.status == 'Pending' and f['status'] == 'Awaiting consideration':
			do_send_email_to_suggested_recommenders(session, auth, db, o['id'])
			do_send_email_to_requester(session, auth, db, o['id'], f['status'])
		elif o.status == 'Awaiting consideration' and f['status'] == 'Under consideration':
			do_send_email_to_requester(session, auth, db, o['id'], f['status'])
			do_send_email_to_suggested_recommenders_useless(session, auth, db, o['id'])
		elif o.status == 'Under consideration' and f['status'] == 'Pre-recommended': 
			do_send_email_to_recommender_status_changed(session, auth, db, o['id'], f['status'])
			do_send_email_to_managers(session, auth, db, o['id'], f['status'])
			# no email for submitter (yet)
			if o.already_published:
				do_send_email_to_contributors(session, auth, db, o['id'])
		elif o.status != f['status']:
			do_send_email_to_recommender_status_changed(session, auth, db, o['id'], f['status'])
			do_send_email_to_requester(session, auth, db, o['id'], f['status'])
		if o.status != f['status'] and f['status'] in ('Awaiting revision', 'Rejected', 'Recommended', 'Cancelled'):
			do_send_email_decision_to_reviewer(session, auth, db, o['id'], f['status'])
	return None

def newArticle(s, articleId):
	do_send_email_to_managers(session, auth, db, articleId, 'Pending')
	return None

def insArticleThumb(f,i):
	makeArticleThumbnail(auth, db, i, size=(150,150))
	return None

def updArticleThumb(s,f):
	o = s.select().first()
	makeArticleThumbnail(auth, db, o.id, size=(150,150))
	return None



db.define_table('t_recommendations',
	Field('id', type='id'),
	Field('article_id', type='reference t_articles', ondelete='RESTRICT', label=T('Article')),
	Field('doi', type='string', label=T('DOI'), represent=lambda text, row: mkDOI(text) ),
	Field('recommender_id', type='reference auth_user', ondelete='RESTRICT', label=T('Recommender')),
	Field('recommendation_title', type='string', length=1024, label=T('Recommendation title'), requires=IS_NOT_EMPTY()),
	Field('recommendation_comments', type='text', label=T('Recommendation'), default=''),
	Field('recommendation_doi', type='string', length=512, label=T('Recommendation DOI'), represent=lambda text, row: mkDOI(text) ),
	Field('recommendation_state', type='string', length=50, label=T('Recommendation state'),  requires=IS_EMPTY_OR(IS_IN_SET(('Ongoing', 'Recommended', 'Rejected', 'Awaiting revision')))),
	Field('recommendation_timestamp', type='datetime', default=request.now, label=T('Recommendation start'), writable=False, requires=IS_NOT_EMPTY()),
	Field('last_change', type='datetime', default=request.now, label=T('Last change'), writable=False),
	Field('is_closed', type='boolean', label=T('Closed'), default=False),
	Field('no_conflict_of_interest', type='boolean', label=T('I/we declare that I/we have no conflict of interest with the authors or the content of the article')),
	Field('reply', type='text', label=T('Author\'s Reply'), default=''),
	#Field('auto_nb_agreements', type='integer', label=T('Number of reviews'), writable=False),
	format=lambda row: mkRecommendationFormat(auth, db, row),
	singular=T("Recommendation"), 
	plural=T("Recommendations"),
	migrate=False,
)
db.t_recommendations.recommender_id.requires = IS_IN_DB(db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == 'recommender')), db.auth_user.id, '%(first_name)s %(last_name)s')
db.t_recommendations._after_insert.append(lambda s,i: newRecommendation(s,i))
db.t_recommendations._after_update.append(lambda s,f: closedRecommendation(s,f))

def newRecommendation(s,i):
	do_send_email_to_thank_recommender(session, auth, db, i)
	return None

def closedRecommendation(s,f):
	o = s.select().first()
	a = db.t_articles[o.article_id]
	if a.already_published and (o.recommendation_comments or '') != '':
		pass #TODO: warn co-recommenders
	return None



db.define_table('t_pdf',
	Field('id', type='id'),
	Field('recommendation_id', type='reference t_recommendations', ondelete='CASCADE', label=T('Recommendation')),
	Field('pdf', type='upload', uploadfield='pdf_data', label=T('PDF')),
	Field('pdf_data', type='blob'),
	singular=T("PDF file"), 
	plural=T("PDF files"),
	migrate=False,
)



db.define_table('t_reviews',
	Field('id', type='id'),
	Field('recommendation_id', type='reference t_recommendations', ondelete='CASCADE', label=T('Recommendation')),
	Field('reviewer_id', type='reference auth_user', ondelete='RESTRICT', label=T('Reviewer')),
	Field('anonymously', type='boolean', label=T('Anonymously'), default=False),
	Field('no_conflict_of_interest', type='boolean', label=T('I declare that I have no conflict of interest with the authors or the content of the article')),
	Field('review', type='text', label=T('Review')),
	Field('last_change', type='datetime', default=request.now, label=T('Last change'), writable=False),
	Field('review_state', type='string', length=50, label=T('Review state'), requires=IS_EMPTY_OR(IS_IN_SET(('Pending', 'Under consideration', 'Declined', 'Terminated'))), writable=False),
	singular=T("Review"), 
	plural=T("Reviews"),
	migrate=False,
)
db.t_reviews.reviewer_id.requires = IS_EMPTY_OR(IS_IN_DB(db, db.auth_user.id, '%(last_name)s, %(first_name)s'))
db.t_reviews.recommendation_id.requires = IS_IN_DB(db, db.t_recommendations.id, '%(doi)s')
db.t_reviews._before_update.append(lambda s,f: reviewDone(s,f))
#db.t_reviews._after_insert.append(lambda s,i: reviewSuggested(s,i))

def reviewDone(s, f):
	o = s.select().first()
	if o['review_state'] == 'Pending' and f['review_state'] == 'Under consideration':
		do_send_email_to_recommenders_review_considered(session, auth, db, o['id'])
		do_send_email_to_thank_reviewer(session, auth, db, o['id'])
	elif o['review_state'] == 'Terminated' and f['review_state'] == 'Under consideration':
		do_send_email_to_reviewer_review_reopened(session, auth, db, o['id'])
	elif o['review_state'] == 'Pending' and f['review_state'] == 'Declined':
		do_send_email_to_recommenders_review_declined(session, auth, db, o['id'])
	if o['reviewer_id'] is not None and f['review_state'] == 'Terminated':
		do_send_email_to_recommenders_review_closed(session, auth, db, o['id'])
	return None

#def reviewSuggested(s, i):
	#do_send_email_to_reviewer_review_suggested(session, auth, db, i)
	#return None




db.define_table('t_suggested_recommenders',
	Field('id', type='id'),
	Field('article_id', type='reference t_articles', ondelete='RESTRICT', label=T('Article')),
	Field('suggested_recommender_id', type='reference auth_user', ondelete='RESTRICT', label=T('Suggested recommender')),
	Field('email_sent', type='boolean', default=False, label=T('email sent')),
	singular=T("Suggested recommender"), 
	plural=T("Suggested recommenders"),
	migrate=False,
)
db.t_suggested_recommenders.suggested_recommender_id.requires = IS_EMPTY_OR(IS_IN_DB(db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == 'recommender')), db.auth_user.id, '%(last_name)s, %(first_name)s'))



db.define_table('t_press_reviews',
	Field('id', type='id'),
	Field('recommendation_id', type='reference t_recommendations', ondelete='CASCADE', label=T('Recommendation')),
	Field('contributor_id', type='reference auth_user', ondelete='RESTRICT', label=T('Contributor')),
	singular=T("Co-recommendation"), 
	plural=T("Co-recommendations"),
	migrate=False,
)
db.t_press_reviews.contributor_id.requires = IS_IN_DB(db((db.auth_user._id==db.auth_membership.user_id) & (db.auth_membership.group_id==db.auth_group._id) & (db.auth_group.role=='recommender')), db.auth_user.id, '%(last_name)s, %(first_name)s')
db.t_press_reviews.recommendation_id.requires = IS_IN_DB(db, db.t_recommendations.id, '%(doi)s')




db.define_table('t_comments',
	Field('id', type='id'),
	Field('article_id', type='reference t_articles', ondelete='CASCADE', label=T('Article')),
	Field('parent_id', type='reference t_comments', ondelete='CASCADE', label=T('Reply to')),
	Field('user_id', type='reference auth_user', ondelete='RESTRICT', label=T('Author')),
	Field('user_comment', type='text', label=T('Comment'), requires=IS_NOT_EMPTY()),
	Field('comment_datetime', type='datetime', default=request.now, label=T('Date & time'), writable=False),
	migrate=False,
	singular=T("Comment"), 
	plural=T("Comments"),
	format=lambda row: row.user_comment[0:100],
)


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

db.define_table('v_article_recommender',
	Field('id', type='id'),
	Field('recommender', type='text', label=T('Recommender')),
	writable=False,
	migrate=False,
)


db.define_table('v_reviewers',
	Field('id', type='id'),
	Field('reviewers', type='text', label=T('Reviewers')),
	writable=False,
	migrate=False,
)


db.define_table('v_recommendation_contributors',
	Field('id', type='id'),
	Field('contributors', type='text', label=T('Co-recommenders')),
	writable=False,
	migrate=False,
)


db.define_table('v_roles',
	Field('id', type='id'),
	Field('roles', type='string', length=512, label=T('Roles')),
	writable=False,
	migrate=False,
)


# -------------------------------------------------------------------------
# after defining tables, uncomment below to enable auditing
# -------------------------------------------------------------------------
#auth.enable_record_versioning(db)
