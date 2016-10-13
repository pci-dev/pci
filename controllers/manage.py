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



# Send email to suggested recommenders for a given article
@auth.requires(auth.has_membership(role='manager'))
def send_email_to_suggested_recommenders():
	articleId = request.vars['articleId']
	if articleId:
		article = db.t_articles[articleId]
		if article is not None:
			do_send_email_to_suggested_recommenders(session, auth, db, articleId)
	redirect(URL('suggested_recommenders', vars=dict(articleId=articleId)))





# Change article status:
#	Pending -> Awaiting consideration
#	Pre-recommended -> Recommended
# Limited to manager or administrator
@auth.requires(auth.has_membership(role='manager'))
def _validate_articles(ids, response):
	for myId in ids:
		art = db.t_articles[myId]
		if art.status == 'Pending':
			art.status = 'Awaiting consideration'
			art.update_record()
		elif art.status == 'Pre-recommended':
			art.status = 'Recommended'
			art.update_record()
			#TODO: tweet article
			link = URL(c='public', f='recommendations', scheme=True, host=True, vars=dict(articleId=art.id))
			print A(link, _href=link)





# Display pending articles and allow management
# Managers or administrators
@auth.requires(auth.has_membership(role='manager'))
def pending_articles():
	resu = _manage_articles(False)
	resu['myTitle'] = T('Pending articles')
	resu['myHelp'] = getHelp(request, auth, dbHelp, '#ManagePendingArticles')
	return resu



# Display all articles and allow management
# Managers or administrators
@auth.requires(auth.has_membership(role='manager'))
def all_articles():
	resu = _manage_articles(True)
	resu['myTitle'] = T('All articles')
	resu['myHelp'] = getHelp(request, auth, dbHelp, '#ManageAllArticles')
	return resu



@auth.requires(auth.has_membership(role='manager'))
def suggest_article_to():
	articleId = request.vars['articleId']
	recommenderId = request.vars['recommenderId']
	db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)
	redirect('pending_articles')




# Allow management of articles
@auth.requires(auth.has_membership(role='manager'))
def _manage_articles(includeRecommended):
	if includeRecommended:
		query = db.t_articles
	else:
		query = ~(db.t_articles.status=='Recommended')
	selectable = [(T('Validate pending or pre-recommended selected articles'), lambda ids: _validate_articles(ids, response), 'class1')]
	db.t_articles.user_id.default = auth.user_id
	db.t_articles.user_id.writable = False
	db.t_articles.user_id.represent = lambda text, row: mkUserWithMail(auth, db, text)
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	db.t_articles.status.writable = True
	db.t_articles.auto_nb_recommendations.readable = False
	db.t_articles.auto_nb_recommendations.writable = False
	db.t_articles.doi.represent = lambda text, row: mkDOI(text)
	if len(request.args) == 0: # we are in grid
		db.t_articles.doi.readable = False
		db.t_articles.authors.readable = False
		db.t_articles.title.readable = False
		db.t_articles.abstract.readable = False
		db.t_articles.keywords.readable = False
		db.t_articles.thematics.readable = False
		db.t_articles.user_id.readable = False
		db.t_articles._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
		db.t_articles._id.label = T('Article')
		db.t_articles.upload_timestamp.represent = lambda text, row: mkLastChange(row.upload_timestamp)
		db.t_articles.last_status_change.represent = lambda text, row: mkLastChange(row.last_status_change)
	else: # we are in grid's form
		db.t_articles.abstract.represent=lambda text, row: WIKI(text)

	links = [
				dict(header=T('Recommenders'), body=lambda row: mkSuggestedRecommendersButton(auth, db, row)),
				dict(header=T('Search recommenders'), body=lambda row: mkSearchRecommendersButton(auth, db ,row)),
				dict(header=T('Manage Recomm.'), body=lambda row: mkRecommendationsButton(auth, db, row, URL(f='manage_recommendations', vars=dict(articleId=row.id)))),
			]
	grid = SQLFORM.grid(query
		,details=False
		,editable=True, deletable=False, create=False, selectable=selectable
		,searchable=False
		,maxtextlength=250, paginate=20
		,csv=csv, exportclasses=expClass
		,fields=[db.t_articles._id, db.t_articles.title, db.t_articles.authors, db.t_articles.abstract, db.t_articles.doi, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.user_id, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations]
		,links=links
		,left=db.t_status_article.on(db.t_status_article.status==db.t_articles.status)
		,orderby=db.t_status_article.priority_level|~db.t_articles.last_status_change
	)
	if grid.elements('th'):
		grid.elements('colgroup')[0].insert(0, XML('<col id="kazakoch" data-column="0">')) # Trick: restore columns alignment
		grid.elements('th')[0].append(SPAN(T('All'), BR(), 
			INPUT(_name='mySelectAll', _type='checkbox', 
				_onclick="jQuery('input[type=checkbox]').each(function(k){if (this.name == 'records') {jQuery(this).prop('checked', !jQuery(this).prop('checked'));} });"
				)
		))
	response.view='default/myLayout.html'
	return dict(grid=grid, 
				myTitle=T('Articles'),
			)




# Allow management of article recommendations
@auth.requires(auth.has_membership(role='manager'))
def manage_recommendations():
	articleId = request.vars['articleId']
	query = db.t_recommendations.article_id == articleId
	db.t_recommendations.recommender_id.default = auth.user_id
	db.t_recommendations.article_id.default = articleId
	db.t_recommendations.article_id.writable = False
	db.t_recommendations.doi.represent = lambda text, row: mkDOI(text)
	db.t_recommendations._id.readable = False
	if len(request.args) == 0: # in grid
		#db.t_recommendations.recommendation_comments.represent=lambda text, row: WIKI(text[:500]+'...') if len(text or '')>500 else WIKI(text or '')
		db.t_recommendations.recommendation_comments.represent=lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
		db.t_recommendations.recommendation_timestamp.represent = lambda text, row: mkLastChange(row.recommendation_timestamp)
		db.t_recommendations.last_change.represent = lambda text, row: mkLastChange(row.last_change)
	else: # in form
		db.t_recommendations.recommendation_comments.represent=lambda text, row: WIKI(text or '')

	grid = SQLFORM.grid( query
		,editable=True
		,deletable=True
		,create=False
		,details=False
		,searchable=False
		,maxtextlength=1000
		,csv=csv, exportclasses=expClass
		,paginate=10
		,fields=[db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.is_closed, db.t_recommendations.recommender_id, db.t_recommendations.recommendation_comments]
		,links = [dict(header=T('Reviews'), body=lambda row: A((db.v_reviewers[row.id]).reviewers or 'ADD', _href=URL(c='recommender', f='reviews', vars=dict(recommendationId=row.id))))]
		,orderby=~db.t_recommendations.recommendation_timestamp
	)
	myContents = mkRepresentArticle(auth, db, articleId)
	response.view='default/recommLayout.html'
	return dict(
				myBackButton = mkBackButton(),
				myTitle=T('Manage recommendations'),
				myContents=myContents,
				grid=grid,
				myHelp=getHelp(request, auth, dbHelp, '#ManageRecommendations'),
			)




@auth.requires(auth.has_membership(role='manager'))
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
	temp_db.qy_recomm.email.represent = lambda text, row: A(text, _href='mailto:'+text)
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
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
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
					dict(header=T('Days since last recommendation'), body=lambda row: db.v_last_recommendation[row.id].days_since_last_recommendation),
					dict(header=T('Suggest as recommender'),         body=lambda row: mkSuggestArticleToButton(auth, db, row, articleId)),
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
		response.view='default/recommenders.html'
		return dict(searchForm=searchForm, 
					myTitle=T('Search recommenders'), 
					myBackButton=mkBackButton(),
					grid=grid, 
					myHelp=getHelp(request, auth, dbHelp, '#SearchRecommenders'),
				)



# Display suggested recommenders for a submitted article
# Logged users only (submission)
@auth.requires(auth.has_membership(role='manager'))
def suggested_recommenders():
	articleId = request.vars['articleId']
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
		,fields=[db.t_suggested_recommenders.suggested_recommender_id, db.t_suggested_recommenders.email_sent]
	)
	myEmailButton = '' #A(SPAN(current.T('Send email to suggested recommenders'), _class='buttontext btn btn-default'), _href=URL(f='send_email_to_suggested_recommenders', vars=dict(articleId=articleId), user_signature=True), _class='button')
	response.view='manage/suggested_recommenders.html'
	return dict(grid=grid, 
				myTitle=T('Suggested recommenders'), 
				myBackButton=mkBackButton(URL(c='manage',f='pending_articles')), 
				myEmailButton=myEmailButton,
				myHelp=getHelp(request, auth, dbHelp, '#ManageSuggestedRecommenders'),
			 )


