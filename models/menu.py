# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

from gluon.custom_import import track_changes; track_changes(True)

# ----------------------------------------------------------------------------------------------------------------------
# Customize your APP title, subtitle and menus here
# ----------------------------------------------------------------------------------------------------------------------

response.logo = ""
response.title = myconf.take('app.longname')
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
appName = ' '+myconf.take('app.longname')

# default public menu
def _BaseMenu():
	app = request.application
	return [
		(T('Home'),       False, URL('default', 'index'), []),
		(T('About'),      False, '#', [
			(T('About', lazy=False)+appName,       False, URL('about', 'about')),
			(T('Ethics', lazy=False)+appName,      False, URL('about', 'ethics')),
			(T('Members of', lazy=False)+appName,  False, URL('public', 'recommenders')),
		]),
	]


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
			(T('Help texts'),        False, URL('help',  'help_texts', user_signature=True)),
		]),
	]


# Appends managers menu
def _ManagerMenu():
	return [
        (T('Management process'), False, '#', [
			(T('Pending articles'),  False, URL('manage', 'pending_articles', user_signature=True)),
			(T('All articles'),      False, URL('manage', 'all_articles', user_signature=True)),
		]),
	]
	

# Appends recommenders menu
def _RecommMenu():
	return [
        (T('Articles requiring a recommander'), False, '#', [
			(T('Articles awaiting consideration in my fields'), False, URL('recommender', 'fields_awaiting_articles', user_signature=True)),
			(T('All articles awaiting consideration'),          False, URL('recommender', 'all_awaiting_articles', user_signature=True)),
		]),
	]


# Appends personnal menu
def _MyMenu():
	myMenu = []
	mySollicitationsMenu = []
	myContributionsMenu = []
	
	if auth.has_membership(None, None, 'recommender'):
		nRecomSug = db( (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id) & (db.t_suggested_recommenders.article_id == db.t_articles.id) & (db.t_articles.status == 'Awaiting consideration') ).count()
		if nRecomSug > 0:
			mySollicitationsMenu.append((T('Articles for which you have been sollicitated:'+' '+str(nRecomSug)),False, 
								URL('recommender', 'my_awaiting_articles', user_signature=True)))
		
		nPreprintsRecomPend = db( (db.t_recommendations.recommender_id==auth.user_id) & (db.t_recommendations.is_closed==False) & (db.t_recommendations.article_id==db.t_articles.id) & (db.t_articles.status.belongs(['Under consideration', 'Awaiting revision', 'Pre-recommended'])) & (db.t_recommendations.is_press_review==False) ).count()
		myContributionsMenu.append((T('Ongoing articles recommendations:'+' '+str(nPreprintsRecomPend)),False, 
								URL('recommender', 'my_recommendations', vars=dict(pendingOnly=True, pressReviews=False), user_signature=True))) 

		nPressRecomPend = db( (db.t_recommendations.recommender_id==auth.user_id) & (db.t_recommendations.is_closed==False) & (db.t_recommendations.article_id==db.t_articles.id) & (db.t_articles.status.belongs(['Under consideration', 'Awaiting revision', 'Pre-recommended'])) & (db.t_recommendations.is_press_review==True) ).count()
		myContributionsMenu.append((T('Ongoing press-review recommendations:'+' '+str(nPressRecomPend)),False, 
								URL('recommender', 'my_recommendations', vars=dict(pendingOnly=True, pressReviews=True), user_signature=True))) 

		myContributionsMenu.append((T('Recommendation process completed (submissions)'), False, 
								URL('recommender', 'my_recommendations', vars=dict(pendingOnly=False, pressReviews=False), user_signature=True)))
		myContributionsMenu.append((T('Recommendation process completed (press-reviews)'), False, 
								URL('recommender', 'my_recommendations', vars=dict(pendingOnly=False, pressReviews=True), user_signature=True)))

	
	# pending reviews, if any
	nRevPend = db( (db.t_reviews.reviewer_id == auth.user_id) &  ( (db.t_reviews.review_state==None) | (db.t_reviews.review_state=='Under consideration') ) ).count()
	if nRevPend > 0:
		mySollicitationsMenu.append((T('Your pending reviews:'+' '+str(nRevPend)), False, 
							   URL('user', 'my_reviews', vars=dict(pendingOnly=True), user_signature=True))) #TODO: filter pendingOnly in my_reviews
	nRevDone = db( (db.t_reviews.reviewer_id == auth.user_id) &  ( (db.t_reviews.review_state==None) | (db.t_reviews.review_state=='Under consideration') ) ).count()
	if nRevDone > 0:
		myContributionsMenu.append((T('Your reviews:'+' '+str(nRevDone)), False, 
							   URL('user', 'my_reviews', vars=dict(pendingOnly=False), user_signature=True))) #TODO: filter pendingOnly in my_reviews
	
	# appends my_press_reviews only if exists
	nContribsPend = db( (db.t_press_reviews.contributor_id == auth.user_id) & ( (db.t_press_reviews.contribution_state==None) | (db.t_press_reviews.contribution_state=='Under consideration') ) ).count()
	if nContribsPend > 0:
		mySollicitationsMenu.append((T('Your pending press review contributions:'+ ' '+str(nContribsPend)), False, 
							   URL('user', 'my_press_reviews', vars=dict(pendingOnly=True), user_signature=True))) #TODO: filter pendingOnly in my_press_reviews
	nContribsDone = db( (db.t_press_reviews.contributor_id == auth.user_id) & ( (db.t_press_reviews.contribution_state==None) | (db.t_press_reviews.contribution_state=='Under consideration') ) ).count()
	if nContribsDone > 0:
		myContributionsMenu.append((T('Your pending press review contributions:'+ ' '+str(nContribsDone)), False, 
							   URL('user', 'my_press_reviews', vars=dict(pendingOnly=False), user_signature=True))) #TODO: filter pendingOnly in my_press_reviews
	
	return [
		(T('Your submissions'), False, URL('user', 'my_articles', user_signature=True)),
        (T('Your contributions'),  False, '#', myContributionsMenu),
        (T('Requests for your input'),  False, '#', mySollicitationsMenu),
	]


response.menu = _BaseMenu()

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
