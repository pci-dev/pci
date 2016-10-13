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



@auth.requires_login()
def new_submission():
	panel = [LI(A(current.T("Click to request a recommendation for a manuscript not yet peer-reviewed that you authored"), _href=URL('user', 'my_articles', args=['new', 't_articles'], user_signature=True), _class="btn btn-success pci-panelButton"), _class="list-group-item list-group-item-centered")]
	response.view='default/info.html'
	return dict(
		panel = DIV(UL( panel, _class="list-group"), _class="panel panel-info"),
		myText = getText(request, auth, dbHelp, '#NewRecommendationRequestInfo'),
		myBackButton = mkBackButton(),
	)

	

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
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
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
def article_cancelled():
	articleId = request.vars['articleId']
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.user_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		art.status = 'Cancelled'
		art.update_record()
		redirect('my_articles')



@auth.requires_login()
def suggest_article_to():
	articleId = request.vars['articleId']
	recommenderId = request.vars['recommenderId']
	db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)
	redirect('my_articles')



# Display suggested recommenders for a submitted article
# Logged users only (submission)
@auth.requires_login()
def suggested_recommenders():
	write_auth = auth.has_membership('administrator') or auth.has_membership('developper')
	query = (db.t_suggested_recommenders.article_id == request.vars['articleId'])
	db.t_suggested_recommenders._id.readable = False
	grid = SQLFORM.grid( query
		,details=False,editable=False,deletable=write_auth,create=False,searchable=False
		,maxtextlength = 250,paginate=100
		,csv = csv, exportclasses = expClass
		,fields=[db.t_suggested_recommenders.suggested_recommender_id]
	)
	response.view='default/recommLayout.html'
	return dict(grid=grid, 
			 myTitle=T('Suggested recommenders'),
			 myHelp=getHelp(request, auth, dbHelp, '#SuggestedRecommenders'),
			)
	


@auth.requires_login()
def search_recommenders():
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
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		qyKwArr = qyKw.split(' ')
		searchForm =  mkSearchForm(auth, db, myVars)
		#RETURNS TABLE(id integer, num integer, score double precision, first_name character varying, last_name character varying, email character varying, uploaded_picture character varying, city character varying, country character varying, laboratory character varying, institution character varying, thematics character varying)
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
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
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



#@auth.requires_login()
#def reply_to_revision():
	#articleId = request.vars['articleId']
	#if articleId is None:
		#raise HTTP(404, "404: "+T('Unavailable'))
	#art = db.t_articles[articleId]
	#if art is None:
		#raise HTTP(404, "404: "+T('Unavailable'))
	## NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	#if art.user_id != auth.user_id:
		#session.flash = auth.not_authorized()
		#redirect(request.env.http_referer)
	#else:
		#lastRecomm = db(db.t_recommendations.article_id == articleId).select(orderby=db.t_recommendations.last_change).last()
		#db.t_recommendations.reply.writable = True
		#form = SQLFORM(db.t_recommendations
					#,deletable=False
					#,record=lastRecomm
					#,showid=False
					#,fields=['reply']
					#,hidden=dict(hiRecommId=db.t_recommendations.recommender_id)
				#)
		#subButton = form.element(_type='submit')
		#subButton['_value'] = T("Reply sent and article revised, please consider it again")
		#subButton['_class'] = 'buttontext btn btn-success'
		#if form.process().accepted:
			## creates next recommendation for recommender
			#db.t_recommendations.validate_and_insert(article_id=articleId, recommender_id=request.vars['hiRecommId'], is_closed=False, doi=art.doi)
			## set current recommendation to closed
			#lR = db.t_recommendations[form.vars.id]
			#lR.is_closed = True
			#lR.update_record
			#redirect(URL(c='user', f='article_revised', vars=dict(articleId=articleId), user_signature=True))
		#response.view='default/myLayout.html'
		#return(dict(form=form,
					#myHelp = getHelp(request, auth, dbHelp, '#UserReplyToRevisionRequest'),
			  #))




# Show my recommendation requests
@auth.requires_login()
def my_articles():
	query = db.t_articles.user_id == auth.user_id
	db.t_articles.user_id.default = auth.user_id
	db.t_articles.user_id.writable = False
	db.t_articles.auto_nb_recommendations.readable = True
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	db.t_articles.status.writable = False
	db.t_articles._id.represent = lambda text, row: mkArticleCellNoRecomm(auth, db, row)
	db.t_articles._id.label = T('Article')
	db.t_articles.doi.readable = False
	db.t_articles.title.readable = False
	db.t_articles.authors.readable = False
	db.t_articles.article_source.readable = False
	links = [
			dict(header=T('Suggested recommenders'), body=lambda row: mkSuggestedRecommendersUserButton(auth, db, row)),
			dict(header=T('Current recommender'), body=lambda row: SPAN((db.v_article_recommender[row.id]).recommender)), #getRecommender(auth, db, row)),
			dict(header='', body=lambda row: mkViewEditRecommendationsUserButton(auth, db, row)),
		]
	if len(request.args) == 0: #in grid
		db.t_articles.abstract.readable = False
		db.t_articles.keywords.readable = False
		db.t_articles.thematics.readable = False
		db.t_articles.upload_timestamp.represent = lambda text, row: mkLastChange(text)
		db.t_articles.upload_timestamp.label = T('Request submitted')
		db.t_articles.last_status_change.represent = lambda text, row: mkLastChange(text)
	elif (request.args[0]=='new') and (request.args[1]=='t_articles'): # in form
		db.t_articles.article_source.writable = False
		db.t_articles.status.readable = False
		db.t_articles.upload_timestamp.readable = False
		db.t_articles.last_status_change.readable = False
	else:
		db.t_articles.doi.represent = lambda text, row: mkDOI(text)
		
	grid = SQLFORM.grid( query
		,searchable=False, details=False, editable=False, deletable=False, create=False
		,csv=csv, exportclasses=expClass
		,maxtextlength=250,paginate=10
		,fields=[db.t_articles._id, db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.abstract, db.t_articles.doi, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations]
		,links=links
		,left=db.t_status_article.on(db.t_status_article.status==db.t_articles.status)
		,orderby=db.t_status_article.priority_level|~db.t_articles.last_status_change
	)
	myTitle=T('My submissions')
	response.view='user/my_articles.html'
	return dict(grid=grid, myTitle=myTitle, 
					myBackButton=mkBackButton(), 
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
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		myContents = mkRecommendedArticle(auth, db, art, printable)
		myContents.append(HR())
		
		if printable:
			if art.status == 'Recommended':
				myTitle=H1(myconf.take('app.longname')+' '+T('Recommended Article'), _class='pci-recommendation-title-printable')
			else:
				myTitle=H1('%s %s %s' % (myconf.take('app.longname'), T('Status:'), T(art.status)), _class='pci-status-title-printable')
			myUpperBtn = ''
			response.view='default/recommended_article_printable.html'
		else:
			if art.status == 'Recommended':
				myTitle=H1(myconf.take('app.longname')+' '+T('Recommended Article'), _class='pci-recommendation-title')
			else:
				myTitle=H1('%s %s %s' % (myconf.take('app.longname'), T('Status:'), T(art.status)), _class='pci-status-title')
			myUpperBtn = A(SPAN(T('Printable page'), _class='buttontext btn btn-info'), 
				_href=URL(f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
				_class='button')#, _target='_blank')
			response.view='default/recommended_articles.html'
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myTitle=myTitle,
					myContents=myContents,
					myUpperBtn=myUpperBtn,
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
		,links=[
					dict(header=T('Article'), body=lambda row: mkViewArticle4ReviewButton(auth, db, row)),
					dict(header=T('Article status'), body=lambda row: mkStatusDiv(auth, db, db.t_articles[db.t_recommendations[row.recommendation_id].article_id].status)),
					dict(header=T('View Recomm.'), body=lambda row: mkRecommendationsButton(auth, db, db.t_articles[db.t_recommendations[row.recommendation_id].article_id], URL(f='recommendations', vars=dict(articleId=db.t_recommendations[row.recommendation_id].article_id)))),
				]
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
		,links=[
					dict(header=T('Article'), body=lambda row: mkViewArticle4ReviewButton(auth, db, row)),
					dict(header=T('Article status'), body=lambda row: mkStatusDiv(auth, db, db.t_articles[db.t_recommendations[row.recommendation_id].article_id].status)),
					dict(header=T('View Recomm.'), body=lambda row: mkRecommendationsButton(auth, db, db.t_articles[db.t_recommendations[row.recommendation_id].article_id], URL(f='recommendations', vars=dict(articleId=db.t_recommendations[row.recommendation_id].article_id)))),
				]
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
	#db(db.t_press_reviews.id==pressId).delete()
	pressRev.contribution_state = 'Declined'
	pressRev.update_record()
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
	#db(db.t_reviews.id==reviewId).delete()
	rev.review_state = 'Declined'
	rev.update_record()
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



@auth.requires_login()
def edit_reply():
	if 'recommId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	art = db.t_articles[recomm.article_id]
	if art.user_id != auth.user_id or art.status != 'Awaiting revision':
		session.flash = T('Unauthorized', lazy=False)
		redirect('my_articles')
	form = SQLFORM(db.t_recommendations
				,record=recomm
				,fields=['reply']
				,showid=False
			)
	if form.process().accepted:
		response.flash = T('Reply saved', lazy=False)
		redirect(URL(f='recommendations', vars=dict(articleId=art.id), user_signature=True))
	elif form.errors:
		response.flash = T('Form has errors', lazy=False)
	response.view='default/myLayout.html'
	return dict(
		form = form,
		myTitle = T('Edit reply'),
		myHelp = getHelp(request, auth, dbHelp, '#UserEditReply'),
		myBackButton = mkBackButton(),
	)


@auth.requires_login()
def edit_my_article():
	if not('articleId' in request.vars):
		session.flash = T('Unavailable')
		redirect(URL('my_articles', user_signature=True))
		#raise HTTP(404, "404: "+T('Malformed URL')) # Forbidden access
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('my_articles', user_signature=True))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	elif art.status not in ('Pending', 'Awaiting revision'):
		session.flash = T('Forbidden access')
		redirect(URL('my_articles', user_signature=True))
	deletable = (art.status == 'Pending')
	db.t_articles.status.readable=False
	db.t_articles.status.writable=False
	form = SQLFORM(db.t_articles
				,record=art
				,deletable=deletable
				,fields=['title', 'authors', 'doi', 'abstract', 'thematics', 'keywords']
				,showid=False
			)
	if form.process().accepted:
		response.flash = T('Article saved', lazy=False)
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

