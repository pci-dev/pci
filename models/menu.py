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
#response.meta.author = myconf.get('app.author')
response.meta.description = myconf.get('app.description')
#response.meta.keywords = myconf.get('app.keywords')
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
    #txtMenu = IMG(_title=T('Development'), _alt=T('Devel.'), _src=URL(c='static', f='images/devel.png'), _class='pci-menuImage')
    txtMenu = SPAN(T('Development'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"))
    return [
        (txtMenu, False, '#', [
	    	(T('TEST: Recommenders country map'),  False, URL('maps', 'recommenders_map', user_signature=True)),
			(T('TEST: Redirection'),  False, URL('admin', 'testRedir', user_signature=True)),

            #LI(_class="divider"),
            #(T('Restart daemon'), False, URL('admin', 'restart_daemon')),
            LI(_class="divider"),
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
			#(T('Transfer help'), False, URL('help', 'transfer_help')),
			#(T('Test flash'), False, URL('alerts', 'test_flash')),
			#(T('Test FB + tweeter'), False, URL('about', 'test')),
			#(T('Shrink user images'), False, URL('admin', 'resizeAllUserImages')),
			#(T('Shrink article images'), False, URL('admin', 'resizeAllArticleImages')),
        ]),
    ]


# default public menu
def _BaseMenu():
	ctr = request.controller
	fct = request.function
	
	isHomeActive = False
	if ctr == 'default' and fct != 'user':
		isHomeActive = True
	isArticleActive = False
	if ctr == 'articles':
		isArticleActive = True

	tracking = myconf.get('config.tracking', default=False)
	
	articleMenu = [
			(T(u'🔍 Search articles'), False, URL('articles', 'recommended_articles')),
			(T('All recommended articles'), False, URL('articles', 'all_recommended_articles')),
	]
	if tracking:
		articleMenu.append((T('Progress log'), False, URL('articles', 'tracking')))
	
	menuBar = [
		((SPAN(_class='pci2-icon-margin-right glyphicon glyphicon-home'), T('Home')),       isHomeActive, URL('default', 'index')),
		#(T(u'🔍 Search'), False, URL('articles', 'recommended_articles')),
		(SPAN(T('Articles'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px") ),      isArticleActive, '#', articleMenu),
	]
	return menuBar

def _ToolsMenu():
	ctr = request.controller
	isActive = False
	if ctr == 'tools':
		isActive = True

	toolMenu = [(T('Convert PDF to MarkDown'),  False, URL('tools', 'convert_pdf_to_markdown', user_signature=True))]

	if auth.has_membership(None, None, 'administrator'):
		myClass = 'pci-admin'
	else:
		myClass = 'pci-manager'


	if auth.has_membership(None, None, 'administrator') or auth.has_membership(None, None, 'developper'):
		toolMenu += [
			LI(_class="divider"),
			(T('Send me a test mail'), False, URL('admin_actions', 'testMail', user_signature=True)),
			(T('Test my email alert'), False, URL('alerts', 'testUserRecommendedAlert', vars=dict(userId=auth.user_id), user_signature=True)),
			#(T('Test ALL email alerts'), False, URL('alerts', 'alertUsers')),
			(T('RSS for bioRxiv'), False, URL('rss', 'rss4bioRxiv', user_signature=True)),
			(T('Social networks', lazy=False),      False, URL('about', 'social', user_signature=True))
		]

	return [
		(SPAN(T('Tools'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"), _class=myClass), isActive, '#', toolMenu),
	]

# Appends administrators menu
def _AdminMenu():
	ctr = request.controller
	isActive = False
	if ctr == 'admin':
		isActive = True


	return [
		(SPAN(T('Admin'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"), _class='pci-admin'), isActive, '#', [
			(T('Users & roles'),     False, URL('admin', 'list_users', user_signature=True)),
			(T('Supports'),          False, URL('admin', 'manage_supports', user_signature=True)),
			#(T('Images'),            False, URL('admin', 'manage_images', user_signature=True)),
			(T('All recommendation citations'),  False, URL('admin', 'allRecommCitations', user_signature=True)),
			(T('Reviews synthesis'),            False, URL('admin', 'recap_reviews', user_signature=True)),
			(T('Resources'),         False, URL('admin', 'manage_resources', user_signature=True)),
			(T('Recommendation PDF files'),              False, URL('admin', 'manage_pdf', user_signature=True)),
			(T('Email lists'),       False, URL('admin', 'mailing_lists', user_signature=True)),
			(T('Thematic fields'),   False, URL('admin', 'thematics_list', user_signature=True)),
			(T('Article status'),    False, URL('admin', 'article_status', user_signature=True)),
			(T('Help texts'),        False, URL('custom_help_text',  'help_texts', user_signature=True)),
			LI(_class="divider"),
			(T('Send email alerts manually'), False, URL('alerts', 'alertUsersLastRecommendations', user_signature=True)),		
		]),
	]


# Appends personnal menu
def _UserMenu():
	ctr = request.controller
	isActive = False
	if ctr == 'user':
		isActive = True

	myContributionsMenu = []
	nRevOngoing = 0
	nRevTot = 0
	revClass = ''
	contribMenuClass = ''
	notificationPin = ''
	# reviews
	# (gab) proposition :

	# pending reviews, if any
	nRevPend = db(  (db.t_reviews.reviewer_id == auth.user_id) 
					& (db.t_reviews.review_state=='Pending') 
					& (db.t_reviews.recommendation_id == db.t_recommendations.id)
					& (db.t_recommendations.article_id == db.t_articles.id) 
					& (db.t_articles.status == 'Under consideration') 
			   ).count()

	# (gab) proposition à la place de :
	txtRevPend = SPAN(T('%s invitations to review a preprint' % nRevPend), _class='pci-recommender')
	# txtRevPend = SPAN(T('Do you agree to review a preprint?'), _class='pci-recommender')

	if nRevPend > 0:
		txtRevPend = SPAN(txtRevPend, _class='pci-enhancedMenuItem')
		contribMenuClass = 'pci-enhancedMenuItem'
		# notificationPin = DIV(nRevPend,_class='pci2-notif-pin')

	myContributionsMenu.append((txtRevPend, False, URL('user', 'my_reviews', vars=dict(pendingOnly=True), user_signature=True)))
	myContributionsMenu.append((T('Submit a preprint'), False, URL('user', 'new_submission', user_signature=True)))
	myContributionsMenu.append(LI(_class="divider"))
	
	nRevisions = db(
					(db.t_articles.user_id == auth.user_id)
				  & (db.t_articles.status == 'Awaiting revision')
				).count()
	if nRevisions > 0:
		myContributionsMenu.append(((SPAN(T('Your submitted preprints'), _class='pci-enhancedMenuItem')), False, URL('user', 'my_articles', user_signature=True)))
		contribMenuClass = 'pci-enhancedMenuItem'
	else:
		myContributionsMenu.append((T('Your submitted preprints'), False, URL('user', 'my_articles', user_signature=True)))


	nRevTot = db(  (db.t_reviews.reviewer_id == auth.user_id) 
			   ).count()
	nRevOngoing = db(  (db.t_reviews.reviewer_id == auth.user_id) 
					 & (db.t_reviews.review_state ==  'Under consideration')
			   ).count()
	if nRevOngoing > 0:
		revClass = 'pci-enhancedMenuItem'
		contribMenuClass = 'pci-enhancedMenuItem'
	if nRevTot>0:
		myContributionsMenu.append((
			SPAN(T('Your reviews'), _class=revClass),
			False,
			URL('user', 'my_reviews', vars=dict(pendingOnly=False), user_signature=True))
		)

	return [
        (SPAN(T('Your contributions'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"), _class=contribMenuClass), isActive, '#', myContributionsMenu),
	]

def _RecommendationMenu():
	ctr = request.controller
	isActive = False
	if ctr == 'recommender':
		isActive = True

	recommendationsMenu = []
	colorRequests = False
	nPostprintsOngoing = 0
	nPreprintsOngoing = 0

	# recommendations

	nPreprintsRecomPend = db( 	(db.t_articles.status == 'Awaiting consideration') 
							  & (db.t_articles._id == db.t_suggested_recommenders.article_id) 
							  & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id) 
							  & (db.t_suggested_recommenders.declined == False)
							).count()
	# (gab) proposition à la place de :
	txtPreprintsRecomPend = SPAN('%s requests to handle a preprint' % nPreprintsRecomPend, _class='pci-recommender')
	# txtPreprintsRecomPend = SPAN('Do you agree to initiate a recommendation?', _class='pci-recommender')

	if nPreprintsRecomPend > 0:
		txtPreprintsRecomPend = SPAN(txtPreprintsRecomPend, _class='pci-enhancedMenuItem')
		colorRequests = True

	recommendationsMenu.append((txtPreprintsRecomPend,False, 
							URL('recommender', 'my_awaiting_articles', vars=dict(pendingOnly=True, pressReviews=False), user_signature=True))) 

	nPreprintsOngoing = db(
				(db.t_recommendations.recommender_id == auth.user_id)
				& (db.t_recommendations.article_id == db.t_articles.id)
				& ~(db.t_articles.already_published == True)
				& (db.t_articles.status == 'Under consideration')
			).count()
	if nPreprintsOngoing > 0:
		classPreprintsOngoing = 'pci-enhancedMenuItem'
		colorRequests = True
	else:
		classPreprintsOngoing = ''

	nPostprintsOngoing = db(
				(db.t_recommendations.recommender_id == auth.user_id)
				& (db.t_recommendations.article_id == db.t_articles.id)
				& (db.t_articles.already_published == True)
				& (db.t_articles.status == 'Under consideration')
			).count()
	if nPostprintsOngoing > 0:
		classPostprintsOngoing = 'pci-enhancedMenuItem'
		colorRequests = True
	else:
		classPostprintsOngoing = ''

	recommendationsMenu.append((SPAN(T('Consider preprint submissions'), _class='pci-recommender'), False, 
							URL('recommender', 'fields_awaiting_articles', user_signature=True)))
	# (gab) proposition :
	recommendationsMenu.append((T('Recommend a postprint'), False, URL('recommender', 'new_submission', user_signature=True)))
	# (gab) fin 


	recommendationsMenu.append(LI(_class="divider"))
	recommendationsMenu.append((SPAN(SPAN(T('Your recommendations of preprints'), _class='pci-recommender'), _class=classPreprintsOngoing), False, 
							URL('recommender', 'my_recommendations', vars=dict(pressReviews=False), user_signature=True)))
	recommendationsMenu.append((SPAN(T('Your co-recommendations'), _class='pci-recommender'), False, 
							URL('recommender', 'my_co_recommendations', vars=dict(pendingOnly=False), user_signature=True)))
	recommendationsMenu.append((SPAN(SPAN(T('Your recommendations of postprints'), _class='pci-recommender'), _class=classPostprintsOngoing), False, 
							URL('recommender', 'my_recommendations', vars=dict(pressReviews=True), user_signature=True)))
	
	
	if colorRequests:
		#requestsMenuTitle = IMG(_title=T('Requests for input'), _alt=T('Requests for input'), _src=URL(c='static', f='images/inputs_enhanced.png'), _class='pci-menuImage')
		requestsMenuTitle = SPAN(SPAN(T('Your Recommendations'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"), _class='pci-recommender'), _class='pci-enhancedMenuItem')
	else:
		#requestsMenuTitle = IMG(_title=T('Requests for input'), _alt=T('Requests for input'), _src=URL(c='static', f='images/inputs.png'), _class='pci-menuImage')
		requestsMenuTitle = SPAN(T('Your Recommendations'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"), _class='pci-recommender')

	return [
		(requestsMenuTitle,  isActive, '#', recommendationsMenu)
	]

# Appends managers menu
def _ManagerMenu():
	ctr = request.controller
	isActive = False
	if ctr == 'manager':
		isActive = True

	#txtMenu = IMG(_title=T('Manage'), _alt=T('Manage'), _src=URL(c='static', f='images/manage.png'), _class='pci-menuImage')
	txtMenu = SPAN(T('Manage'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"))
	
	nbPend = db( db.t_articles.status.belongs(('Pending', 'Pre-recommended', 'Pre-revision', 'Pre-rejected')) ).count()
	txtPending = str(nbPend)+' '+(T('Pending validations') if nbPend > 1 else T('Pending validation'))
	if nbPend>0:
		txtPending = SPAN(SPAN(txtPending, _class='pci-enhancedMenuItem'), _class='pci-manager')
		#txtMenu = IMG(_title=T('Manage'), _alt=T('Manage'), _src=URL(c='static', f='images/manage_enhanced.png'), _class='pci-menuImage')
		txtMenu = SPAN(T('Manage'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"), _class='pci-enhancedMenuItem')
	
	nbGoing = db( db.t_articles.status.belongs(('Under consideration', 'Awaiting revision', 'Awaiting consideration')) ).count()
	txtGoing = str(nbGoing)+' '+(T('Recommendation processes underway') if nbGoing > 1 else T('Recommendation process underway'))
	if nbGoing>0:
		txtGoing = SPAN(SPAN(txtGoing, _class='pci-enhancedMenuItem'), _class='pci-manager')
		#txtMenu = IMG(_title=T('Manage'), _alt=T('Manage'), _src=URL(c='static', f='images/manage_enhanced.png'), _class='pci-menuImage')
		txtMenu = SPAN(T('Manage'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"), _class='pci-enhancedMenuItem')


	return [
        (SPAN(txtMenu, _class='pci-manager'), isActive, '#', [
			(txtPending, False, URL('manager', 'pending_articles', user_signature=True)),
			(txtGoing, False, URL('manager', 'ongoing_articles', user_signature=True)),
			(SPAN(T('Recommenders\' tasks underway')),  False, URL('manager', 'all_recommendations', user_signature=True)),
			(SPAN(T('Recommendation processes completed'), _class='pci-manager'),   False, URL('manager', 'completed_articles', user_signature=True)),
			(SPAN(T('All articles'), _class='pci-manager'),   False, URL('manager', 'all_articles', user_signature=True)),
			(SPAN(T('Comments'), _class='pci-manager'),   False, URL('manager', 'manage_comments', user_signature=True)),
		]),
	]	


def _AboutMenu():
	ctr = request.controller
	isActive = False
	if ctr == 'about':
		isActive = True

	showGuideLines = myconf.get('menu.guidelines', False)

	aboutMenu = []

	aboutMenu += [
			#LI(_class="divider"),
			(T('About', lazy=False)+appName, False, URL('about', 'about')),
			(T('General Terms of Use', lazy=False),       False, URL('about', 'gtu')),
			(T('Code of conduct', lazy=False),      False, URL('about', 'ethics')),
			(T('Supporting organisations', lazy=False),      False, URL('about', 'supports')),
			(T('Recommenders', lazy=False),  False, URL('about', 'recommenders')),
			# (gab) added this cause use nowhere
			(T('Managers', lazy=False),  False, URL('about', 'managers')),
			(T('Thanks to reviewers', lazy=False),  False, URL('about', 'thanks_to_reviewers')),
			(T('Resources', lazy=False),  False, URL('about', 'resources')),
			(T('Contact & credits', lazy=False),      False, URL('about', 'contact')),
			##TODO: for later use?
			##(T('They talk about', lazy=False)+appName,      False, URL('about', 'buzz')),
		]

	return [
		(SPAN(T('About'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px")), isActive, '#', aboutMenu)
	]


def _HelpMenu():
	ctr = request.controller
	isActive = False
	if ctr == 'help':
		isActive = True

	showGuideLines = myconf.get('menu.guidelines', False)

	helpMenu = []

	helpMenu += [
		(T('How does it work?'),  False, URL('help', 'help_generic')),
	]

	if showGuideLines:
		helpMenu += [
			(T('Submission guidelines'),  False, URL('help', 'help_guidelines')),
		]

	helpMenu += [
		(T('How to ...?'), False, URL('help', 'help_practical')),
		(T('FAQs', lazy=False), False, URL('help', 'faq')),
		(T('How should you cite an article?', lazy=False), False, URL('help', 'cite')),
	]
	
	return [
		(SPAN(T('Help'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px")), isActive, '#', helpMenu)
	]


def _AccountMenu():
	ctr = request.controller
	fct = request.function
	isActive = False
	if ctr == 'default' and fct == 'user':
		isActive = True
	
	txtMenu = SPAN(T('Log in'), I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"))
	auth_menu = []

	if auth.is_logged_in():
		txtMenu = SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-user"), auth.user.first_name, I(_class="glyphicon glyphicon-triangle-bottom", _style="font-size: 12px; margin-right: Opx; margin-left: 7.5px; top: 1px"))

		hasPublicProfilePage = (db( (db.auth_membership.user_id==auth.user.id) ).count() > 0) or auth.has_membership(role='administrator') or auth.has_membership(role='developper')

		if hasPublicProfilePage:
			auth_menu += [
				(SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-briefcase"), T('Public page')), False,  URL(c='public', f='user_public_page', vars=dict(userId=auth.user.id))),
				LI(_class="divider")
			]

		auth_menu += [
			(SPAN(I( _class="pci2-icon-margin-right glyphicon glyphicon-user"), T('Profile')), False, URL('default', 'user/profile', user_signature=True)),
			(SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-lock"), T('Change password')), False, URL('default', 'user/change_password', user_signature=True)),
			LI(_class="divider"),
			(SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-off"), T('Log out')), False, URL('default', 'user/logout', user_signature=True))
		]
	else:
		auth_menu += [
			(SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-log-in"), T('Log in')), False, URL('default', 'user/login', user_signature=True)),
			(SPAN(I(_class="pci2-icon-margin-right glyphicon glyphicon-edit"), T('Sign up')), False, URL('default', 'user/register', user_signature=True))
		]

	return [(SPAN(txtMenu, _class='pci-manager'), isActive, '#', auth_menu)]

response.menu = _BaseMenu()
response.footer_menu = _BaseMenu()


if auth.is_logged_in():
	response.menu += _UserMenu()
	response.footer_menu += _UserMenu()

if auth.has_membership(None, None, 'recommender'):
	response.menu += _RecommendationMenu()
	response.footer_menu += _RecommendationMenu()

if auth.has_membership(None, None, 'manager'):
	response.menu += _ManagerMenu()
	response.footer_menu += _ManagerMenu()

if auth.has_membership(None, None, 'administrator') or auth.has_membership(None, None, 'developper'):
	response.menu += _AdminMenu()
	response.footer_menu += _AdminMenu()

if auth.has_membership(None, None, 'administrator') or auth.has_membership(None, None, 'manager') or auth.has_membership(None, None, 'developper'):
	response.menu += _ToolsMenu()
	response.footer_menu += _ToolsMenu()

if auth.has_membership(None, None, 'developper'):
	response.menu += _DevMenu()

response.footer_menu += _AboutMenu()
response.footer_menu += _HelpMenu()

response.help_about_menu = _AboutMenu()
response.help_about_menu += _HelpMenu()
response.help_about_menu += _AccountMenu()


# set the language
if 'adminLanguage' in request.cookies and not (request.cookies['adminLanguage'] is None):
    T.force(request.cookies['adminLanguage'].value)
