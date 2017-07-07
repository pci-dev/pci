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



#@auth.requires_login()
def new_submission():
	if auth.user:
		button = A(current.T("Start your request"), 
					_href=URL('user', 'fill_new_article', user_signature=True), 
					_class="btn btn-success pci-panelButton")
	else:
		button = SPAN(B('To start your request, please: '), 
						A(current.T('Log in'), _href=URL(c='default', f='user', args=['login', 'user', 'new_submission']), _class="btn btn-info"),
						LABEL(current.T(' or ')),
						A(current.T('Register'), _href=URL(c='default', f='user', args=['register', 'user', 'new_submission']), _class="btn btn-info"))
	myText = DIV(
			getText(request, auth, db, '#NewRecommendationRequestInfo'),
			DIV(
				button,
				_style='margin-top:16px; text-align:center;',
			)
		)
	response.view='default/info.html' #OK
	return dict(
		myText = myText,
	)



@auth.requires_login()
def fill_new_article():
	db.t_articles.article_source.writable = False
	db.t_articles.status.readable = False
	db.t_articles.upload_timestamp.readable = False
	db.t_articles.status.readable = False
	db.t_articles.status.writable = False
	db.t_articles.user_id.default = auth.user_id
	db.t_articles.user_id.writable = False
	db.t_articles.user_id.readable = False
	db.t_articles.last_status_change.readable = False
	db.t_articles.auto_nb_recommendations.readable = False
	db.t_articles.already_published.default = False
	db.t_articles.already_published.readable = False
	db.t_articles.already_published.writable = False
	myScript = """jQuery(document).ready(function(){
					
					if(jQuery('#t_articles_picture_rights_ok').prop('checked')) {
						jQuery('#t_articles_uploaded_picture').prop('disabled', false);
					} else {
						jQuery('#t_articles_uploaded_picture').prop('disabled', true);
					}
					
					if(jQuery('#t_articles_already_published').prop('checked')) {
						jQuery('#t_articles_article_source__row').show();
					} else {
						jQuery('#t_articles_article_source__row').hide();
						jQuery(':submit').prop('disabled', true);
					}
					
					if(jQuery('#t_articles_already_published').length) jQuery(':submit').prop('disabled', false);
					
					if(jQuery('#t_articles_is_not_reviewed_elsewhere').prop('checked') & jQuery('#t_articles_i_am_an_author').prop('checked')) {
						jQuery(':submit').prop('disabled', false);
					} else {
						jQuery(':submit').prop('disabled', true);
					}
					
					jQuery('#t_articles_picture_rights_ok').change(function(){
								if(jQuery('#t_articles_picture_rights_ok').prop('checked')) {
									jQuery('#t_articles_uploaded_picture').prop('disabled', false);
								} else {
									jQuery('#t_articles_uploaded_picture').prop('disabled', true);
									jQuery('#t_articles_uploaded_picture').val('');
								}
					});
					
					jQuery('#t_articles_already_published').change(function(){
								if(jQuery('#t_articles_already_published').prop('checked')) {
									jQuery('#t_articles_article_source__row').show();
								} else {
									jQuery('#t_articles_article_source__row').hide();
								}
					});
					
					jQuery('#t_articles_is_not_reviewed_elsewhere').change(function(){
								if(jQuery('#t_articles_is_not_reviewed_elsewhere').prop('checked') & jQuery('#t_articles_i_am_an_author').prop('checked')) {
									jQuery(':submit').prop('disabled', false);
								} else {
									jQuery(':submit').prop('disabled', true);
								}
					});
					jQuery('#t_articles_i_am_an_author').change(function(){
								if(jQuery('#t_articles_is_not_reviewed_elsewhere').prop('checked') & jQuery('#t_articles_i_am_an_author').prop('checked')) {
									jQuery(':submit').prop('disabled', false);
								} else {
									jQuery(':submit').prop('disabled', true);
								}
					});
				});
	"""
	form = SQLFORM( db.t_articles, keepvalues=True )
	form.element(_type='submit')['_value'] = T('Send your request')
	if form.process().accepted:
		articleId=form.vars.id
		session.flash = T('Article submitted', lazy=False)
		myVars = dict(articleId=articleId)
		#for thema in form.vars.thematics:
			#myVars['qy_'+thema] = 'on'
		#myVars['qyKeywords'] = form.vars.keywords
		redirect(URL(c='user', f='add_suggested_recommender', vars=myVars, user_signature=True))
	elif form.errors:
		response.flash = T('Form has errors', lazy=False)
	response.view='default/myLayout.html'
	return dict(
				myHelp = getHelp(request, auth, db, '#UserSubmitNewArticle'),
				myTitle=getTitle(request, auth, db, '#UserSubmitNewArticleTitle'),
				myText=getText(request, auth, db, '#UserSubmitNewArticleText'),
				form=form, 
				myFinalScript = SCRIPT(myScript),
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
	if not((art.user_id == auth.user_id or auth.has_membership(role='manager')) and art.status == 'Awaiting revision'):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		print 'article_revised'
		art.status = 'Under consideration'
		art.update_record()
		last_recomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
		last_recomm.is_closed = True
		last_recomm.update_record()
		newRecomm = db.t_recommendations.validate_and_insert(article_id=articleId, recommender_id=last_recomm.recommender_id, doi=art.doi, is_closed=False, recommendation_state='Ongoing', recommendation_title=last_recomm.recommendation_title)
		#print newRecomm
		redirect(URL(f='my_articles', user_signature=True))




@auth.requires_login()
def do_cancel_article():
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
		session.flash = T('Preprint submission cancelled')
		redirect(URL(f='my_articles', user_signature=True))



@auth.requires_login()
def do_delete_article():
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
		db(db.t_articles.id == articleId).delete()
		session.flash = T('Preprint submission deleted')
		redirect(URL(f='my_articles', user_signature=True))



@auth.requires_login()
def suggest_article_to():
	articleId = request.vars['articleId']
	recommenderId = request.vars['recommenderId']
	do_suggest_article_to(auth, db, articleId, recommenderId)
	redirect(URL(f='add_suggested_recommender', vars=dict(articleId=articleId), user_signature=True))



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
	response.view='default/myLayout.html'
	return dict(
				myBackButton = mkBackButton(),
				myTitle=getTitle(request, auth, db, '#SuggestedRecommendersTitle'),
				myText=getText(request, auth, db, '#SuggestedRecommendersText'),
				myHelp=getHelp(request, auth, db, '#SuggestedRecommenders'),
				grid=grid, 
			)
	


@auth.requires_login()
def del_suggested_recommender():
	suggId = request.vars['suggId']
	if suggId:
		if db( (db.t_suggested_recommenders.id==suggId) & (db.t_articles.id==db.t_suggested_recommenders.article_id) & (db.t_articles.user_id==auth.user_id) ).count() > 0:
			db( (db.t_suggested_recommenders.id==suggId) ).delete()
	redirect(request.env.http_referer)



@auth.requires_login()
def add_suggested_recommender():
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if (art.user_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		recommendersListSel = db( (db.t_suggested_recommenders.article_id==articleId) & (db.t_suggested_recommenders.suggested_recommender_id==db.auth_user.id) ).select()
		recommendersList = []
		reviewersIds = [auth.user_id]
		for con in recommendersListSel:
			reviewersIds.append(con.auth_user.id)
			if con.t_suggested_recommenders.declined:
				recommendersList.append(LI(mkUser(auth, db, con.auth_user.id), T('(declined)')))
			else:
				recommendersList.append(LI(mkUser(auth, db, con.auth_user.id),
									A('X', 
									   _href=URL(c='user', f='del_suggested_recommender', vars=dict(suggId=con.t_suggested_recommenders.id)), 
									   _title=T('Delete'), _style='margin-left:8px;'),
									))
		excludeList = ','.join(map(str,reviewersIds))
		if len(recommendersList)>0:
			myContents = DIV(
				LABEL(T('Suggested recommenders:')),
				UL(recommendersList)
			)
			txtbtn = current.T('Search another recommender?')
		else:
			myContents = ''
			txtbtn = current.T('Search a recommender?')

		myUpperBtn = DIV(
							A(SPAN(txtbtn, _class='buttontext btn btn-info'), 
								_href=URL(c='user', f='search_recommenders', vars=dict(articleId=articleId, exclude=excludeList), user_signature=True)),
							_style='margin-top:16px; text-align:center;'
						)
		myAcceptBtn = DIV(
							A(SPAN(T('Terminate your submission'), _class='buttontext btn btn-success'), 
								_href=URL(c='user', f='my_articles', user_signature=True)),
							_style='margin-top:16px; text-align:center;'
						)
		response.view='default/myLayout.html'
		return dict(
					myTitle=getTitle(request, auth, db, '#UserAddSuggestedRecommenderTitle'),
					myText=getText(request, auth, db, '#UserAddSuggestedRecommenderText'),
					myHelp = getHelp(request, auth, db, '#UserAddSuggestedRecommender'),
					myUpperBtn=myUpperBtn,
					content=myContents, 
					form='', 
					myAcceptBtn = myAcceptBtn,
					#myFinalScript=myScript,
				)



@auth.requires_login()
def recommenders():
	articleId = request.vars['articleId']
	article = db.t_articles[articleId]
	if (article.user_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		query = (db.t_suggested_recommenders.article_id == articleId)
		db.t_suggested_recommenders._id.readable = False
		db.t_suggested_recommenders.article_id.default = articleId
		db.t_suggested_recommenders.article_id.writable = False
		db.t_suggested_recommenders.article_id.readable = False
		db.t_suggested_recommenders.email_sent.writable = False
		db.t_suggested_recommenders.email_sent.readable = False
		db.t_suggested_recommenders.suggested_recommender_id.writable = True
		db.t_suggested_recommenders.suggested_recommender_id.represent = lambda rid,row: mkUser(auth, db, rid) if row else ''
		if len(request.args)>0 and request.args[0]=='new':
			myAcceptBtn = ''
		else:
			myAcceptBtn = DIV(
							A(SPAN(current.T('Done'), _class='buttontext btn btn-info'), 
										_href=URL(c='user', f='my_articles', user_signature=True)),
							_style='margin-top:16px; text-align:center;'
						)
		grid = SQLFORM.grid( query
			,details=False
			,editable=False
			,deletable=article.status in ('Pending', 'Awaiting consideration')
			,create=False
			,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_suggested_recommenders.article_id, db.t_suggested_recommenders.suggested_recommender_id]
		)
		response.view='default/myLayout.html'
		return dict(
					myTitle=getTitle(request, auth, db, '#UserManageRecommendersTitle'),
					myText=getText(request, auth, db, '#UserManageRecommendersText'),
					myHelp = getHelp(request, auth, db, '#UserManageRecommenders'),
					grid=grid, 
					myAcceptBtn = myAcceptBtn,
				)



@auth.requires_login()
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
		elif (myVar == 'articleId'):
			articleId = myValue
		elif (myVar == 'exclude'):
			excludeList = map(int, myValue.split(','))
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
		qyKwArr = qyKw.split(' ')
		searchForm =  mkSearchForm(auth, db, myVars)
		#RETURNS TABLE(id integer, num integer, score double precision, first_name character varying, last_name character varying, email character varying, uploaded_picture character varying, city character varying, country character varying, laboratory character varying, institution character varying, thematics character varying)
		filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s, %s);', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
		for fr in filtered:
			qy_recomm.insert(**fr)
				
		temp_db.qy_recomm._id.readable = False
		temp_db.qy_recomm.uploaded_picture.readable = False
		links = [
					#dict(header=T('Picture'), body=lambda row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100))),
					dict(header=T(''), body=lambda row: mkSuggestUserArticleToButton(auth, db, row, art.id)),
			]
		selectable = [(T('Suggest to checked recommenders'), lambda ids: [suggest_article_to_all(articleId, ids)], 'class1')]
		temp_db.qy_recomm.num.readable = False
		temp_db.qy_recomm.score.readable = False
		grid = SQLFORM.grid( qy_recomm
			,editable = False,deletable = False,create = False,details=False,searchable=False
			,selectable=selectable
			,maxtextlength=250,paginate=100
			,csv=csv,exportclasses=expClass
			,fields=[temp_db.qy_recomm.num, temp_db.qy_recomm.score, temp_db.qy_recomm.uploaded_picture, temp_db.qy_recomm.first_name, temp_db.qy_recomm.last_name, temp_db.qy_recomm.laboratory, temp_db.qy_recomm.institution, temp_db.qy_recomm.city, temp_db.qy_recomm.country, temp_db.qy_recomm.thematics]
			,links=links
			,orderby=temp_db.qy_recomm.num
			,args=request.args
		)
		myAcceptBtn = DIV(A(SPAN(current.T('I don\'t wish to suggest recommenders now'), _class='buttontext btn btn-info'), _href=URL(c='user', f='my_articles', user_signature=True), _class='button'), _style='text-align:center; margin-top:16px;')
		response.view='default/myLayout.html'
		return dict(
					myHelp = getHelp(request, auth, db, '#UserSearchRecommenders'),
					myText=getText(request, auth, db, '#UserSearchRecommendersText'),
					myTitle=getTitle(request, auth, db, '#UserSearchRecommendersTitle'),
					myAcceptBtn=myAcceptBtn,
					searchForm=searchForm, 
					grid=grid, 
				)




def suggest_article_to_all(articleId, recommenderIds):
	for recommenderId in recommenderIds:
		do_suggest_article_to(auth, db, articleId, recommenderId)
	redirect(URL(f='add_suggested_recommender', vars=dict(articleId=articleId), user_signature=True))
	


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
	if art.user_id != auth.user_id or art.status not in ('Pending', 'Awaiting consideration'):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		query = ( 
					  (db.t_suggested_recommenders.article_id == articleId)
					& (db.t_suggested_recommenders.suggested_recommender_id == db.auth_user.id)
				)
		db.t_suggested_recommenders._id.readable = False
		db.t_suggested_recommenders.suggested_recommender_id.represent = lambda userId, row: mkUser(auth, db, userId)
		grid = SQLFORM.grid( query
			,details=False,editable=False,deletable=True,searchable=False,create=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_suggested_recommenders.id, db.t_suggested_recommenders.suggested_recommender_id, db.auth_user.thematics]
			,field_id=db.t_suggested_recommenders.id
		)
		response.view='default/myLayout.html'
		return dict(
					#myBackButton=mkBackButton(),
					myHelp = getHelp(request, auth, db, '#UserSuggestedRecommenders'),
					myText=getText(request, auth, db, '#UserSuggestedRecommendersText'),
					myTitle=getTitle(request, auth, db, '#UserSuggestedRecommendersTitle'),
					grid=grid, 
				)



def mkSuggestedRecommendersUserButton(auth, db, row):
	butts = []
	suggRecomsTxt = []
	exclude = [str(auth.user_id)]
	suggRecomms = db(db.t_suggested_recommenders.article_id==row.id).select()
	for sr in suggRecomms:
		exclude.append(str(sr.suggested_recommender_id))
		if sr.declined:
			suggRecomsTxt.append(mkUser(auth, db, sr.suggested_recommender_id)+XML(':&nbsp;declined')+BR())
		else:
			suggRecomsTxt.append(mkUser(auth, db, sr.suggested_recommender_id)+BR())
	if len(suggRecomsTxt)>0:
		butts += suggRecomsTxt
	if row.status in ('Pending', 'Awaiting consideration'):
		if len(suggRecomsTxt)>0:
			butts.append( A(current.T('[MANAGE]'), _href=URL(c='user', f='recommenders', vars=dict(articleId=row.id))) )
		myVars = dict(articleId=row['id'])
		#if len(exclude)>0:
			#myVars['exclude'] = ','.join(exclude)
		#for thema in row['thematics']:
			#myVars['qy_'+thema] = 'on'
		#butts.append( BR() )
		butts.append( A(current.T('[+ADD]'), _href=URL(c='user', f='add_suggested_recommender', vars=myVars, user_signature=True)) )
	#else:
		#butts.append( SPAN((db.v_suggested_recommenders[row.id]).suggested_recommenders) )
	return butts




# Show my recommendation requests
@auth.requires_login()
def my_articles():
	query = db.t_articles.user_id == auth.user_id
	db.t_articles.user_id.default = auth.user_id
	db.t_articles.user_id.writable = False
	db.t_articles.auto_nb_recommendations.writable = False
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
			#dict(header=T('Recommender'), body=lambda row: SPAN((db.v_article_recommender[row.id]).recommender)), #getRecommender(auth, db, row)),
			dict(header=T('Recommender'), body=lambda row: getRecommender(auth, db, row)),
			dict(header='', body=lambda row: A(SPAN(current.T('View / Edit'), _class='buttontext btn btn-default pci-button'), 
												_target="_blank", 
												_href=URL(c='user', f='recommendations', vars=dict(articleId=row.id), user_signature=True), 
												_class='button', 
												_title=current.T('View and/or edit article')
											)
				),
		]
	if len(request.args) == 0: #in grid
		db.t_articles.abstract.readable = False
		db.t_articles.keywords.readable = False
		db.t_articles.thematics.readable = False
		db.t_articles.upload_timestamp.represent = lambda text, row: mkLastChange(text)
		db.t_articles.upload_timestamp.label = T('Request submitted')
		db.t_articles.last_status_change.represent = lambda text, row: mkLastChange(text)
		db.t_articles.auto_nb_recommendations.readable = True
	#elif (request.args[0]=='new') and (request.args[1]=='t_articles'): # in form
		#db.t_articles.article_source.writable = False
		#db.t_articles.status.readable = False
		#db.t_articles.upload_timestamp.readable = False
		#db.t_articles.last_status_change.readable = False
		#db.t_articles.auto_nb_recommendations.readable = False
	else:
		db.t_articles.doi.represent = lambda text, row: mkDOI(text)
		
	grid = SQLFORM.grid( query
		,searchable=False, details=False, editable=False, deletable=False, create=False
		,csv=csv, exportclasses=expClass
		,maxtextlength=250
		,paginate=20
		,fields=[db.t_articles.uploaded_picture, db.t_articles._id, db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.abstract, db.t_articles.doi, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations]
		,links=links
		,left=db.t_status_article.on(db.t_status_article.status==db.t_articles.status)
		#,orderby=db.t_status_article.priority_level|~db.t_articles.last_status_change
		,orderby=~db.t_articles.last_status_change
	)
	response.view='default/myLayout.html'
	return dict(
				#myBackButton=mkBackButton(), 
				myHelp = getHelp(request, auth, db, '#UserMyArticles'),
				myText=getText(request, auth, db, '#UserMyArticlesText'),
				myTitle=getTitle(request, auth, db, '#UserMyArticlesTitle'),
				grid=grid, 
			 ) 




# Recommendations of my articles
@auth.requires_login()
def recommendations():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value
	revCpt = 0
	if art.user_id == auth.user_id:
		revCpt += 1 # NOTE: checkings owner rights.
	# NOTE: checking reviewer rights
	revCpt += db( (db.t_recommendations.article_id==articleId) & (db.t_recommendations.id==db.t_reviews.recommendation_id) & (db.t_reviews.reviewer_id==auth.user_id) ).count()
	if revCpt == 0:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		myContents = mkFeaturedArticle(auth, db, art, printable, quiet=False)
		myContents.append(HR())
		
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
				_href=URL(c="user", f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
				_class='button')
			response.view='default/recommended_articles.html' #OK
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, db, '#UserRecommendations'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)




@auth.requires_login()
def my_reviews():
	pendingOnly = ('pendingOnly' in request.vars) and (request.vars['pendingOnly'] == "True")
	if pendingOnly:
		query = (
				  (db.t_reviews.reviewer_id == auth.user_id) 
				& (db.t_reviews.review_state == 'Pending') 
				& (db.t_reviews.recommendation_id == db.t_recommendations._id)  
				& (db.t_recommendations.article_id == db.t_articles._id)
				& (db.t_articles.status == 'Under consideration')
			)
		myTitle=getTitle(request, auth, db, '#UserMyReviewsRequestsTitle')
		myText=getText(request, auth, db, '#UserMyReviewsRequestsText')
		btnTxt = current.T('Accept or decline')
		db.t_reviews.anonymously.readable=False
	else:
		query = (
				  (db.t_reviews.reviewer_id == auth.user_id) 
				& (db.t_reviews.review_state != 'Pending') 
				& (db.t_reviews.recommendation_id == db.t_recommendations._id)  
				& (db.t_recommendations.article_id == db.t_articles._id)
			)
		myTitle=getTitle(request, auth, db, '#UserMyReviewsTitle')
		myText=getText(request, auth, db, '#UserMyReviewsText')
		btnTxt = current.T('View / Edit')
	
	db.t_articles._id.readable = False
	#db.t_articles._id.represent = lambda aId, row: mkRepresentArticleLight(auth, db, aId)
	#db.t_articles._id.label = T('Article')
	db.t_recommendations._id.represent = lambda rId, row: mkRepresentRecommendationLight(auth, db, rId)
	db.t_recommendations._id.label = T('Recommendation')
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	db.t_reviews.last_change.label = T('Days elapsed')
	db.t_reviews.last_change.represent = lambda text,row: mkElapsed(text)
	db.t_reviews.reviewer_id.writable = False
	#db.t_reviews.recommendation_id.writable = False
	#db.t_reviews.recommendation_id.label = T('Member in charge of the recommendation process')
	#db.t_reviews.recommendation_id.label = T('Recommender')
	#db.t_reviews.recommendation_id.represent = lambda text,row: mkRecommendation4ReviewFormat(auth, db, row.t_reviews)
	db.t_reviews._id.readable = False
	db.t_reviews.review.readable=False
	db.t_reviews.review_state.represent = lambda text,row: mkReviewStateDiv(auth, db, text)
	db.t_reviews.anonymously.represent = lambda anon,row: mkAnonymousMask(auth, db, anon)
	#db.t_reviews.review.represent=lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
	#db.t_reviews.review.label = T('Your review')
	#links = [dict(header='toto', body=lambda row: row.t_articles.id),]
	links = [
			dict(header=T(''), 
					body=lambda row: A(SPAN(btnTxt, _class='buttontext btn btn-default pci-button'), 
									_href=URL(c='user', f='recommendations', vars=dict(articleId=row.t_articles.id), user_signature=True), 
									_target="_blank", 
									_class='button', 
									_title=current.T('View and/or edit review')
									)
				),
		]
	grid = SQLFORM.grid( query
		,searchable=False, deletable=False, create=False, editable=False, details=False
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=[db.t_articles.uploaded_picture, db.t_recommendations._id, db.t_articles._id, db.t_articles.status, db.t_reviews.review_state, db.t_reviews.last_change, db.t_reviews.anonymously,  db.t_reviews.review]
		,links=links
		,orderby=~db.t_reviews.last_change|~db.t_reviews.review_state
	)
	response.view='default/myLayout.html'
	return dict(
				#myBackButton=mkBackButton(), 
				myHelp = getHelp(request, auth, db, '#UserMyReviews'),
				myTitle=myTitle,
				myText=myText,
				grid=grid, 
			 )


@auth.requires_login()
def accept_new_review():
	if not('reviewId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	reviewId = request.vars['reviewId']
	if reviewId is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	rev = db.t_reviews[reviewId]
	if rev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if rev['reviewer_id'] != auth.user_id:
		raise HTTP(403, "403: "+T('Forbidden'))
	ethics_not_signed = not(db.auth_user[auth.user_id].ethical_code_approved)
	if ethics_not_signed:
		myEthicalTitle = getText(request, auth, db, '#EthicsTitle'),
		myEthicalContents = getText(request, auth, db, '#EthicsInfo'),
		myEthical = DIV(
				DIV(myEthicalTitle, _class="pci-myTextInfo pci-myTitleText"),
				DIV(myEthicalContents, _class="pci-myTextInfo pci-embeddedEthicContents"),
				FORM(
					DIV(SPAN(INPUT(_type="checkbox", _name="ethics_approved", _id="ethics_approved", _value="yes", value=False), LABEL(T('Yes, I agree to comply with this code of ethical conduct'))), _style='padding:16px;'),
					DIV(SPAN(INPUT(_type="checkbox", _name="no_conflict_of_interest", _id="no_conflict_of_interest", _value="yes", value=False), LABEL(T('I declare that I have no conflict of interest with the authors or the content of the article'))), _style='padding:16px;'),
					INPUT(_type='submit', _value=T("Yes, I consider this preprint for review"), _class="btn btn-success pci-panelButton"), 
					hidden=dict(reviewId=reviewId),
					_action=URL('user', 'do_accept_new_review'),
					_style='text-align:center;',
				),
				_class="pci-embeddedEthic",
			)
		myScript = SCRIPT("""
			jQuery(document).ready(function(){
				
				if(jQuery('#ethics_approved').prop('checked') & jQuery('#no_conflict_of_interest').prop('checked')) {
					jQuery(':submit').prop('disabled', false);
				} else {
					jQuery(':submit').prop('disabled', true);
				}
				
				jQuery('#ethics_approved').change(function(){
					if(jQuery('#ethics_approved').prop('checked') & jQuery('#no_conflict_of_interest').prop('checked')) {
						jQuery(':submit').prop('disabled', false);
					} else {
						jQuery(':submit').prop('disabled', true);
					}
				});
				
				jQuery('#no_conflict_of_interest').change(function(){
					if(jQuery('#ethics_approved').prop('checked') & jQuery('#no_conflict_of_interest').prop('checked')) {
						jQuery(':submit').prop('disabled', false);
					} else {
						jQuery(':submit').prop('disabled', true);
					}
				});
			});
			""")
	else:
		myEthical = DIV(
				FORM(
					DIV(B(T('You agreed to comply with the code of ethical conduct'), _style='color:green;'), _style='text-align:center; margin:32px;'),
					DIV(SPAN(INPUT(_type="checkbox", _name="no_conflict_of_interest", _id="no_conflict_of_interest", _value="yes", value=False), LABEL(T('I declare that I have no conflict of interest with the authors or the content of the article'))), _style='padding:16px;'),
					INPUT(_type='submit', _value=T("Yes, I consider this preprint for review"), _class="btn btn-success pci-panelButton"), 
					hidden=dict(reviewId=reviewId, ethics_approved=True),
					_action=URL('user', 'do_accept_new_review'),
					_style='text-align:center;',
				),
				_class="pci-embeddedEthic",
			)
		myScript = SCRIPT("""
			jQuery(document).ready(function(){
				
				if(jQuery('#no_conflict_of_interest').prop('checked')) {
					jQuery(':submit').prop('disabled', false);
				} else {
					jQuery(':submit').prop('disabled', true);
				}
				
				jQuery('#no_conflict_of_interest').change(function(){
					if(jQuery('#no_conflict_of_interest').prop('checked')) {
						jQuery(':submit').prop('disabled', false);
					} else {
						jQuery(':submit').prop('disabled', true);
					}
				});
			});
			""")

	myTitle = getTitle(request, auth, db, '#AcceptReviewInfoTitle')
	myText = DIV(
			getText(request, auth, db, '#AcceptReviewInfoText'),
			myEthical,
		)
	response.view='default/info.html' #OK
	return dict(
		myText=myText,
		myTitle=myTitle,
		myFinalScript = myScript,
	)


@auth.requires_login()
def do_accept_new_review():
	if 'reviewId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	reviewId = request.vars['reviewId']
	theUser = db.auth_user[auth.user_id]
	if 'ethics_approved' in request.vars and theUser.ethical_code_approved is False:
		theUser.ethical_code_approved = True
		theUser.update_record()
	if not(theUser.ethical_code_approved):
		raise HTTP(403, "403: "+T('Forbidden'))
	if 'no_conflict_of_interest' not in request.vars:
		raise HTTP(403, "403: "+T('Forbidden'))
	noConflict = request.vars['no_conflict_of_interest']
	if noConflict != "yes":
		raise HTTP(403, "403: "+T('Forbidden'))
	rev = db.t_reviews[reviewId]
	if rev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if rev.reviewer_id != auth.user_id:
		raise HTTP(403, "403: "+T('Forbidden'))
	rev.review_state = 'Under consideration'
	rev.no_conflict_of_interest = True
	rev.update_record()
	# email to recommender sent at database level
	recomm = db.t_recommendations[rev.recommendation_id]
	redirect(URL(c='user', f='recommendations', vars=dict(articleId=recomm.article_id), user_signature=True))
	#redirect(URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), user_signature=True))





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
	redirect(URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), user_signature=True))



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
	if not ((art.user_id == auth.user_id or auth.has_membership(role='manager')) and (art.status == 'Awaiting revision')):
		session.flash = T('Unauthorized', lazy=False)
		redirect('my_articles')
	db.t_recommendations.reply_pdf.label=T('OR Upload your reply as PDF file')
	form = SQLFORM(db.t_recommendations
				,record=recommId
				,fields=['id', 'reply', 'reply_pdf']
				,upload=URL('download')
				,showid=False
			)
	if form.process().accepted:
		response.flash = T('Reply saved', lazy=False)
		redirect(URL(f='recommendations', vars=dict(articleId=art.id), user_signature=True))
	elif form.errors:
		response.flash = T('Form has errors', lazy=False)
	response.view='default/myLayout.html'
	return dict(
				myHelp = getHelp(request, auth, db, '#UserEditReply'),
				myBackButton = mkBackButton(),
				myText=getText(request, auth, db, '#UserEditReplyText'),
				myTitle=getTitle(request, auth, db, '#UserEditReplyTitle'),
				form = form,
			)



@auth.requires_login()
def edit_review():
	if 'reviewId' not in request.vars:
		raise HTTP(404, "404: "+T('ID Unavailable'))
	reviewId = request.vars['reviewId']
	review = db.t_reviews[reviewId]
	if review is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	recomm = db.t_recommendations[review.recommendation_id]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	art = db.t_articles[recomm.article_id]
	if review.reviewer_id != auth.user_id or review.review_state != 'Under consideration' or art.status != 'Under consideration':
		session.flash = T('Unauthorized', lazy=False)
		redirect(URL(c='user', f='recommendations', vars=dict(articleId=art.id), user_signature=True))
	else:
		buttons = [
					INPUT(_type='Submit', _name='save',      _class='btn btn-info', _value='Save'),
					INPUT(_type='Submit', _name='terminate', _class='btn btn-success', _value='Save & terminate'),
				]
		db.t_reviews.no_conflict_of_interest.writable = not(review.no_conflict_of_interest)
		db.t_reviews.anonymously.label = T('I wish to remain anonymous')
		db.t_reviews.review_pdf.label = T('OR Upload review as PDF')
		form = SQLFORM(db.t_reviews
					,record=review
					,fields=['anonymously', 'review', 'review_pdf', 'no_conflict_of_interest']
					,showid=False
					,buttons=buttons
					,upload=URL('download')
				)
		if form.process().accepted:
			if form.vars.save:
				session.flash = T('Review saved', lazy=False)
				redirect(URL(c='user', f='recommendations', vars=dict(articleId=art.id), user_signature=True))
			elif form.vars.terminate:
				redirect(URL(c='user', f='review_completed', vars=dict(reviewId=review.id), user_signature=True))
		elif form.errors:
			response.flash = T('Form has errors', lazy=False)
	myScript = """jQuery(document).ready(function(){
					if(jQuery('#t_reviews_no_conflict_of_interest').prop('checked')) {
						jQuery(':submit').prop('disabled', false);
					} else {
						jQuery(':submit').prop('disabled', true);
					}
					jQuery('#t_reviews_no_conflict_of_interest').change(function(){
								if(jQuery('#t_reviews_no_conflict_of_interest').prop('checked')) {
									jQuery(':submit').prop('disabled', false);
								} else {
									jQuery(':submit').prop('disabled', true);
								}
					});
				});
	"""
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, db, '#UserEditReview'),
				#myBackButton=mkBackButton(),
				myText=getText(request, auth, db, '#UserEditReviewText'),
				myTitle=getTitle(request, auth, db, '#UserEditReviewTitle'),
				form=form,
				myFinalScript=SCRIPT(myScript),
			)



@auth.requires_login()
def edit_my_article():
	if not('articleId' in request.vars):
		session.flash = T('Unavailable')
		redirect(URL('my_articles', user_signature=True))
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
				,articleId
				,fields=['title', 'authors', 'doi', 'abstract', 'thematics', 'keywords']
				,upload=URL('default', 'download')
				,deletable=deletable
				,showid=False
			)
	if form.process().accepted:
		response.flash = T('Article saved', lazy=False)
		redirect(URL(f='recommendations', vars=dict(articleId=art.id), user_signature=True))
	elif form.errors:
		response.flash = T('Form has errors', lazy=False)
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, db, '#UserEditArticle'),
				myText=getText(request, auth, db, '#UserEditArticleText'),
				myTitle=getTitle(request, auth, db, '#UserEditArticleTitle'),
				form=form,
			)




@auth.requires_login()
def new_comment():
	if not('articleId' in request.vars):
		session.flash = T('Unavailable')
		redirect(URL('my_articles', user_signature=True))
	articleId = request.vars['articleId']
	if 'parentId' in request.vars:
		parentId = request.vars['parentId']
		fields = ['article_id', 'parent_id', 'user_comment']
	else:
		parentId = None
		fields = ['article_id', 'user_comment']
	db.t_comments.user_id.default = auth.user_id
	db.t_comments.user_id.readable = False
	db.t_comments.user_id.writable = False
	db.t_comments.article_id.default = articleId
	db.t_comments.article_id.writable = False
	db.t_comments.parent_id.default = parentId
	db.t_comments.parent_id.writable = False
	form = SQLFORM(db.t_comments
				,fields=fields
				,showid=False
			)
	if form.process().accepted:
		response.flash = T('Article saved', lazy=False)
		redirect(URL(c='public', f='rec', vars=dict(id=articleId, comments=True), user_signature=True))
	elif form.errors:
		response.flash = T('Form has errors', lazy=False)
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, db, '#UserComment'),
				myText=getText(request, auth, db, '#UserCommentText'),
				myTitle=getTitle(request, auth, db, '#UserCommentTitle'),
				form=form,
			)
	