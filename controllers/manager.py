# -*- coding: utf-8 -*-

import re
import copy
import tempfile
from datetime import datetime, timedelta
import glob
import os

# sudo pip install tweepy
#import tweepy

import codecs
import html2text
from gluon.contrib.markdown import WIKI
from common import *
from helper import *

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

# frequently used constants
from emailing import filename, mail_sleep
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get('config.trgm_limit') or 0.4
not_considered_delay_in_days = 20


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_validate_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Pending':
		art.status = 'Awaiting consideration'
		art.update_record()
		session.flash = T('Request now available to recommenders')
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))




######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_cancel_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		#art.status = 'Cancelled' #TEST
		art.status = 'Rejected'
		art.update_record()
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_recommend_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Pre-recommended':
		art.status = 'Recommended'
		art.update_record()
		redirect(URL(c='public', f='rec', vars=dict(id=art.id), user_signature=True))
	else:
		redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_revise_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Pre-revision':
		art.status = 'Awaiting revision'
		art.update_record()
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_reject_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Pre-rejected':
		art.status = 'Rejected'
		art.update_record()
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))




######################################################################################################################################################################
# Display ALL articles and allow management
@auth.requires(auth.has_membership(role='manager'))
def all_articles():
	resu = _manage_articles(None, 'all_articles')
	resu['myText']=getText(request, auth, db, '#ManagerAllArticlesText')
	resu['myTitle']=getTitle(request, auth, db, '#ManagerAllArticlesTitle')
	resu['myHelp'] = getHelp(request, auth, db, '#ManageAllArticlesHelp')
	return resu



######################################################################################################################################################################
# Display pending articles and allow management
@auth.requires(auth.has_membership(role='manager'))
def pending_articles():
	resu = _manage_articles(['Pending', 'Pre-recommended', 'Pre-revision', 'Pre-rejected'], 'pending_articles')
	resu['myText']=getText(request, auth, db, '#ManagerPendingArticlesText')
	resu['myTitle']=getTitle(request, auth, db, '#ManagerPendingArticlesTitle')
	resu['myHelp'] = getHelp(request, auth, db, '#ManagePendingValidations')
	return resu



######################################################################################################################################################################
# Display ongoing articles and allow management
@auth.requires(auth.has_membership(role='manager'))
def ongoing_articles():
	resu = _manage_articles(['Awaiting consideration', 'Under consideration', 'Awaiting revision'], 'ongoing_articles')
	resu['myText']=getText(request, auth, db, '#ManagerOngoingArticlesText')
	resu['myTitle']=getTitle(request, auth, db, '#ManagerOngoingArticlesTitle')
	resu['myHelp'] = getHelp(request, auth, db, '#ManageOngoingArticles')
	return resu



######################################################################################################################################################################
# Display completed articles and allow management
@auth.requires(auth.has_membership(role='manager'))
def completed_articles():
	db.t_articles.status.label = T('Outcome')
	resu = _manage_articles(['Cancelled', 'Recommended', 'Rejected', 'Not considered'], 'completed_articles')
	resu['myText']=getText(request, auth, db, '#ManagerCompletedArticlesText')
	resu['myTitle']=getTitle(request, auth, db, '#ManagerCompletedArticlesTitle')
	resu['myHelp'] = getHelp(request, auth, db, '#ManageCompletedArticles')
	return resu




######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def suggest_article_to():
	articleId = request.vars['articleId']
	whatNext = request.vars['whatNext']
	recommenderId = request.vars['recommenderId']
	db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)
	redirect(whatNext)





######################################################################################################################################################################
def mkRecommenderButton(row):
	last_recomm = db( db.t_recommendations.article_id==row.id ).select(orderby=db.t_recommendations.id).last()
	if last_recomm:
		resu = SPAN(mkUserWithMail(auth, db, last_recomm.recommender_id))
		corecommenders = db(db.t_press_reviews.recommendation_id==last_recomm.id).select(db.t_press_reviews.contributor_id)
		if len(corecommenders) > 0:
			resu.append(BR())
			resu.append(B(current.T('Co-recommenders:')))
			resu.append(BR())
			for corecommender in corecommenders:
				resu.append(SPAN(mkUserWithMail(auth, db, corecommender.contributor_id))+BR())
		return resu
	else:
		return ''



######################################################################################################################################################################
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
		if sr.declined:
			suggRecomsTxt.append(mkUserWithMail(auth, db, sr.suggested_recommender_id)+XML(':&nbsp;declined')+BR())
		else:
			suggRecomsTxt.append(mkUserWithMail(auth, db, sr.suggested_recommender_id)+BR())
	myVars = dict(articleId=row.id, whatNext=whatNext)
	if len(exclude)>0:
		myVars['exclude'] = ','.join(exclude)
	if len(suggRecomsTxt)>0: 
		butts.append(DIV(suggRecomsTxt))
		if row.status in ('Awaiting consideration', 'Pending'):
			butts.append( A(current.T('Manage'), _class='btn btn-default pci-manager', _href=URL(c='manager', f='suggested_recommenders', vars=myVars)) )
	#for thema in row.thematics:
		#myVars['qy_'+thema] = 'on'
	#butts.append( BR() )
	if row.status in ('Awaiting consideration', 'Pending'):
		butts.append( A(current.T('Add'), _class='btn btn-default pci-manager', _href=URL(c='manager', f='search_recommenders', vars=myVars, user_signature=True)) )
	return butts





######################################################################################################################################################################
# Common function which allow management of articles filtered by status
######################################################################################################################################################################
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
	db.t_articles.keywords.readable = False
	db.t_articles.keywords.writable = False
	db.t_articles.auto_nb_recommendations.readable = False
	db.t_articles.auto_nb_recommendations.writable = False
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
		links += [ dict(header=T('Suggested recommenders'), body=lambda row: mkSuggestedRecommendersManagerButton(row, '%s://%s%s' % (request.env.wsgi_url_scheme, request.env.http_host,
           request.env.request_uri)) ), ]
	links += [
				dict(header=T('Recommenders'), body=lambda row: mkRecommenderButton(row)),
				dict(header=T('Recommendation title'), body=lambda row: mkLastRecommendation(auth, db, row.id)),
				dict(header=T('Actions'), 
						body=lambda row: DIV(
											A(SPAN(current.T('Check & Edit')), 
												_href=URL(c='manager', f='recommendations', vars=dict(articleId=row.id), user_signature=True), 
												_target="_blank", 
												_class='buttontext btn btn-default pci-button pci-manager', 
												_title=current.T('View and/or edit review')
											),
											A(SPAN(current.T('Email to more'),BR(),T('recommenders')), 
												_href=URL(c='manager', f='warn_recommenders', vars=dict(mkTFDict(row.thematics), articleId=row.id, qyKeywords=row.keywords, comeback=URL())),
												_class='button btn btn-info pci-manager', 
												_title=current.T('Pick up recommenders not already suggested and send them an email')
											) if (row.status == 'Awaiting consideration' 
													and row.already_published is False ) else '',
											A(SPAN(current.T('Set "Not considered"')), 
												_href=URL(c='manager', f='set_not_considered', vars=dict(articleId=row.id), user_signature=True), 
												_class='buttontext btn btn-danger pci-button pci-manager', 
												_title=current.T('Set this preprint as "Not considered"')
											) if (row.status == 'Awaiting consideration' 
													and row.already_published is False 
													and datetime.datetime.now() - row.upload_timestamp > timedelta(days=not_considered_delay_in_days) ) else '',
										)
					),
			]
	grid = SQLFORM.grid(  query
		,details=False, editable=False, deletable=False, create=False
		,searchable=True
		,maxtextlength=250, paginate=20
		,csv=csv, exportclasses=expClass
		,fields=[db.t_articles.uploaded_picture, db.t_articles._id, db.t_articles.already_published, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations, db.t_articles.user_id, db.t_articles.thematics, db.t_articles.keywords]
		,links=links
		,orderby=~db.t_articles.last_status_change
	)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#ManagerArticlesText'),
				myTitle=getTitle(request, auth, db, '#ManagerArticlesTitle'),
				grid=grid, 
			)



######################################################################################################################################################################
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def recommendations():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
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






######################################################################################################################################################################
# Allow management of article recommendations
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def manage_recommendations():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = T('Unavailable')
		redirect(request.env.http_referer)
	query = db.t_recommendations.article_id == articleId
	db.t_recommendations.recommender_id.default = auth.user_id
	db.t_recommendations.article_id.default = articleId
	db.t_recommendations.article_id.writable = False
	db.t_recommendations.last_change.writable = False
	db.t_recommendations.doi.represent = lambda text, row: mkDOI(text)
	db.t_pdf.pdf.represent = lambda text, row: A(IMG(_src=URL('static', 'images/application-pdf.png')), _href=URL('default', 'download', args=text)) if text else ''
	db.t_recommendations._id.readable = False
	if len(request.args) == 0: # in grid
		db.t_recommendations.recommender_id.represent = lambda id, row: mkUserWithMail(auth, db, id)
		db.t_recommendations.recommendation_state.represent = lambda state, row: mkContributionStateDiv(auth, db, (state or ''))
		db.t_recommendations.recommendation_comments.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
		db.t_recommendations.recommendation_timestamp.represent = lambda text, row: mkLastChange(text)
		db.t_recommendations.last_change.represent = lambda text, row: mkLastChange(text)
	else: # in form
		db.t_recommendations.recommendation_comments.represent=lambda text, row: WIKI(text or '')

	links = [dict(header=T('Co-recommenders'), body=lambda row: A((db.v_recommendation_contributors[(row.get('t_recommendations') or row).id]).contributors or 'ADD', _href=URL(c='recommender', f='contributions', vars=dict(recommId=(row.get('t_recommendations') or row).id))))]
	if not(art.already_published):
		links += [dict(header=T('Reviews'), body=lambda row: A((db.v_reviewers[(row.get('t_recommendations') or row).id]).reviewers or 'ADD', _href=URL(c='recommender', f='reviews', vars=dict(recommId=(row.get('t_recommendations') or row).id))))]
	#links += [dict(header=T('PDF'), body=lambda row: A(db(db.t_pdf.recommendation_id==row.id).select().last()['pdf'], _href=URL(c='admin', f='manage_pdf', vars=dict(keywords='t_pdf.recommendation_id="%s"'%row.id) )))]
	grid = SQLFORM.grid( query
		,editable=True
		,deletable=True
		,create=True
		,details=False
		,searchable=False
		,maxtextlength=1000
		,csv=csv, exportclasses=expClass
		,paginate=10
		,left=db.t_pdf.on(db.t_pdf.recommendation_id==db.t_recommendations.id)
		,fields=[db.t_recommendations.doi, db.t_recommendations.ms_version, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.recommendation_state, db.t_recommendations.is_closed, db.t_recommendations.recommender_id, db.t_recommendations.recommendation_comments, db.t_recommendations.reply, db.t_recommendations.reply_pdf, db.t_recommendations.track_change, db.t_pdf.pdf]
		,links=links
		,orderby=~db.t_recommendations.recommendation_timestamp
	)
	if grid.element(_title="Add record to database"):
		grid.element(_title="Add record to database")[0] = T('Manually add new round')
		grid.element(_title="Add record to database")['_title'] = T('Manually add new round of recommendation. Expert use!!')
	myContents = mkRepresentArticle(auth, db, articleId)
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, db, '#ManageRecommendations'),
				myText=getText(request, auth, db, '#ManageRecommendationsText'),
				myTitle=getTitle(request, auth, db, '#ManageRecommendationsTitle'),
				content=myContents,
				grid=grid,
			)



######################################################################################################################################################################
######################################################################################################################################################################
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
			Field('city', type='string', label=T('City'), represent=lambda t,r: t if t else ''),
			Field('country', type='string', label=T('Country'), represent=lambda t,r: t if t else ''),
			Field('laboratory', type='string', label=T('Laboratory'), represent=lambda t,r: t if t else ''),
			Field('institution', type='string', label=T('Institution'), represent=lambda t,r: t if t else ''),
			Field('thematics', type='list:string', label=T('Thematic fields')),
			Field('excluded', type='boolean', label=T('Excluded')),
		)
		temp_db.qy_recomm.email.represent = lambda text, row: A(text, _href='mailto:'+text)
		qyKwArr = qyKw.split(' ')
		searchForm = mkSearchForm(auth, db, myVars)
		if searchForm.process(keepvalues=True).accepted:
			response.flash = None
		else:
			qyTF = []
			for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
				qyTF.append(thema.keyword)
		filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s, %s);', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
		for fr in filtered:
			qy_recomm.insert(**fr)
				
		links = [
					dict(header=T('Days since last recommendation'), body=lambda row: db.v_last_recommendation[row.id].days_since_last_recommendation),
					dict(header='',         body=lambda row: '' if row.excluded else A(SPAN(current.T('Suggest'), _class='btn btn-default pci-manager'), 
																							_href=URL(c='manager', f='suggest_article_to', 
																									vars=dict(articleId=articleId, recommenderId=row['id'], whatNext=whatNext), 
																									user_signature=True), 
																						_class='button')),
			]
		temp_db.qy_recomm._id.readable = False
		temp_db.qy_recomm.uploaded_picture.readable = False
		temp_db.qy_recomm.num.readable = False
		temp_db.qy_recomm.score.readable = False
		temp_db.qy_recomm.excluded.readable = False
		grid = SQLFORM.grid( qy_recomm
			,editable = False,deletable = False,create = False,details=False,searchable=False
			,maxtextlength=250,paginate=1000
			,csv=csv,exportclasses=expClass
			,fields=[temp_db.qy_recomm.num, temp_db.qy_recomm.score, temp_db.qy_recomm.uploaded_picture, temp_db.qy_recomm.first_name, temp_db.qy_recomm.last_name, temp_db.qy_recomm.email, temp_db.qy_recomm.laboratory, temp_db.qy_recomm.institution, temp_db.qy_recomm.city, temp_db.qy_recomm.country, temp_db.qy_recomm.thematics, temp_db.qy_recomm.excluded]
			,links=links
			,orderby=temp_db.qy_recomm.num
			,args=request.args
		)
		response.view='default/myLayout.html'
		return dict(
					myBackButton=mkBackButton(target=whatNext),
					myHelp=getHelp(request, auth, db, '#ManagerSearchRecommenders'),
					myText=getText(request, auth, db, '#ManagerSearchRecommendersText'),
					myTitle=getTitle(request, auth, db, '#ManagerSearchRecommendersTitle'),
					grid=grid,
					searchForm=searchForm, 
				)



######################################################################################################################################################################
# Display suggested recommenders for a submitted article
# Logged users only (submission)
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def suggested_recommenders():
	articleId = request.vars['articleId']
	whatNext = request.vars['whatNext']
	if articleId is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	query = (db.t_suggested_recommenders.article_id == articleId)
	db.t_suggested_recommenders._id.readable = False
	db.t_suggested_recommenders.suggested_recommender_id.represent = lambda text, row: mkUserWithMail(auth, db, text)
	links = []
	if art.status == 'Awaiting consideration':
		links.append(dict(header='', body=lambda row: A(T('Send a reminder'), _class='btn btn-info pci-manager', _href=URL(c='manager', f='send_suggested_recommender_reminder', vars=dict(suggRecommId=row.id))) if not(row.declined) else ''))
	grid = SQLFORM.grid( query
		,details=False,editable=False,deletable=True,create=False,searchable=False
		,maxtextlength = 250,paginate=100
		,csv = csv, exportclasses = expClass
		,fields=[db.t_suggested_recommenders.id, db.t_suggested_recommenders.suggested_recommender_id, db.t_suggested_recommenders.email_sent, db.t_suggested_recommenders.declined]
		,field_id=db.t_suggested_recommenders.id
		,links=links
	)
	response.view='default/myLayout.html'
	return dict(
					#myBackButton=mkBackButton(target=URL(c='manager',f='pending_articles')), 
					myBackButton=mkBackButton(target=whatNext), 
					myHelp=getHelp(request, auth, db, '#ManageSuggestedRecommenders'),
					myText=getText(request, auth, db, '#ManageSuggestedRecommendersText'),
					myTitle=getTitle(request, auth, db, '#ManageSuggestedRecommendersTitle'),
					grid=grid, 
				)





######################################################################################################################################################################
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def edit_article():
	if not('articleId' in request.vars):
		session.flash = T('Unavailable')
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art == None:
		raise HTTP(404, "404: "+T('Unavailable'))
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




######################################################################################################################################################################
######################################################################################################################################################################
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


######################################################################################################################################################################
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def resizeArticleImages(ids):
	for articleId in ids:
		makeArticleThumbnail(auth, db, articleId, size=(150,150))




######################################################################################################################################################################
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def set_not_considered():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Awaiting consideration':
		session.flash = T('Article set "Not considered"')
		art.status = 'Not considered'
		art.update_record()
	redirect(request.env.http_referer)


######################################################################################################################################################################
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def send_suggested_recommender_reminder():
	if ('suggRecommId' in request.vars):
		suggRecommId = request.vars['suggRecommId']
		do_send_reminder_email_to_suggested_recommender(session, auth, db, suggRecommId)
	else:
		session.flash = T('Unavailable')
	redirect(request.env.http_referer)



######################################################################################################################################################################
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager') or auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def warn_recommenders(): 
	myVars = request.vars
	qyKw = ''
	qyTF = []
	excludeList = []
	articleId = None
	comeback = None
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
		elif (myVar == 'comeback'):
			comeback = myValue
		#elif (myVar == 'exclude'):
			#excludeList = map(int, myValue.split(','))
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))

	#TODO 
	excludeList.append(art.user_id)
	excludeList.append(auth.user_id)
	for sr in db(db.t_suggested_recommenders.article_id == articleId).select(db.t_suggested_recommenders.suggested_recommender_id):
		excludeList.append(sr.suggested_recommender_id)
	
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
	sfDict = copy.deepcopy(request.vars)
	sfDict['qyKeywords'] = qyKw
	searchForm =  mkSearchForm(auth, db, sfDict)
	if searchForm.process(keepvalues=True).accepted:
		response.flash = None
	elif len(qyTF)==0:
		qyTF = []
		for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
			qyTF.append(thema.keyword)
	filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s, %s);', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
	for fr in filtered:
		if fr['excluded'] is False:
			qy_recomm.insert(**fr)
	
	links = []
	selectable = [(T('Send email to checked recommenders'), lambda ids: [f_email_article_to_recommenders(articleId, ids, comeback)], 'btn btn-success pci-manager')]
	temp_db.qy_recomm._id.readable = False
	temp_db.qy_recomm.uploaded_picture.readable = False
	temp_db.qy_recomm.num.readable = False
	temp_db.qy_recomm.score.readable = True
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
	response.view='default/myLayout.html'
	return dict(
				myBackButton=mkBackButton(target=comeback) if comeback else '',
				myHelp=getHelp(request, auth, db, '#UserSearchRecommendersForWarning'),
				myText=getText(request, auth, db, '#UserSearchRecommendersForWarningText'),
				myTitle=getTitle(request, auth, db, '#UserSearchRecommendersForWarningTitle'),
				searchForm=searchForm, 
				grid=grid, 
			)


######################################################################################################################################################################
######################################################################################################################################################################
def f_email_article_to_recommenders(articleId, ids, comeback):
	redirect(URL(c='manager', f='email_article_to_recommenders', vars=dict(articleId=articleId, ids=ids, comeback=comeback)))

######################################################################################################################################################################
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager') or auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def email_article_to_recommenders():
	if 'articleId' in request.vars and request.vars['articleId']:
		articleId = request.vars['articleId']
		art = db.t_articles[articleId]
	if 'ids' in request.vars and request.vars['ids']:
		ids = request.vars['ids']
	if 'comeback' in request.vars and request.vars['comeback']:
		comeback = request.vars['comeback']
	if art is None or ids is None or len(ids)==0:
		raise HTTP(404, "404: "+T('Unavailable'))
	else:
		scheme = myconf.take('alerts.scheme')
		host = myconf.take('alerts.host')
		port = myconf.take('alerts.port', cast=lambda v: takePort(v) )
		site_url = URL(c='default', f='index', scheme=scheme, host=host, port=port)
		description = myconf.take('app.description')
		longname = myconf.take('app.longname')
		contact = myconf.take('contacts.managers')
		art_authors = art.authors
		art_title = art.title
		art_doi = art.doi
		linkTarget = URL(c='recommender', f='article_details', vars=dict(articleId=art.id), scheme=scheme, host=host, port=port)
		linkHelp = URL(c='about', f='help_generic', scheme=scheme, host=host, port=port)
		default_subject='%(longname)s: Preprint available for recommenders' % locals()
		default_message = """Dear recommender of %(longname)s,

We would like to inform you that the following preprint has recently been submitted to %(longname)s and still requires a recommender to handle its evaluation. You have declared keywords in your profile that match those of this submission, this is why you receive this message.

* Title : %(art_title)s
* By: %(art_authors)s
* DOI: %(art_doi)s

You can obtain information about this submission and accept or decline to handle the evaluation of the preprint by following this link:
%(linkTarget)s 
or by going to the %(longname)s website, logging in, and going to 'Requests for input —> Consider preprint submissions' in the top menu.

The role of a recommender for %(longname)s is very similar to that of a journal editor (finding reviewers, collecting reviews, taking editorial decisions based on reviews), and may lead to the recommendation of the preprint after several rounds of reviews. The evaluation forms the basis of the decision to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by %(longname)s is a complete article that may be used and cited like the ‘classic’ articles published in peer-reviewed journals.

If after one or several rounds of review, you decide to recommend this preprint, you will need to write a “recommendation” that will have its own DOI and be published by %(longname)s under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (at least the reference of the preprint recommended). All the editorial correspondence (reviews, your decisions, authors’ replies) will also be published by %(longname)s.

If you agree to handle this preprint, you will be responsible for managing the evaluation process until you reach a final decision (i.e. recommend or reject this preprint). You will be able to invite, through the %(longname)s website, reviewers included in the %(longname)s database or not already present in this database.

Details about the recommendation process can be found here: %(linkHelp)s. 
You can also watch this short video: https://youtu.be/u5greO-q8-M

Thanks again for your help.

Yours sincerely,

The Managing Board of %(longname)s""" % locals()

	report = []
	selRec = []
	for rid in ids:
		selRec.append(LI(mkUserWithMail(auth, db, rid)))
	content = DIV(H3(T('To each selected recommender:')), UL(selRec), _style='margin-left:400px;')
	form = SQLFORM.factory(
			#Field('replyto', label=T('Reply-to'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default=replyto_address, writable=False),
			#Field('bcc', label=T('BCC'), type='string', length=250, requires=IS_EMAIL(error_message=T('invalid email!')), default='%s, %s'%(replyto.email, contact), writable=False),
			#Field('reviewer_email', label=T('Reviewer email address'), type='string', length=250, default=reviewer.email, writable=False, requires=IS_EMAIL(error_message=T('invalid email!'))),
			Field('subject', label=T('Subject'), type='string', length=250, default=default_subject, required=True),
			Field('message', label=T('Message'), type='text', default=default_message, required=True),
		)
	form.element(_type='submit')['_value'] = T("Send email so selected recommenders")
	form.element('textarea[name=message]')['_style'] = 'height:550px;'
	
	if form.process().accepted:
		response.flash = None
		mySubject = request.vars['subject']
		myContent = request.vars['message']
		myMessage = render(filename=filename, context=dict(content=XML(WIKI(myContent)), footer=mkFooter()))
		for rid in ids:
			destPerson = mkUserWithMail(auth, db, rid)
			destAddress = db.auth_user[rid].email
			mail_resu = False
			try:
				mail_resu = mail.send(to=[destAddress], cc=contact, subject=mySubject, message=myMessage)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to %s' % destPerson.flatten() )
			time.sleep(mail_sleep)
		
		print '\n'.join(report)
		if session.flash is None:
			session.flash = '; '.join(report)
		else:
			session.flash += '; ' + '; '.join(report)
		if comeback:
			redirect(comeback)
		else:
			redirect(request.env.http_referer)

	response.view='default/myLayout.html'
	return dict(
		content=content,
		form=form,
		myHelp=getHelp(request, auth, db, '#EmailToWarnRecommendersHelp'),
		myTitle=getTitle(request, auth, db, '#EmailToWarnRecommendersTitle'),
		myText=getText(request, auth, db, '#EmailToWarnRecommendersInfoText'),
		myBackButton=mkBackButton(),
	)

