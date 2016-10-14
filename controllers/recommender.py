# -*- coding: utf-8 -*-

import re
import copy
import datetime
from dateutil.relativedelta import *

from gluon.contrib.markdown import WIKI
from common import *
from helper import *


# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4




@auth.requires(auth.has_membership(role='recommender'))
def new_submission():
	panel = [LI(A(current.T("Click to start a recommendation process of a manuscript already peer-reviewed"), 
					_href=URL('recommender', 'direct_submission', user_signature=True), 
					_class="btn btn-success pci-panelButton"), 
				_class="list-group-item list-group-item-centered")
			]
	response.view='default/info.html'
	return dict(
		panel = DIV(UL( panel, _class="list-group"), _class="panel panel-info"),
		myText = getText(request, auth, dbHelp, '#NewRecommendationInfo'),
		myBackButton = mkBackButton(),
	)





@auth.requires(auth.has_membership(role='recommender'))
def search_reviewers():
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
		elif (re.match('^qy_', myVar)):
			qyTF.append(re.sub(r'^qy_', '', myVar))
	qyKwArr = qyKw.split(' ')
	searchForm =  mkSearchForm(auth, db, myVars)
	#TODO: modify search_reviewers for possibly limiting to recommenders only
	filtered = db.executesql('SELECT * FROM search_reviewers(%s, %s, %s);', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
	for fr in filtered:
		qy_reviewers.insert(**fr)
			
	temp_db.qy_reviewers._id.readable = False
	temp_db.qy_reviewers.uploaded_picture.readable = False
	links = []
	if 'recommId' in request.vars:
		recommId = request.vars['recommId']
		links.append(  dict(header=T('Days since last recommendation'), body=lambda row: db.v_last_recommendation[row.id].days_since_last_recommendation)  )
		if myGoal == '4review':
			links.append(  dict(header=T('Propose review'), body=lambda row: mkSuggestReviewToButton(auth, db, row, recommId, myGoal)) )
			myTitle = T('Search for reviewers')
			myHelp=getHelp(request, auth, dbHelp, '#RecommenderSearchReviewers')
		elif myGoal == '4press':
			links.append(  dict(header=T('Propose contribution'), body=lambda row: mkSuggestReviewToButton(auth, db, row, recommId, myGoal))  )
			myTitle = T('Search for collaborators')
			myHelp=getHelp(request, auth, dbHelp, '#RecommenderSearchCollaborators')
	grid = SQLFORM.grid( qy_reviewers
		,editable = False,deletable = False,create = False,details=False,searchable=False
		,maxtextlength=250,paginate=100
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_reviewers.num, temp_db.qy_reviewers.score, temp_db.qy_reviewers.uploaded_picture, temp_db.qy_reviewers.first_name, temp_db.qy_reviewers.last_name, temp_db.qy_reviewers.email, temp_db.qy_reviewers.laboratory, temp_db.qy_reviewers.institution, temp_db.qy_reviewers.city, temp_db.qy_reviewers.country, temp_db.qy_reviewers.thematics]
		,links=links
		,orderby=temp_db.qy_reviewers.num
		,args=request.args
	)
	#response.view='default/recommenders.html'
	response.view='default/myLayout.html'
	return dict(
				myHelp=myHelp,
				myTitle=myTitle,
				myBackButton=mkBackButton(),
				searchForm=searchForm, 
				grid=grid, 
			 )



def mkViewEditArticleRecommenderButton(auth, db, row):
	return A(SPAN(current.T('View'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='recommender', f='article_details', vars=dict(articleId=row.id), user_signature=True), _class='button', _title=current.T('View and accept or decline recommendation'))



@auth.requires(auth.has_membership(role='recommender'))
def my_awaiting_articles():
	query = ( 
				(db.t_articles.status == 'Awaiting consideration')
			  & (db.t_articles._id == db.t_suggested_recommenders.article_id) 
			  & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
		)
	db.t_articles.user_id.writable = False
	#db.t_articles.doi.represent = lambda text, row: mkDOI(text)
	db.t_articles.auto_nb_recommendations.readable = False
	#db.t_articles.status.readable = False
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
	grid = SQLFORM.grid( query
		,searchable=False,editable=False,deletable=False,create=False,details=False
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,fields=[db.t_articles._id, db.t_articles.abstract, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.user_id, db.t_articles.upload_timestamp, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations, db.t_articles.status]
		,links=[
			dict(header=T('Suggested recommenders'), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders),
			dict(header=T(''), body=lambda row: mkViewEditArticleRecommenderButton(auth, db, row)),
		]
		,orderby=~db.t_articles.upload_timestamp
	)
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, dbHelp, '#RecommenderSuggestedArticles'),
				myBackButton=mkBackButton(), 
				myTitle=T('Requests for recommendation of prereview articles'), 
				grid=grid, 
			)



# Common function for articles needing attention
@auth.requires(auth.has_membership(role='recommender'))
def _awaiting_articles(myVars):
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
		Field('upload_timestamp', type='datetime', default=request.now, label=T('Submission date/time')),
		Field('thematics', type='string', length=1024, label=T('Thematic fields')),
		Field('keywords', type='text', label=T('Keywords')),
		Field('auto_nb_recommendations', type='integer', label=T('Number of recommendations'), default=0),
		Field('status', type='string', length=50, default='Pending', label=T('Status')),
		Field('last_status_change', type='datetime', default=request.now, label=T('Last status change')),
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
		elif (re.match('^qy_', myVar)):
			qyTF.append(re.sub(r'^qy_', '', myVar))
	qyKwArr = qyKw.split(' ')
	searchForm =  mkSearchForm(auth, db, myVars)
	filtered = db.executesql('SELECT * FROM search_articles(%s, %s, %s, %s, %s);', placeholders=[qyTF, qyKwArr, 'Awaiting consideration', trgmLimit, True], as_dict=True)
	for fr in filtered:
		qy_art.insert(**fr)
	
	temp_db.qy_art.auto_nb_recommendations.readable = False
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
	else:
		temp_db.qy_art._id.readable = False
		temp_db.qy_art.num.readable = False
		temp_db.qy_art.score.readable = False
		temp_db.qy_art.doi.represent = lambda text, row: mkDOI(text)
		temp_db.qy_art.abstract.represent = lambda text, row: WIKI(text or '')
		
	grid = SQLFORM.grid(temp_db.qy_art
		,searchable=False,editable=False,deletable=False,create=False,details=False
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_art.num, temp_db.qy_art.score, temp_db.qy_art._id, temp_db.qy_art.title, temp_db.qy_art.authors, temp_db.qy_art.article_source, temp_db.qy_art.abstract, temp_db.qy_art.thematics, temp_db.qy_art.keywords, temp_db.qy_art.upload_timestamp, temp_db.qy_art.last_status_change, temp_db.qy_art.status, temp_db.qy_art.auto_nb_recommendations]
		,links=[
			dict(header=T('Suggested recommenders'), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders),
			dict(header=T(''), body=lambda row: mkViewEditArticleRecommenderButton(auth, db, row)),
		]
		,orderby=temp_db.qy_art.num
	)
	response.view='default/myLayout.html'
	return dict(grid=grid, searchForm=searchForm, 
				myTitle=T('Articles requiring a recommender'), 
				myBackButton=mkBackButton(), 
			)



@auth.requires(auth.has_membership(role='recommender'))
def fields_awaiting_articles():
	resu = _awaiting_articles(request.vars)
	resu['myTitle'] = T('Articles awaiting consideration in my fields')
	resu['myHelp'] = getHelp(request, auth, dbHelp, '#RecommenderArticlesAwaitingRecommendation:InMyFields')
	return resu



@auth.requires(auth.has_membership(role='recommender'))
def all_awaiting_articles():
	myVars = request.vars
	for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
		myVars['qy_'+thema.keyword] = 'on'
	resu = _awaiting_articles(myVars)
	resu['myTitle'] = T('All articles awaiting consideration')
	resu['myHelp'] = getHelp(request, auth, dbHelp, '#RecommenderArticlesAwaitingRecommendation:All')
	return resu




@auth.requires(auth.has_membership(role='recommender'))
def article_details():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	amIAllowed = db( (db.t_recommendations.article_id == articleId) ).count() == 0
	if not(amIAllowed):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		if printable:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
				DIV(
					DIV(I(myconf.take('app.longname')+': ')+T(art.status), _class='pci-ArticleText printable'),
					_class='pci-ArticleHeaderIn printable'
				))
			myUpperBtn = ''
			response.view='default/recommended_article_printable.html' #OK
		else:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
				DIV(
					DIV(I(myconf.take('app.longname'))+BR()+T(art.status), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn'
				))
			myUpperBtn = A(SPAN(T('Printable page'), _class='pci-ArticleTopButton buttontext btn btn-info'), 
				_href=URL(c="user", f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
				_class='button')
			response.view='default/recommended_articles.html' #OK
		
		myContents = mkFeaturedArticle(auth, db, art, printable, quiet=False)
		myContents.append(HR())
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, dbHelp, '#RecommenderArticlesRequiringRecommender'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)


@auth.requires(auth.has_membership(role='recommender'))
def accept_new_article_to_recommend():
	articleId = request.vars['articleId']
	article = db.t_articles[articleId]
	if article.status == 'Awaiting consideration':
		db.t_recommendations.insert(article_id=articleId, recommender_id=auth.user_id, doi=article.doi)
		article.status = 'Under consideration'
		article.update_record()
		redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))
	else:
		session.flash = T('Article no more available', lazy=False)
		redirect('my_awaiting_articles')



@auth.requires(auth.has_membership(role='recommender'))
def recommend_article():
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		recomm.is_closed=True
		recomm.update_record()
		art = db.t_articles[recomm.article_id]
		art.status = 'Pre-recommended'
		art.update_record()
		#db.commit()
		redirect(URL(c='recommender', f='recommendations', vars=dict(articleId=recomm.article_id), user_signature=True))



@auth.requires(auth.has_membership(role='recommender'))
def reject_article():
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		recomm.is_closed=True
		recomm.update_record()
		art = db.t_articles[recomm.article_id]
		art.status = 'Rejected'
		art.update_record()
		db.commit()
		redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))



@auth.requires(auth.has_membership(role='recommender'))
def revise_article():
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		# Do not close recommendation due to reply
		art = db.t_articles[recomm.article_id]
		art.status = 'Awaiting revision'
		art.update_record()
		db.commit()
		redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))



@auth.requires(auth.has_membership(role='recommender'))
def decline_new_article_to_recommend():
	articleId = request.vars['articleId']
	if articleId is not None:
		#NOTE: No security hole as only logged user can be deleted
		db(db.t_suggested_recommenders.article_id == articleId and db.t_suggested_recommenders.suggested_recommender_id == auth.user_id).delete()
	redirect(URL('my_awaiting_articles', user_signature=True))



@auth.requires(auth.has_membership(role='recommender'))
def suggest_review_to():
	reviewerId = request.vars['reviewerId']
	if reviewerId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		#if request.vars['myGoal'] == '4review':
		db.t_reviews.update_or_insert(recommendation_id=recommId, reviewer_id=reviewerId)
		redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))
		#elif request.vars['myGoal'] == '4press':
			#db.t_press_reviews.update_or_insert(recommendation_id=recommId, contributor_id=reviewerId)
			#redirect(URL('my_recommendations', vars=dict(pressReviews=True), user_signature=True))
		#else:
			#raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access



@auth.requires(auth.has_membership(role='recommender'))
def suggest_collaboration_to():
	reviewerId = request.vars['reviewerId']
	if reviewerId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		#if request.vars['myGoal'] == '4review':
			#db.t_reviews.update_or_insert(recommendation_id=recommId, reviewer_id=reviewerId)
			#redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))
		#elif request.vars['myGoal'] == '4press':
		db.t_press_reviews.update_or_insert(recommendation_id=recommId, contributor_id=reviewerId)
		redirect(URL('my_recommendations', vars=dict(pressReviews=True), user_signature=True))
		#else:
			#raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access



def mkViewEditRecommendationsRecommenderButton(auth, db, row):
	return A(SPAN(current.T('Check & Edit'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='recommender', f='recommendations', vars=dict(articleId=row.article_id), user_signature=True), _class='button', _title=current.T('View and/or edit article'))

@auth.requires(auth.has_membership(role='recommender'))
def my_recommendations():
	isPress = ( ('pressReviews' in request.vars) and (request.vars['pressReviews']=='True') )
	if isPress:
		query = ( (db.t_recommendations.recommender_id == auth.user_id) 
				& (db.t_recommendations.article_id == db.t_articles.id) 
				& (db.t_articles.already_published == True)
			)
		myTitle = T('Your recommendations of reviewed articles')
		fields = [db.t_recommendations.article_id, db.t_articles.status, db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.is_closed, db.t_recommendations.recommendation_comments]
		links = [
				dict(header=T('Contributors'), body=lambda row: mkSollicitedPress(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				#dict(header=T('Declined contributions'),   body=lambda row:   mkDeclinedPress(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				#dict(header=T('Ongoing contributions'),    body=lambda row:    mkOngoingPress(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				#dict(header=T('Closed contributions'),     body=lambda row:     mkClosedPress(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T(''),                        body=lambda row: mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
			]
	else:
		query = ( (db.t_recommendations.recommender_id == auth.user_id) 
				& (db.t_recommendations.article_id == db.t_articles.id) 
				& (db.t_articles.already_published == False)
				& (db.t_recommendations.is_closed == False)
			)
		myTitle = T('Your recommendations of prereview articles')
		fields = [db.t_recommendations.article_id, db.t_articles.status, db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.is_closed, db.t_recommendations.recommendation_comments]
		links = [
				dict(header=T('Sollicited reviewers'), body=lambda row: mkSollicitedRev(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T('Declined reviews'),   body=lambda row:   mkDeclinedRev(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T('Ongoing reviews'),    body=lambda row:    mkOngoingRev(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T('Closed reviews'),     body=lambda row:     mkClosedRev(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T(''),                     body=lambda row: mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
			]
		
	db.t_recommendations.recommender_id.writable = False
	db.t_recommendations.doi.writable = False
	db.t_recommendations.article_id.writable = False
	db.t_recommendations._id.readable = False
	#db.t_recommendations.is_press_review.writable = False
	#db.t_recommendations.is_press_review.readable = False
	#db.t_recommendations.reply.writable = False
	#db.t_recommendations.reply.readable=False
	db.t_recommendations.is_closed.readable = False
	db.t_recommendations.is_closed.writable = False
	db.t_recommendations.recommendation_timestamp.label = T('Last change')
	db.t_recommendations.recommendation_timestamp.represent = lambda text, row: mkLastChange(row.t_recommendations.recommendation_timestamp) if 't_recommendations' in row else mkElapsed(row.recommendation_timestamp)
	db.t_recommendations.article_id.represent = lambda aid, row: mkArticleCellNoRecomm(auth, db, db.t_articles[aid])
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	db.t_recommendations.doi.readable=False
	db.t_recommendations.last_change.readable=False
	db.t_recommendations.recommendation_comments.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
	grid = SQLFORM.grid( query
		,searchable=False, create=False, deletable=False, editable=False, details=False
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=fields
		,links=links
		,orderby=~db.t_recommendations.last_change
	)
	#myBackButton = A(SPAN(T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')
	#response.view='recommender/my_recommendations.html'
	response.view='default/myLayout.html'
	return dict(
				myHelp = getHelp(request, auth, dbHelp, '#RecommenderMyRecommendations'),
				myTitle=myTitle, 
				myBackButton=mkBackButton(), 
				grid=grid, 
			 )


@auth.requires(auth.has_membership(role='recommender'))
def process_opinion():
	print request.vars
	if 'recommender_opinion' in request.vars and 'recommId' in request.vars:
		ro = request.vars['recommender_opinion']
		rId = request.vars['recommId']
		if ro == 'do_recommend': 
			redirect(URL(c='recommender', f='recommend_article', vars=dict(recommId=rId), user_signature=True))
		elif ro == 'do_revise': 
			redirect(URL(c='recommender', f='revise_article', vars=dict(recommId=rId), user_signature=True))
		elif ro == 'do_reject': 
			redirect(URL(c='recommender', f='reject_article', vars=dict(recommId=rId), user_signature=True))
	redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))




@auth.requires(auth.has_membership(role='recommender'))
def direct_submission():
	myTitle=T('Initiate the recommendation of an article')
	db.t_articles.user_id.default = None
	db.t_articles.user_id.writable = False
	db.t_articles.status.default = 'Under consideration'
	db.t_articles.status.writable = False
	db.t_articles.already_published.readable = False
	db.t_articles.already_published.writable = False
	db.t_articles.already_published.default = True
	fields = [db.t_articles.already_published, db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.doi, db.t_articles.abstract, db.t_articles.thematics, db.t_articles.keywords]
	form = SQLFORM.factory(*fields, table_name='t_articles')
	if form.process().accepted:
		newId = db.t_articles.insert(**db.t_articles._filter_fields(form.vars))
		recommId = db.t_recommendations.insert(article_id=newId, recommender_id=auth.user_id, doi=form.vars.doi)
		#redirect(URL('my_recommendations', vars=dict(pressReviews=True), user_signature=True))
		redirect(URL('contributions', vars=dict(recommId=recommId), user_signature=True))
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, dbHelp, '#RecommenderDirectSubmission'),
				myBackButton=mkBackButton(),
				myTitle=myTitle, 
				form=form, 
			 )



@auth.requires(auth.has_membership(role='recommender'))
def recommendations():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	amIAllowed = db(
					(
						(db.t_recommendations.recommender_id == auth.user_id)
					  | ( (db.t_press_reviews.contributor_id == auth.user_id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id) )
					)
				  & (db.t_recommendations.article_id == articleId) 
			).count() > 0
	if not(amIAllowed):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		if printable:
			if art.status == 'Recommended':
				myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
						DIV(
							DIV(T('Recommended Article'), _class='pci-ArticleText printable'),
							_class='pci-ArticleHeaderIn recommended printable'
						))
			else:
				myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
					DIV(
						DIV(I(myconf.take('app.longname')+': ')+T(art.status), _class='pci-ArticleText printable'),
						_class='pci-ArticleHeaderIn printable'
					))
			myUpperBtn = ''
			response.view='default/recommended_article_printable.html' #OK
		else:
			if art.status == 'Recommended':
				myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
					DIV(
						DIV(I(myconf.take('app.longname'))+BR()+T('Recommended Article'), _class='pci-ArticleText'),
						_class='pci-ArticleHeaderIn recommended'
					))
			else:
				myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
					DIV(
						DIV(I(myconf.take('app.longname'))+BR()+T(art.status), _class='pci-ArticleText'),
						_class='pci-ArticleHeaderIn'
					))
			myUpperBtn = A(SPAN(T('Printable page'), _class='buttontext btn btn-info'), 
				_href=URL(c="user", f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
				_class='button')
			response.view='default/recommended_articles.html' #OK
		
		myContents = mkFeaturedArticle(auth, db, art, printable, quiet=False)
		myContents.append(HR())
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, dbHelp, '#RecommenderOtherRecommendations'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)



@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reopen_review(ids):
	if auth.has_membership(role='manager'):
		for myId in ids:
			rev = db.t_reviews[myId]
			if rev.review_state != 'Under consideration':
				rev.review_state = 'Under consideration'
				rev.update_record()
	elif auth.has_membership(role='recommender'):
		for myId in ids:
			rev = db.t_reviews[myId]
			recomm = db.t_recommendations[rev.recommendation_id]
			if (recomm.recommender_id == auth.user_id) and not(rev.review_state == 'Under consideration'):
				rev.review_state = 'Under consideration'
				rev.update_record()
			




@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reviews():
	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if recomm == None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		myContents = mkRecommendationFormat(auth, db, recomm)
		db.t_reviews._id.readable = False
		db.t_reviews.recommendation_id.default = recommId
		db.t_reviews.recommendation_id.writable = False
		db.t_reviews.recommendation_id.readable = False
		db.t_reviews.reviewer_id.writable = False
		db.t_reviews.reviewer_id.default = auth.user_id
		db.t_reviews.reviewer_id.represent = lambda text,row: mkUserWithMail(auth, db, row.reviewer_id) if row else ''
		db.t_reviews.anonymously.default = True
		db.t_reviews.anonymously.writable = auth.has_membership(role='manager')
		db.t_reviews.review.writable = auth.has_membership(role='manager')
		db.t_reviews.review_state.writable = auth.has_membership(role='manager')
		
		if len(request.args)==0 or (len(request.args)==1 and request.args[0]=='auth_user'): # grid view
			selectable = [(T('Re-open selected reviews'), lambda ids: [reopen_review(ids)], 'class1')]
			db.t_reviews.review.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
		else: # form view
			selectable = None
			db.t_reviews.review.represent = lambda text, row: WIKI(text or '')
		
		query = (db.t_reviews.recommendation_id == recommId)
		grid = SQLFORM.grid( query
			,details=True
			,editable=lambda row: auth.has_membership(role='manager') or (row.review_state!='Terminated' and row.reviewer_id is None)
			,deletable=auth.has_membership(role='manager')
			,create=True
			,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_reviews.recommendation_id, db.t_reviews.reviewer_id, db.t_reviews.anonymously, db.t_reviews.review, db.t_reviews.review_state]
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
		
		#response.view='recommender/reviews.html'
		response.view='default/myLayout.html'
		return dict(
				myHelp = getHelp(request, auth, dbHelp, '#RecommenderArticleReviews'),
				myTitle=T('Reviews for recommendation'), 
				myBackButton=mkBackButton(),
				content=myContents, 
				grid=grid, 
				myFinalScript=myScript,
			  )
	



@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def contributions():
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
		#db.t_press_reviews.contributor_id.default = auth.user_id
		db.t_press_reviews.contributor_id.represent = lambda text,row: mkUserWithMail(auth, db, row.contributor_id) if row else ''
		#db.t_press_reviews.last_change.readable = False
		#db.t_press_reviews.contribution_state.readable = False
		#db.t_press_reviews.contribution_state.writable = False
		#db.t_press_reviews.contribution_state.represent = lambda state,row: mkContributionStateDiv(auth, db, state)
		
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
		# This script renames the "Add record" button
		myScript = SCRIPT("""$(function() { 
						$('span').filter(function(i) {
								return $(this).attr("title") ? $(this).attr("title").indexOf('"""+T("Add record to database")+"""') != -1 : false;
							})
							.each(function(i) {
								$(this).text('"""+T("Add a contributor")+"""').attr("title", '"""+T("Add a new contributor to this recommendation")+"""');
							});
						})""",
						_type='text/javascript')
		response.view='default/myLayout.html'
		return dict(
					myHelp = getHelp(request, auth, dbHelp, '#RecommenderContributionsToPressReviews'),
					myTitle=T('Add or manage contributors to your recommendation'), 
					myBackButton=mkBackButton(),
					contents=myContents, 
					grid=grid, 
					myAcceptButton = DIV(
										A(SPAN(current.T('Write recommendation now'), _class='buttontext btn btn-info'), 
											_href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recommId), user_signature=True)),
										A(SPAN(current.T('Later'), _class='buttontext btn btn-info'), 
													_href=URL(c='recommender', f='my_recommendations', user_signature=True)),
										),
					myFinalScript=myScript,
				)




@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def edit_recommendation():
	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	art = db.t_articles[recomm.article_id]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	elif art.status not in ('Under consideration', 'Pre-recommended'):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		form = SQLFORM(db.t_recommendations
					,record=recomm
					,deletable=False
					,fields=['recommendation_comments']
					,showid=False
				)
		if form.process().accepted:
			response.flash = T('Recommendation saved', lazy=False)
			redirect(URL(f='recommendations', vars=dict(articleId=art.id), user_signature=True))
		elif form.errors:
			response.flash = T('Form has errors', lazy=False)
		response.view='default/myLayout.html'
		return dict(
			form = form,
			myTitle = T('Edit article'),
			myHelp = getHelp(request, auth, dbHelp, '#UserEditArticle'),
			myBackButton = mkBackButton(),
		)



@auth.requires(auth.has_membership(role='recommender'))
def my_press_reviews():
	#pendingOnly = ('pendingOnly' in request.vars) and (request.vars['pendingOnly'] == "True")
	#if pendingOnly:
		#query = ( 
				  #(db.t_press_reviews.contributor_id == auth.user_id) 
				#& (db.t_press_reviews.contribution_state == 'Pending') 
				#& (db.t_press_reviews.recommendation_id==db.t_recommendations.id) 
				#& (db.t_recommendations.article_id==db.t_articles.id)
				#)
		#myTitle = T('Requests for co-recommendations of reviewed articles')
	#else:
	query = (
			  (db.t_press_reviews.contributor_id == auth.user_id) 
			& (db.t_press_reviews.recommendation_id==db.t_recommendations.id) 
			& (db.t_recommendations.article_id==db.t_articles.id)
			)
	myTitle = T('Your co-recommendations of reviewed articles')
	db.t_press_reviews.contributor_id.writable = False
	db.t_press_reviews.recommendation_id.writable = False
	db.t_articles._id.readable = True
	db.t_articles._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
	db.t_articles._id.label = T('Article')
	db.t_articles.status.writable = False
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	#db.t_press_reviews.recommendation_id.represent = lambda text,row: mkRecommendation4PressReviewFormat(auth, db, row)
	db.t_press_reviews._id.readable = False
	#db.t_press_reviews.contribution_state.represent = lambda state,row: mkContributionStateDiv(auth, db, state)
	db.t_recommendations.recommender_id.represent = lambda uid,row: mkUserWithMail(auth, db, uid)
	db.t_recommendations.article_id.readable = False
	grid = SQLFORM.grid( query
		,searchable=False, deletable=False, create=False, editable=False, details=False
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=[db.t_articles.id, db.t_articles.status, db.t_recommendations.article_id, db.t_recommendations.recommender_id]
		,links=[
				dict(header=T('Other contributors'), body=lambda row: mkOtherContributors(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T(''), 
						body=lambda row: A(SPAN(current.T('View / Edit'), _class='buttontext btn btn-default pci-button'), 
										_href=URL(c='recommender', f='recommendations', vars=dict(articleId=row.t_articles.id), user_signature=True), 
										_target="_blank", 
										_class='button', 
										_title=current.T('View and/or validate press review')
										)
					),
				]
		,orderby=~db.t_press_reviews.id
	)
	myContents = ''
	response.view='default/myLayout.html'
	return dict(
					myHelp = getHelp(request, auth, dbHelp, '#UserMyPressReviews'),
					myTitle=myTitle, 
					myBackButton=mkBackButton(), 
					contents=myContents, 
					grid=grid, 
			 )



@auth.requires(auth.has_membership(role='recommender'))
def agree_new_press_review():
	if 'pressId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	pressId = request.vars['pressId']
	pressRev = db.t_press_reviews[pressId]
	if pressRev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if pressRev.contributor_id != auth.user_id:
		session.flash = T('Unauthorized', lazy=False)
		redirect('my_press_reviews')
	pressRev.contribution_state = 'Recommendation agreed'
	pressRev.update_record()
	# email to recommender sent at database level
	redirect('my_press_reviews')



@auth.requires(auth.has_membership(role='recommender'))
def accept_new_press_review():
	if 'pressId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	pressId = request.vars['pressId']
	pressRev = db.t_press_reviews[pressId]
	if pressRev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if pressRev.contributor_id != auth.user_id:
		session.flash = T('Unauthorized', lazy=False)
		redirect('my_press_reviews')
	pressRev.contribution_state = 'Under consideration'
	pressRev.update_record()
	# email to recommender sent at database level
	redirect('my_press_reviews')



@auth.requires(auth.has_membership(role='recommender'))
def decline_new_press_review():
	if 'pressId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	pressId = request.vars['pressId']
	pressRev = db.t_press_reviews[pressId]
	if pressRev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if pressRev.contributor_id != auth.user_id:
		session.flash = T('Unauthorized', lazy=False)
		redirect('my_press_reviews')
	#db(db.t_press_reviews.id==pressId).delete()
	pressRev.contribution_state = 'Declined'
	pressRev.update_record()
	# email to recommender sent at database level
	redirect('my_press_reviews')
	


