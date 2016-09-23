# -*- coding: utf-8 -*-

import re
import copy

from gluon.contrib.markdown import WIKI
from common import *
from helper import *

# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4



# Ask for cancellation of a submetted request
@auth.requires_login()
def article_revised():
	articleId = request.vars['articleId']
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.user_id != auth.user_id:
		auth.not_authorized()
	else:
		art.status = 'Under consideration'
		art.update_record()
		last_recomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.last_change).last()
		last_recomm.is_closed = True
		last_recomm.update_record()
		db.t_recommendations.validate_and_insert(article_id=articleId, recommender_id=last_recomm.recommender_id, doi=art.doi, is_closed=False)
		db.commit()
		redirect('my_articles')


@auth.requires_login()
def article_to_cancel():
	articleId = request.vars['articleId']
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.user_id != auth.user_id:
		auth.not_authorized()
	else:
		art.status = 'Cancelled'
		art.update_record()
		redirect('my_articles')



@auth.requires_login()
def suggest_article_to():
	try:
		articleId = request.vars['articleId']
		recommenderId = request.vars['recommenderId']
		db.executesql("""INSERT INTO t_suggested_recommenders (suggested_recommender_id, article_id) VALUES (%s, %s);""" , placeholders=[recommenderId, articleId])
	except:
		pass # ignore duplicated keys, lazy way ;-S
	redirect('my_articles')



@auth.requires_login()
def search_recommenders():
	# We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
	temp_db = DAL('sqlite:memory')
	qy_recomm = temp_db.define_table('qy_recomm',
		Field('id', type='integer'),
		Field('num', type='integer'),
		Field('score', type='double', label=T('Score'), default=0),
		#Field('user_title', type='string', length=10, label=T('Title')),
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
	myVars = request.vars
	qyKw = ''
	qyTF = []
	articleId = None
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (re.match('^qy_', myVar)):
			qyTF.append(re.sub(r'^qy_', '', myVar))
		elif (myVar == 'articleId'):
			articleId = myValue
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.user_id != auth.user_id:
		auth.not_authorized()
	else:
		qyKwArr = qyKw.split(' ')
		searchForm =  mkSearchForm(auth, db, myVars)
		filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s);', placeholders=[qyTF, qyKwArr], as_dict=True)
		for fr in filtered:
			qy_recomm.insert(**fr)
				
		temp_db.qy_recomm._id.readable = False
		temp_db.qy_recomm.uploaded_picture.readable = False
		links = [
					dict(header=T('Picture'), body=lambda row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100))),
					dict(header=T('Suggest as recommender'),         body=lambda row: mkSuggestUserArticleToButton(auth, db, row, art.id)),
			]
		grid = SQLFORM.grid( qy_recomm
			,editable = False,deletable = False,create = False,details=False,searchable=False
			,maxtextlength=250,paginate=100
			,csv=csv,exportclasses=expClass
			,fields=[temp_db.qy_recomm.num, temp_db.qy_recomm.score, temp_db.qy_recomm.uploaded_picture, temp_db.qy_recomm.first_name, temp_db.qy_recomm.last_name, temp_db.qy_recomm.laboratory, temp_db.qy_recomm.institution, temp_db.qy_recomm.city, temp_db.qy_recomm.country, temp_db.qy_recomm.thematics]
			,links=links
			,orderby=temp_db.qy_recomm.num
			,args=request.args
		)
		response.view='default/recommenders.html'
		return dict(searchForm=searchForm, 
					myTitle=T('Search recommenders'), 
					myBackButton=mkBackButton(),
					grid=grid, 
					myHelp = getHelp(request, auth, dbHelp, '#UserSearchRecommenders'),
				)




# Display suggested recommenders for a submitted article
# Logged users only (submission)
@auth.requires_login()
def suggested_recommenders():
	articleId = request.vars['articleId']
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.user_id != auth.user_id:
		auth.not_authorized()
	else:
		query = (db.t_suggested_recommenders.article_id == articleId)
		db.t_suggested_recommenders._id.readable = False
		grid = SQLFORM.grid( query
			,details=False,editable=False,deletable=True,create=False,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_suggested_recommenders.suggested_recommender_id]
		)
		response.view='default/myLayout.html'
		return dict(grid=grid, 
					myTitle=T('Suggested recommenders'), 
					myBackButton=mkBackButton(),
					myHelp = getHelp(request, auth, dbHelp, '#UserSuggestedRecommenders'),
				)



@auth.requires_login()
def reply_to_revision():
	articleId = request.vars['articleId']
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.user_id != auth.user_id:
		auth.not_authorized()
	else:
		lastRecomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.last_change).last()
		db.t_recommendations.reply.writable = True
		form = SQLFORM(db.t_recommendations
					,deletable=False
					,record=lastRecomm
					,showid=False
					,fields=['reply']
					,hidden=dict(hiRecommId=db.t_recommendations.recommender_id)
				)
		subButton = form.element(_type='submit')
		subButton['_value'] = T("Reply sent and article revised, please consider it again")
		subButton['_class'] = 'buttontext btn btn-success'
		if form.process().accepted:
			# creates next recommendation for recommender
			db.t_recommendations.validate_and_insert(article_id=articleId, recommender_id=request.vars['hiRecommId'], is_closed=False, doi=art.doi)
			# set current recommendation to closed
			lR = db.t_recommendations[form.vars.id]
			lR.is_closed = True
			lR.update_record
			redirect(URL(c='user', f='article_revised', vars=dict(articleId=articleId), user_signature=True))
		response.view='default/myLayout.html'
		return(dict(form=form,
					myHelp = getHelp(request, auth, dbHelp, '#UserReplyToRevisionRequest'),
			  ))




# Show my recommendation requests
@auth.requires_login()
def my_articles():
	query = db.t_articles.user_id == auth.user_id
	db.t_articles.user_id.default = auth.user_id
	db.t_articles.user_id.writable = False
	db.t_articles.auto_nb_recommendations.readable = False
	db.t_articles.status.represent = lambda text, row: mkUserStatusButton(auth, db, row)
	db.t_articles.status.writable = False
	db.t_articles._id.represent = lambda text, row: mkArticleCell(auth, db, row)
	db.t_articles.doi.readable = False
	db.t_articles.title.readable = False
	db.t_articles.authors.readable = False
	db.t_articles.article_source.readable = False
	links = [
			dict(header=T('Recommenders'), body=lambda row: mkSuggestedRecommendersUserButton(auth, db, row)),
			dict(header=T('Suggest recommenders'), body=lambda row: mkSearchRecommendersUserButton(auth, db, row) if row.status=='Pending' else ''),
		]
	if len(request.args) == 0: #in grid
		db.t_articles.abstract.readable = False
		db.t_articles.keywords.readable = False
		db.t_articles.upload_timestamp.represent = lambda text, row: mkLastChange(text)
		db.t_articles.last_status_change.represent = lambda text, row: mkLastChange(text)
	else: # in form
		db.t_articles.doi.represent = lambda text, row: mkDOI(text)
	grid = SQLFORM.grid( query
		,searchable=False
		,editable=lambda r: (r.status == 'Pending' or r.status == 'Awaiting revision')
		,deletable=lambda r: (r.status == 'Pending')
		,csv=csv, exportclasses=expClass
		,maxtextlength=250,paginate=10
		,fields=[db.t_articles._id, db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.abstract, db.t_articles.doi, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.upload_timestamp, db.t_articles.last_status_change, db.t_articles.status, db.t_articles.auto_nb_recommendations]
		,links=links
		,left=db.t_status_article.on(db.t_status_article.status==db.t_articles.status)
		,orderby=db.t_status_article.priority_level|~db.t_articles.last_status_change
	)
	myCancelBtn = ''
	if grid.create_form: 
		myTitle=T('Submit new article')
		if grid.create_form.process().accepted:
			redirect(URL(c='user', f='search_recommenders', vars=dict(articleId=grid.create_form.vars['id'])))
	elif grid.view_form:
		myTitle=T('My recommendation request')
		articleId=request.args(2)
		if articleId is not None:
			art = db.t_articles[articleId]
			if (art is not None) and (art.status != "Cancelled"):
				myCancelBtn = A(SPAN(T('Please, cancel this recommendation request'), _class='buttontext btn btn-warning'), 
												_href=URL(c='user', f='article_to_cancel', vars=dict(articleId=articleId), user_signature=True),
												_class='button')
	elif grid.update_form:
		myTitle=T('My recommendation request')
		grid.element(_type='submit')['_value'] = T("Save")
		articleId=request.args(2)
		if articleId is not None:
			art = db.t_articles[articleId]
			if (art is not None) and (art.status != "Cancelled"):
				grid.update_form.add_button(SPAN(T('Please, cancel this recommendation request'), _class='buttontext btn btn-warning'), 
												URL(c='user', f='article_to_cancel', vars=dict(articleId=articleId), user_signature=True))
			if (art is not None) and (art.status == "Awaiting revision"):
				grid.update_form.add_button(SPAN(T('Step 2: reply to revision'), _class='buttontext btn btn-success'), 
												URL(c='user', f='reply_to_revision', vars=dict(articleId=articleId), user_signature=True))
	else:
		myTitle=T('My recommendation requests')
	response.view='user/my_articles.html'
	return dict(grid=grid, myTitle=myTitle, 
					myBackButton=mkBackButton(), 
					myAcceptBtn=myCancelBtn,
					myHelp = getHelp(request, auth, dbHelp, '#UserMyArticles'),
			 ) 



# Recommendations of my articles
@auth.requires_login()
def recommendations():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.user_id != auth.user_id:
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
					myHelp = getHelp(request, auth, dbHelp, '#UserRecommendations'),
				)



@auth.requires_login()
def my_reviews():
	query = db.t_reviews.reviewer_id == auth.user_id
	db.t_reviews.reviewer_id.writable = False
	db.t_reviews.recommendation_id.writable = False
	db.t_reviews.last_change.represent = lambda text,row: mkElapsed(row.last_change)
	db.t_reviews.last_change.label = T('Duration')
	db.t_reviews.recommendation_id.represent = lambda text,row: mkRecommendation4ReviewFormat(auth, db, row)
	db.t_reviews.recommendation_id.label = T('Member in charge of the recommendation process')
	db.t_reviews._id.readable = False
	if len(request.args) == 0:
		db.t_reviews.review.represent=lambda text, row: WIKI(text[:500]+'...') if len(text or '')>500 else WIKI(text or '')
	else:
		db.t_reviews.review.represent=lambda text, row: WIKI(text or '')
	db.t_reviews.review.label = T('My review')
	grid = SQLFORM.grid( query
		,searchable=False, deletable=False, create=False
		,editable= lambda row: (row.review_state == 'Under consideration')
		,details=True #lambda row: (row.is_closed==True)  #TODO #BUG
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=[db.t_reviews.recommendation_id, db.t_reviews.review, db.t_reviews.last_change, db.t_reviews.anonymously, db.t_reviews.review_state]
		,links=[dict(header=T('Article'), body=lambda row: mkViewArticle4ReviewButton(auth, db, row)),
				dict(header=T('Article status'), body=lambda row: mkReviewerArticleStatusButton(auth, db, row))]
		,links_placement = 'left'
		,orderby=~db.t_reviews.last_change|~db.t_reviews.review_state
	)
	myAcceptBtn = None
	if grid.view_form:
		myState = db.t_reviews[request.args(2)]['review_state']
		if myState is None:
			myAcceptBtn = DIV(
				A(SPAN(T('Yes, I accept this review'), _class='buttontext btn btn-success'), 
					_href=URL(c='user', f='accept_new_review',  vars=dict(reviewId=request.args(2)), user_signature=True), _class='button'),
				A(SPAN(T('No thanks, I decline this review'), _class='buttontext btn btn-warning'), 
					_href=URL(c='user', f='decline_new_review', vars=dict(reviewId=request.args(2)), user_signature=True), _class='button'),
				_class='pci-opinionform')
		elif myState == 'Under consideration':
			myAcceptBtn = DIV(
				A(SPAN(T('This review is now completed'), _class='buttontext btn btn-success'), 
					_href=URL(c='user', f='review_completed',  vars=dict(reviewId=request.args(2)), user_signature=True), _class='button'),
				_class='pci-opinionform'
				)
	myContents = ''
	response.view='default/reviewsLayout.html'
	return dict(grid=grid, myTitle=T('My reviews'), 
					myBackButton=mkBackButton(), 
					myAcceptBtn=myAcceptBtn,
					myContents=myContents,
					myHelp = getHelp(request, auth, dbHelp, '#UserMyReviews'),
			 )



#@auth.requires_login()
#def is_my_press_review_editable(auth, db, row):
	#resu = True
	#recomm = db.t_recommendations[row.recommendation_id]
	#if row.contribution_state is None:
		#resu = False
	#elif recomm.is_closed:
		#resu = False
	#else:
		#article = db.t_articles[recomm.article_id]
		#if article.status not in ("Under consideration", "Pre-recommended", "Rejected"):
			#resu = False
	#return resu


@auth.requires_login()
def my_press_reviews():
	query = db.t_press_reviews.contributor_id == auth.user_id
	db.t_press_reviews.contributor_id.writable = False
	db.t_press_reviews.recommendation_id.writable = False
	db.t_press_reviews.recommendation_id.represent = lambda text,row: mkRecommendation4PressReviewFormat(auth, db, row)
	db.t_press_reviews._id.readable = False
	db.t_press_reviews.contribution_state.represent = lambda text, row: T(text or '')
	grid = SQLFORM.grid( query
		,searchable=False, deletable=False, create=False
		,editable=False #lambda row: is_my_press_review_editable(auth, db, row)
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=[db.t_press_reviews.recommendation_id, db.t_press_reviews.last_change, db.t_press_reviews.contribution_state]
		,links=[dict(header=T('Article'), body=lambda row: mkViewArticle4ReviewButton(auth, db, row)),
				dict(header=T('Article status'), body=lambda row: mkReviewerArticleStatusButton(auth, db, row))]
		,links_placement = 'left'
		,orderby=~db.t_press_reviews.last_change
	)
	myAcceptBtn = None
	if grid.view_form:
		myState = db.t_press_reviews[request.args(2)]['contribution_state']
		if myState is None:
			myAcceptBtn = DIV(
				A(SPAN(T('Yes, I contribute to this press review'), _class='buttontext btn btn-success'), 
					_href=URL(c='user', f='accept_new_press_review',  vars=dict(pressId=request.args(2)), user_signature=True), _class='button'),
				A(SPAN(T('No thanks, I decline this contribution'), _class='buttontext btn btn-warning'), 
					_href=URL(c='user', f='decline_new_press_review', vars=dict(pressId=request.args(2)), user_signature=True), _class='button'),
				_class='pci-opinionform',
				)
		elif myState == 'Under consideration':
			myAcceptBtn = DIV(
				A(SPAN(T('Yes, I agree to this press review'), _class='buttontext btn btn-success'), 
					_href=URL(c='user', f='agree_new_press_review',  vars=dict(pressId=request.args(2)), user_signature=True), _class='button'),
				_class='pci-opinionform')
	myBackButton = A(SPAN(T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')
	myContents = ''
	response.view='default/reviewsLayout.html'
	return dict(grid=grid, 
					myTitle=T('My press review contributions'), 
					myBackButton=myBackButton, 
					myContents=myContents, 
					myAcceptBtn=myAcceptBtn,
					myHelp = getHelp(request, auth, dbHelp, '#UserMyPressReviews'),
			 )



@auth.requires_login()
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



@auth.requires_login()
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



@auth.requires_login()
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
	db(pressRev).delete()
	# email to recommender sent at database level
	redirect('my_press_reviews')
	


@auth.requires_login()
def accept_new_review():
	if 'reviewId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	reviewId = request.vars['reviewId']
	rev = db.t_reviews[reviewId]
	if rev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if rev.reviewer_id != auth.user_id:
		session.flash = T('Unauthorized', lazy=False)
		redirect('my_reviews')
	rev.review_state = 'Under consideration'
	rev.update_record()
	# email to recommender sent at database level
	redirect('my_reviews')



@auth.requires_login()
def decline_new_review():
	if 'reviewId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	reviewId = request.vars['reviewId']
	rev = db.t_reviews[reviewId]
	if rev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if rev.reviewer_id != auth.user_id:
		session.flash = T('Unauthorized', lazy=False)
		redirect('my_reviews')
	db(rev).delete()
	# email to recommender sent at database level
	redirect('my_reviews')



@auth.requires_login()
def review_completed():
	if 'reviewId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	reviewId = request.vars['reviewId']
	rev = db.t_reviews[reviewId]
	if rev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if rev.reviewer_id != auth.user_id:
		session.flash = T('Unauthorized', lazy=False)
		redirect('my_reviews')
	rev.review_state = 'Terminated'
	rev.update_record()
	# email to recommender sent at database level
	redirect('my_reviews')
