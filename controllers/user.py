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
	myText = DIV(
			getText(request, auth, dbHelp, '#NewRecommendationRequestInfo'),
			DIV(
				A(current.T("Start your request"), 
					_href=URL('user', 'fill_new_article', user_signature=True), 
					_class="btn btn-success pci-panelButton"),
				_style='margin-top:16px; text-align:center;',
			)
		)
	response.view='default/info.html' #OK
	return dict(
		#panel = DIV(UL( panel, _class="list-group"), _class="panel panel-info"),
		myText = myText,
		myBackButton = mkBackButton(),
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
	myTitle=T('Your preprint for which you request a recommendation')
	myScript = """jQuery(document).ready(function(){
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
					jQuery('#t_articles_already_published').change(function(){
								if(jQuery('#t_articles_already_published').prop('checked')) {
									jQuery('#t_articles_article_source__row').show();
								} else {
									jQuery('#t_articles_article_source__row').hide();
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
	form.element(_type='submit')['_value'] = T("Send for request")
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
				form=form, 
				myTitle=myTitle, 
				myBackButton=mkBackButton(), 
				myHelp = getHelp(request, auth, dbHelp, '#UserSubmitNewArticle'),
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
	if art.user_id != auth.user_id or art.status != 'Awaiting revision':
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
		redirect(URL(f='my_articles', user_signature=True))



@auth.requires_login()
def suggest_article_to():
	articleId = request.vars['articleId']
	recommenderId = request.vars['recommenderId']
	db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)
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
	#response.view='default/recommLayout.html'
	response.view='default/myLayout.html'
	return dict(
				myTitle=T('Suggested recommenders'),
				myBackButton = mkBackButton(),
				myHelp=getHelp(request, auth, dbHelp, '#SuggestedRecommenders'),
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
		#db.t_suggested_recommenders._id.readable = False
		#db.t_suggested_recommenders.article_id.default = articleId
		#db.t_suggested_recommenders.article_id.writable = False
		#db.t_suggested_recommenders.article_id.readable = False
		#db.t_suggested_recommenders.email_sent.writable = False
		#db.t_suggested_recommenders.email_sent.readable = False
		#db.t_suggested_recommenders.suggested_recommender_id.writable = True
		#db.t_suggested_recommenders.suggested_recommender_id.represent = lambda text,row: mkUser(auth, db, row.suggested_recommender_id) if row else ''
		#alreadySugg = db(db.t_suggested_recommenders.article_id==articleId)._select(db.t_suggested_recommenders.suggested_recommender_id)
		#otherSuggQy = db((db.auth_user._id!=auth.user_id) & (db.auth_user._id==db.auth_membership.user_id) & (db.auth_membership.group_id==db.auth_group._id) & (db.auth_group.role=='recommender') & (~db.auth_user.id.belongs(alreadySugg)) )
		#db.t_suggested_recommenders.suggested_recommender_id.requires = IS_IN_DB(otherSuggQy, db.auth_user.id, '%(last_name)s, %(first_name)s')
		#form = SQLFORM(db.t_suggested_recommenders)
		#if form.process().accepted:
			#redirect(URL(c='user', f='add_suggested_recommender', vars=dict(articleId=articleId), user_signature=True))
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
					myHelp = getHelp(request, auth, dbHelp, '#UserAddSuggestedRecommender'),
					myTitle=T('Suggest recommenders?'), 
					myUpperBtn=myUpperBtn,
					#myBackButton=mkBackButton(T('Close'), URL(c='user', f='my_articles', user_signature=True)),
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
		db.t_suggested_recommenders.suggested_recommender_id.represent = lambda text,row: mkUser(auth, db, row.suggested_recommender_id) if row else ''
		if len(request.args)>0 and request.args[0]=='new':
			myAcceptBtn = ''
		else:
			myAcceptBtn = DIV(
							A(SPAN(current.T('Terminated'), _class='buttontext btn btn-info'), 
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
		## This script renames the "Add record" button
		#myScript = SCRIPT("""$(function() { 
						#$('span').filter(function(i) {
								#return $(this).attr("title") ? $(this).attr("title").indexOf('"""+T("Add record to database")+"""') != -1 : false;
							#})
							#.each(function(i) {
								#$(this).text('"""+T("Add a recommender")+"""').attr("title", '"""+T("Suggest this article to a potential recommender")+"""');
							#});
						#})""",
						#_type='text/javascript')
		response.view='default/myLayout.html'
		return dict(
					myHelp = getHelp(request, auth, dbHelp, '#UserManageRecommenders'),
					myTitle=T('Manage recommenders for your article'), 
					myBackButton=mkBackButton(),
					grid=grid, 
					myAcceptBtn = myAcceptBtn,
					#myFinalScript=myScript,
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
		elif (re.match('^qy_', myVar)):
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
		#TODO: ugly
		grid = SQLFORM.grid( qy_recomm
			,editable = False,deletable = False,create = False,details=False,searchable=False
			,maxtextlength=250,paginate=100
			,csv=csv,exportclasses=expClass
			,fields=[temp_db.qy_recomm.num, temp_db.qy_recomm.score, temp_db.qy_recomm.uploaded_picture, temp_db.qy_recomm.first_name, temp_db.qy_recomm.last_name, temp_db.qy_recomm.laboratory, temp_db.qy_recomm.institution, temp_db.qy_recomm.city, temp_db.qy_recomm.country, temp_db.qy_recomm.thematics]
			,links=links
			,orderby=temp_db.qy_recomm.num
			,args=request.args
		)
		myBackButton = A(SPAN(current.T('I don\'t wish to suggest recommenders now'), _class='buttontext btn btn-info'), _href=URL(c='user', f='my_articles', user_signature=True), _class='button')
		response.view='default/myLayout.html'
		return dict(
					myHelp = getHelp(request, auth, dbHelp, '#UserSearchRecommenders'),
					myTitle=T('Suggest recommenders for your submitted article'), 
					#myBackButton=mkBackButton(),
					myBackButton=myBackButton,
					searchForm=searchForm, 
					grid=grid, 
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
					myTitle=T('Suggested recommenders'), 
					myBackButton=mkBackButton(),
					myHelp = getHelp(request, auth, dbHelp, '#UserSuggestedRecommenders'),
					grid=grid, 
				)



def mkSuggestedRecommendersUserButton(auth, db, row):
	butts = []
	suggRecomsTxt = []
	exclude = [str(auth.user_id)]
	suggRecomms = db(db.t_suggested_recommenders.article_id==row.id).select()
	for sr in suggRecomms:
		exclude.append(str(sr.suggested_recommender_id))
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
			dict(header=T('Current recommender'), body=lambda row: SPAN((db.v_article_recommender[row.id]).recommender)), #getRecommender(auth, db, row)),
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
		,fields=[db.t_articles._id, db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.abstract, db.t_articles.doi, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations]
		,links=links
		,left=db.t_status_article.on(db.t_status_article.status==db.t_articles.status)
		#,orderby=db.t_status_article.priority_level|~db.t_articles.last_status_change
		,orderby=~db.t_articles.last_status_change
	)
	myTitle=T('Your submitted articles')
	response.view='default/myLayout.html'
	return dict(
				grid=grid, 
				myTitle=myTitle, 
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
					DIV(I(myconf.take('app.longname')+' '+T('status:')), mkStatusBigDiv(auth, db, art.status), _class='pci-ArticleText'),
						_class='pci-ArticleHeaderIn'
					))
			myUpperBtn = A(SPAN(T('Printable page'), _class='buttontext btn btn-info'), 
				_href=URL(c="user", f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
				_class='button')
			response.view='default/recommended_articles.html' #OK
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, dbHelp, '#UserRecommendations'),
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
			)
		myTitle = T('Requests for reviews')
		db.t_reviews.anonymously.readable=False
	else:
		query = (
				  (db.t_reviews.reviewer_id == auth.user_id) 
				& (db.t_reviews.review_state != 'Pending') 
				& (db.t_reviews.recommendation_id == db.t_recommendations._id)  
				& (db.t_recommendations.article_id == db.t_articles._id)
			)
		myTitle = T('Your reviews')
	
	db.t_articles._id.represent = lambda aId, row: mkRepresentArticleLight(auth, db, aId)
	db.t_articles._id.label = T('Article')
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	db.t_reviews.last_change.label = T('Elapsed days')
	db.t_reviews.last_change.represent = lambda text,row: mkElapsed(text)
	db.t_reviews.reviewer_id.writable = False
	db.t_reviews.recommendation_id.writable = False
	#db.t_reviews.recommendation_id.label = T('Member in charge of the recommendation process')
	db.t_reviews.recommendation_id.label = T('Recommender')
	db.t_reviews.recommendation_id.represent = lambda text,row: mkRecommendation4ReviewFormat(auth, db, row.t_reviews)
	db.t_reviews._id.readable = False
	db.t_reviews.review.readable=False
	db.t_reviews.review_state.represent = lambda text,row: mkReviewStateDiv(auth, db, text)
	db.t_reviews.anonymously.represent = lambda anon,row: mkAnonymousMask(auth, db, anon)
	#db.t_reviews.review.represent=lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
	#db.t_reviews.review.label = T('Your review')
	#links = [dict(header='toto', body=lambda row: row.t_articles.id),]
	links = [
			dict(header=T(''), 
					body=lambda row: A(SPAN(current.T('View / Edit'), _class='buttontext btn btn-default pci-button'), 
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
		,fields=[db.t_articles._id, db.t_articles.status, db.t_reviews.review_state, db.t_reviews.last_change, db.t_reviews.anonymously, db.t_reviews.recommendation_id, db.t_reviews.review]
		,links=links
		,orderby=~db.t_reviews.last_change|~db.t_reviews.review_state
	)
	response.view='default/myLayout.html'
	return dict(
				myHelp = getHelp(request, auth, dbHelp, '#UserMyReviews'),
				myTitle=myTitle,
				myBackButton=mkBackButton(), 
				grid=grid, 
			 )



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
		myTitle = T('Edit your reply to recommender'),
		myHelp = getHelp(request, auth, dbHelp, '#UserEditReply'),
		myBackButton = mkBackButton(),
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
		form = SQLFORM(db.t_reviews
					,record=review
					,fields=['anonymously', 'review', 'no_conflict_of_interest']
					,showid=False
				)
		if form.process().accepted:
			response.flash = T('Review saved', lazy=False)
			redirect(URL(c='user', f='recommendations', vars=dict(articleId=art.id), user_signature=True))
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
		myHelp = getHelp(request, auth, dbHelp, '#UserEditReview'),
		myBackButton = mkBackButton(),
		myTitle = T('Edit review'),
		form = form,
		myFinalScript = SCRIPT(myScript),
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


