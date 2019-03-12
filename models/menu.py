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
    txtMenu = T('Development')
    return [
        (txtMenu, False, '#', [
	    (T('TEST: Recommenders country map'),  False, URL('maps', 'recommenders_map', user_signature=True)),
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
	showGuideLines = myconf.get('menu.guidelines', False)
	helpMenu = []
	aboutMenu = []

	helpMenu += [
		(T('How does it work?'),  False, URL('about', 'help_generic')),
	]
	if showGuideLines:
		helpMenu += [
			(T('Submission guidelines'),  False, URL('about', 'help_guidelines')),
		]
	helpMenu += [
		(T('How to ...?'),        False, URL('about', 'help_practical')),
		(T('FAQs', lazy=False),      False, URL('about', 'faq')),
		(T('How should you cite an article?', lazy=False), False, URL('about', 'cite')),
	]
	#if auth.is_logged_in():
		#helpMenu.append((T('Help for registered users', lazy=False), False, URL('about', 'help_user')))
	aboutMenu += [
			#LI(_class="divider"),
			(T('About', lazy=False)+appName,       False, URL('about', 'about')),
			(T('General Terms of Use', lazy=False),       False, URL('about', 'gtu')),
			(T('Code of conduct', lazy=False),      False, URL('about', 'ethics')),
			(T('Supporting organisations', lazy=False),      False, URL('about', 'supports')),
			(T('Recommenders', lazy=False),  False, URL('public', 'recommenders')),
			(T('Thanks to reviewers', lazy=False),  False, URL('about', 'thanks_to_reviewers')),
			(T('Resources', lazy=False),  False, URL('about', 'resources')),
			(T('Contact & credits', lazy=False),      False, URL('about', 'contact')),
			##TODO: for later use?
			##(T('They talk about', lazy=False)+appName,      False, URL('about', 'buzz')),
		]
	
	recommendationsMenu = [
			(T(u'🔍 Search articles'), False, URL('public', 'recommended_articles')),
			(T('All recommended articles'), False, URL('public', 'all_recommended_articles')),
		]
	
	menuBar = [
		(T('Home'),       False, URL('default', 'index')),
		#(T(u'🔍 Search'), False, URL('public', 'recommended_articles')),
		(T('Articles'),      False, '#', recommendationsMenu),
		(T('About'),      False, '#', aboutMenu),
		(T('Help'),       False, '#', helpMenu),
	]
	return menuBar

def _ToolsMenu():
	if auth.has_membership(None, None, 'administrator'):
		myClass = 'pci-admin'
	else:
		myClass = 'pci-manager'
	return [
		(SPAN(T('Tools'), _class=myClass), False, '#', [
			(T('Convert PDF to MarkDown'),  False, URL('tools', 'convert_pdf_to_markdown', user_signature=True)),
			#(T('Convert PDF to HTML'),  False, URL('tools', 'convert_pdf_to_html', user_signature=True)),
		]),
	]

# Appends administrators menu
def _AdminMenu():
	return [
		(SPAN(T('Admin.'), _class='pci-admin'), False, '#', [
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
			(T('Help texts'),        False, URL('help',  'help_texts', user_signature=True)),
			LI(_class="divider"),
			(T('Send email alerts manually'), False, URL('alerts', 'alertUsersLastRecommendations')),
			LI(_class="divider"),
			(T('Send me a test mail'), False, URL('admin', 'testMail')),
			(T('Test my email alert'), False, URL('alerts', 'testUserRecommendedAlert', vars=dict(userId=auth.user_id))),
			#(T('Test ALL email alerts'), False, URL('alerts', 'alertUsers')),
			(T('Logout', lazy=False),      False, URL('default', 'user', args=['logout'])),
			(T('RSS for bioRxiv'), False, URL('public', 'rss4bioRxiv')),
			(T('Social networks', lazy=False),      False, URL('about', 'social')),
		]),
	]


# Appends personnal menu
def _UserMenu():
	# prepare 2 submenus
	myContributionsMenu = []
	myInvitationsMenu = []
	nPostprintsOngoing = 0
	nPreprintsOngoing = 0
	nRevOngoing = 0
	nRevTot = 0
	revClass = ''
	contribMenuClass = ''
	### contributions menu
	#myContributionsMenu.append((T('Request a recommendation for your preprint'), False, URL('user', 'new_submission', user_signature=True)))

	# reviews
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
		myContributionsMenu.append(LI(_class="divider"))
		myContributionsMenu.append((SPAN(T('Your reviews'), _class=revClass), False, URL('user', 'my_reviews', vars=dict(pendingOnly=False), user_signature=True)))
	
	# recommendations
	if auth.has_membership(None, None, 'recommender'):
		nPreprintsOngoing = db(
					(db.t_recommendations.recommender_id == auth.user_id)
					& (db.t_recommendations.article_id == db.t_articles.id)
					& ~(db.t_articles.already_published == True)
					& (db.t_articles.status == 'Under consideration')
				).count()
		if nPreprintsOngoing > 0:
			classPreprintsOngoing = 'pci-enhancedMenuItem'
			contribMenuClass = 'pci-enhancedMenuItem'
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
			contribMenuClass = 'pci-enhancedMenuItem'
		else:
			classPostprintsOngoing = ''
		myContributionsMenu.append(LI(_class="divider"))
		myContributionsMenu.append((SPAN(SPAN(T('Your recommendations of preprints'), _class='pci-recommender'), _class=classPreprintsOngoing), False, 
								URL('recommender', 'my_recommendations', vars=dict(pressReviews=False), user_signature=True)))
		myContributionsMenu.append(LI(_class="divider"))
		myContributionsMenu.append((SPAN(SPAN(T('Your recommendations of postprints'), _class='pci-recommender'), _class=classPostprintsOngoing), False, 
								URL('recommender', 'my_recommendations', vars=dict(pressReviews=True), user_signature=True)))
		myContributionsMenu.append((SPAN(T('Your co-recommendations'), _class='pci-recommender'), False, 
								URL('recommender', 'my_co_recommendations', vars=dict(pendingOnly=False), user_signature=True)))

	
	### Invitations menu
	colorRequests = False
	# pending reviews, if any
	nRevPend = db(  (db.t_reviews.reviewer_id == auth.user_id) 
					& (db.t_reviews.review_state=='Pending') 
					& (db.t_reviews.recommendation_id == db.t_recommendations.id)
					& (db.t_recommendations.article_id == db.t_articles.id) 
					& (db.t_articles.status == 'Under consideration') 
			   ).count()
	txtRevPend = SPAN(T('Do you agree to review a preprint?'), _class='pci-recommender')
	if nRevPend > 0:
		txtRevPend = SPAN(txtRevPend, _class='pci-enhancedMenuItem')
		colorRequests = True
	myInvitationsMenu.append((txtRevPend, False, 
							URL('user', 'my_reviews', vars=dict(pendingOnly=True), user_signature=True)))
	
	# recommendations
	if auth.has_membership(None, None, 'recommender'):
		nPreprintsRecomPend = db( 	(db.t_articles.status == 'Awaiting consideration') 
								  & (db.t_articles._id == db.t_suggested_recommenders.article_id) 
								  & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id) 
								  & (db.t_suggested_recommenders.declined == False)
								).count()
		#print('nPreprintsRecomPend=%s' % (nPreprintsRecomPend))
		txtPreprintsRecomPend = SPAN('Do you agree to initiate a recommendation?', _class='pci-recommender')
		if nPreprintsRecomPend > 0:
			txtPreprintsRecomPend = SPAN(txtPreprintsRecomPend, _class='pci-enhancedMenuItem')
			colorRequests = True
		myInvitationsMenu.append((txtPreprintsRecomPend,False, 
								URL('recommender', 'my_awaiting_articles', vars=dict(pendingOnly=True, pressReviews=False), user_signature=True))) 
		myInvitationsMenu += [
				LI(_class="divider"),
				(SPAN(T('Consider preprint submissions'), _class='pci-recommender'),          False, URL('recommender', 'fields_awaiting_articles', user_signature=True)),
			]
	resu = [
        (SPAN(T('Your contributions'), _class=contribMenuClass),       False, '#', myContributionsMenu),
	]
	if colorRequests:
		#requestsMenuTitle = IMG(_title=T('Requests for input'), _alt=T('Requests for input'), _src=URL(c='static', f='images/inputs_enhanced.png'), _class='pci-menuImage')
		requestsMenuTitle = SPAN(SPAN(T('Requests for input'), _class='pci-recommender'), _class='pci-enhancedMenuItem')
	else:
		#requestsMenuTitle = IMG(_title=T('Requests for input'), _alt=T('Requests for input'), _src=URL(c='static', f='images/inputs.png'), _class='pci-menuImage')
		requestsMenuTitle = SPAN(T('Requests for input'), _class='pci-recommender')
	if (auth.has_membership(None, None, 'recommender') or ( auth.is_logged_in() and colorRequests ) ):
		resu.append( (requestsMenuTitle,  False, '#', myInvitationsMenu) )
	return resu


# Appends managers menu
def _ManagerMenu():
	#txtMenu = IMG(_title=T('Manage'), _alt=T('Manage'), _src=URL(c='static', f='images/manage.png'), _class='pci-menuImage')
	txtMenu = T('Manage')
	
	nbPend = db( db.t_articles.status.belongs(('Pending', 'Pre-recommended', 'Pre-revision', 'Pre-rejected')) ).count()
	txtPending = str(nbPend)+' '+(T('Pending validations') if nbPend > 1 else T('Pending validation'))
	if nbPend>0:
		txtPending = SPAN(SPAN(txtPending, _class='pci-enhancedMenuItem'), _class='pci-manager')
		#txtMenu = IMG(_title=T('Manage'), _alt=T('Manage'), _src=URL(c='static', f='images/manage_enhanced.png'), _class='pci-menuImage')
		txtMenu = SPAN(T('Manage'), _class='pci-enhancedMenuItem')
	
	nbGoing = db( db.t_articles.status.belongs(('Under consideration', 'Awaiting revision', 'Awaiting consideration')) ).count()
	txtGoing = str(nbGoing)+' '+(T('Recommendation processes underway') if nbGoing > 1 else T('Recommendation process underway'))
	if nbGoing>0:
		txtGoing = SPAN(SPAN(txtGoing, _class='pci-enhancedMenuItem'), _class='pci-manager')
		#txtMenu = IMG(_title=T('Manage'), _alt=T('Manage'), _src=URL(c='static', f='images/manage_enhanced.png'), _class='pci-menuImage')
		txtMenu = SPAN(T('Manage'), _class='pci-enhancedMenuItem')
		
	return [
        (SPAN(txtMenu, _class='pci-manager'), False, '#', [
			(txtPending, False, URL('manager', 'pending_articles', user_signature=True)),
			(txtGoing, False, URL('manager', 'ongoing_articles', user_signature=True)),
			(SPAN(T('Recommendation processes completed'), _class='pci-manager'),   False, URL('manager', 'completed_articles', user_signature=True)),
			(SPAN(T('All articles'), _class='pci-manager'),   False, URL('manager', 'all_articles', user_signature=True)),
			(SPAN(T('Comments'), _class='pci-manager'),   False, URL('manager', 'manage_comments', user_signature=True)),
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

if auth.has_membership(None, None, 'administrator') or auth.has_membership(None, None, 'manager') or auth.has_membership(None, None, 'developper'):
	response.menu += _ToolsMenu()

if auth.has_membership(None, None, 'developper'):
	response.menu += _DevMenu()

# set the language
if 'adminLanguage' in request.cookies and not (request.cookies['adminLanguage'] is None):
    T.force(request.cookies['adminLanguage'].value)
