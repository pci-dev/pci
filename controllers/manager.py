# -*- coding: utf-8 -*-

import re
import copy

# sudo pip install tweepy
#import tweepy

from gluon.contrib.markdown import WIKI
from common import *
from helper import *

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get('config.trgm_limit') or 0.4



@auth.requires(auth.has_membership(role='manager'))
def do_validate_article():
	if not('articleId' in request.vars):
		raise HTTP(404, "404: "+T('Unavailable'))
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if art.status == 'Pending':
		art.status = 'Awaiting consideration'
		art.update_record()
		session.flash = T('Request now available to recommenders')
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))




@auth.requires(auth.has_membership(role='manager'))
def do_cancel_article():
	if not('articleId' in request.vars):
		raise HTTP(404, "404: "+T('Unavailable'))
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	else:
		art.status = 'Cancelled'
		art.update_record()
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))



@auth.requires(auth.has_membership(role='manager'))
def do_recommend_article():
	if not('articleId' in request.vars):
		raise HTTP(404, "404: "+T('Unavailable'))
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if art.status == 'Pre-recommended':
		art.status = 'Recommended'
		art.update_record()
		redirect(URL(c='public', f='rec', vars=dict(id=art.id), user_signature=True))
		#NOTE: tweet article
		#message = ''
		#scheme=myconf.take('alerts.scheme')
		#host=myconf.take('alerts.host')
		#port=myconf.take('alerts.port')
		#link = URL(c='public', f='rec', scheme=scheme, host=host, port=port, vars=dict(id=art.id))
		#print 'To be tweeted:', A(link, _href=link)
		#tweeterAcc = myconf.get('social.tweeter')
		#consumer_key = myconf.get('social.tweeter_consumer_key')
		#consumer_secret = myconf.get('social.tweeter_consumer_secret')
		#access_token = myconf.get('social.tweeter_access_token')
		#access_token_secret = myconf.get('social.tweeter_access_token_secret')
		#if tweeterAcc and consumer_key and consumer_secret and access_token and access_token_secret :
			#try:
				#twAuth = tweepy.OAuthHandler(consumer_key, consumer_secret)
				#twAuth.set_access_token(access_token, access_token_secret)
				#api = tweepy.API(twAuth)
				#api.update_status(status="New recommendation: "+link)
				#frames = []
				#frames.append(H2('Tweeter'))
				#frames.append(DIV(XML('<a class="twitter-timeline" href="https://twitter.com/%(tweeterAcc)s">Tweets by %(tweeterAcc)s</a> <script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>' % locals() ), _class='tweeterPanel'))
				#message = DIV(frames, _class='pci-socialDiv')
			#except:
				#message = T('Failure!')
				#pass
		#else:
			#message = T('Configure [socials] in private/appconfig.ini')
		#response.view='default/info.html'
		#return dict(
					#myHelp=getHelp(request, auth, db, '#ManageTweetRecommendation'),
					#myText=getText(request, auth, db, '#ManageTweetRecommendationText'),
					#myTitle=getTitle(request, auth, db, '#ManageTweetRecommendationTitle'),
					#message=message,
				#)
	else:
		redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))




# Display ALL articles and allow management
@auth.requires(auth.has_membership(role='manager'))
def all_articles():
	resu = _manage_articles(None, 'all_articles')
	resu['myText']=getText(request, auth, db, '#ManagerAllArticlesText')
	resu['myTitle']=getTitle(request, auth, db, '#ManagerAllArticlesTitle')
	resu['myHelp'] = getHelp(request, auth, db, '#ManageAllArticlesHelp')
	return resu



# Display pending articles and allow management
@auth.requires(auth.has_membership(role='manager'))
def pending_articles():
	resu = _manage_articles(['Pending', 'Pre-recommended'], 'pending_articles')
	resu['myText']=getText(request, auth, db, '#ManagerPendingArticlesText')
	resu['myTitle']=getTitle(request, auth, db, '#ManagerPendingArticlesTitle')
	resu['myHelp'] = getHelp(request, auth, db, '#ManagePendingValidations')
	return resu



# Display ongoing articles and allow management
@auth.requires(auth.has_membership(role='manager'))
def ongoing_articles():
	resu = _manage_articles(['Awaiting consideration', 'Under consideration', 'Awaiting revision'], 'ongoing_articles')
	resu['myText']=getText(request, auth, db, '#ManagerOngoingArticlesText')
	resu['myTitle']=getTitle(request, auth, db, '#ManagerOngoingArticlesTitle')
	resu['myHelp'] = getHelp(request, auth, db, '#ManageOngoingArticles')
	return resu



# Display completed articles and allow management
@auth.requires(auth.has_membership(role='manager'))
def completed_articles():
	db.t_articles.status.label = T('Outcome')
	resu = _manage_articles(['Cancelled', 'Recommended', 'Rejected'], 'completed_articles')
	resu['myText']=getText(request, auth, db, '#ManagerCompletedArticlesText')
	resu['myTitle']=getTitle(request, auth, db, '#ManagerCompletedArticlesTitle')
	resu['myHelp'] = getHelp(request, auth, db, '#ManageCompletedArticles')
	return resu





@auth.requires(auth.has_membership(role='manager'))
def suggest_article_to():
	articleId = request.vars['articleId']
	whatNext = request.vars['whatNext']
	recommenderId = request.vars['recommenderId']
	db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)
	redirect(whatNext)





def mkRecommenderButton(row):
	last_recomm = db( db.t_recommendations.article_id==row.id ).select(orderby=db.t_recommendations.id).last()
	if last_recomm:
		return mkUserWithMail(auth, db, last_recomm.recommender_id)
	else:
		return ''



def mkSuggestedRecommendersManagerButton(row, whatNext):
	if row.already_published:
		return ''
	butts = []
	suggRecomsTxt = []
	exclude = [str(auth.user_id)]
	#sr = db.v_suggested_recommenders[row.id].suggested_recommenders
	suggRecomms = db(db.t_suggested_recommenders.article_id==row.id).select()
	for sr in suggRecomms:
		exclude.append(str(sr.suggested_recommender_id))
		suggRecomsTxt.append(mkUserWithMail(auth, db, sr.suggested_recommender_id)+BR())
	if len(suggRecomsTxt)>0:
		butts.append(DIV(suggRecomsTxt))
		butts.append( A(current.T('[MANAGE]'), _href=URL(c='manager', f='suggested_recommenders', vars=dict(articleId=row.id))) )
	myVars = dict(articleId=row.id, whatNext=whatNext)
	if len(exclude)>0:
		myVars['exclude'] = ','.join(exclude)
	for thema in row.thematics:
		myVars['qy_'+thema] = 'on'
	#butts.append( BR() )
	butts.append( A(current.T('[+ADD]'), _href=URL(c='manager', f='search_recommenders', vars=myVars, user_signature=True)) )
	return butts





# Common function which allow management of articles filtered by status
@auth.requires(auth.has_membership(role='manager'))
def _manage_articles(statuses, whatNext):
	if statuses:
		query = (db.t_articles.status.belongs(statuses))
	else:
		query = (db.t_articles)
	
	db.t_articles.user_id.default = auth.user_id
	db.t_articles.user_id.writable = False
	db.t_articles.user_id.represent = lambda text, row: mkUserWithMail(auth, db, text)
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	db.t_articles.status.writable = True
	db.t_articles.auto_nb_recommendations.readable = False
	db.t_articles.auto_nb_recommendations.writable = False
	#db.t_articles.doi.represent = lambda text, row: mkDOI(text)
	#if len(request.args) == 0: # we are in grid
	#db.t_articles.doi.readable = False
	#db.t_articles.authors.readable = False
	#db.t_articles.title.readable = False
	#db.t_articles.abstract.readable = False
	#db.t_articles.keywords.readable = False
	#db.t_articles.thematics.readable = False
	#db.t_articles.user_id.readable = False
	db.t_articles._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
	db.t_articles._id.label = T('Article')
	db.t_articles.upload_timestamp.represent = lambda text, row: mkLastChange(row.upload_timestamp)
	db.t_articles.upload_timestamp.label = T('Submission date')
	db.t_articles.last_status_change.represent = lambda text, row: mkLastChange(row.last_status_change)
	db.t_articles.already_published.represent = lambda press, row: mkJournalImg(auth, db, press)
	#else: # we are in grid's form
		#db.t_articles.abstract.represent=lambda text, row: WIKI(text)

	links = []
	if whatNext != 'completed_articles':
		links += [ dict(header=T('Suggested recommenders'), body=lambda row: mkSuggestedRecommendersManagerButton(row, whatNext) ), ]
	links += [
				dict(header=T('Recommender'), body=lambda row: mkRecommenderButton(row)),
				dict(header=T('Recommendation title'), body=lambda row: mkLastRecommendation(auth, db, row.id)),
				dict(header=T(''), 
						body=lambda row: A(SPAN(current.T('Check & Edit'), _class='buttontext btn btn-default pci-button'), 
										_href=URL(c='manager', f='recommendations', vars=dict(articleId=row.id), user_signature=True), 
										_target="_blank", 
										_class='button', 
										_title=current.T('View and/or edit review')
										)
					),
			]
	grid = SQLFORM.grid(  query
		,details=False, editable=False, deletable=False, create=False
		,searchable=True
		,maxtextlength=250, paginate=20
		,csv=csv, exportclasses=expClass
		,fields=[db.t_articles.uploaded_picture, db.t_articles._id, db.t_articles.already_published, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations, db.t_articles.user_id, db.t_articles.thematics]
		,links=links
		,orderby=~db.t_articles.last_status_change
	)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#ManagerArticlesText'),
				myTitle=getTitle(request, auth, db, '#ManagerArticlesTitle'),
				grid=grid, 
			)



@auth.requires(auth.has_membership(role='manager'))
def recommendations():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		#raise HTTP(404, "404: "+T('Unavailable'))
		session.flash = T('Unavailable')
		redirect(URL(c='manager', f='ongoing_articles', user_signature=True))
	if printable:
		if art.status == 'Recommended':
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
					DIV(
						DIV(T('Recommended article'), _class='pci-ArticleText printable'),
						_class='pci-ArticleHeaderIn recommended printable'
					))
		else:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
				DIV(
					DIV(mkStatusBigDiv(auth, db, art.status), _class='pci-ArticleText printable'),
					_class='pci-ArticleHeaderIn printable'
				))
		myUpperBtn = ''
		response.view='default/recommended_article_printable.html' #OK
	else:
		if art.status == 'Recommended':
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
				DIV(
					DIV(I(T('Recommended article')), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn recommended'
				))
		else:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
				DIV(
					DIV(mkStatusBigDiv(auth, db, art.status), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn'
				))
		myUpperBtn = A(SPAN(T('Printable page'), _class='buttontext btn btn-info'), 
			_href=URL(c="manager", f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
			_class='button')
		response.view='default/recommended_articles.html' #OK
	
	myContents = mkFeaturedArticle(auth, db, art, printable, quiet=False)
	myContents.append(HR())
		
	response.title = (art.title or myconf.take('app.longname'))
	return dict(
				myCloseButton=mkCloseButton(),
				statusTitle=myTitle,
				myContents=myContents,
				myUpperBtn=myUpperBtn,
				myHelp = getHelp(request, auth, db, '#ManagerRecommendations'),
			)








# Allow management of article recommendations
@auth.requires(auth.has_membership(role='manager'))
def manage_recommendations():
	if not('articleId' in request.vars):
		session.flash = T('Unavailable')
		redirect(request.env.http_referer)
		#raise HTTP(404, "404: "+T('Malformed URL')) # Forbidden access
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(request.env.http_referer)
	query = db.t_recommendations.article_id == articleId
	db.t_recommendations.recommender_id.default = auth.user_id
	db.t_recommendations.article_id.default = articleId
	db.t_recommendations.article_id.writable = False
	db.t_recommendations.doi.represent = lambda text, row: mkDOI(text)
	db.t_recommendations._id.readable = False
	if len(request.args) == 0: # in grid
		db.t_recommendations.recommendation_state.represent = lambda state, row: mkContributionStateDiv(auth, db, (state or ''))
		db.t_recommendations.recommendation_comments.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
		db.t_recommendations.recommendation_timestamp.represent = lambda text, row: mkLastChange(row.recommendation_timestamp)
		db.t_recommendations.last_change.represent = lambda text, row: mkLastChange(row.last_change)
	else: # in form
		db.t_recommendations.recommendation_comments.represent=lambda text, row: WIKI(text or '')

	if art.already_published:
		links = [dict(header=T('Contributions'), body=lambda row: A((db.v_recommendation_contributors[row.id]).contributors or 'ADD', _href=URL(c='recommender', f='contributions', vars=dict(recommId=row.id))))]
	else:
		links = [dict(header=T('Reviews'), body=lambda row: A((db.v_reviewers[row.id]).reviewers or 'ADD', _href=URL(c='recommender', f='reviews', vars=dict(recommId=row.id))))]
	grid = SQLFORM.grid( query
		,editable=True
		,deletable=True
		,create=False
		,details=False
		,searchable=False
		,maxtextlength=1000
		,csv=csv, exportclasses=expClass
		,paginate=10
		,fields=[db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.recommendation_state, db.t_recommendations.is_closed, db.t_recommendations.recommender_id, db.t_recommendations.recommendation_comments]
		,links = links
		,orderby=~db.t_recommendations.recommendation_timestamp
	)
	myContents = mkRepresentArticle(auth, db, articleId)
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, db, '#ManageRecommendations'),
				myText=getText(request, auth, db, '#ManageRecommendationsText'),
				myTitle=getTitle(request, auth, db, '#ManageRecommendationsTitle'),
				content=myContents,
				grid=grid,
			)



@auth.requires(auth.has_membership(role='manager'))
def search_recommenders():
	myVars = request.vars
	qyKw = ''
	qyTF = []
	excludeList = []
	articleId = None
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (re.match('^qy_', myVar) and myValue=='on'):
			qyTF.append(re.sub(r'^qy_', '', myVar))
		elif (myVar == 'exclude'):
			excludeList = map(int, myValue.split(','))
	whatNext = request.vars['whatNext']
	articleId = request.vars['articleId']
	if articleId is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		# We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
		temp_db = DAL('sqlite:memory')
		qy_recomm = temp_db.define_table('qy_recomm',
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
		)
		temp_db.qy_recomm.email.represent = lambda text, row: A(text, _href='mailto:'+text)
		qyKwArr = qyKw.split(' ')
		searchForm =  mkSearchForm(auth, db, myVars)
		filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s, %s);', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
		for fr in filtered:
			qy_recomm.insert(**fr)
				
		temp_db.qy_recomm._id.readable = False
		temp_db.qy_recomm.uploaded_picture.readable = False
		temp_db.qy_recomm.num.readable = False
		temp_db.qy_recomm.score.readable = False
		links = [
					dict(header=T('Days since last recommendation'), body=lambda row: db.v_last_recommendation[row.id].days_since_last_recommendation),
					dict(header=T('Suggest as recommender'),         body=lambda row: A(SPAN(current.T('Suggest'), _class='buttontext btn btn-default'), 
																							_href=URL(c='manager', f='suggest_article_to', 
																									vars=dict(articleId=articleId, recommenderId=row['id'], whatNext=whatNext), 
																									user_signature=True), 
																						_class='button')),
			]
		grid = SQLFORM.grid( qy_recomm
			,editable = False,deletable = False,create = False,details=False,searchable=False
			,maxtextlength=250,paginate=100
			,csv=csv,exportclasses=expClass
			,fields=[temp_db.qy_recomm.num, temp_db.qy_recomm.score, temp_db.qy_recomm.uploaded_picture, temp_db.qy_recomm.first_name, temp_db.qy_recomm.last_name, temp_db.qy_recomm.email, temp_db.qy_recomm.laboratory, temp_db.qy_recomm.institution, temp_db.qy_recomm.city, temp_db.qy_recomm.country, temp_db.qy_recomm.thematics]
			,links=links
			,orderby=temp_db.qy_recomm.num
			,args=request.args
		)
		response.view='default/myLayout.html'
		return dict(searchForm=searchForm, 
					myHelp=getHelp(request, auth, db, '#ManagerSearchRecommenders'),
					myText=getText(request, auth, db, '#ManagerSearchRecommendersText'),
					myTitle=getTitle(request, auth, db, '#ManagerSearchRecommendersTitle'),
					grid=grid, 
				)



# Display suggested recommenders for a submitted article
# Logged users only (submission)
@auth.requires(auth.has_membership(role='manager'))
def suggested_recommenders():
	articleId = request.vars['articleId']
	whatNext = request.vars['whatNext']
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	query = (db.t_suggested_recommenders.article_id == articleId)
	db.t_suggested_recommenders._id.readable = False
	db.t_suggested_recommenders.suggested_recommender_id.represent = lambda text, row: mkUserWithMail(auth, db, text)
	grid = SQLFORM.grid( query
		,details=False,editable=False,deletable=True,create=False,searchable=False
		,maxtextlength = 250,paginate=100
		,csv = csv, exportclasses = expClass
		,fields=[db.t_suggested_recommenders.id, db.t_suggested_recommenders.suggested_recommender_id, db.t_suggested_recommenders.email_sent]
		,field_id=db.t_suggested_recommenders.id
	)
	response.view='default/myLayout.html'
	return dict(
					myBackButton=mkBackButton(URL(c='manager',f='pending_articles')), 
					myHelp=getHelp(request, auth, db, '#ManageSuggestedRecommenders'),
					myText=getText(request, auth, db, '#ManageSuggestedRecommendersText'),
					myTitle=getTitle(request, auth, db, '#ManageSuggestedRecommendersTitle'),
					grid=grid, 
				)





@auth.requires(auth.has_membership(role='manager'))
def edit_article():
	if not('articleId' in request.vars):
		session.flash = T('Unavailable')
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(request.env.http_referer)
	#db.t_articles.status.readable=False
	db.t_articles.status.writable=True
	db.t_articles.user_id.writable=True
	form = SQLFORM(db.t_articles
				,articleId
				,upload=URL('default', 'download')
				,deletable=True
				,showid=True
			)
	if form.process().accepted:
		response.flash = T('Article saved', lazy=False)
		redirect(URL(c='manager', f='recommendations', vars=dict(articleId=art.id), user_signature=True))
	elif form.errors:
		response.flash = T('Form has errors', lazy=False)
	response.view='default/myLayout.html'
	return dict(
				#myBackButton = mkBackButton(),
				myHelp = getHelp(request, auth, db, '#ManagerEditArticle'),
				myText=getText(request, auth, db, '#ManagerEditArticleText'),
				myTitle=getTitle(request, auth, db, '#ManagerEditArticleTitle'),
				form = form,
			)


@auth.requires(auth.has_membership(role='manager'))
def manage_comments():
	db.t_comments.parent_id.label=T('Parent comment')
	grid = SQLFORM.smartgrid(db.t_comments
					,create=False
					,fields=[db.t_comments.article_id, db.t_comments.comment_datetime, db.t_comments.user_id, db.t_comments.parent_id, db.t_comments.user_comment]
					,linked_tables=['t_comments']
					,csv=csv, exportclasses=dict(t_comments=expClass)
					,maxtextlength=250
					,paginate=25
					,orderby=~db.t_comments.comment_datetime
			)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#ManageCommentsText'),
				myTitle=getTitle(request, auth, db, '#ManageCommentsTitle'),
				myHelp=getHelp(request, auth, db, '#ManageComments'),
				grid=grid, 
			 )


@auth.requires(auth.has_membership(role='manager'))
def resizeArticleImages(ids):
	for articleId in ids:
		makeArticleThumbnail(auth, db, articleId, size=(150,150))


