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
	myGoal = '4review' # default
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (myVar == '4review' or myVar == '4press'):
			myGoal = myVar
		elif (re.match('^qy_', myVar)):
			qyTF.append(re.sub(r'^qy_', '', myVar))
	qyKwArr = qyKw.split(' ')
	searchForm =  mkSearchForm(auth, db, myVars)
	filtered = db.executesql('SELECT * FROM search_reviewers(%s, %s);', placeholders=[qyTF, qyKwArr], as_dict=True)
	for fr in filtered:
		qy_reviewers.insert(**fr)
			
	temp_db.qy_reviewers._id.readable = False
	temp_db.qy_reviewers.uploaded_picture.readable = False
	links = [
				dict(header=T('Picture'), body=lambda row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100)))
		]
	if 'recommendationId' in request.vars:
		recommendationId = request.vars['recommendationId']
		links.append(  dict(header=T('Days since last recommendation'), body=lambda row: db.v_last_recommendation[row.id].days_since_last_recommendation)  )
		if myGoal == '4review':
			links.append(  dict(header=T('Propose review'), body=lambda row: mkSuggestReviewToButton(auth, db, row, recommendationId, myGoal)) )
			myTitle = T('Reviewers')
		if myGoal == '4press':
			links.append(  dict(header=T('Propose contribution'), body=lambda row: mkSuggestReviewToButton(auth, db, row, recommendationId, myGoal))  )
			myTitle = T('Collaborators')
	grid = SQLFORM.grid( qy_reviewers
		,editable = False,deletable = False,create = False,details=False,searchable=False
		,maxtextlength=250,paginate=100
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_reviewers.num, temp_db.qy_reviewers.score, temp_db.qy_reviewers.uploaded_picture, temp_db.qy_reviewers.first_name, temp_db.qy_reviewers.last_name, temp_db.qy_reviewers.email, temp_db.qy_reviewers.laboratory, temp_db.qy_reviewers.institution, temp_db.qy_reviewers.city, temp_db.qy_reviewers.country, temp_db.qy_reviewers.thematics]
		,links=links
		,orderby=temp_db.qy_reviewers.num
		,args=request.args
	)
	response.view='default/recommenders.html'
	return dict(searchForm=searchForm, 
				grid=grid, 
				myTitle=myTitle,
				myHelp=getHelp(request, auth, dbHelp, '#RecommenderSearchReviewers'),
			 )




@auth.requires(auth.has_membership(role='recommender'))
def my_awaiting_articles():
	query = (db.t_articles.status == 'Awaiting consideration') & (db.t_articles._id == db.t_suggested_recommenders.article_id) & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
	db.t_articles.user_id.writable = False
	db.t_articles.doi.represent = lambda text, row: mkDOI(text)
	db.t_articles.auto_nb_recommendations.readable = False
	db.t_articles.status.readable = False
	db.t_articles.status.writable = False
	if len(request.args) == 0: # we are in grid
		db.t_articles.doi.readable = False
		db.t_articles.authors.readable = False
		db.t_articles.title.readable = False
		db.t_articles.abstract.readable = False
		db.t_articles.keywords.readable = False
		db.t_articles._id.readable = True
		db.t_articles._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
		db.t_articles._id.label = T('Article')
		#db.t_articles.abstract.represent=lambda text, row: WIKI(text[:500]+'...') if len(text or '')>500 else WIKI(text or '')
	else: # we are in grid's form
		db.t_articles._id.readable = False
		db.t_articles.abstract.represent=lambda text, row: WIKI(text)
	grid = SQLFORM.grid( query
		,searchable=False,editable=False,deletable=False,create=False,details=True
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		#,fields=[db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.abstract, db.t_articles.doi, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.user_id, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations]
		,fields=[db.t_articles._id, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.user_id, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations]
		,links=[
			dict(header=T('Suggested recommenders'), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders),
			dict(header=T('Status'), body=lambda row: mkStatusButton(auth, db, row)),
		]
		,orderby=db.t_articles.upload_timestamp
	)
	myBackButton = A(SPAN(T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')
	if auth.has_membership('recommender') and len(request.args) >= 3:
		myAcceptBtn = DIV(
					A(SPAN(T('Yes, I consider this article'), _class='buttontext btn btn-success'), 
						_href=URL(c='recommender', f='accept_new_article_to_recommend', vars=dict(articleId=request.args(2)), user_signature=True),
						_class='button'),
					A(SPAN(T('Thanks, I decline this suggestion'), _class='buttontext btn btn-warning'), 
						_href=URL(c='recommender', f='decline_new_article_to_recommend', vars=dict(articleId=request.args(2)), user_signature=True),
						_class='button'),
					_class='pci-opinionform'
				)
	else:
		myAcceptBtn = ''
	response.view='default/awaiting_articles.html'
	return dict(grid=grid, 
				myTitle=T('Suggested considerations'), 
				myBackButton=myBackButton, 
				myAcceptBtn=myAcceptBtn,
				myHelp=getHelp(request, auth, dbHelp, '#RecommenderSuggestedArticles'),
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
	filtered = db.executesql('SELECT * FROM search_articles(%s, %s, %s, %s);', placeholders=[qyTF, qyKwArr, 'Awaiting consideration', trgmLimit], as_dict=True)
	for fr in filtered:
		qy_art.insert(**fr)
	
	temp_db.qy_art.auto_nb_recommendations.readable = False
	if len(request.args)==0: # in grid
		temp_db.qy_art._id.readable = True
		temp_db.qy_art._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
		temp_db.qy_art.title.readable = False
		temp_db.qy_art.authors.readable = False
		#temp_db.qy_art.status.readable = False
		temp_db.qy_art.article_source.readable = False
		temp_db.qy_art.upload_timestamp.represent = lambda t, row: mkLastChange(t)
		temp_db.qy_art.last_status_change.represent = lambda t, row: mkLastChange(t)
		temp_db.qy_art.abstract.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
		temp_db.qy_art.status.represent = lambda text, row: mkRecommenderStatusButton(auth, db, row)
	else:
		temp_db.qy_art._id.readable = False
		temp_db.qy_art.num.readable = False
		temp_db.qy_art.score.readable = False
		temp_db.qy_art.doi.represent = lambda text, row: mkDOI(text)
		temp_db.qy_art.abstract.represent = lambda text, row: WIKI(text or '')
		
	grid = SQLFORM.grid(temp_db.qy_art
		,searchable=False,editable=False,deletable=False,create=False,details=True
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_art.num, temp_db.qy_art.score, temp_db.qy_art._id, temp_db.qy_art.title, temp_db.qy_art.authors, temp_db.qy_art.article_source, temp_db.qy_art.abstract, temp_db.qy_art.thematics, temp_db.qy_art.keywords, temp_db.qy_art.upload_timestamp, temp_db.qy_art.last_status_change, temp_db.qy_art.status, temp_db.qy_art.auto_nb_recommendations]
		,orderby=temp_db.qy_art.num
	)
	myBackButton = A(SPAN(T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')
	if auth.has_membership('recommender') and len(request.args) >= 3:
		myAcceptBtn = DIV(
					A(SPAN(T('I consider this article'), _class='buttontext btn btn-success'), 
						_href=URL(c='recommender', f='accept_new_article_to_recommend', vars=dict(articleId=request.args(2)), user_signature=True),
						_class='button'),
					_class='pci-opinionform'
				)
	else:
		myAcceptBtn = ''
	response.view='default/awaiting_articles.html'
	return dict(grid=grid, searchForm=searchForm, 
				myTitle=T('Articles awaiting consideration'), 
				myBackButton=myBackButton, 
				myAcceptBtn=myAcceptBtn,
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
def accept_new_article_to_recommend():
	articleId = request.vars['articleId']
	article = db.t_articles[articleId]
	if article.status == 'Awaiting consideration':
		db.t_recommendations.insert(article_id=articleId, recommender_id=auth.user_id, doi=article.doi)
		article.status = 'Under consideration'
		article.update_record()
		redirect('my_recommendations')
	else:
		session.flash = T('Article no more available', lazy=False)
		redirect('my_awaiting_articles')



@auth.requires(auth.has_membership(role='recommender'))
def recommend_article():
	#print request.vars
	recommId = request.vars['recommendationId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		auth.not_authorized()
		#raise HTTP(403, "403: "+T('Access forbidden')) # Forbidden access
	else:
		art = db.t_articles[recomm.article_id]
		art.status = 'Pre-recommended'
		art.update_record()
		db.commit()
		redirect('my_recommendations')



@auth.requires(auth.has_membership(role='recommender'))
def reject_article():
	recommId = request.vars['recommendationId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		auth.not_authorized()
	else:
		art = db.t_articles[recomm.article_id]
		art.status = 'Rejected'
		art.update_record()
		db.commit()
		redirect('my_recommendations')



@auth.requires(auth.has_membership(role='recommender'))
def revise_article():
	recommId = request.vars['recommendationId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		auth.not_authorized()
	else:
		art = db.t_articles[recomm.article_id]
		art.status = 'Awaiting revision'
		art.update_record()
		db.commit()
		redirect('my_recommendations')



@auth.requires(auth.has_membership(role='recommender'))
def decline_new_article_to_recommend():
	articleId = request.vars['articleId']
	if articleId is not None:
		#NOTE: No security hole as only logged user can be deleted
		db(db.t_suggested_recommenders.article_id == articleId and db.t_suggested_recommenders.suggested_recommender_id == auth.user_id).delete()
	redirect('my_awaiting_articles')



@auth.requires(auth.has_membership(role='recommender'))
def suggest_review_to():
	reviewerId = request.vars['reviewerId']
	if reviewerId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recommId = request.vars['recommendationId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		auth.not_authorized()
	else:
		try:
			if request.vars['myGoal'] == '4review':
				db.t_reviews.insert(recommendation_id=recommId, reviewer_id=reviewerId)
			elif request.vars['myGoal'] == '4press':
				db.t_press_reviews.insert(recommendation_id=recommId, contributor_id=reviewerId)
		except:
			pass # ignore duplicated keys, ugly lazy way ;-S  #TODO: improve!
		redirect('my_recommendations')


def is_my_recommendation_editable(auth, db, row):
	resu = True
	if 't_recommendations' in row:
		recomm = row.t_recommendations
	else:
		recomm = row
	if 'article_id' not in recomm:
		resu = False
	else:
		article = db.t_articles[recomm.article_id]
		if recomm.is_closed:
			resu = False
		elif article and article.status not in ("Under consideration", "Pre-recommended", "Rejected"):
			resu = False
	return resu


@auth.requires(auth.has_membership(role='recommender'))
def my_recommendations():
	query = (db.t_recommendations.recommender_id == auth.user_id)
	db.t_recommendations.recommender_id.writable = False
	db.t_recommendations.doi.writable = False
	db.t_recommendations.article_id.writable = False
	db.t_recommendations._id.readable = False
	db.t_recommendations.is_press_review.writable = False #TODO Good idea???
	db.t_recommendations.reply.writable = False
	db.t_recommendations.is_closed.readable = False
	db.t_recommendations.is_closed.writable = False
	db.t_status_article.priority_level.readable=True
	db.t_status_article.priority_level.writable=False
	db.t_status_article.priority_level.label = T('Status')
	db.t_recommendations.recommendation_timestamp.label = T('Elapsed days')
	
	#db.t_recommendations.reply.represent = lambda text, row: WIKI(text[:500]+'...') if len(text or '')>500 else WIKI(text or '') #BUG Poor compatibility between WIKI and show_if
	#db.t_recommendations.recommendation_timestamp.represent = lambda text, row: relativedelta(datetime.datetime.now(), row.t_recommendations.recommendation_timestamp if 't_recommendations' in row else row.recommendation_timestamp).days
	db.t_recommendations.recommendation_timestamp.represent = lambda text, row: mkElapsed(row.t_recommendations.recommendation_timestamp) if 't_recommendations' in row else mkElapsed(row.recommendation_timestamp)
	db.t_recommendations.article_id.represent = lambda text, row: mkViewArticle4Recommendation(auth, db, row)
	db.t_status_article.priority_level.represent = lambda text, row: mkRecommStatusButton(auth, db, row.t_recommendations if 't_recommendations' in row else row)
	#db.t_recommendations.recommendation_comments.represent = lambda text, row: WIKI(text[:500]+'...') if len(text or '')>500 else WIKI(text or '')
	db.t_recommendations.is_press_review.represent = lambda yesno, row: IMG(_src=URL(r=request,c='static',f='images/journal.png')) if yesno else ''
	
	#BUG: crap on toast!
	#db.t_recommendations.auto_nb_agreements.show_if = (db.t_recommendations.is_press_review==True or False)
	#db.t_recommendations.reply.show_if = (db.t_recommendations.is_press_review==False and db.t_recommendations.is_closed==True)
	#db.t_recommendations.is_closed.show_if = (db.t_recommendations.is_press_review==True)
	
	if len(request.args) == 0: # grid view
		db.t_recommendations.doi.readable=False
		db.t_recommendations.last_change.readable=False
		db.t_recommendations.reply.readable=False
		db.t_recommendations.recommendation_comments.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
	else: # form view
		db.t_recommendations.recommendation_comments.represent = lambda text, row: WIKI(text or '')
	
	grid = SQLFORM.grid( query
		,left=[db.t_articles.on(db.t_articles.id==db.t_recommendations.article_id), db.t_status_article.on(db.t_status_article.status==db.t_articles.status)]
		,searchable=False
		,create=False
		,deletable=False
		,editable = lambda row: is_my_recommendation_editable(auth, db, row)
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=[db.t_recommendations.article_id, db.t_recommendations.is_press_review, db.t_status_article.priority_level, db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.is_closed, db.t_recommendations.recommendation_comments, db.t_recommendations.auto_nb_agreements, db.t_recommendations.reply]
		,links=[
			dict(header=T('Search reviewers'), body=lambda row: mkSearchReviewersButton(auth, db, row.t_recommendations if 't_recommendations' in row else row) if not (row.t_recommendations if 't_recommendations' in row else row).is_closed else ''),
			dict(header=T('Reviewers'), body=lambda row: mkRecommReviewsButton(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
		]
		,orderby=db.t_status_article.priority_level|~db.t_recommendations.last_change #|db.t_recommendations.is_closed
	)
	
	opinionForm = None
	if grid.view_form:
		myRecom = db.t_recommendations[request.args(2)]
		myArt = db.t_articles[myRecom.article_id]
		if myRecom['is_press_review'] and myRecom.auto_nb_agreements > 0 and myRecom.is_closed==False and myArt.status not in ('Pre-recommended', 'Recommended'):
			if myRecom['auto_nb_agreements'] > 0: # press review agreed by at least 1 user
				opinionForm = FORM(LABEL(T('Final recommendation:')),
						SPAN(INPUT(_name='recommender_opinion', _type='checkbox', _value='do_recommend'), T('I recommend this article'), _class='pci-radio pci-recommend'),
						INPUT(_value=T('submit'), _type='submit', _class='btn btn-primary pci-radio'),
						_class='pci-opinionform', keepvalues=True, 
						_action=URL('process_opinion', vars=dict(recommendationId=myRecom['id']), user_signature=True),
						_name='opinionForm'
					)
		elif myRecom.is_closed==False and myArt.status not in ('Pre-recommended', 'Recommended'): # not a press review
			opinionForm = FORM(LABEL(T('Final recommendation:')),
					SPAN(INPUT(_name='recommender_opinion', _type='radio', _value='do_recommend'), T('I recommend this article'), _class='pci-radio pci-recommend'),
					SPAN(INPUT(_name='recommender_opinion', _type='radio', _value='do_revise'), T('This article worth a revision'), _class='pci-radio pci-review'),
					SPAN(INPUT(_name='recommender_opinion', _type='radio', _value='do_reject'), T('I reject this article'), _class='pci-radio pci-reject'),
					INPUT(_value=T('submit'), _type='submit', _class='btn btn-primary pci-radio'),
					_class='pci-opinionform', keepvalues=True,
					_action=URL('process_opinion', vars=dict(recommendationId=myRecom['id']), user_signature=True),
					_name='opinionForm'
				)
	myBackButton = A(SPAN(T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')
	response.view='recommender/my_recommendations.html'
	return dict(grid=grid, 
				myTitle=T('My recommendations'), 
				myBackButton=myBackButton, 
				opinionForm=opinionForm,
				myHelp = getHelp(request, auth, dbHelp, '#RecommenderMyRecommendations'),
			 )


def process_opinion():
	print request.vars
	#if opinionForm: # and opinionForm.process().accepted:
	if 'recommender_opinion' in request.vars and 'recommendationId' in request.vars:
		ro = request.vars['recommender_opinion']
		rId = request.vars['recommendationId']
		if ro == 'do_recommend': 
			redirect(URL(c='recommender', f='recommend_article', vars=dict(recommendationId=rId), user_signature=True))
		elif ro == 'do_revise': 
			redirect(URL(c='recommender', f='revise_article', vars=dict(recommendationId=rId), user_signature=True))
		elif ro == 'do_reject': 
			redirect(URL(c='recommender', f='reject_article', vars=dict(recommendationId=rId), user_signature=True))
	redirect(URL('my_recommendations', user_signature=True))




@auth.requires(auth.has_membership(role='recommender'))
def direct_submission():
	myTitle=T('Submit new article and initiate recommendation')
	db.t_articles.user_id.default = None
	db.t_articles.user_id.writable = False
	db.t_articles.status.default = 'Under consideration'
	db.t_articles.status.writable = False
	fields = [Field('is_press_review', type='boolean', label=T('Is press review?'), default=True)]
	fields += [field for field in db.t_articles]
	form = SQLFORM.factory(*fields, table_name='t_articles')
	if form.process().accepted:
		newId = db.t_articles.insert(**db.t_articles._filter_fields(form.vars))
		db.t_recommendations.insert(article_id=newId, recommender_id=auth.user_id, doi=form.vars.doi, is_press_review=form.vars['is_press_review'])
		redirect(URL(c='recommender', f='my_recommendations'))
	response.view='user/my_articles.html'
	return dict(form=form, 
				myTitle=myTitle, 
				myBackButton=mkBackButton(),
				myHelp = getHelp(request, auth, dbHelp, '#RecommenderDirectSubmission'),
			 )



# Recommendations of other's articles
@auth.requires(auth.has_membership(role='recommender'))
def recommendations():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.status != 'Awaiting consideration':
		auth.not_authorized()
	else:
		myContents = mkRecommendedArticle(auth, db, art, printable)
		myContents.append(HR())
		
		if printable:
			if art.status == 'Recommended':
				myTitle=H1(myconf.take('app.name')+' '+T('Recommended Article'), _class='pci-recommendation-title-printable')
			else:
				myTitle=H1('%s %s %s' % (myconf.take('app.name'), T('Status:'), T(art.status)), _class='pci-status-title-printable')
			myAcceptBtn = ''
			response.view='default/recommended_article_printable.html'
		else:
			if art.status == 'Recommended':
				myTitle=H1(myconf.take('app.name')+' '+T('Recommended Article'), _class='pci-recommendation-title')
			else:
				myTitle=H1('%s %s %s' % (myconf.take('app.name'), T('Status:'), T(art.status)), _class='pci-status-title')
			myAcceptBtn = A(SPAN(T('Printable page'), _class='buttontext btn btn-info'), 
				_href=URL(c='public', f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
				_class='button')#, _target='_blank')
			response.view='default/recommended_articles.html'
		
		response.title = (art.title or myconf.take('app.name'))
		return dict(
					myTitle=myTitle,
					myContents=myContents,
					myAcceptBtn=myAcceptBtn,
					shareable=True,
					myHelp = getHelp(request, auth, dbHelp, '#RecommenderOtherRecommendations'),
				)


@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reopen_review(ids):
	if auth.has_membership(role='manager'):
		for myId in ids:
			db.executesql("UPDATE t_reviews SET review_state='Under consideration' WHERE id=%s;", placeholders=[myId])
	elif auth.has_membership(role='recommender'):
		for myId in ids:
			db.executesql("""UPDATE t_reviews SET review_state='Under consideration'
								FROM t_recommendations
								WHERE t_reviews.id=%s 
								AND t_reviews.recommendation_id = t_recommendations.id
								AND t_recommendations.recommender_id=%s;""", placeholders=[myId, auth.user_id])



@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reviews():
	recommendationId = request.vars['recommendationId']
	recomm = db.t_recommendations[recommendationId]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		auth.not_authorized()
	else:
		myContents = mkRecommendationFormat(auth, db, recomm)
		db.t_reviews._id.readable = False
		db.t_reviews.recommendation_id.default = recommendationId
		db.t_reviews.recommendation_id.writable = False
		db.t_reviews.recommendation_id.readable = False
		db.t_reviews.reviewer_id.writable = True
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
		
		query = (db.t_reviews.recommendation_id == recommendationId)
		grid = SQLFORM.grid( query
			,details=True
			,editable=lambda row: auth.has_membership(role='manager') or (row.review_state!='Terminated' and row.reviewer_id is None)
			,deletable=auth.has_membership(role='manager')
			,create=False
			,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_reviews.recommendation_id, db.t_reviews.reviewer_id, db.t_reviews.anonymously, db.t_reviews.review, db.t_reviews.review_state]
			,selectable=selectable
		)
		
		response.view='recommender/reviews.html'
		return dict(myContents=myContents, 
				grid=grid, 
				myTitle=T('Reviews for recommendation:'), 
				myBackButton=mkBackButton(),
				myHelp = getHelp(request, auth, dbHelp, '#RecommenderArticleReviews'),
			  )
	



@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def contributions():
	recommendationId = request.vars['recommendationId']
	recomm = db.t_recommendations[recommendationId]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		auth.not_authorized()
	else:
		myContents = mkRecommendationFormat(auth, db, recomm)
		query = (db.t_press_reviews.recommendation_id == recommendationId)
		db.t_press_reviews._id.readable = False
		db.t_press_reviews.recommendation_id.default = recommendationId
		db.t_press_reviews.recommendation_id.writable = False
		db.t_press_reviews.recommendation_id.readable = False
		db.t_press_reviews.contributor_id.writable = False
		db.t_press_reviews.contributor_id.default = auth.user_id
		db.t_press_reviews.contributor_id.represent = lambda text,row: mkUserWithMail(auth, db, row.contributor_id) if row else ''
		db.t_press_reviews.contribution_state.writable = False
		
		grid = SQLFORM.grid( query
			,details=False
			,editable=False #lambda row: auth.has_membership(role='manager')
			,deletable=lambda row: row.contribution_state is None or auth.has_membership(role='manager')
			,create=False
			,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_press_reviews.recommendation_id, db.t_press_reviews.contributor_id, db.t_press_reviews.last_change, db.t_press_reviews.contribution_state]
		)
		response.view='recommender/reviews.html'
		return dict(myContents=myContents, 
					grid=grid, 
					myTitle=T('Contributions'), 
					myBackButton=mkBackButton(),
					myHelp = getHelp(request, auth, dbHelp, '#RecommenderContributionsToPressReviews'),
				)
	



