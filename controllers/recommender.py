# -*- coding: utf-8 -*-

import re
import copy

from gluon.contrib.markdown import WIKI
from common import *


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
		Field('user_title', type='string', length=10, label=T('Title')),
		Field('first_name', type='string', length=128, label=T('First name')),
		Field('last_name', type='string', length=128, label=T('Last name')),
		Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
		Field('city', type='string', label=T('City')),
		Field('country', type='string', label=T('Country')),
		Field('laboratory', type='string', label=T('Laboratory')),
		Field('institution', type='string', label=T('Institution')),
		Field('thematics', type='list:string', label=T('Thematic fields')),
		Field('roles', type='string', length=1024, label=T('Roles')),
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
		links.append(  dict(header=T('Propose review'), body=lambda row: mkSuggestReviewToButton(auth, db, row, recommendationId))  )
	grid = SQLFORM.grid( qy_reviewers
		,editable = False,deletable = False,create = False,details=False,searchable=False
		,maxtextlength=250,paginate=100
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_reviewers.num, temp_db.qy_reviewers.score, temp_db.qy_reviewers.uploaded_picture, temp_db.qy_reviewers.user_title, temp_db.qy_reviewers.first_name, temp_db.qy_reviewers.last_name, temp_db.qy_reviewers.laboratory, temp_db.qy_reviewers.institution, temp_db.qy_reviewers.city, temp_db.qy_reviewers.country, temp_db.qy_reviewers.thematics]
		,links=links
		,orderby=temp_db.qy_reviewers.num
		,args=request.args
	)
	response.view='default/recommenders.html'
	return dict(searchForm=searchForm, grid=grid, myTitle=T('Reviewers'))




@auth.requires(auth.has_membership(role='recommender'))
def my_awaiting_articles():
	query = (db.t_articles.status == 'Awaiting consideration') & (db.t_articles._id == db.t_suggested_recommenders.article_id) & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
	db.t_articles.user_id.writable = False
	db.t_articles._id.readable = False
	db.t_articles.doi.represent = lambda text, row: mkDOI(text)
	db.t_articles.auto_nb_recommendations.readable = False
	db.t_articles.status.readable = False
	db.t_articles.status.writable = False
	grid = SQLFORM.grid( query
		,searchable=False,editable=False,deletable=False,create=False,details=True
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,fields=[db.t_articles.title, db.t_articles.authors, db.t_articles.abstract, db.t_articles.doi, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.user_id, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations]
		,links=[
			#dict(header=T('DOI'), body=lambda row: A(row.doi, _href="http://dx.doi.org/"+re.sub(r'doi: *', '', row.doi), _class="doi_url", _target="_blank") if (row.doi) else SPAN('', _class="doi_url")),
			dict(header=T('Suggested recommenders'), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders),
			dict(header=T('Status'), body=lambda row: mkStatusButton(auth, db, row)),
		]
		,orderby=db.t_articles.upload_timestamp
	)
	myBackButton = A(SPAN(T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')
	if auth.has_membership('recommender') and len(request.args) >= 3:
		myAcceptBtn = SPAN(A(SPAN(T('Yes, I consider this article'), _class='buttontext btn btn-success'), 
				  _href=URL(c='recommender', f='accept_new_article_to_recommend', vars=dict(articleId=request.args(2)), user_signature=True),
				  _class='button'),
				A(SPAN(T('Thanks, I decline this suggestion'), _class='buttontext btn btn-warning'), 
				  _href=URL(c='recommender', f='decline_new_article_to_recommend', vars=dict(articleId=request.args(2)), user_signature=True),
				  _class='button'))
	else:
		myAcceptBtn = ''
	response.view='default/awaiting_articles.html'
	return dict(grid=grid, myTitle=T('Suggested considerations'), myBackButton=myBackButton, myAcceptBtn=myAcceptBtn)



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
		Field('doi', type='string', label=T('DOI')),
		Field('abstract', type='text', label=T('Abstract')),
		Field('upload_timestamp', type='date', default=request.now, label=T('Submission date/time')),
		Field('thematics', type='string', length=1024, label=T('Thematic fields')),
		Field('keywords', type='text', label=T('Keywords')),
		Field('auto_nb_recommendations', type='integer', label=T('Number of recommendations'), default=0),
		Field('status', type='string', length=50, default='Pending', label=T('Status')),
		Field('last_status_change', type='date', default=request.now, label=T('Last status change')),
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
	temp_db.qy_art._id.readable = False
	temp_db.qy_art.doi.represent = lambda text, row: mkDOI(text)
	temp_db.qy_art.auto_nb_recommendations.readable = False
	temp_db.qy_art.status.represent = lambda text, row: mkRecommenderStatusButton(auth, db, row)
	grid = SQLFORM.grid(temp_db.qy_art
		,searchable=False,editable=False,deletable=False,create=False,details=True
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_art.num, temp_db.qy_art.score, temp_db.qy_art.title, temp_db.qy_art.authors, temp_db.qy_art.abstract, temp_db.qy_art.thematics, temp_db.qy_art.keywords, temp_db.qy_art.upload_timestamp, temp_db.qy_art.last_status_change, temp_db.qy_art.status, temp_db.qy_art.auto_nb_recommendations]
		,orderby=temp_db.qy_art.num
	)
	myBackButton = A(SPAN(T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')
	if auth.has_membership('recommender') and len(request.args) >= 3:
		myAcceptBtn = A(SPAN(T('Yes, I consider this article'), _class='buttontext btn btn-success'), 
				  _href=URL(c='recommender', f='accept_new_article_to_recommend', vars=dict(articleId=request.args(2)), user_signature=True),
				  _class='button')
	else:
		myAcceptBtn = ''
	response.view='default/awaiting_articles.html'
	return dict(grid=grid, searchForm=searchForm, myTitle=T('Articles awaiting consideration'), myBackButton=myBackButton, myAcceptBtn=myAcceptBtn)



@auth.requires(auth.has_membership(role='recommender'))
def fields_awaiting_articles():
	resu = _awaiting_articles(request.vars)
	resu['myTitle'] = T('Articles awaiting consideration in my fields')
	return resu



@auth.requires(auth.has_membership(role='recommender'))
def all_awaiting_articles():
	myVars = request.vars
	for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
		myVars['qy_'+thema.keyword] = 'on'
	resu = _awaiting_articles(myVars)
	resu['myTitle'] = T('All articles awaiting consideration')
	return resu



@auth.requires(auth.has_membership(role='recommender'))
def accept_new_article_to_recommend():
	articleId = request.vars['articleId']
	article = db.t_articles[articleId]
	db.executesql("""INSERT INTO t_recommendations (article_id, recommender_id, doi) VALUES (%s, %s, %s);""", placeholders=[articleId, auth.user_id, article.doi])
	db.executesql("""UPDATE t_articles SET status=%s WHERE id=%s""", placeholders=['Under consideration', articleId])
	redirect('my_recommendations')



@auth.requires(auth.has_membership(role='recommender'))
def recommend_article():
	recommId = request.vars['recommendationId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		raise HTTP(403, "403: "+T('Access forbidden')) # Forbidden access
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
		raise HTTP(403, "403: "+T('Access forbidden')) # Forbidden access
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
		raise HTTP(403, "403: "+T('Access forbidden')) # Forbidden access
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
		db.executesql("""DELETE FROM t_suggested_recommenders WHERE article_id=%s AND suggested_recommender_id=%s""", placeholders=[articleId, auth.user_id])
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
		raise HTTP(403, "403: "+T('Access forbidden')) # Forbidden access
	try:
		db.executesql("""INSERT INTO t_reviews (recommendation_id, reviewer_id) VALUES (%s, %s);""",  placeholders=[recommId, reviewerId])
	except:
		pass # ignore duplicated keys, lazy way ;-S
	redirect('my_recommendations')



@auth.requires(auth.has_membership(role='recommender'))
def my_recommendations():
	query = db.t_recommendations.recommender_id == auth.user_id
	db.t_recommendations.recommender_id.writable = False
	db.t_recommendations.doi.writable = False
	#db.t_recommendations.is_closed.readable = False
	db.t_recommendations.is_closed.writable = False
	db.t_recommendations.article_id.writable = False
	db.t_recommendations.article_id.readable = False
	db.t_recommendations._id.readable = False
	db.t_recommendations.reply.writable = False
	grid = SQLFORM.grid( query
		,searchable=False,create=False,deletable=False
		,editable = lambda row: db.t_articles[row.article_id].status in ("Under consideration", "Pre-recommended", "Rejected") and not row.is_closed
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=[db.t_recommendations.article_id, db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.is_closed, db.t_recommendations.recommendation_comments, db.t_recommendations.reply]
		,links=[
			dict(header=T('Article'), body=lambda row: mkViewArticle4RecommendationButton(auth, db, row)),
			dict(header=T('Article status'), body=lambda row: mkRecommStatusButton(auth, db, row)),
			dict(header=T('Reviews'), body=lambda row: mkRecommReviewsButton(auth, db, row)),
			dict(header=T('Search reviewers'), body=lambda row: mkSearchReviewersButton(auth, db, row) if not row.is_closed else ''),
		]
		,links_placement = 'left'
		,orderby=~db.t_recommendations.recommendation_timestamp
	)
	myBackButton = A(SPAN(T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')
	if grid.update_form:
		grid.element(_type='submit')['_value'] = T("Save")
		grid.update_form.add_button(SPAN(T('Pre-recommended'), _class='buttontext btn btn-success'), 
							URL(c='recommender', f='recommend_article', vars=dict(recommendationId=request.args(2)), user_signature=True))
		grid.update_form.add_button(SPAN(T('Awaiting revision'), _class='buttontext btn btn-default'), 
							URL(c='recommender', f='revise_article', vars=dict(recommendationId=request.args(2)), user_signature=True))
		grid.update_form.add_button(SPAN(T('Rejected'), _class='buttontext btn btn-danger'), 
							URL(c='recommender', f='reject_article', vars=dict(recommendationId=request.args(2)), user_signature=True))
	response.view='default/recommLayout.html'
	return dict(grid=grid, myTitle=T('My recommendations'), myBackButton=myBackButton)





@auth.requires(auth.has_membership(role='recommender'))
def direct_submission():
	myTitle=T('Submit new article and initiate recommendation')
	db.t_articles.user_id.default = auth.user_id
	db.t_articles.user_id.writable = False
	db.t_articles.status.default = 'Under consideration'
	db.t_articles.status.writable = False
	form = SQLFORM(db.t_articles)
	if form.process().accepted:
		db.executesql("""INSERT INTO t_recommendations (article_id, recommender_id, doi) VALUES (%s, %s, %s);""", placeholders=[form.vars.id, auth.user_id, form.vars.doi])
		redirect('my_recommendations')
	response.view='user/my_articles.html'
	return dict(form=form, myTitle=myTitle, myBackButton=mkBackButton())



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
		raise HTTP(403, "403: "+T('Access forbidden')) # Forbidden access

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
			)




@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reviews():
	#write_auth = lambda row: auth.has_membership('administrator') or auth.has_membership('manager') or (auth.has_membership('recommender') and row.recommender_id == auth.user_id)
	write_auth = lambda row: auth.has_membership('recommender')
	query = (db.t_reviews.recommendation_id == request.vars['recommendationId'])
	db.t_reviews._id.readable = False
	db.t_reviews.recommendation_id.default = request.vars['recommendationId']
	db.t_reviews.recommendation_id.writable = False
	db.t_reviews.reviewer_id.writable = False
	db.t_reviews.anonymously.default = True
	db.t_reviews.anonymously.writable = False
	grid = SQLFORM.grid( query
		,details=True
		,editable=write_auth
		,deletable=write_auth
		,create=write_auth
		,searchable=False
		,maxtextlength = 250,paginate=100
		,csv = csv, exportclasses = expClass
		,fields=[db.t_reviews.recommendation_id, db.t_reviews.reviewer_id, db.t_reviews.anonymously, db.t_reviews.review]
	)
	response.view='recommender/reviews.html'
	return dict(grid=grid, myTitle=T('Reviews'))
	



