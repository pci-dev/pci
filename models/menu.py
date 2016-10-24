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

# Appends developpers menu (web2py)
def _DevMenu():
    app = request.application
    ctr = request.controller
    return [
        (T('Dev.'), False, '#', [
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
			#(T('Queue tasks in scheduler'), False, URL(app, 'admin', 'queueTasks')),
			#(T('Terminate scheduler'), False, URL(app, 'admin', 'terminateScheduler')),
			#(T('Kill scheduler'), False, URL(app, 'admin', 'killScheduler')),
        ]),
    ]


# default public menu
def _BaseMenu():
	return [
		#(T('Home'),       False, URL('default', 'index'), []),
		(IMG(_title=T('Home'), _alt=T('Home'), _src=URL(c='static',f='images/home.png'), _class='pci-menuImage'), False, URL('default', 'index'), []),
		(IMG(_title=T('About'), _alt=T('About'), _src=URL(c='static',f='images/about.png'), _class='pci-menuImage'),      False, '#', [
			(T('Search recommended articles', lazy=False), False, URL('public', 'recommended_articles')),
			LI(_class="divider"),
			(T('About', lazy=False)+appName,       False, URL('about', 'about')),
			(T('Ethics of', lazy=False)+appName,      False, URL('about', 'ethics')),
			(T('Members of', lazy=False)+appName,  False, URL('public', 'recommenders')),
		]),
	]


# Appends administrators menu
def _AdminMenu():
	return [
        (IMG(_alt=T('Admin.'), _title=T('Admin.'), _src=URL(c='static',f='images/admin.png'), _class='pci-menuImage'), False, '#', [
			(T('Users & roles'),     False, URL('admin', 'list_users', user_signature=True)),
			(T('Thematic fields'),   False, URL('admin', 'thematics_list', user_signature=True)),
			(T('Article status'),    False, URL('admin', 'article_status', user_signature=True)),
			(T('Help texts'),        False, URL('help',  'help_texts', user_signature=True)),
			LI(_class="divider"),
			(T('Send me a test mail'), False, URL('admin', 'testMail')),
			(T('Test my email alert'), False, URL('alerts', 'testUserRecommendedAlert', vars=dict(userId=auth.user_id))),
			#(T('Test ALL email alerts'), False, URL('alerts', 'alertUsers')),
		]),
	]


# Appends personnal menu
def _UserMenu():
	# prepare 2 submenus
	myContributionsMenu = []
	mySollicitationsMenu = []
	
	### contributions menu
	# reviews
	myContributionsMenu.append((T('Your submitted articles'), False, URL('user', 'my_articles', user_signature=True)))
	nRevTot = db(  (db.t_reviews.reviewer_id == auth.user_id) 
					& (db.t_reviews.recommendation_id == db.t_recommendations.id)
					& (db.t_recommendations.article_id == db.t_articles.id) 
			   ).count()
	if nRevTot>0:
		myContributionsMenu.append(LI(_class="divider"))
		myContributionsMenu.append((T('Your reviews'), False, URL('user', 'my_reviews', vars=dict(pendingOnly=False), user_signature=True)))
	# recommendations
	if auth.has_membership(None, None, 'recommender'):
		myContributionsMenu.append(LI(_class="divider"))
		myContributionsMenu.append((T('Your recommendations of prereview articles'), False, 
								URL('recommender', 'my_recommendations', vars=dict(pressReviews=False), user_signature=True)))
		myContributionsMenu.append(LI(_class="divider"))
		myContributionsMenu.append((T('Your recommendations of reviewed articles'), False, 
								URL('recommender', 'my_recommendations', vars=dict(pressReviews=True), user_signature=True)))
		myContributionsMenu.append((T('Your co-recommendations of reviewed articles'), False, 
								URL('recommender', 'my_press_reviews', vars=dict(pendingOnly=False), user_signature=True)))

	
	### sollicitations menu
	colorRequests = False
	# pending reviews, if any
	nRevPend = db(  (db.t_reviews.reviewer_id == auth.user_id) 
					& (db.t_reviews.review_state=='Pending') 
					& (db.t_reviews.recommendation_id == db.t_recommendations.id)
					& (db.t_recommendations.article_id == db.t_articles.id) 
					& (db.t_articles.status == 'Under consideration') 
			   ).count()
	#txtRevPend = str(nRevPend)+' '+(T('Reviews') if nRevPend > 1 else T('Review'))
	txtRevPend = T('Accept a solicitation to review?')
	if nRevPend > 0:
		txtRevPend = SPAN(txtRevPend, _style='color:#94c11f;;')
		colorRequests = True
	mySollicitationsMenu.append((txtRevPend, False, 
							URL('user', 'my_reviews', vars=dict(pendingOnly=True), user_signature=True))) 
	# recommendations
	if auth.has_membership(None, None, 'recommender'):
		nPreprintsRecomPend = db( 	(db.t_articles.status == 'Awaiting consideration') 
								  & (db.t_articles._id == db.t_suggested_recommenders.article_id) 
								  & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id) 
								).count()
		#txtPreprintsRecomPend = str(nPreprintsRecomPend)+' '+(T('Recommendations of prereview articles') if nPreprintsRecomPend>1 else T('Recommendation of prereview articles'))
		txtPreprintsRecomPend = 'Accept a solicitation to start a recommendation?'
		if nPreprintsRecomPend > 0:
			txtPreprintsRecomPend = SPAN(txtPreprintsRecomPend, _style='color:#94c11f;;')
			colorRequests = True
		mySollicitationsMenu.append((txtPreprintsRecomPend,False, 
								URL('recommender', 'my_awaiting_articles', vars=dict(pendingOnly=True, pressReviews=False), user_signature=True))) 
		mySollicitationsMenu += [
				LI(_class="divider"),
				#(T('Articles requiring a recommender in my fields'), False, URL('recommender', 'fields_awaiting_articles', user_signature=True)),
				#(T('All articles requiring a recommender'),          False, URL('recommender', 'all_awaiting_articles', user_signature=True)),
				(T('Articles requiring a recommender'),          False, URL('recommender', 'fields_awaiting_articles', user_signature=True)),
			]
	resu = [
		#(T('Your submissions'),         False, URL('user', 'my_articles', user_signature=True)),
        #(T('Your contributions'),       False, '#', myContributionsMenu),
        (IMG(_title=T('Your contributions'), _alt=T('Your contributions'), _src=URL(c='static', f='images/your_contribs.png'), _class='pci-menuImage'),       False, '#', myContributionsMenu),
	]
	if colorRequests:
		#requestsMenuTitle = SPAN(T('Requests for input'), _style='color:#94c11f;;')
		requestsMenuTitle = IMG(_title=T('Requests for input'), _alt=T('Requests for input'), _src=URL(c='static', f='images/inputs_enhanced.png'), _class='pci-menuImage')
	else:
		#requestsMenuTitle = T('Requests for input')
		requestsMenuTitle = IMG(_title=T('Requests for input'), _alt=T('Requests for input'), _src=URL(c='static', f='images/inputs.png'), _class='pci-menuImage')
	if (auth.has_membership(None, None, 'recommender') or ( auth.is_logged_in() and colorRequests ) ):
		resu.append( (requestsMenuTitle,  False, '#', mySollicitationsMenu) )
	return resu


## Appends recommenders menu
#def _RecommMenu():
	#return [
        #(T('Articles requiring a recommender'), False, '#', [
			#(T('Articles in my fields'), False, URL('recommender', 'fields_awaiting_articles', user_signature=True)),
			#(T('All articles'),          False, URL('recommender', 'all_awaiting_articles', user_signature=True)),
		#]),
	#]

# Appends managers menu
def _ManagerMenu():
	txtMenu = IMG(_title=T('Manage'), _alt=T('Manage'), _src=URL(c='static', f='images/manage.png'), _class='pci-menuImage')
	nbPend = db( db.t_articles.status.belongs(('Pending', 'Pre-recommended')) ).count()
	txtPending = str(nbPend)+' '+(T('Pending validations') if nbPend > 1 else T('Pending validation'))
	if nbPend>0:
		txtPending = SPAN(txtPending, _style='color:#94c11f;;')
		txtMenu = IMG(_title=T('Manage'), _alt=T('Manage'), _src=URL(c='static', f='images/manage_enhanced.png'), _class='pci-menuImage')
	nbGoing = db( db.t_articles.status.belongs(('Under consideration', 'Awaiting revision', 'Awaiting consideration')) ).count()
	txtGoing = str(nbGoing)+' '+(T('Recommendation processes in progress') if nbGoing > 1 else T('Recommendation process in progress'))
	if nbGoing>0:
		txtGoing = SPAN(txtGoing, _style='color:#94c11f;;')
		txtMenu = IMG(_title=T('Manage'), _alt=T('Manage'), _src=URL(c='static', f='images/manage_enhanced.png'), _class='pci-menuImage')
	return [
        (txtMenu, False, '#', [
			(txtPending, False, URL('manager', 'pending_articles', user_signature=True)),
			(txtGoing, False, URL('manager', 'ongoing_articles', user_signature=True)),
			(T('Recommendation processes completed'),   False, URL('manager', 'completed_articles', user_signature=True)),
			LI(_class="divider"),
			(T('Send email alerts manually'), False, URL('alerts', 'alertUsersLastRecommendations')),
		]),
	]
	



response.menu = _BaseMenu()

if auth.is_logged_in():
	response.menu += _UserMenu()

#if auth.has_membership(None, None, 'recommender'):
	#response.menu += _RecommMenu()

if auth.has_membership(None, None, 'manager'):
	response.menu += _ManagerMenu()

if auth.has_membership(None, None, 'administrator') or auth.has_membership(None, None, 'developper'):
	response.menu += _AdminMenu()

if auth.has_membership(None, None, 'developper'):
	response.menu += _DevMenu()

# set the language
if 'adminLanguage' in request.cookies and not (request.cookies['adminLanguage'] is None):
    T.force(request.cookies['adminLanguage'].value)
