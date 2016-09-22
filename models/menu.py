# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

from gluon.custom_import import track_changes; track_changes(True)

# ----------------------------------------------------------------------------------------------------------------------
# Customize your APP title, subtitle and menus here
# ----------------------------------------------------------------------------------------------------------------------

response.logo = ""
response.title = myconf.take('app.name')
response.subtitle = T(myconf.take('app.description'))

# ----------------------------------------------------------------------------------------------------------------------
# read more at http://dev.w3.org/html5/markup/meta.name.html
# ----------------------------------------------------------------------------------------------------------------------
response.meta.author = myconf.get('app.author')
response.meta.description = myconf.get('app.description')
response.meta.keywords = myconf.get('app.keywords')
response.meta.generator = myconf.get('app.generator')

# ----------------------------------------------------------------------------------------------------------------------
# your http://google.com/analytics id
# ----------------------------------------------------------------------------------------------------------------------
response.google_analytics_id = None

# ----------------------------------------------------------------------------------------------------------------------
# this is the main application menu add/remove items as required
# ----------------------------------------------------------------------------------------------------------------------

# Appends developpers menu (web2py)
def _DevMenu():
    app = request.application
    ctr = request.controller
    return [
        (T('Developpement'), False, '#', [
            (T('Design'), False, URL('admin', 'default', 'design/%s' % app)),
            LI(_class="divider"),
            (T('Controller'), False,
             URL(
                 'admin', 'default', 'edit/%s/controllers/%s.py' % (app, ctr))),
            (T('View'), False,
             URL(
                 'admin', 'default', 'edit/%s/views/%s' % (app, response.view))),
            (T('DB Model'), False,
             URL(
                 'admin', 'default', 'edit/%s/models/db.py' % app)),
            (T('Menu Model'), False,
             URL(
                 'admin', 'default', 'edit/%s/models/menu.py' % app)),
            (T('Config.ini'), False,
             URL(
                 'admin', 'default', 'edit/%s/private/appconfig.ini' % app)),
            (T('Layout'), False,
             URL(
                 'admin', 'default', 'edit/%s/views/layout.html' % app)),
            (T('Stylesheet'), False,
             URL(
                 'admin', 'default', 'edit/%s/static/css/web2py-bootstrap3.css' % app)),
            (T('Database'), False, URL(app, 'appadmin', 'index')),
            (T('Errors'), False, URL(
                'admin', 'default', 'errors/' + app)),
            (T('About'), False, URL(
                'admin', 'default', 'about/' + app)),
        ]),
    ]


# Appends administrators menu
def _AdminMenu():
	return [
        (T('Administration'), False, '#', [
			(T('Users & roles'),     False, URL('admin', 'list_users', user_signature=True)),
			(T('Thematic fields'),   False, URL('admin', 'thematics_list', user_signature=True)),
			(T('Article status'),    False, URL('admin', 'article_status', user_signature=True)),
		]),
	]


# Appends managers menu
def _ManagerMenu():
	return [
        (T('Management'), False, '#', [
			(T('Pending articles'),  False, URL('manage', 'pending_articles', user_signature=True)),
			(T('All articles'),      False, URL('manage', 'all_articles', user_signature=True)),
		]),
	]
	

# Appends recommenders menu
def _RecommMenu():
	return [
        (T('Articles to be considered'), False, '#', [
			(T('Articles wor which you have been sollicitated'),False, URL('recommender', 'my_awaiting_articles', user_signature=True)),
			(T('Articles awaiting consideration in my fields'), False, URL('recommender', 'fields_awaiting_articles', user_signature=True)),
			(T('All articles awaiting consideration'),          False, URL('recommender', 'all_awaiting_articles', user_signature=True)),
		]),
	]


# Appends personnal menu
def _MyMenu():
	myMenu = []
	myMenu.append((T('My recommendation requests'),              False, URL('user', 'my_articles', user_signature=True)))
	# appends my_reviews only if exists
	nrev = db(db.t_reviews.reviewer_id == auth.user_id).count()
	if nrev > 0:
		myMenu.append((T('My reviews'),                          False, URL('user', 'my_reviews', user_signature=True)))
	# appends my_press_reviews only if exists
	ncontribs = db(db.t_press_reviews.contributor_id == auth.user_id).count()
	if ncontribs > 0:
		myMenu.append((T('My press review contributions'),                    False, URL('user', 'my_press_reviews', user_signature=True)))
	# appends my_recommendations only if recommender
	if auth.has_membership(None, None, 'recommender'):
		myMenu.append((T('My recommendations'),                  False, URL('recommender', 'my_recommendations', user_signature=True)))
	return [
        (T('My contributions'), False, '#', myMenu)
	]


# default public menu (global)
response.menu = [
    (T('Home'),       False, URL('default', 'index'), []),
	(T('About'),      False, '#', [
		('%s %s' % (T('About'), myconf.take('app.name')),   False, URL('public', 'managers')),
		('%s %s' % (T('Members of'), myconf.take('app.name')),       False, URL('public', 'recommenders')),
	]),
]


if auth.is_logged_in():
	response.menu += _MyMenu()

if auth.has_membership(None, None, 'recommender'):
	response.menu += _RecommMenu()

if auth.has_membership(None, None, 'manager'):
	response.menu += _ManagerMenu()

if auth.has_membership(None, None, 'administrator') or auth.has_membership(None, None, 'developper'):
	response.menu += _AdminMenu()

if auth.has_membership(None, None, 'developper'):
	response.menu += _DevMenu()

# set the language
if 'adminLanguage' in request.cookies and not (request.cookies['adminLanguage'] is None):
    T.force(request.cookies['adminLanguage'].value)
