# -*- coding: utf-8 -*-

import re
import copy
import datetime

from gluon.contrib.markdown import WIKI
from app_modules.common import *
from app_modules.helper import *

from app_modules import user_module
from app_modules import common_tools
from app_modules import common_forms

# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get('config.trgm_limit', default=0.4)
parallelSubmissionAllowed = myconf.get('config.parallel_submission', default=False)

######################################################################################################################################################################
def new_submission():
	response.view='default/info.html'
	if auth.user:
		button = A(current.T("Submit your preprint"), 
					_href=URL('user', 'fill_new_article', user_signature=True), 
					_class="btn btn-success pci-panelButton")
	else:
		button = SPAN(B(current.T('Before submitting your preprint, please:'), _style='margin-right:8px;'), 
						A(current.T('Log in'), _href=URL(c='default', f='user', args=['login'], vars=dict(_next=URL(c='user', f='new_submission'))), _class="btn btn-info"),
						LABEL(current.T(' or ')),
						A(current.T('Register'), _href=URL(c='default', f='user', args=['register'], vars=dict(_next=URL(c='user', f='new_submission'))), _class="btn btn-info"))
	myText = DIV(
			getText(request, auth, db, '#NewRecommendationRequestInfo'),
			DIV(
				button,
				_style='margin-top:16px; text-align:center;',
			)
		)
	return dict(
		myText = myText,
		myTitle=getTitle(request, auth, db, '#UserBeforeSubmissionTitle')
	)


######################################################################################################################################################################
def viewUserCard():
	response.view='default/info.html'

	myContents = ''
	if not('userId' in request.vars):
		session.flash = T('Unavailable')
		redirect(request.env.http_referer)
	else:
		userId = request.vars['userId']
		if userId:
			hasRoles = (db( (db.auth_membership.user_id==userId) ).count() > 0) or auth.has_membership(role='administrator') or auth.has_membership(role='developper')
			if not(hasRoles):
				#session.flash = T('Unavailable')
				#redirect(request.env.http_referer)
				myContents = B(T('Unavailable'))
			else:
				myContents = mkUserCard(auth, db, response, userId, withMail=False)
		else:
			#session.flash = T('Unavailable')
			#redirect(request.env.http_referer)
			myContents = B(T('Unavailable'))
	resu = dict(
				myHelp=getHelp(request, auth, db, '#PublicUserCard'),
				myTitle=getTitle(request, auth, db, '#PublicUserCardTitle'),
				myText = myContents
			)
	return resu

######################################################################################################################################################################
@auth.requires_login()
def fill_new_article():
	response.view='default/myLayout.html'
	db.t_articles.article_source.writable = False
	db.t_articles.ms_version.writable = True
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
	db.t_articles.cover_letter.readable = True
	db.t_articles.cover_letter.writable = True
	db.t_articles.parallel_submission.label = T('This preprint is (or will be) also submitted to a journal')
	myScript = common_tools.get_template('script','fill_new_article.js')

	form = SQLFORM( db.t_articles, keepvalues=True )
	form.element(_type='submit')['_value'] = T('Complete your submission')
	form.element(_type='submit')['_class'] = 'btn btn-success'
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
	return dict(
				myHelp = getHelp(request, auth, db, '#UserSubmitNewArticle'),
				myTitle=getTitle(request, auth, db, '#UserSubmitNewArticleTitle'),
				myText=getText(request, auth, db, '#UserSubmitNewArticleText'),
				form=form, 
				myFinalScript = SCRIPT(myScript),
			 ) 



######################################################################################################################################################################
@auth.requires_login()
def edit_my_article():
	response.view='default/myLayout.html'
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
	#deletable = (art.status == 'Pending')
	deletable = False
	db.t_articles.status.readable=False
	db.t_articles.status.writable=False
	if parallelSubmissionAllowed and art.status == 'Pending':
		db.t_articles.parallel_submission.label = T('This preprint is (or will be) also submitted to a journal')
		fields = ['title', 'anonymous_submission', 'is_not_reviewed_elsewhere', 'parallel_submission', 'authors', 'doi', 'ms_version', 'picture_rights_ok', 'uploaded_picture', 'abstract', 'thematics', 'keywords']
		myScript = common_tools.get_template('script','edit_my_article.js')

	else:
		fields = ['title', 'anonymous_submission', 'authors', 'doi', 'ms_version', 'picture_rights_ok', 'uploaded_picture', 'abstract', 'thematics', 'keywords']
		myScript = ''

	form = SQLFORM(db.t_articles
				,articleId
				,fields=fields
				,upload=URL('default', 'download')
				,deletable=deletable
				,showid=False
			)

	form.element(_type='submit')['_value'] = T("Save")

	if form.process().accepted:
		response.flash = T('Article saved', lazy=False)
		redirect(URL(c='user', f='recommendations', vars=dict(articleId=art.id), user_signature=True))
	elif form.errors:
		response.flash = T('Form has errors', lazy=False)
	return dict(
				myHelp=getHelp(request, auth, db, '#UserEditArticle'),
				myText=getText(request, auth, db, '#UserEditArticleText'),
				myTitle=getTitle(request, auth, db, '#UserEditArticleTitle'),
				form=form,
				myFinalScript = SCRIPT(myScript),
			)



######################################################################################################################################################################
# Display suggested recommenders for a submitted article
# Logged users only (submission)
@auth.requires_login()
def suggested_recommenders():
	response.view='default/myLayout.html'
	write_auth = auth.has_membership('administrator') or auth.has_membership('developper')
	query = (db.t_suggested_recommenders.article_id == request.vars['articleId'])
	db.t_suggested_recommenders._id.readable = False
	grid = SQLFORM.grid( query
		,details=False,editable=False,deletable=write_auth,create=False,searchable=False
		,maxtextlength = 250,paginate=100
		,csv = csv, exportclasses = expClass
		,fields=[db.t_suggested_recommenders.suggested_recommender_id]
	)
	return dict(
				myBackButton = mkBackButton(),
				myTitle=getTitle(request, auth, db, '#SuggestedRecommendersTitle'),
				myText=getText(request, auth, db, '#SuggestedRecommendersText'),
				myHelp=getHelp(request, auth, db, '#SuggestedRecommenders'),
				grid=grid, 
			)
	



######################################################################################################################################################################
@auth.requires_login()
def add_suggested_recommender():
	response.view='default/myLayout.html'

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
				recommendersList.append(LI(mkUser(auth, db, con.auth_user.id), I(T('(declined)'))))
			else:
				recommendersList.append(
									LI(mkUser(auth, db, con.auth_user.id),
									A('Remove', _class='btn btn-warning', _href=URL(c='user_actions', f='del_suggested_recommender', vars=dict(suggId=con.t_suggested_recommenders.id)), _title=T('Delete'), _style='margin-left:8px;') if (art.status=='Pending') else '',
									))
		#excludeList = ','.join(map(str,reviewersIds))
		excludeList = reviewersIds
		if len(recommendersList)>0:
			myContents = DIV(
				LABEL(T('Suggested recommenders:')),
				UL(recommendersList, _class='pci-li-spacy')
			)
			txtbtn = current.T('Suggest another recommender?')
		else:
			myContents = ''
			txtbtn = current.T('Suggest recommenders')

		myUpperBtn = DIV(
							A(SPAN(txtbtn, _class='buttontext btn btn-info'), 
								_href=URL(c='user', f='search_recommenders', vars=dict(articleId=articleId, exclude=excludeList), user_signature=True)),
							_style='margin-top:16px; text-align:center;'
						)
		myAcceptBtn = DIV(
							A(SPAN(T('Complete your submission'), _class='buttontext btn btn-success'), 
								_href=URL(c='user', f='my_articles', user_signature=True)),
							_style='margin-top:16px; text-align:center;'
						)
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



######################################################################################################################################################################
@auth.requires_login()
def recommenders():
	response.view='default/myLayout.html'
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
			,deletable=article.status in ('Pending')
			,create=False
			,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_suggested_recommenders.article_id, db.t_suggested_recommenders.suggested_recommender_id]
		)

		return dict(
					myTitle=getTitle(request, auth, db, '#UserManageRecommendersTitle'),
					myText=getText(request, auth, db, '#UserManageRecommendersText'),
					myHelp = getHelp(request, auth, db, '#UserManageRecommenders'),
					grid=grid, 
					myAcceptBtn = myAcceptBtn,
				)



######################################################################################################################################################################
@auth.requires_login()
def search_recommenders(): 
	response.view='default/myLayout.html'
	myVars = request.vars

	qyKw = ''
	qyTF = []
	excludeList = []
	articleId = None
	for myVar in myVars:
		if (myVar == 'exclude'):
			#excludeList = map(int, myValue.split(','))
			for v in myVars[myVar]:
				excludeList.append(int(v))
		elif isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (re.match('^qy_', myVar) and myValue=='on'):
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
				Field('city', type='string', label=T('City'), represent=lambda t,r: t if t else ''),
				Field('country', type='string', label=T('Country'), represent=lambda t,r: t if t else ''),
				Field('laboratory', type='string', label=T('Laboratory'), represent=lambda t,r: t if t else ''),
				Field('institution', type='string', label=T('Institution'), represent=lambda t,r: t if t else ''),
				Field('thematics', type='list:string', label=T('Thematic fields')),
				Field('excluded', type='boolean', label=T('Excluded')),
			)
		qyKwArr = qyKw.split(' ')
		searchForm = common_forms.getSearchForm(auth, db, myVars)
		if searchForm.process(keepvalues=True).accepted:
			response.flash = None
		else:
			qyTF = []
			for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
				qyTF.append(thema.keyword)

		filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s, %s);', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
		for fr in filtered:
			qy_recomm.insert(**fr)
				
		temp_db.qy_recomm._id.readable = False
		temp_db.qy_recomm.uploaded_picture.readable = False
		links = [dict(header=T(''), body=lambda row: "" if row.excluded else mkSuggestUserArticleToButton(auth, db, row, art.id, excludeList, myVars)),]
		selectable = None
		temp_db.qy_recomm.num.readable = False
		temp_db.qy_recomm.score.readable = False
		temp_db.qy_recomm.excluded.readable = False
		grid = SQLFORM.grid( qy_recomm
			,editable = False,deletable = False,create = False,details=False,searchable=False
			,selectable=selectable
			,maxtextlength=250,paginate=1000
			,csv=csv,exportclasses=expClass
			,fields=[temp_db.qy_recomm.num, temp_db.qy_recomm.score, temp_db.qy_recomm.uploaded_picture, temp_db.qy_recomm.first_name, temp_db.qy_recomm.last_name, temp_db.qy_recomm.laboratory, temp_db.qy_recomm.institution, temp_db.qy_recomm.city, temp_db.qy_recomm.country, temp_db.qy_recomm.thematics, temp_db.qy_recomm.excluded]
			,links=links
			,orderby=temp_db.qy_recomm.num
			,args=request.args
		)
		if len(excludeList) > 1:
			btnTxt = current.T('Done')
		else:
			btnTxt = current.T('I don\'t wish to suggest recommenders now')
		myAcceptBtn = DIV(A(SPAN(btnTxt, _class='buttontext btn btn-info'), _href=URL(c='user', f='add_suggested_recommender', vars=dict(articleId=articleId, exclude=excludeList)), _class='button'), _style='text-align:center; margin-top:16px;')
		return dict(
					myHelp = getHelp(request, auth, db, '#UserSearchRecommenders'),
					myText=getText(request, auth, db, '#UserSearchRecommendersText'),
					myTitle=getTitle(request, auth, db, '#UserSearchRecommendersTitle'),
					myUpperBtn=myAcceptBtn,
					myAcceptBtn=myAcceptBtn,
					searchForm=searchForm, 
					grid=grid, 
				)




######################################################################################################################################################################
# Display suggested recommenders for a submitted article
# Logged users only (submission)
@auth.requires_login()
def suggested_recommenders():
	response.view='default/myLayout.html'
	articleId = request.vars['articleId']

	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.user_id != auth.user_id or art.status not in ('Pending'):
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
		return dict(
					#myBackButton=mkBackButton(),
					myHelp = getHelp(request, auth, db, '#UserSuggestedRecommenders'),
					myText=getText(request, auth, db, '#UserSuggestedRecommendersText'),
					myTitle=getTitle(request, auth, db, '#UserSuggestedRecommendersTitle'),
					grid=grid, 
				)





######################################################################################################################################################################
# Show my submissions
@auth.requires_login()
def my_articles():
	response.view='default/myLayout.html'

	query = db.t_articles.user_id == auth.user_id
	db.t_articles.user_id.default = auth.user_id
	db.t_articles.user_id.writable = False
	db.t_articles.auto_nb_recommendations.writable = False
	db.t_articles.status.represent = lambda text, row: mkStatusDivUser(auth, db, text)
	db.t_articles.status.writable = False
	db.t_articles._id.represent = lambda text, row: mkArticleCellNoRecomm(auth, db, row)
	db.t_articles._id.label = T('Article')
	db.t_articles.doi.readable = False
	db.t_articles.title.readable = False
	db.t_articles.authors.readable = False
	db.t_articles.article_source.readable = False
	db.t_articles.anonymous_submission.label = T('Anonymous submission')
	db.t_articles.anonymous_submission.represent = lambda anon,r: mkAnonymousMask(auth, db, anon)
	links = [
			dict(header=T('Suggested recommenders'), body=lambda row: user_module.mkSuggestedRecommendersUserButton(auth, db, row)),
			dict(header=T('Recommender(s)'), body=lambda row: getRecommender(auth, db, row)),
			dict(header='', body=lambda row: A(SPAN(current.T('View / Edit'), _class='buttontext btn btn-default pci-button pci-submitter'), 
												_target="_blank", 
												_href=URL(c='user', f='recommendations', vars=dict(articleId=row["t_articles.id"]), user_signature=True), 
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
		db.t_articles.upload_timestamp.label = T('Submitted')
		db.t_articles.last_status_change.represent = lambda text, row: mkLastChange(text)
		db.t_articles.auto_nb_recommendations.readable = True
	else:
		db.t_articles.doi.represent = lambda text, row: mkDOI(text)
		
	if parallelSubmissionAllowed:
		fields = [db.t_articles.uploaded_picture, db.t_articles._id, db.t_articles.title, db.t_articles.anonymous_submission, db.t_articles.parallel_submission, db.t_articles.authors, db.t_articles.article_source, db.t_articles.abstract, db.t_articles.doi, db.t_articles.ms_version, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations]
	else:
		fields = [db.t_articles.uploaded_picture, db.t_articles._id, db.t_articles.title, db.t_articles.anonymous_submission, db.t_articles.authors, db.t_articles.article_source, db.t_articles.abstract, db.t_articles.doi, db.t_articles.ms_version, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations]
	grid = SQLFORM.grid( query
		,searchable=False, details=False, editable=False, deletable=False, create=False
		,csv=csv, exportclasses=expClass
		,maxtextlength=250
		,paginate=20
		,fields=fields
		,links=links
		,left=db.t_status_article.on(db.t_status_article.status==db.t_articles.status)
		,orderby=~db.t_articles.last_status_change
	)
	return dict(
				#myBackButton=mkBackButton(), 
				myHelp = getHelp(request, auth, db, '#UserMyArticles'),
				myText=getText(request, auth, db, '#UserMyArticlesText'),
				myTitle=getTitle(request, auth, db, '#UserMyArticlesTitle'),
				grid=DIV(grid, _style='max-width:100%; overflow-x:auto;'), 
			 ) 




######################################################################################################################################################################
# Recommendations of my articles
@auth.requires_login()
def recommendations():
	response.view='default/recommended_articles.html'
	printable = False

	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
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
		if art.status == 'Recommended':
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
				DIV(
					DIV(I(T('Recommended article')), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn recommended'
				))
		else:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
				DIV(
					DIV(mkStatusBigDivUser(auth, db, art.status), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn'
				))
		myUpperBtn = A(SPAN(T('Printable page'), _class='buttontext btn btn-info'), 
			_href=URL(c="user", f='recommendations_printable', vars=dict(articleId=articleId), user_signature=True),
			_class='button')
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, db, '#UserRecommendations'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)

@auth.requires_login()
def recommendations_printable():
	response.view='default/recommended_article_printable.html'
	printable = True

	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
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
		
		if art.status == 'Recommended':
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
					DIV(
						DIV(T('Recommended article'), _class='pci-ArticleText printable'),
						_class='pci-ArticleHeaderIn recommended printable'
					))
		else:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
				DIV(
					#DIV(def my_, _class='pci-ArticleText printable'),
					_class='pci-ArticleHeaderIn printable'
				))
		myUpperBtn = ''

		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, db, '#UserRecommendations'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)




######################################################################################################################################################################
@auth.requires_login()
def my_reviews():
	response.view='default/myLayout.html'

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
	
	#db.t_articles._id.readable = False
	db.t_articles._id.represent = lambda aId, row: mkRepresentArticleLight(auth, db, aId)
	db.t_articles._id.label = T('Article')
	db.t_recommendations._id.represent = lambda rId, row: mkRepresentRecommendationLight(auth, db, rId)
	db.t_recommendations._id.label = T('Recommendation')
	db.t_articles.status.represent = lambda text, row: mkStatusDivUser(auth, db, text)
	db.t_reviews.last_change.label = T('Days elapsed')
	db.t_reviews.last_change.represent = lambda text,row: mkElapsed(text)
	db.t_reviews.reviewer_id.writable = False
	#db.t_reviews.recommendation_id.writable = False
	#db.t_reviews.recommendation_id.label = T('Member in charge of the recommendation process')
	#db.t_reviews.recommendation_id.label = T('Recommender')
	#db.t_reviews.recommendation_id.represent = lambda text,row: mkRecommendation4ReviewFormat(auth, db, row.t_reviews)
	db.t_reviews._id.readable = False
	#db.t_reviews.review.readable=False
	db.t_reviews.review_state.represent = lambda text,row: mkReviewStateDiv(auth, db, text)
	db.t_reviews.anonymously.represent = lambda anon,row: mkAnonymousMask(auth, db, anon)
	db.t_reviews.review.represent=lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
	#db.t_reviews.review.label = T('Your review')
	#links = [dict(header='toto', body=lambda row: row.t_articles.id),]
	links = [
			dict(header=T(''), 
					body=lambda row: A(SPAN(btnTxt, _class='buttontext btn btn-default pci-reviewer'), 
									_href=URL(c='user', f='recommendations', vars=dict(articleId=row.t_articles.id), user_signature=True), 
									_target="_blank", 
									_class='button', 
									_title=current.T('View and/or edit review')
									) if row.t_reviews.review_state in ('Pending', 'Under consideration', 'Completed') else ''
				),
		]
	grid = SQLFORM.grid( query
		,searchable=False, deletable=False, create=False, editable=False, details=False
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=[db.t_articles.status, db.t_articles._id, db.t_reviews.review_state, db.t_reviews.last_change, db.t_reviews.anonymously,  db.t_reviews.review, db.t_reviews.review_pdf]
		,links=links
		,orderby=~db.t_reviews.last_change|~db.t_reviews.review_state
	)
	return dict(
				#myBackButton=mkBackButton(), 
				myHelp = getHelp(request, auth, db, '#UserMyReviews'),
				myTitle=myTitle,
				myText=myText,
				grid=grid, 
			 )


######################################################################################################################################################################
@auth.requires_login()
def accept_new_review():
	response.view='default/info.html'

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
	isParallel = db((db.t_recommendations.id==rev['recommendation_id']) & (db.t_recommendations.article_id==db.t_articles.id)).select(db.t_articles.parallel_submission).last()

	_next = None
	if '_next' in request.vars:
		_next = request.vars['_next']
	ethics_not_signed = not(db.auth_user[auth.user_id].ethical_code_approved)
	if ethics_not_signed:
		redirect(URL(c='about', f='ethics', vars=dict(_next=URL('user', 'accept_new_review', vars=dict(reviewId=reviewId) if reviewId else ''))))
	else:
		if (isParallel):
			due_time = myconf.get('config.review_due_time_for_parallel_submission', default='three weeks')
		else:
			due_time = myconf.get('config.review_due_time_for_exclusive_submission', default='three weeks')
		myEthical = DIV(
				FORM(
					DIV(
						SPAN(INPUT(_type="checkbox", _name="no_conflict_of_interest", _id="no_conflict_of_interest", _value="yes", value=False), LABEL(T('I declare that I have no conflict of interest with the authors or the content of the article'))),
						DIV(getText(request, auth, db, '#ConflictsForReviewers')), 
						_style='padding:16px;'),
					DIV(SPAN(INPUT(_type="checkbox", _name="due_time", _id="due_time", _value="yes", value=False), LABEL('I agree to post my review within %s' % due_time)), _style='padding:16px;'),
					INPUT(_type='submit', _value=T("Yes, I consider this preprint for review"), _class="btn btn-success pci-panelButton"), 
					hidden=dict(reviewId=reviewId, ethics_approved=True),
					_action=URL('user_actions', 'do_accept_new_review', vars=dict(reviewId=reviewId) if reviewId else ''),
					_style='text-align:center;',
				),
				_class="pci-embeddedEthic",
			)
		myScript = SCRIPT(common_tools.get_template('script', 'accept_new_review.js'))

	myTitle = getTitle(request, auth, db, '#AcceptReviewInfoTitle')
	myText = DIV(
			getText(request, auth, db, '#AcceptReviewInfoText'),
			myEthical,
		)
	return dict(
		myText=myText,
		myTitle=myTitle,
		myFinalScript = myScript,
	)

######################################################################################################################################################################
@auth.requires_login()
def edit_reply():
	response.view='default/myLayout.html'
	if 'recommId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	recommId = request.vars['recommId']

	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	art = db.t_articles[recomm.article_id]
	if not ((art.user_id == auth.user_id or auth.has_membership(role='manager')) and (art.status == 'Awaiting revision')):
		session.flash = T('Unauthorized', lazy=False)
		redirect(URL(c='user', f='my_articles'))
	db.t_recommendations.reply_pdf.label=T('OR Upload your reply as PDF file')
	form = SQLFORM(db.t_recommendations
				,record=recommId
				,fields=['id', 'reply', 'reply_pdf', 'track_change']
				,upload=URL('default', 'download')
				,showid=False
			)
	form.element(_type='submit')['_value'] = T('Save')
	do_complete = DIV(BUTTON(current.T('Save & submit your reply'), _title=current.T('Click here when the revision is completed in order to submit the new version'), _type='submit', _name='completed', _class='buttontext btn btn-success', _style='margin-top:32px;'), _style='text-align:center;')
	form[0].insert(99, do_complete)
	
	if form.process().accepted:
		if request.vars.completed:
			session.flash = T('Reply completed', lazy=False)
			redirect(URL(c='user_actions', f='article_revised', vars=dict(articleId=art.id), user_signature=True))
		else:
			session.flash = T('Reply saved', lazy=False)
			redirect(URL(c='user', f='recommendations', vars=dict(articleId=art.id), user_signature=True))
	elif form.errors:
		response.flash = T('Form has errors', lazy=False)
	return dict(
				myHelp = getHelp(request, auth, db, '#UserEditReply'),
				#myBackButton = mkBackButton(),
				myText=getText(request, auth, db, '#UserEditReplyText'),
				myTitle=getTitle(request, auth, db, '#UserEditReplyTitle'),
				form = form,
			)



######################################################################################################################################################################
@auth.requires_login()
def edit_review():
	response.view='default/myLayout.html'
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
					INPUT(_type='Submit', _name='terminate', _class='btn btn-success', _value='Save & Submit Your Review'),
				]
		db.t_reviews.no_conflict_of_interest.writable = not(review.no_conflict_of_interest)
		db.t_reviews.anonymously.label = T('I wish to remain anonymous')
		#db.t_reviews.anonymously.writable = review.reviewer_id != recomm.recommender_id
		db.t_reviews.review_pdf.label = T('OR Upload review as PDF')
		db.t_reviews.review_pdf.comment = T('Upload your PDF with the button or download it from the "file" link.')
		form = SQLFORM(db.t_reviews
					,record=review
					,fields=['anonymously', 'review', 'review_pdf', 'no_conflict_of_interest']
					,showid=False
					,buttons=buttons
					,upload=URL('default', 'download')
				)
		if form.process().accepted:
			if form.vars.save:
				session.flash = T('Review saved', lazy=False)
				redirect(URL(c='user', f='recommendations', vars=dict(articleId=art.id), user_signature=True))
			elif form.vars.terminate:
				redirect(URL(c='user_actions', f='review_completed', vars=dict(reviewId=review.id), user_signature=True))
		elif form.errors:
			response.flash = T('Form has errors', lazy=False)
			
	myScript = common_tools.get_template('script', 'edit_review.js')

	return dict(
				myHelp=getHelp(request, auth, db, '#UserEditReview'),
				myBackButton=mkBackButton(),
				myText=getText(request, auth, db, '#UserEditReviewText'),
				myTitle=getTitle(request, auth, db, '#UserEditReviewTitle'),
				form=form,
				myFinalScript=SCRIPT(myScript),
			)



######################################################################################################################################################################
@auth.requires_login()
def new_comment():
	response.view='default/myLayout.html'

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
		redirect(URL(c='articles', f='rec', vars=dict(id=articleId, comments=True), user_signature=True))
	elif form.errors:
		response.flash = T('Form has errors', lazy=False)

	return dict(
		myHelp=getHelp(request, auth, db, '#UserComment'),
		myText=getText(request, auth, db, '#UserCommentText'),
		myTitle=getTitle(request, auth, db, '#UserCommentTitle'),
		form=form,
	)
	
