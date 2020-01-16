# -*- coding: utf-8 -*-

import re
import copy
import datetime
from dateutil.relativedelta import *
from gluon.utils import web2py_uuid
from gluon.contrib.markdown import WIKI
from gluon.html import markmin_serializer

from app_modules.common import *
from app_modules.helper import *

from app_modules import recommender_module
from app_modules import common_tools
from app_modules import new_common

# frequently used constants
myconf = AppConfig(reload=True)
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get('config.parallel_submission', default=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4


######################################################################################################################################################################
## Menu Routes
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def new_submission():
	response.view='default/info.html'

	ethics_not_signed = not(db.auth_user[auth.user_id].ethical_code_approved)
	if ethics_not_signed:
		redirect(URL(c='about', f='ethics', vars=dict(_next=URL())))
	else:
		c = getText(request, auth, db, '#ConflictsForRecommenders')
		myEthical = DIV(
				FORM(
					DIV(
						SPAN(INPUT(_type="checkbox", _name="no_conflict_of_interest", _id="no_conflict_of_interest", _value="yes", value=False), LABEL(T('I declare that I have no conflict of interest with the authors or the content of the article'))), 
						DIV(c), 
						_style='padding:16px;'),
					INPUT(_type='submit', _value=T("Recommend a postprint"), _class="btn btn-success pci-panelButton pci-recommender"), 
					hidden=dict(ethics_approved=True),
					_action=URL('recommender', 'direct_submission'),
					_style='text-align:center;',
				),
				_class="pci-embeddedEthic",
			)
		myScript = SCRIPT(common_tools.get_template('script', 'new_submission.js'))

	myText = DIV(
				getText(request, auth, db, '#NewRecommendationInfo'),
				myEthical,
			)

	return dict(
		myTitle=getTitle(request, auth, db, '#RecommenderBeforePostprintSubmissionTitle'),
		myText = myText,
		myFinalScript = myScript
	)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def search_reviewers():
	response.view='default/list_layout.html'

	# We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
	temp_db = DAL('sqlite:memory')
	qy_reviewers = temp_db.define_table('qy_reviewers',
		Field('id', type='integer'),
		Field('num', type='integer'),
		Field('score', type='double', label=T('Score'), default=0),
		Field('first_name', type='string', length=128, label=T('First name')),
		Field('last_name', type='string', length=128, label=T('Last name')),
		Field('email', type='string', length=512, label=T('email')),
		Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
		Field('city', type='string', label=T('City')),
		Field('country', type='string', label=T('Country')),
		Field('laboratory', type='string', label=T('Laboratory')),
		Field('institution', type='string', label=T('Institution')),
		Field('thematics', type='list:string', label=T('Thematic fields')),
		Field('roles', type='string', length=1024, label=T('Roles')),
		Field('excluded', type='boolean', label=T('Excluded')),
	)
	temp_db.qy_reviewers.email.represent = lambda text, row: A(text, _href='mailto:'+text)
	myVars = request.vars
	qyKw = ''
	qyTF = []
	excludeList = []
	myGoal = '4review' # default
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (myVar == 'myGoal'):
			myGoal = myValue
		elif (myVar == 'exclude'):
			excludeList = map(int, myValue.split(','))
		elif (re.match('^qy_', myVar) and myValue=='on'):
			qyTF.append(re.sub(r'^qy_', '', myVar))

	if 'recommId' in request.vars:
		recommId = request.vars['recommId']
		if recommId:
			recomm = db.t_recommendations[recommId]
			if recomm:
				excludeList.append(recomm.recommender_id)
				art = db.t_articles[recomm.article_id]
				if art:
					uid = art.user_id
					if uid:
						excludeList.append(uid)
						
	qyKwArr = qyKw.split(' ')
	searchForm = new_common.getSearchForm(auth, db, myVars, allowBlank=True)
	if searchForm.process(keepvalues=True).accepted:
		response.flash = None
	else:
		qyTF = []
		for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
			qyTF.append(thema.keyword)


	filtered = db.executesql('SELECT * FROM search_reviewers(%s, %s, %s);', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
	for fr in filtered:
		qy_reviewers.insert(**fr)
			
	temp_db.qy_reviewers._id.readable = False
	temp_db.qy_reviewers.uploaded_picture.readable = False
	temp_db.qy_reviewers.excluded.readable = False
	links = []
	if 'recommId' in request.vars:
		recommId = request.vars['recommId']
		links.append(  dict(header=T('Days since last recommendation'), body=lambda row: db.v_last_recommendation[row.id].days_since_last_recommendation)  )
		if myGoal == '4review':
			links.append(  dict(header=T('Select'), body=lambda row: '' if row.excluded else mkSuggestReviewToButton(auth, db, row, recommId, myGoal)) )
			#myTitle = T('Search for reviewers')
			myTitle=getTitle(request, auth, db, '#RecommenderSearchReviewersTitle')
			myText=getText(request, auth, db, '#RecommenderSearchReviewersText')
			myHelp=getHelp(request, auth, db, '#RecommenderSearchReviewers')
		elif myGoal == '4press':
			links.append(  dict(header=T('Propose contribution'), body=lambda row: '' if row.excluded else mkSuggestReviewToButton(auth, db, row, recommId, myGoal))  )
			#myTitle = T('Search for collaborators')
			myTitle=getTitle(request, auth, db, '#RecommenderSearchCollaboratorsTitle')
			myText=getText(request, auth, db, '#RecommenderSearchCollaboratorsText')
			myHelp=getHelp(request, auth, db, '#RecommenderSearchCollaborators')
	temp_db.qy_reviewers.num.readable=False
	temp_db.qy_reviewers.score.readable=False
	grid = SQLFORM.grid( qy_reviewers
		,editable = False,deletable = False,create = False,details=False,searchable=False
		,maxtextlength=250
		,paginate=1000
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_reviewers.num, temp_db.qy_reviewers.score, temp_db.qy_reviewers.uploaded_picture, temp_db.qy_reviewers.first_name, temp_db.qy_reviewers.last_name, temp_db.qy_reviewers.email, temp_db.qy_reviewers.laboratory, temp_db.qy_reviewers.institution, temp_db.qy_reviewers.city, temp_db.qy_reviewers.country, temp_db.qy_reviewers.thematics, temp_db.qy_reviewers.excluded]
		,links=links
		,orderby=temp_db.qy_reviewers.num
		,args=request.args
	)
	return dict(
				myHelp=myHelp,
				myTitle=myTitle,
				myText=myText,
				myBackButton=mkBackButton(),
				searchForm=searchForm, 
				grid=grid, 
			 )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def my_awaiting_articles():
	response.view='default/myLayout.html'

	query = ( 
				(db.t_articles.status == 'Awaiting consideration')
			  & (db.t_articles._id == db.t_suggested_recommenders.article_id) 
			  & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
			  & (db.t_suggested_recommenders.declined == False)
		)
	db.t_articles.user_id.writable = False
	db.t_articles.user_id.represent = lambda userId, row: mkAnonymousArticleField(auth, db, row.anonymous_submission, mkUser(auth, db, userId))
	#db.t_articles.doi.represent = lambda text, row: mkDOI(text)
	db.t_articles.auto_nb_recommendations.readable = False
	db.t_articles.anonymous_submission.readable = False
	db.t_articles.anonymous_submission.writable = False
	db.t_articles.status.writable = False
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	if len(request.args) == 0: # we are in grid
		#db.t_articles.doi.readable = False
		#db.t_articles.authors.readable = False
		#db.t_articles.title.readable = False
		db.t_articles.upload_timestamp.represent = lambda t, row: mkLastChange(t)
		db.t_articles.last_status_change.represent = lambda t, row: mkLastChange(t)
		db.t_articles._id.readable = True
		db.t_articles._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
		db.t_articles._id.label = T('Article')
		db.t_articles.abstract.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
	else: # we are in grid's form
		db.t_articles._id.readable = False
		db.t_articles.abstract.represent=lambda text, row: WIKI(text)
	if parallelSubmissionAllowed:
		fields = [db.t_articles._id, db.t_articles.anonymous_submission, db.t_articles.parallel_submission, db.t_articles.abstract, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.user_id, db.t_articles.upload_timestamp, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations, db.t_articles.status]
	else:
		fields = [db.t_articles._id, db.t_articles.anonymous_submission, db.t_articles.abstract, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.user_id, db.t_articles.upload_timestamp, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations, db.t_articles.status]
	grid = SQLFORM.grid( query
		,searchable=False,editable=False,deletable=False,create=False,details=False
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,fields=fields
		,links=[
			dict(header=T('Suggested recommenders'), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders),
			dict(header=T(''), body=lambda row: recommender_module.mkViewEditArticleRecommenderButton(auth, db, row)),
		]
		,orderby=~db.t_articles.upload_timestamp
	)
	return dict(
				myHelp=getHelp(request, auth, db, '#RecommenderSuggestedArticles'),
				myText=getText(request, auth, db, '#RecommenderSuggestedArticlesText'),
				myTitle=getTitle(request, auth, db, '#RecommenderSuggestedArticlesTitle'),
				grid=grid, 
			)



######################################################################################################################################################################
# Common function for articles needing attention
@auth.requires(auth.has_membership(role='recommender'))
def _awaiting_articles(myVars):
	response.view='default/list_layout.html'

	# We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
	temp_db = DAL('sqlite:memory')
	qy_art = temp_db.define_table('qy_art',
		Field('id', type='integer'),
		Field('num', type='integer'),
		Field('score', type='double', label=T('Score'), default=0),
		Field('title', type='text', label=T('Title')),
		Field('authors', type='text', label=T('Authors')),
		Field('article_source', type='string', label=T('Source')),
		Field('doi', type='string', label=T('DOI')),
		Field('abstract', type='text', label=T('Abstract')),
		Field('upload_timestamp', type='datetime', default=request.now, label=T('Submission date')),
		Field('thematics', type='string', length=1024, label=T('Thematic fields')),
		Field('keywords', type='text', label=T('Keywords')),
		Field('auto_nb_recommendations', type='integer', label=T('Rounds of reviews'), default=0),
		Field('status', type='string', length=50, default='Pending', label=T('Status')),
		Field('last_status_change', type='datetime', default=request.now, label=T('Last status change')),
		Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
		Field('already_published', type='boolean', label=T('Postprint')),
		Field('anonymous_submission', type='boolean', label=T('Anonymous submission')),
		Field('parallel_submission', type='boolean', label=T('Parallel submission')),
	)
	myVars = request.vars
	qyKw = ''
	qyTF = []
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (re.match('^qy_', myVar) and myValue=='on'):
			qyTF.append(re.sub(r'^qy_', '', myVar))
	qyKwArr = qyKw.split(' ')

	search = new_common.getSearchForm(auth, db, myVars)

	filtered = db.executesql('SELECT * FROM search_articles(%s, %s, %s, %s, %s);', placeholders=[qyTF, qyKwArr, 'Awaiting consideration', trgmLimit, True], as_dict=True)
	
	for fr in filtered:
		qy_art.insert(**fr)
	
	temp_db.qy_art.auto_nb_recommendations.readable = False
	temp_db.qy_art.uploaded_picture.represent = lambda text,row: (IMG(_src=URL('default', 'download', args=text), _width=100)) if (text is not None and text != '') else ('')
	temp_db.qy_art.authors.represent = lambda text, row: mkAnonymousArticleField(auth, db, row.anonymous_submission, (text or ''))
	temp_db.qy_art.anonymous_submission.represent = lambda anon, row: mkAnonymousMask(auth, db, anon or False)
	temp_db.qy_art.parallel_submission.represent = lambda p,r:SPAN('//', _class="pci-parallelSubmission") if p else ''
	if len(request.args)==0: # in grid
		temp_db.qy_art._id.readable = True
		temp_db.qy_art._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
		temp_db.qy_art._id.label = T('Article')
		temp_db.qy_art.title.readable = False
		temp_db.qy_art.authors.readable = False
		#temp_db.qy_art.status.readable = False
		temp_db.qy_art.article_source.readable = False
		temp_db.qy_art.upload_timestamp.represent = lambda t, row: mkLastChange(t)
		temp_db.qy_art.last_status_change.represent = lambda t, row: mkLastChange(t)
		temp_db.qy_art.abstract.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
		temp_db.qy_art.status.represent = lambda text, row: mkStatusDiv(auth, db, row.status)
		temp_db.qy_art.num.readable = False
		temp_db.qy_art.score.readable = False
	else:
		temp_db.qy_art._id.readable = False
		temp_db.qy_art.num.readable = False
		temp_db.qy_art.score.readable = False
		temp_db.qy_art.doi.represent = lambda text, row: mkDOI(text)
		temp_db.qy_art.abstract.represent = lambda text, row: WIKI(text or '')
		
	links = []
	#links.append(dict(header=T('Suggested recommenders'), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders))
	links.append(dict(header=T(''), body=lambda row: recommender_module.mkViewEditArticleRecommenderButton(auth, db, row)))
	if parallelSubmissionAllowed:
		fields = [temp_db.qy_art.num, temp_db.qy_art.score, temp_db.qy_art.uploaded_picture, temp_db.qy_art._id, temp_db.qy_art.title, temp_db.qy_art.authors, temp_db.qy_art.article_source, temp_db.qy_art.anonymous_submission, temp_db.qy_art.parallel_submission, temp_db.qy_art.abstract, temp_db.qy_art.thematics, temp_db.qy_art.keywords, temp_db.qy_art.upload_timestamp, temp_db.qy_art.last_status_change, temp_db.qy_art.status, temp_db.qy_art.auto_nb_recommendations]
	else:
		fields = [temp_db.qy_art.num, temp_db.qy_art.score, temp_db.qy_art.uploaded_picture, temp_db.qy_art._id, temp_db.qy_art.title, temp_db.qy_art.authors, temp_db.qy_art.article_source, temp_db.qy_art.anonymous_submission, temp_db.qy_art.abstract, temp_db.qy_art.thematics, temp_db.qy_art.keywords, temp_db.qy_art.upload_timestamp, temp_db.qy_art.last_status_change, temp_db.qy_art.status, temp_db.qy_art.auto_nb_recommendations]
	grid = SQLFORM.grid(temp_db.qy_art
		,searchable=False,editable=False,deletable=False,create=False,details=False
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,fields=fields
		,links=links
		,orderby=temp_db.qy_art.num
	)
	return dict(
				#myTitle=T('Articles requiring a recommender'), 
				myTitle=getTitle(request, auth, db, '#RecommenderAwaitingArticlesTitle'),
				myText=getText(request, auth, db, '#RecommenderAwaitingArticlesText'),
				grid=grid, 

				searchableList = True,
				search = search
			)



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def fields_awaiting_articles():
	resu = _awaiting_articles(request.vars)
	resu['myHelp'] = getHelp(request, auth, db, '#RecommenderArticlesAwaitingRecommendation:InMyFields')
	resu['myText'] = getText(request, auth, db, '#RecommenderArticlesAwaitingRecommendationText:InMyFields')
	return resu



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def all_awaiting_articles():
	myVars = request.vars
	for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
		myVars['qy_'+thema.keyword] = 'on'
	resu = _awaiting_articles(myVars)
	resu['myHelp'] = getHelp(request, auth, db, '#RecommenderArticlesAwaitingRecommendation:All')
	resu['myText'] = getText(request, auth, db, '#RecommenderArticlesAwaitingRecommendationText:All')
	return resu



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def article_details():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	amIAllowed = db(  (( db.t_recommendations.article_id == articleId) & (db.t_recommendations.recommender_id == auth.user_id))
					| (( db.t_suggested_recommenders.article_id == articleId) & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id) & (db.t_suggested_recommenders.declined == False))
				).count() > 0
	if (amIAllowed is False) and (art.status == 'Awaiting consideration') and (auth.has_membership(role='recommender')):
		amIAllowed = True
	
	if amIAllowed:
		alreadyUnderProcess = (db( (db.t_recommendations.article_id == articleId) & (db.t_recommendations.recommender_id != auth.user_id) ).count() > 0) 
		
		if printable:
			myTitle = DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
				DIV(
					DIV(mkStatusBigDiv(auth, db, art.status), _class='pci-ArticleText printable'),
					_class='pci-ArticleHeaderIn printable'
				))
			myUpperBtn = ''
			response.view='default/recommended_article_printable.html'
		else:
			myTitle = DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
				DIV(
					DIV(mkStatusBigDiv(auth, db, art.status), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn'
				))
			myUpperBtn = A(SPAN(T('Printable page'), _class='pci-ArticleTopButton buttontext btn btn-info'), 
				_href=URL(c="user", f='recommendations', vars=dict(articleId=articleId, printable=True)),
				_class='button')
			response.view='default/recommended_articles.html'
		
		if alreadyUnderProcess:
			contact = myconf.take('contacts.managers')
			myContents = DIV(
				SPAN("Another recommender has already selected this article (DOI: ", mkDOI(art.doi), "), for which you were considering handling the evaluation. If you wish, we can inform the recommender handling this article that you would like to be a co-recommender or a reviewer (which would be much appreciated). If you are willing to help in this way, simply send us a message at: "), 
				A(contact, _href='mailto:%s' % contact), 
				SPAN(" stating that you want to become a co-recommender or a reviewer, and we will alert the recommender."),
				BR(),
				SPAN("Otherwise, you may",
				A(T('decline'), _href=URL('recommender_actions', 'decline_new_article_to_recommend', vars=dict(articleId=articleId)), _class="btn btn-info")),
				SPAN(' this suggestion.'),
				_class="pci-alreadyUnderProcess")
		else:
			myContents = mkFeaturedArticle(auth, db, art, printable, quiet=False)
			myContents.append(HR())
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderArticlesRequiringRecommender'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)
	else:
		raise HTTP(403, "403: "+T('Access denied'))



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def accept_new_article_to_recommend():
	response.view='default/info.html'

	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	ethics_not_signed = not(db.auth_user[auth.user_id].ethical_code_approved)
	if ethics_not_signed:
		redirect(URL(c='about', f='ethics'))
	else:
		longname = myconf.take('app.longname')
		myEthical = DIV(
				FORM(
					DIV(
						UL(
							LI(INPUT(_type="checkbox", _name="interesting", _id="interesting", _value="yes", value=False), B(T('I find the preprint interesting')), SPAN(T(' and therefore worth sending out for peer-review.'))),
							LI(INPUT(_type="checkbox", _name="invitations", _id="invitations", _value="yes", value=False), B(T('I agree to send invitations to 5-10 potential reviewers within the next 24 hours')), SPAN(T(' and then to send reminders and/or new invitations until I find at least two reviewers willing to review the preprint. This process of finding reviews should take no more than a week.'))),
							LI(INPUT(_type="checkbox", _name="ten_days", _id="ten_days", _value="yes", value=False), B(T('I agree to post my decision')), SPAN(T(' or to write my recommendation text ')), B(T('within 10 days')), SPAN(T(' of receiving the reviews.'))),
							LI(INPUT(_type="checkbox", _name="recomm_text", _id="recomm_text", _value="yes", value=False), B(T('I agree to write a recommendation text')), SPAN(T(' if I decide to recommend this preprint for %s at the end of the evaluation process.') % longname)),
							LI(INPUT(_type="checkbox", _name="no_conflict_of_interest", _id="no_conflict_of_interest", _value="yes", value=False), B(T('I declare that I have no conflict of interest with the authors or the content of the article: ')), SPAN(T('I should not handle articles written by close colleagues (people belonging to the same laboratory/unit/department in the last four years, people with whom they have published in the last four years, with whom they have received joint funding in the last four years, or with whom they are currently writing a manuscript, or submitting a grant proposal), or written by family members, friends, or anyone for whom bias might affect the nature of my evaluation. ')), A(T('See the code of ethical conduct.'), _href=URL(c='about', f='ethics'))), 
							LI(INPUT(_type="checkbox", _name="commitments", _id="commitments", _value="yes", value=False), I(T('I understand that if I do not respect these commitments, the managing board of %s reserves the right to pass responsibility for the evaluation of this article to someone else.') % longname)),
							_style="list-style-type:none;"),
						_class='pci-ChecksList',
					),
					DIV(
						INPUT(_type='submit', _value=T("Yes, I will consider this preprint for recommendation"), _class="btn btn-success pci-panelButton"), 
						_style='text-align:center;',
					),
					hidden=dict(articleId=articleId, ethics_approved=True),
					_action=URL('recommender_actions', 'do_accept_new_article_to_recommend'),
				),
				#_class="pci-embeddedEthic",
			)
		myScript = SCRIPT(common_tools.get_template('script', 'accept_new_article_to_recommend.js'))

	myTitle = getTitle(request, auth, db, '#AcceptPreprintInfoTitle')
	myText = DIV(
			getText(request, auth, db, '#AcceptPreprintInfoText'),
			myEthical,
	)
	return dict(
		myText=myText,
		myTitle=myTitle,
		myFinalScript = myScript,
	)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def my_recommendations():
	response.view='default/myLayout.html'

	scheme = myconf.take('alerts.scheme')
	host = myconf.take('alerts.host')
	port = myconf.take('alerts.port', cast=lambda v: takePort(v) )
	#goBack='%s://%s%s' % (request.env.wsgi_url_scheme, request.env.http_host, request.env.request_uri)
	goBack = URL(re.sub(r'.*/([^/]+)$', '\\1', request.env.request_uri), scheme=scheme, host=host, port=port)

	isPress = ( ('pressReviews' in request.vars) and (request.vars['pressReviews']=='True') )
	if isPress: ## NOTE: POST-PRINTS
		query = ( (db.t_recommendations.recommender_id == auth.user_id) 
				& (db.t_recommendations.article_id == db.t_articles.id) 
				& (db.t_articles.already_published == True)
			)
		myTitle=getTitle(request, auth, db, '#RecommenderMyRecommendationsPostprintTitle')
		myText=getText(request, auth, db, '#RecommenderMyRecommendationsPostprintText')
		fields = [db.t_recommendations._id, db.t_recommendations.article_id, db.t_articles.status, db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.is_closed]
		links = [
				dict(header=T('Co-recommenders'), body=lambda row: mkCoRecommenders(auth, db, row.t_recommendations if 't_recommendations' in row else row, goBack)),
				dict(header=T(''),             body=lambda row: mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
			]
		db.t_recommendations.article_id.label = T('Postprint')
	else: ## NOTE: PRE-PRINTS
		query = ( (db.t_recommendations.recommender_id == auth.user_id) 
				& (db.t_recommendations.article_id == db.t_articles.id) 
				& (db.t_articles.already_published == False)
			)
		myTitle=getTitle(request, auth, db, '#RecommenderMyRecommendationsPreprintTitle')
		myText=getText(request, auth, db, '#RecommenderMyRecommendationsPreprintText')
		fields = [db.t_recommendations._id, db.t_recommendations.article_id, db.t_articles.status, db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.is_closed, db.t_recommendations.recommendation_state, db.t_recommendations.is_closed, db.t_recommendations.recommender_id]
		links = [
				dict(header=T('Co-recommenders'),    body=lambda row: mkCoRecommenders(auth, db, row.t_recommendations if 't_recommendations' in row else row, goBack)),
				dict(header=T('Reviews'),            body=lambda row: mkReviewsSubTable(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T(''),                   body=lambda row: mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
			]
		db.t_recommendations.article_id.label = T('Preprint')
		
	db.t_recommendations.recommender_id.writable = False
	db.t_recommendations.doi.writable = False
	#db.t_recommendations.article_id.readable = False
	db.t_recommendations.article_id.writable = False
	db.t_recommendations._id.readable = False
	#db.t_recommendations._id.represent = lambda rId, row: mkRepresentRecommendationLight(auth, db, rId)
	db.t_recommendations.recommender_id.readable = False
	db.t_recommendations.recommendation_state.readable = False
	db.t_recommendations.is_closed.readable = False
	db.t_recommendations.is_closed.writable = False
	db.t_recommendations.recommendation_timestamp.label = T('Started')
	db.t_recommendations.last_change.label = T('Last change')
	db.t_recommendations.last_change.represent = lambda text, row: mkElapsedDays(row.t_recommendations.last_change) if 't_recommendations' in row else mkElapsedDays(row.last_change)
	db.t_recommendations.recommendation_timestamp.represent = lambda text, row: mkElapsedDays(row.t_recommendations.recommendation_timestamp) if 't_recommendations' in row else mkElapsedDays(row.recommendation_timestamp)
	db.t_recommendations.article_id.represent = lambda aid, row: DIV(mkArticleCellNoRecomm(auth, db, db.t_articles[aid]), _class='pci-w200Cell')
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	db.t_recommendations.doi.readable=False
	db.t_recommendations.last_change.readable=True
	db.t_recommendations.recommendation_comments.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
	grid = SQLFORM.grid( query
		,searchable=False, create=False, deletable=False, editable=False, details=False
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=fields
		,links=links
		,orderby=~db.t_recommendations.last_change
	)
	return dict(
				#myBackButton=mkBackButton(), 
				myHelp = getHelp(request, auth, db, '#RecommenderMyRecommendations'),
				myTitle=myTitle, 
				myText=myText,
				grid=grid, 
			 )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def direct_submission():
	response.view='default/myLayout.html'

	theUser = db.auth_user[auth.user_id]
	if 'ethics_approved' in request.vars:
		theUser.ethical_code_approved = True
		theUser.update_record()
	if not(theUser.ethical_code_approved):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	noConflict = False
	if 'no_conflict_of_interest' in request.vars:
		if request.vars['no_conflict_of_interest']=='yes':
			noConflict = True
	db.t_articles.user_id.default = None
	db.t_articles.user_id.writable = False
	db.t_articles.status.default = 'Under consideration'
	db.t_articles.status.writable = False
	db.t_articles.already_published.readable = False
	db.t_articles.already_published.writable = False
	db.t_articles.already_published.default = True
	myScript = """jQuery(document).ready(function(){
					
					if(jQuery('#t_articles_picture_rights_ok').prop('checked')) {
						jQuery('#t_articles_uploaded_picture').prop('disabled', false);
					} else {
						jQuery('#t_articles_uploaded_picture').prop('disabled', true);
					}
					jQuery('#t_articles_picture_rights_ok').change(function(){
								if(jQuery('#t_articles_picture_rights_ok').prop('checked')) {
									jQuery('#t_articles_uploaded_picture').prop('disabled', false);
								} else {
									jQuery('#t_articles_uploaded_picture').prop('disabled', true);
									jQuery('#t_articles_uploaded_picture').val('');
								}
					});
				});
	"""
	fields = ['title', 'authors', 'article_source', 'doi', 'picture_rights_ok', 'uploaded_picture', 'abstract', 'thematics', 'keywords', 'picture_data']
	form = SQLFORM( db.t_articles, fields=fields, keepvalues=True, submit_button=T('Continue...'), hidden=dict(no_conflict_of_interest= 'yes' if noConflict else 'no') )
	if form.process().accepted:
		articleId=form.vars.id
		recommId = db.t_recommendations.insert(article_id=articleId, recommender_id=auth.user_id, doi=form.vars.doi, recommendation_state='Ongoing', no_conflict_of_interest=noConflict)
		redirect(URL(c='recommender', f='add_contributor', vars=dict(recommId=recommId, goBack=URL('recommender', 'my_recommendations', vars=dict(pressReviews=True)), onlyAdd=False)))
	return dict(
				myHelp=getHelp(request, auth, db, '#RecommenderDirectSubmission'),
				#myBackButton=mkBackButton(),
				myTitle=getTitle(request, auth, db, '#RecommenderDirectSubmissionTitle'),
				myText=getText(request, auth, db, '#RecommenderDirectSubmissionText'),
				form=form, 
				myFinalScript = SCRIPT(myScript),
			 )



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def recommendations():
	response.view='default/recommended_articles.html'
	printable = False
	articleId = request.vars['articleId']

	art = db.t_articles[articleId]
	if art is None:
		print("Missing article %s" % articleId)
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	# NOTE: 2018-09-05 bug corrected by splitting the query and adding counts; weird but it works
	countPre = db(
					(db.t_recommendations.recommender_id == auth.user_id)
				  & (db.t_recommendations.article_id == articleId) 
			).count()
	countPost = db(
					( (db.t_press_reviews.contributor_id == auth.user_id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id) )
				  & (db.t_recommendations.article_id == articleId) 
			).count()
	amIAllowed = ((countPre + countPost) > 0)
	if not(amIAllowed):
		print("Not allowed: userId=%s, articleId=%s" % (auth.user_id, articleId))
		#print(db._lastsql)
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:

		if art.status == 'Recommended':
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
				DIV(
					DIV(T('Recommended article'), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn recommended'
				))
		else:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
				DIV(
					DIV(mkStatusBigDiv(auth, db, art.status), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn'
				))
		myUpperBtn = A(SPAN(T('Printable page'), _class='buttontext btn btn-info'), 
			_href=URL(c="recommender", f='recommendations_printable', vars=dict(articleId=articleId)),
			_class='button')

		myContents = mkFeaturedArticle(auth, db, art, printable, quiet=False)
		myContents.append(HR())
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderOtherRecommendations'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)

def recommendations_printable():
	response.view='default/recommended_article_printable.html'
	printable = True
	articleId = request.vars['articleId']
	
	art = db.t_articles[articleId]
	if art is None:
		print("Missing article %s" % articleId)
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	# NOTE: 2018-09-05 bug corrected by splitting the query and adding counts; weird but it works
	countPre = db(
					(db.t_recommendations.recommender_id == auth.user_id)
				  & (db.t_recommendations.article_id == articleId) 
			).count()
	countPost = db(
					( (db.t_press_reviews.contributor_id == auth.user_id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id) )
				  & (db.t_recommendations.article_id == articleId) 
			).count()
	amIAllowed = ((countPre + countPost) > 0)
	if not(amIAllowed):
		print("Not allowed: userId=%s, articleId=%s" % (auth.user_id, articleId))
		#print(db._lastsql)
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		
		if art.status == 'Recommended':
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
					DIV(
						DIV(T('Recommended article'), _class='pci-ArticleText'),
						_class='pci-ArticleHeaderIn recommended printable'
					))
		else:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
				DIV(
					DIV(mkStatusBigDiv(auth, db, art.status), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn printable'
				))
		myUpperBtn = ''
		
		myContents = mkFeaturedArticle(auth, db, art, printable, quiet=False)
		myContents.append(HR())
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderOtherRecommendations'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)
			

######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def one_review():
	response.view='default/myLayout.html'

	revId = request.vars['reviewId']
	rev = db.t_reviews[revId]
	form = ''
	if rev == None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm == None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	db.t_reviews._id.readable = False
	#db.t_reviews.recommendation_id.default = recommId
	#db.t_reviews.recommendation_id.writable = False
	#db.t_reviews.recommendation_id.readable = False
	db.t_reviews.reviewer_id.writable = False
	#db.t_reviews.reviewer_id.default = auth.user_id
	db.t_reviews.reviewer_id.represent = lambda text,row: mkUserWithMail(auth, db, row.reviewer_id) if row else ''
	db.t_reviews.anonymously.default = True
	db.t_reviews.anonymously.writable = auth.has_membership(role='manager')
	db.t_reviews.review.writable = auth.has_membership(role='manager')
	db.t_reviews.review_state.writable = auth.has_membership(role='manager')
	db.t_reviews.review_state.represent = lambda text,row: mkReviewStateDiv(auth, db, text)
	db.t_reviews.review.represent = lambda text,row: WIKI(text)
	#db.t_reviews.review_pdf
	form = SQLFORM(db.t_reviews, record=revId, readonly=True
					,fields=['reviewer_id', 'no_conflict_of_interest', 'anonymously', 'review', 'review_pdf']
					,showid=False
					,upload=URL('default', 'download')
				)
	return dict(
			myHelp = getHelp(request, auth, db, '#RecommenderArticleOneReview'),
			myText=getText(request, auth, db, '#RecommenderArticleOneReviewText'),
			myTitle=getTitle(request, auth, db, '#RecommenderArticleOneReviewTitle'),
			myBackButton=mkCloseButton(),
			#content=myContents, 
			form=form, 
			#myFinalScript=myScript,
			)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reviews():
	response.view='default/myLayout.html'

	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if recomm == None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		myContents = T('If you want to give a reviewer who has completed his/her review an opportunity to modify the review, please check the reviewer below then click on the black button entitled "Re-open selected reviews"')
		db.t_reviews._id.readable = False
		db.t_reviews.recommendation_id.default = recommId
		db.t_reviews.recommendation_id.writable = False
		db.t_reviews.recommendation_id.readable = False
		db.t_reviews.reviewer_id.writable = auth.has_membership(role='manager')
		db.t_reviews.reviewer_id.default = auth.user_id
		db.t_reviews.reviewer_id.represent = lambda text,row: mkUserWithMail(auth, db, row.reviewer_id) if row else ''
		db.t_reviews.anonymously.default = True
		db.t_reviews.anonymously.writable = auth.has_membership(role='manager')
		db.t_reviews.review.writable = auth.has_membership(role='manager')
		db.t_reviews.review_state.writable = auth.has_membership(role='manager')
		db.t_reviews.review_state.represent = lambda text,row: mkReviewStateDiv(auth, db, text)
		db.t_reviews.emailing.writable = False
		db.t_reviews.emailing.represent = lambda text,row: XML(text) if text else ''
		db.t_reviews.last_change.writable = True
		
		if len(request.args)==0 or (len(request.args)==1 and request.args[0]=='auth_user'): # grid view
			selectable = [(T('Re-open selected reviews'), lambda ids: [recommender_module.reopen_review(auth, db, ids)], 'button btn btn-info')]
			db.t_reviews.review.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
			db.t_reviews.emailing.readable = False
		else: # form view
			selectable = None
			db.t_reviews.review.represent = lambda text, row: WIKI(text or '')
			db.t_reviews.emailing.readable = True
		
		query = (db.t_reviews.recommendation_id == recommId)
		grid = SQLFORM.grid( query
			,details=True
			,editable=lambda row: auth.has_membership(role='manager') or (row.review_state!='Completed' and row.reviewer_id is None)
			,deletable=auth.has_membership(role='manager')
			,create=auth.has_membership(role='manager')
			,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_reviews.recommendation_id, db.t_reviews.reviewer_id, db.t_reviews.anonymously, db.t_reviews.review_state, db.t_reviews.acceptation_timestamp, db.t_reviews.last_change, db.t_reviews.review, db.t_reviews.review_pdf, db.t_reviews.emailing]
			,selectable=selectable
		)
		
		# This script renames the "Add record" button
		myScript = SCRIPT("""$(function() { 
						$('span').filter(function(i) {
								return $(this).attr("title") ? $(this).attr("title").indexOf('"""+T("Add record to database")+"""') != -1 : false;
							})
							.each(function(i) {
								$(this).text('"""+T("Add a review")+"""').attr("title", '"""+T("Add a new review from scratch")+"""');
							});
						})""",
						_type='text/javascript')
		
		return dict(
				myHelp = getHelp(request, auth, db, '#RecommenderArticleReviews'),
				myText=getText(request, auth, db, '#RecommenderArticleReviewsText'),
				myTitle=getTitle(request, auth, db, '#RecommenderArticleReviewsTitle'),
				#myBackButton=mkBackButton(),
				content=myContents, 
				grid=grid, 
				myFinalScript=myScript,
			  )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reviewers():
	response.view='default/myLayout.html'

	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		reviewersListSel = db( (db.t_reviews.recommendation_id==recommId) & (db.t_reviews.reviewer_id==db.auth_user.id) ).select(db.t_reviews.id, db.t_reviews.review_state, db.auth_user.id)
		reviewersList = []
		reviewersIds = [auth.user_id]
		selfFlag = False
		selfFlagCancelled = False
		for con in reviewersListSel:
			if con.t_reviews.review_state is None: # delete this unfinished review declaration
				db(db.t_reviews.id==con.t_reviews.id).delete()
			else:
				if recomm.recommender_id == con.auth_user.id:
					selfFlag=True
					if con.t_reviews.review_state == 'Cancelled':
						selfFlagCancelled = True
				reviewersIds.append(con.auth_user.id)
				reviewersList.append(LI(mkUserWithMail(auth, db, con.auth_user.id), ' ',
									B(T(' (YOU) ')) if con.auth_user.id == recomm.recommender_id else '',
									I('('+(con.t_reviews.review_state or '')+')'),
								))
		excludeList = ','.join(map(str,reviewersIds))
		if len(reviewersList)>0:
			myContents = DIV(
				H3(T('Reviewers already invited:')),
				UL(reviewersList)
			)
		else:
			myContents = ''
		longname = myconf.take('app.longname')
		myUpperBtn = DIV(
							A(SPAN(current.T('Choose a reviewer from %s database')%(longname), _class='btn btn-success'), _href=URL(c='recommender', f='search_reviewers', vars=dict(recommId=recommId, myGoal='4review', exclude=excludeList))),
							A(SPAN(current.T('Choose a reviewer outside %s database')%(longname), _class='btn btn-default'), _href=URL(c='recommender', f='email_for_new_reviewer', vars=dict(recommId=recommId))),
							_style='margin-top:8px; margin-bottom:16px; text-align:left;'
						)
		if auth.user_id == recomm.recommender_id:
			myAcceptBtn = DIV(A(SPAN(T('Done'), _class='btn btn-info'), _href=URL(c='recommender', f='my_recommendations', vars=dict(pressReviews=False))), _style='margin-top:16px; text-align:center;')
		else:
			myAcceptBtn = DIV(A(SPAN(T('Done'), _class='btn btn-info'), _href=URL(c='manager', f='all_recommendations')), _style='margin-top:16px; text-align:center;')
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderAddReviewers'),
					myText=getText(request, auth, db, '#RecommenderAddReviewersText'),
					myTitle=getTitle(request, auth, db, '#RecommenderAddReviewersTitle'),
					myAcceptBtn=myAcceptBtn,
					content=myContents, 
					form='', 
					myUpperBtn = myUpperBtn,
				)

######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def cancel_email_to_registered_reviewer():
	reviewId = request.vars['reviewId']
	if reviewId is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	review = db.t_reviews[reviewId]
	if review is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	recommId = review.recommendation_id
	db(db.t_reviews.id == reviewId).delete()
	#session.flash = T('Reviewer "%s" cancelled') % (mkUser(auth, db, review.reviewer_id).flatten())
	redirect(URL(c='recommender', f='reviewers', vars=dict(recommId=recommId)))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def email_for_registered_reviewer():
	response.view='default/myLayout.html'

	reviewId = request.vars['reviewId']
	if reviewId is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	review = db.t_reviews[reviewId]
	if review is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	recomm = db.t_recommendations[review.recommendation_id]
	if recomm is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	art = db.t_articles[recomm.article_id]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	reviewer = db.auth_user[review.reviewer_id]
	if reviewer is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	scheme = myconf.take('alerts.scheme')
	host = myconf.take('alerts.host')
	port = myconf.take('alerts.port', cast=lambda v: takePort(v) )
	destUser = mkUser(auth, db, reviewer.id).flatten()
	sender = mkUser(auth, db, auth.user_id).flatten()
	description = myconf.take('app.description')
	longname = myconf.take('app.longname')
	art_authors = '[undisclosed]' if (art.anonymous_submission) else art.authors
	art_title = art.title
	art_doi = mkLinkDOI(recomm.doi or art.doi)
	#art_doi = (recomm.doi or art.doi)
	#linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
	linkTarget = URL(c='user', f='recommendations', vars=dict(articleId=art.id), scheme=scheme, host=host, port=port)
	parallelText = ""
	if parallelSubmissionAllowed:
		parallelText += """Note that if the authors abandon the process at %(longname)s after reviewers have written their reports, we will post the reviewers' reports on the %(longname)s website as recognition of their work and in order to enable critical discussion.\n""" % locals()
		if art.parallel_submission:
			parallelText += """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(longname)s, and hope you will agree to review this preprint.\n""" % locals()

	default_message = common_tools.get_template('text', 'default_review_invitation_register_user.txt') % locals()
	
	default_subject = '%(longname)s: Invitation to review a preprint' % locals()
	#replyto = db(db.auth_user.id==auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
	replyto = db(db.auth_user.id==recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
	replyto_address = '%s, %s'%(replyto.email, myconf.take('contacts.managers'))
	form = SQLFORM.factory(
			Field('replyto', label=T('Reply-to'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default=replyto_address, writable=False),
			Field('cc', label=T('CC'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default='%s, %s'%(replyto.email, myconf.take('contacts.managers')), writable=False),
			Field('reviewer_email', label=T('Reviewer email address'), type='string', length=250, default=reviewer.email, writable=False, requires=IS_EMAIL(error_message=T('invalid email!'))),
			Field('subject', label=T('Subject'), type='string', length=250, default=default_subject, required=True),
			Field('message', label=T('Message'), type='text', default=default_message, required=True),
		)
	form.element(_type='submit')['_value'] = T("Send email")
	form.element('textarea[name=message]')['_style'] = 'height:500px;'
	form.append(DIV(
				A(SPAN(T('Cancel invitation')), _class='btn btn-warning', _href=URL(c='recommender', f='cancel_email_to_registered_reviewer', vars=dict(reviewId=reviewId)))
				, _style='margin-top:16px; text-align:center;'
			))
	
	if form.process().accepted:
		try:
			do_send_personal_email_to_reviewer(session, auth, db, reviewId, replyto_address, myconf.take('contacts.managers'), request.vars['subject'], request.vars['message'], None, linkTarget)
		except Exception, e:
			session.flash = (session.flash or '') + T('Email failed.')
			raise e
		redirect(URL(c='recommender', f='reviewers', vars=dict(recommId=recomm.id)))
		
	return dict(
		form=form,
		myHelp=getHelp(request, auth, db, '#EmailForRegisterdReviewer'),
		myTitle=getTitle(request, auth, db, '#EmailForRegisteredReviewerInfoTitle'),
		myText=getText(request, auth, db, '#EmailForRegisteredReviewerInfo'),
	)

######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def email_for_new_reviewer():
	response.view='default/myLayout.html'

	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	art = db.t_articles[recomm.article_id]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	sender = mkUser(auth, db, auth.user_id).flatten()
	description = myconf.take('app.description')
	longname = myconf.take('app.longname')
	thematics = myconf.take('app.thematics')
	scheme = myconf.take('alerts.scheme')
	host = myconf.take('alerts.host')
	port = myconf.take('alerts.port', cast=lambda v: takePort(v) )
	site_url = URL(c='default', f='index', scheme=scheme, host=host, port=port)
	art_authors = '[Undisclosed]' if (art.anonymous_submission) else art.authors
	art_title = art.title
	art_doi = mkLinkDOI(recomm.doi or art.doi)
	#art_doi = (recomm.doi or art.doi)
	# NOTE: 4 parallel submission
	parallelText = ""
	if parallelSubmissionAllowed:
		parallelText += """Note that if the authors abandon the process at %(longname)s after reviewers have written their reports, we will post the reviewers' reports on the %(longname)s website as recognition of their work and in order to enable critical discussion.\n""" % locals()
		if art.parallel_submission:
			parallelText += """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(longname)s, and hope you will agree to review this preprint.\n""" % locals()
	
	default_message = common_tools.get_template('text', 'default_review_invitation_new_user.txt') % locals()

	default_subject = '%(longname)s: Invitation to review a preprint' % locals()
	#replyto = db(db.auth_user.id==auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
	replyto = db(db.auth_user.id==recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
	replyto_address = '%s, %s'%(replyto.email, myconf.take('contacts.managers'))
	form = SQLFORM.factory(
			Field('replyto', label=T('Reply-to'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default=replyto_address, writable=False),
			Field('cc', label=T('CC'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default='%s, %s'%(replyto.email, myconf.take('contacts.managers')), writable=False),
			Field('reviewer_first_name', label=T('Reviewer first name'), type='string', length=250, required=True),
			Field('reviewer_last_name', label=T('Reviewer last name'), type='string', length=250, required=True),
			Field('reviewer_email', label=T('Reviewer email address'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!'))),
			Field('subject', label=T('Subject'), type='string', length=250, default=default_subject, required=True),
			Field('message', label=T('Message'), type='text', default=default_message, required=True),
		)
	form.element(_type='submit')['_value'] = T("Send email")
	form.element('textarea[name=message]')['_style'] = 'height:500px;'
	if form.process().accepted:
		new_user_id = None
		# search for already-existing user
		existingUser = db(db.auth_user.email.upper() == request.vars['reviewer_email'].upper()).select().last()
		if existingUser:
			new_user_id = existingUser.id
			# NOTE: update reset_password_key if not empty with a fresh new one
			if existingUser.reset_password_key is not None and existingUser.reset_password_key != '':
				max_time = time.time()
				#NOTE adapt long-delay key for invitation
				reset_password_key = str((15*24*60*60)+int(max_time)) + '-' + web2py_uuid()
				existingUser.update_record(reset_password_key=reset_password_key)
				existingUser = None
			nbExistingReviews = db( (db.t_reviews.recommendation_id == recommId) & (db.t_reviews.reviewer_id == new_user_id) ).count()
		else:
			# create user
			try:
				my_crypt = CRYPT(key=auth.settings.hmac_key)
				crypt_pass = my_crypt( auth.random_password() )[0]
				new_user_id = db.auth_user.insert(
								first_name=request.vars['reviewer_first_name'],
								last_name=request.vars['reviewer_last_name'],
								email=request.vars['reviewer_email'],
								password=crypt_pass,
							)
				# reset password link
				new_user = db.auth_user(new_user_id)
				max_time = time.time()
				#NOTE adapt long-delay key for invitation
				reset_password_key = str((15*24*60*60)+int(max_time)) + '-' + web2py_uuid()
				new_user.update_record(reset_password_key=reset_password_key)
				nbExistingReviews = 0
				session.flash = T('User "%(reviewer_email)s" created.') % (request.vars)
			except:
				session.flash = T('User creation failed :-(')
				redirect(request.env.http_referer)
		
		# Create review
		reviewId = db.t_reviews.insert(recommendation_id=recommId, reviewer_id=new_user_id, review_state=None) # State will be validated after emailing
		
		if nbExistingReviews > 0:
			session.flash = T('User "%(reviewer_email)s" have already been invited. Email cancelled.') % (request.vars)
		else:
			linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
			#linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True))
			if existingUser:
				try:
					do_send_personal_email_to_reviewer(session, auth, db, reviewId, replyto_address, myconf.take('contacts.managers'), request.vars['subject'], request.vars['message'], None, linkTarget)
					#currentReview = db(db.t_reviews.id==reviewId).select().first()
					#currentReview.update_record(review_state='Pending')
				except Exception, e:
					session.flash = (session.flash or '') + T('Email failed.')
					pass
			else:
				try:
					do_send_personal_email_to_reviewer(session, auth, db, reviewId, replyto_address, myconf.take('contacts.managers'), request.vars['subject'], request.vars['message'], reset_password_key, linkTarget)
					#currentReview = db(db.t_reviews.id==reviewId).select().first()
					#currentReview.update_record(review_state='Pending')
				except Exception, e:
					session.flash = (session.flash or '') + T('Email failed.')
					pass
		
		redirect(URL(c='recommender', f='reviewers', vars=dict(recommId=recommId)))
		
	return dict(
		form=form,
		myHelp=getHelp(request, auth, db, '#EmailForNewReviewer'),
		myTitle=getTitle(request, auth, db, '#EmailForNewReviewerInfoTitle'),
		myText=getText(request, auth, db, '#EmailForNewReviewerInfo'),
		myBackButton=mkBackButton(),
	)



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def send_review_reminder():
	response.view='default/myLayout.html'

	reviewId = request.vars['reviewId']
	if reviewId is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	review = db.t_reviews[reviewId]
	if review is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	recomm = db.t_recommendations[review.recommendation_id]
	if recomm is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	art = db.t_articles[recomm.article_id]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	reviewer = db.auth_user[review.reviewer_id]
	if reviewer is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	scheme = myconf.take('alerts.scheme')
	host = myconf.take('alerts.host')
	port = myconf.take('alerts.port', cast=lambda v: takePort(v) )
	site_url = URL(c='default', f='index', scheme=scheme, host=host, port=port)
	destUser = mkUser(auth, db, reviewer.id).flatten()
	sender = mkUser(auth, db, auth.user_id).flatten()
	description = myconf.take('app.description')
	thematics = myconf.take('app.thematics')
	longname = myconf.take('app.longname')
	contact = myconf.take('contacts.managers')
	reset_password_key = None
	art_authors = '[undisclosed]' if (art.anonymous_submission) else art.authors
	art_title = art.title
	art_doi = mkLinkDOI(recomm.doi or art.doi)
	#art_doi = (recomm.doi or art.doi)
	if (review.review_state or 'Pending') == 'Pending':
		default_subject = '%(longname)s reminder: Invitation to review a preprint' % locals()
		linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
		# NOTE: parallel submission
		parallelText = ""
		if parallelSubmissionAllowed:
			parallelText += """Note that if the authors abandon the process at %(longname)s after reviewers have written their reports, we will post the reviewers' reports on the %(longname)s website as recognition of their work and in order to enable critical discussion.\n""" % locals()
			if art.parallel_submission:
				parallelText += """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(longname)s, and hope you will agree to review this preprint.\n""" % locals()
		if len(reviewer.reset_password_key or '')>0: # even not logged in yet
			reset_password_key = reviewer.reset_password_key
			default_message = common_tools.get_template('text', 'default_review_reminder_new_user.txt') % locals()

		else:
			default_message = common_tools.get_template('text', 'default_review_reminder_register_user.txt') % locals()			

	elif(review.review_state == 'Under consideration'):
		default_subject = '%(longname)s reminder: Review due' % locals()
		linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=scheme, host=host, port=port)
		default_message = common_tools.get_template('text', 'default_review_reminder_under_consideration.txt') % locals()			
	
	replyto = db(db.auth_user.id==recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
	replyto_address = '%s, %s'%(replyto.email, myconf.take('contacts.managers'))
	form = SQLFORM.factory(
			Field('replyto', label=T('Reply-to'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default=replyto_address, writable=False),
			Field('cc', label=T('CC'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default='%s, %s'%(replyto.email, contact), writable=False),
			Field('reviewer_email', label=T('Reviewer email address'), type='string', length=250, default=reviewer.email, writable=False, requires=IS_EMAIL(error_message=T('invalid email!'))),
			Field('subject', label=T('Subject'), type='string', length=250, default=default_subject, required=True),
			Field('message', label=T('Message'), type='text', default=default_message, required=True),
		)
	form.element(_type='submit')['_value'] = T("Send email")
	form.element('textarea[name=message]')['_style'] = 'height:500px;'
	
	if form.process().accepted:
		try:
			do_send_personal_email_to_reviewer(session, auth, db, reviewId, replyto_address, myconf.take('contacts.managers'), request.vars['subject'], request.vars['message'], reset_password_key, linkTarget)
		except Exception, e:
			session.flash = (session.flash or '') + T('Email failed.')
			raise e #TODO pass
		if auth.user_id == recomm.recommender_id:
			redirect(URL(c='recommender', f='my_recommendations', vars=dict(pressReviews=False)))
		else:
			redirect(URL(c='manager', f='all_recommendations'))
		
	return dict(
		form=form,
		myHelp=getHelp(request, auth, db, '#EmailForRegisterdReviewer'),
		myTitle=getTitle(request, auth, db, '#EmailForRegisteredReviewerInfoTitle'),
		myText=getText(request, auth, db, '#EmailForRegisteredReviewerInfo'),
		myBackButton=mkBackButton(),
	)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def send_review_cancellation():
	response.view='default/myLayout.html'

	reviewId = request.vars['reviewId']
	if reviewId is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	review = db.t_reviews[reviewId]
	if review is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	recomm = db.t_recommendations[review.recommendation_id]
	if recomm is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	art = db.t_articles[recomm.article_id]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	reviewer = db.auth_user[review.reviewer_id]
	if reviewer is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	scheme = myconf.take('alerts.scheme')
	host = myconf.take('alerts.host')
	port = myconf.take('alerts.port', cast=lambda v: takePort(v) )
	destUser = mkUser(auth, db, reviewer.id).flatten()
	sender = mkUser(auth, db, auth.user_id).flatten()
	description = myconf.take('app.description')
	longname = myconf.take('app.longname')
	contact = myconf.take('contacts.managers')
	art_authors = '[undisclosed]' if (art.anonymous_submission) else art.authors
	art_title = art.title
	art_doi = mkLinkDOI(recomm.doi or art.doi)
	#art_doi = (recomm.doi or art.doi)
	linkTarget = None #URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
	if (review.review_state or 'Pending') == 'Pending':
		default_subject = '%(longname)s: Cancellation of a review request' % locals()
		default_message = common_tools.get_template('text', 'default_review_cancellation.txt') % locals()
		
	else:
		pass
	replyto = db(db.auth_user.id==auth.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
	replyto_address = '%s, %s'%(replyto.email, myconf.take('contacts.managers'))
	form = SQLFORM.factory(
			Field('replyto', label=T('Reply-to'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default=replyto_address, writable=False),
			Field('cc', label=T('CC'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default='%s, %s'%(replyto.email, contact), writable=False),
			Field('reviewer_email', label=T('Reviewer email address'), type='string', length=250, default=reviewer.email, writable=False, requires=IS_EMAIL(error_message=T('invalid email!'))),
			Field('subject', label=T('Subject'), type='string', length=250, default=default_subject, required=True),
			Field('message', label=T('Message'), type='text', default=default_message, required=True),
		)
	form.element(_type='submit')['_value'] = T("Send email")
	form.element('textarea[name=message]')['_style'] = 'height:500px;'
	
	if form.process().accepted:
		try:
			review.update_record(review_state='Cancelled')
			do_send_personal_email_to_reviewer(session, auth, db, reviewId, replyto_address, myconf.take('contacts.managers'), request.vars['subject'], request.vars['message'], None, linkTarget)
		except Exception, e:
			session.flash = (session.flash or '') + T('Email failed.')
			raise e
		if auth.user_id == recomm.recommender_id:
			redirect(URL(c='recommender', f='my_recommendations', vars=dict(pressReviews=False)))
		else:
			redirect(URL(c='manager', f='all_recommendations'))
		
	return dict(
		form=form,
		myHelp=getHelp(request, auth, db, '#EmailForRegisterdReviewer'),
		myTitle=getTitle(request, auth, db, '#EmailForRegisteredReviewerInfoTitle'),
		myText=getText(request, auth, db, '#EmailForRegisteredReviewerInfo'),
		myBackButton=mkBackButton(),
	)

######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def email_for_reviewer():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#TemplateEmailForReviewInfoTitle'),
		myText=getText(request, auth, db, '#TemplateEmailForReviewInfo'),
		myBackButton=mkBackButton(),
	)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def email_for_author():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#TemplateEmailForAuthorInfoTitle'),
		myText=getText(request, auth, db, '#TemplateEmailForAuthorInfo'),
		myBackButton=mkBackButton(),
	)






######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def add_contributor():
	response.view='default/myLayout.html'

	recommId = request.vars['recommId']
	onlyAdd = request.vars['onlyAdd'] or True
	goBack = request.vars['goBack']
	recomm = db.t_recommendations[recommId]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		roleClass = ' pci-manager' if (recomm.recommender_id != auth.user_id) and auth.has_membership(role='manager') else ' pci-recommender'
		art = db.t_articles[recomm.article_id]
		contributorsListSel = db( (db.t_press_reviews.recommendation_id==recommId) & (db.t_press_reviews.contributor_id==db.auth_user.id) ).select(db.t_press_reviews.id, db.auth_user.id)
		contributorsList = []
		for con in contributorsListSel:
			contributorsList.append(LI(mkUserWithMail(auth, db, con.auth_user.id),
									A(T('Delete'), _class='btn btn-warning pci-smallBtn '+roleClass,
									   _href=URL(c='recommender_actions', f='del_contributor', vars=dict(pressId=con.t_press_reviews.id)), 
									   _title=T('Delete this co-recommender')) #, _style='margin-left:8px; color:red;'),
									))
		myContents = DIV(
			LABEL(T('Co-recommenders:')),
			UL(contributorsList),
		)
		myAcceptBtn = DIV(mkBackButton('Done', target=goBack), _style='width:100%; text-align:center;')
		myBackButton = ''
		db.t_press_reviews._id.readable = False
		db.t_press_reviews.recommendation_id.default = recommId
		db.t_press_reviews.recommendation_id.writable = False
		db.t_press_reviews.recommendation_id.readable = False
		db.t_press_reviews.contributor_id.writable = True
		db.t_press_reviews.contributor_id.label = T('Select a co-recommender')
		db.t_press_reviews.contributor_id.represent = lambda text,row: mkUserWithMail(auth, db, row.contributor_id) if row else ''
		alreadyCo = db((db.t_press_reviews.recommendation_id==recommId) & (db.t_press_reviews.contributor_id != None))._select(db.t_press_reviews.contributor_id)
		otherContribsQy = db((db.auth_user._id!=auth.user_id) & (db.auth_user._id==db.auth_membership.user_id) & (db.auth_membership.group_id==db.auth_group._id) & (db.auth_group.role=='recommender') & (~db.auth_user.id.belongs(alreadyCo)) )
		db.t_press_reviews.contributor_id.requires = IS_IN_DB(otherContribsQy, db.auth_user.id, '%(last_name)s, %(first_name)s')
		form = SQLFORM(db.t_press_reviews)
		form.element(_type='submit')['_value'] = T("Add")
		form.element(_type='submit')['_style'] = 'margin-right:300px;'
		form.element(_type='submit')['_class'] = 'btn btn-info '+roleClass
		if form.process().accepted:
			redirect(URL(c='recommender', f='add_contributor', vars=dict(recommId=recomm.id, goBack=goBack, onlyAdd=onlyAdd)))
		if art.already_published and onlyAdd is False:
			myAcceptBtn = DIV(
							A(SPAN(current.T('Add a co-recommender later'), _class='btn btn-info'+roleClass), _href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recomm.id))) if len(contributorsListSel)==0 else '', 
							A(SPAN(current.T('Write / Edit your recommendation'), _class='btn btn-default'+roleClass), _href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recomm.id))), 
							_style='margin-top:64px; text-align:center;'
						)
		return dict(
					myBackButton = myBackButton,
					myHelp = getHelp(request, auth, db, '#RecommenderAddContributor'),
					myText=getText(request, auth, db, '#RecommenderAddContributorText'),
					myTitle=getTitle(request, auth, db, '#RecommenderAddContributorTitle'),
					content=myContents, 
					form=form, 
					myAcceptBtn = myAcceptBtn,
				)



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def contributions():
	response.view='default/myLayout.html'

	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		myContents = mkRecommendationFormat(auth, db, recomm)
		query = (db.t_press_reviews.recommendation_id == recommId)
		db.t_press_reviews._id.readable = False
		db.t_press_reviews.recommendation_id.default = recommId
		db.t_press_reviews.recommendation_id.writable = False
		db.t_press_reviews.recommendation_id.readable = False
		db.t_press_reviews.contributor_id.writable = True
		db.t_press_reviews.contributor_id.represent = lambda text,row: mkUserWithMail(auth, db, row.contributor_id) if row else ''
		alreadyCo = db(db.t_press_reviews.recommendation_id==recommId)._select(db.t_press_reviews.contributor_id)
		otherContribsQy = db((db.auth_user._id!=auth.user_id) & (db.auth_user._id==db.auth_membership.user_id) & (db.auth_membership.group_id==db.auth_group._id) & (db.auth_group.role=='recommender') & (~db.auth_user.id.belongs(alreadyCo)) )
		db.t_press_reviews.contributor_id.requires = IS_IN_DB(otherContribsQy, db.auth_user.id, '%(last_name)s, %(first_name)s')
		grid = SQLFORM.grid( query
			,details=False
			,editable=False
			,deletable=True
			,create=True
			,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_press_reviews.recommendation_id, db.t_press_reviews.contributor_id]
		)
		#myAcceptBtn = DIV(
							#A(SPAN(current.T('Write recommendation now'), _class='buttontext btn btn-info'), 
								#_href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recommId))),
							#A(SPAN(current.T('Later'), _class='buttontext btn btn-info'), 
										#_href=URL(c='recommender', f='my_recommendations')),
							#_style='margin-top:16px; text-align:center;'
						#)
		# This script renames the "Add record" button
		myScript = SCRIPT(common_tools.get_template('script', 'contributions.js'),
						_type='text/javascript')
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderContributionsToPressReviews'),
					myText=getText(request, auth, db, '#RecommenderContributionsToPressReviewsText'),
					myTitle=getTitle(request, auth, db, '#RecommenderContributionsToPressReviewsTitle'),
					contents=myContents, 
					grid=grid, 
					#myAcceptBtn = myAcceptBtn,
					myFinalScript=myScript,
				)




######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def edit_recommendation():
	response.view='default/myLayout.html'

	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	art = db.t_articles[recomm.article_id]
	isPress = None
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	elif art.status not in ('Under consideration', 'Pre-recommended', 'Pre-revision', 'Pre-cancelled'):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		nbCoRecomm = db(db.t_press_reviews.recommendation_id == recommId).count()
		isPress = art.already_published
		triptyque = DIV(DIV(H3(current.T('Your decision')),
						SPAN(INPUT(_id='opinion_recommend', _name='recommender_opinion', _type='radio', _value='do_recommend', _checked=(recomm.recommendation_state=='Recommended')), current.T('I recommend this preprint'), _class='pci-radio pci-recommend btn-success'),
						SPAN(INPUT(_id='opinion_revise', _name='recommender_opinion', _type='radio', _value='do_revise', _checked=(recomm.recommendation_state=='Revision')), current.T('This preprint merits a revision'), _class='pci-radio pci-review btn-default'),
						SPAN(INPUT(_id='opinion_reject', _name='recommender_opinion', _type='radio', _value='do_reject', _checked=(recomm.recommendation_state=='Rejected')), current.T('I reject this preprint'), _class='pci-radio pci-reject btn-warning'),
						# TEST # SPAN(INPUT(_id='opinion_none', _name='recommender_opinion', _type='radio', _value='none', _checked=(recomm.recommendation_state=='?')), current.T('I still hesitate'), _class='pci-radio btn-default'),
						_style="padding:8px; margin-bottom:12px;"
					), _style='text-align:center;')
		buttons = [	INPUT(_type='Submit', _name='save',      _class='btn btn-info', _value='Save'), ]
		if isPress:
			#buttons += [INPUT(_type='Submit', _name='terminate', _class='btn btn-success', _value='Save and submit your recommendation')]
			db.t_recommendations.no_conflict_of_interest.writable = False
		else:
			buttons += [INPUT(_type='Submit', _name='terminate', _class='btn btn-success', _value='Save and submit your decision')]
		db.t_recommendations.recommendation_state.readable = False
		db.t_recommendations.recommendation_state.writable = False
		if isPress:
			db.t_recommendations.recommendation_title.label = T('Recommendation title')
			db.t_recommendations.recommendation_comments.label = T('Recommendation')
			myText=getText(request, auth, db, '#RecommenderEditRecommendationText')
			myHelp=getHelp(request, auth, db, '#RecommenderEditRecommendation')
			myTitle=getTitle(request, auth, db, '#RecommenderEditRecommendationTitle')
		else:
			db.t_recommendations.recommendation_title.label = T('Decision or recommendation title')
			db.t_recommendations.recommendation_comments.label = T('Decision or recommendation')
			myText=getText(request, auth, db, '#RecommenderEditDecisionText')
			myHelp=getHelp(request, auth, db, '#RecommenderEditDecision')
			myTitle=getTitle(request, auth, db, '#RecommenderEditDecisionTitle')
		
		if isPress:
			fields = ['no_conflict_of_interest', 'recommendation_title', 'recommendation_comments']
		else:
			fields = ['no_conflict_of_interest', 'recommendation_title', 'recommendation_comments', 'recommender_file', 'recommender_file_data']
		
		form = SQLFORM(db.t_recommendations
					,record=recomm
					,deletable=False
					,fields=fields
					,showid=False
					,buttons=buttons
					,upload=URL('default', 'download')
				)
		if isPress is False:
			form.insert(0, triptyque)

		if form.process().accepted:
			if form.vars.save:
				if form.vars.recommender_opinion == 'do_recommend':
					recomm.recommendation_state = 'Recommended'
				elif form.vars.recommender_opinion == 'do_revise':
					recomm.recommendation_state = 'Revision'
				elif form.vars.recommender_opinion == 'do_reject':
					recomm.recommendation_state = 'Rejected'
				#print form.vars.no_conflict_of_interest
				if form.vars.no_conflict_of_interest:
					recomm.no_conflict_of_interest = True
				recomm.recommendation_title = form.vars.recommendation_title
				recomm.recommendation_comments = form.vars.recommendation_comments
				# manual bypass:
				rf = request.vars.recommender_file
				if rf is not None:
					if hasattr(rf, 'value'):
						recomm.recommender_file_data = rf.value
						recomm.recommender_file = rf
					elif (hasattr(request.vars, 'recommender_file__delete') and request.vars.recommender_file__delete == 'on'):
						recomm.recommender_file_data = None
						recomm.recommender_file = None
				recomm.update_record()
				session.flash = T('Recommendation saved', lazy=False)
				redirect(URL(c='recommender', f='my_recommendations', vars=dict(pressReviews=isPress)))
			elif form.vars.terminate:
				session.flash = T('Recommendation saved and completed', lazy=False)
				recomm.no_conflict_of_interest = form.vars.no_conflict_of_interest
				recomm.recommendation_title = form.vars.recommendation_title
				recomm.recommendation_comments = form.vars.recommendation_comments
				recomm.recommender_file = form.vars.recommender_file
				# manual bypass:
				rf = request.vars.recommender_file
				if rf is not None:
					if hasattr(rf, 'value'):
						recomm.recommender_file_data = rf.value
						recomm.recommender_file = rf
					elif (hasattr(request.vars, 'recommender_file__delete') and request.vars.recommender_file__delete == 'on'):
						recomm.recommender_file_data = None
						recomm.recommender_file = None
				if isPress is False:
					if form.vars.recommender_opinion == 'do_recommend':
						recomm.recommendation_state = 'Recommended'
						art.status = 'Pre-recommended'
					elif form.vars.recommender_opinion == 'do_revise':
						recomm.recommendation_state = 'Revision'
						art.status = 'Pre-revision'
					elif form.vars.recommender_opinion == 'do_reject':
						recomm.recommendation_state = 'Rejected'
						art.status = 'Pre-rejected'
				else:
					recomm.recommendation_state = 'Recommended'
					art.status = 'Pre-recommended'
				recomm.update_record()
				art.update_record()
				redirect(URL(c='recommender', f='my_recommendations', vars=dict(pressReviews=isPress)))
		elif form.errors:
			response.flash = T('Form has errors', lazy=False)
		
		if isPress is False:
			myScript = common_tools.get_template('script', 'edit_recommendation.js')
		else:
			myScript = common_tools.get_template('script', 'edit_recommendation_is_press.js')

		return dict(
					form=form,
					myText=myText,
					myHelp=myHelp,
					myTitle=myTitle,
					myFinalScript = SCRIPT(myScript),
					myBackButton = mkBackButton(),
				)



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender'))
def my_co_recommendations():
	response.view='default/myLayout.html'

	query = (
			  (db.t_press_reviews.contributor_id == auth.user_id) 
			& (db.t_press_reviews.recommendation_id==db.t_recommendations.id) 
			& (db.t_recommendations.article_id==db.t_articles.id)
			)
	db.t_press_reviews.contributor_id.writable = False
	db.t_press_reviews.recommendation_id.writable = False
	db.t_articles._id.readable = False
	#db.t_articles._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
	#db.t_articles._id.label = T('Article')
	db.t_recommendations._id.label = T('Recommendation')
	db.t_recommendations._id.represent = lambda rId, row: mkRepresentRecommendationLight(auth, db, rId)
	db.t_articles.status.writable = False
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	#db.t_press_reviews.recommendation_id.represent = lambda text,row: mkRecommendation4PressReviewFormat(auth, db, row)
	db.t_press_reviews._id.readable = False
	#db.t_press_reviews.contribution_state.represent = lambda state,row: mkContributionStateDiv(auth, db, state)
	db.t_recommendations.recommender_id.represent = lambda uid,row: mkUserWithMail(auth, db, uid)
	db.t_recommendations.article_id.readable = False
	#db.t_articles.already_published.represent = lambda press, row: 'TRUE' if press else 'FALSE'
	db.t_articles.already_published.represent = lambda press, row: mkJournalImg(auth, db, press)
	grid = SQLFORM.grid( query
		,searchable=False, deletable=False, create=False, editable=False, details=False
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=[db.t_articles.uploaded_picture, db.t_recommendations._id, db.t_articles._id, db.t_articles.already_published, db.t_articles.status, db.t_articles.last_status_change, db.t_recommendations.article_id, db.t_recommendations.recommender_id]
		,links=[
				dict(header=T('Other co-recommenders'), body=lambda row: mkOtherContributors(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T(''), 
						body=lambda row: A(SPAN(current.T('View'), _class='btn btn-default pci-button'), 
										_href=URL(c='recommender', f='recommendations', vars=dict(articleId=row.t_articles.id)), 
										_target="_blank", 
										_class='button', 
										_title=current.T('View this co-recommendation')
										)
					),
				]
		,orderby=~db.t_articles.last_status_change|~db.t_press_reviews.id
	)
	myContents = ''
	return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderMyPressReviews'),
					myText=getText(request, auth, db, '#RecommenderMyPressReviewsText'),
					myTitle=getTitle(request, auth, db, '#RecommenderMyPressReviewsTitle'),
					#myBackButton=mkBackButton(), 
					contents=myContents, 
					grid=grid, 
			 )


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def review_emails():
	response.view='default/info.html'

	revId = request.vars['reviewId']
	rev = db.t_reviews[revId]
	myContents = DIV()
	myContents.append(SPAN(B(T('Reviewer: ')), mkUserWithMail(auth, db, rev.reviewer_id)))
	myContents.append(H2(T('Emails:')))
	myContents.append(DIV(
						#WIKI((rev.emailing or '*None yet*'), safe_mode=False)
						XML((rev.emailing or '<b>None yet</b>'))
					   ,_style='margin-left:20px; border-left:1px solid #cccccc; padding-left:4px;'))
	return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderReviewEmails'),
					myText=getText(request, auth, db, '#RecommenderReviewEmailsText'),
					myTitle=getTitle(request, auth, db, '#RecommenderReviewEmailsTitle'),
					myBackButton=mkCloseButton(), 
					message=myContents, 
			 )