# -*- coding: utf-8 -*-

import re
import copy

from gluon.storage import Storage
from gluon.contrib.markdown import WIKI

from datetime import datetime, timedelta, date
from dateutil import parser
from gluon.contrib.appconfig import AppConfig
from lxml import etree

from app_modules.common import *
from app_modules.helper import *
from app_modules import new_common

myconf = AppConfig(reload=True)

# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4



######################################################################################################################################################################
# Recommended articles search & list (public)
def recommended_articles():
	response.view='default/list_layout.html'

	myVars = request.vars
	qyKwArr = []
	qyTF = []
	myVars2 = {}
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
			myVars2[myVar] = myValue
			qyKwArr = qyKw.split(' ')
		elif (myVar == 'qyThemaSelect') and myValue:
			qyTF=[myValue]
			myVars2['qy_'+myValue] = True
		elif (re.match('^qy_', myVar) and myValue=='on' and not('qyThemaSelect' in myVars)):
			qyTF.append(re.sub(r'^qy_', '', myVar))
			myVars2[myVar] = myValue

	filtered = db.executesql('SELECT * FROM search_articles(%s, %s, %s, %s, %s);', placeholders=[qyTF, qyKwArr, 'Recommended', trgmLimit, True], as_dict=True)
	
	totalArticles = len(filtered)
	myRows = []
	for row in filtered:
		r = mkRecommArticleRow(auth, db, Storage(row), withImg=True, withScore=False, withDate=True)
		if r:
			myRows.append(r)
			
	grid = DIV(DIV(
				DIV(T('%s articles found')%(totalArticles), _class='pci-nResults'),
				TABLE(
					#THEAD(TR(TH(T('Score')), TH(T('Recommendation')), TH(T('Article')), _class='pci-lastArticles-row')),
					TBODY(myRows),
				_class='web2py_grid pci-lastArticles-table'), 
			_class='pci-lastArticles-div'), _class='searchRecommendationsDiv')


	searchForm = new_common.getSearchForm(auth, db, myVars2)
	
	return dict(
				grid=grid, 
				myTitle=getTitle(request, auth, db, '#RecommendedArticlesTitle'),
				myText=getText(request, auth, db, '#RecommendedArticlesText'),
				myHelp=getHelp(request, auth, db, '#RecommendedArticles'),
				shareable=True,
				searchableList = True,
				searchForm = searchForm
			)


######################################################################################################################################################################
def all_recommended_articles():
	response.view='default/myLayout.html'

	allR = db.executesql('SELECT * FROM search_articles(%s, %s, %s, %s, %s);', placeholders=[['.*'], None, 'Recommended', trgmLimit, True], as_dict=True)
	myRows = []
	for row in allR:
		r = mkRecommArticleRow(auth, db, Storage(row), withImg=True, withScore=False, withDate=True)
		if r:
			myRows.append(r)
	n = len(allR)
	grid = DIV(DIV(
				DIV(T('%s articles found')%(n), _class='pci-nResults'),
				TABLE(
					#THEAD(TR(TH(T('Score')), TH(T('Recommendation')), TH(T('Article')), _class='pci-lastArticles-row')),
					TBODY(myRows),
				_class='web2py_grid pci-lastArticles-table'), 
			_class='pci-lastArticles-div'), _class='searchRecommendationsDiv')
	return dict(
				grid=grid, 
				#searchForm=searchForm, 
				myTitle=getTitle(request, auth, db, '#AllRecommendedArticlesTitle'),
				myText=getText(request, auth, db, '#AllRecommendedArticlesText'),
				myHelp=getHelp(request, auth, db, '#AllRecommendedArticles'),
				shareable=True,
			)

######################################################################################################################################################################
# Recommendations of an article (public)
def rec():
	response.view='default/recommended_articles.html'
	printable = False

	if 'reviews' in request.vars and request.vars['reviews']=='True':
		with_reviews = True
	else:
		with_reviews = False
	if 'comments' in request.vars and request.vars['comments']=='True':
		with_comments = True
	else:
		with_comments = False
	if 'asPDF' in request.vars and request.vars['asPDF']=='True':
		as_pdf = True
	else:
		as_pdf = False
	
	if ('articleId' in request.vars):
		articleId = request.vars['articleId']
	elif ('id' in request.vars):
		articleId = request.vars['id']
	else:
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
	# NOTE: check id is numeric!
	if (not articleId.isdigit()):
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
		
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
	# NOTE: security hole possible by articleId injection: Enforced checkings below.
	elif art.status != 'Recommended':
		session.flash = T('Forbidden access')
		redirect(URL('articles', 'recommended_articles', user_signature=True))

	if (as_pdf):
		pdfQ = db( (db.t_pdf.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == art.id) ).select(db.t_pdf.id, db.t_pdf.pdf)
		if len(pdfQ) > 0:
			redirect(URL('default', 'download', args=pdfQ[0]['pdf']))
		else:
			session.flash = T('Unavailable')
			redirect(redirect(request.env.http_referer))

	myFeaturedRecommendation = mkFeaturedRecommendation(auth, db, art, printable=printable, with_reviews=with_reviews, with_comments=with_comments)
	myContents = myFeaturedRecommendation['myContents']
	nbReviews = myFeaturedRecommendation['nbReviews']
	pdf = myFeaturedRecommendation['pdf']
	myMeta = myFeaturedRecommendation['myMeta']
	

	if with_reviews:
		btnSHRtxt = T('Hide reviews')
	else:
		btnSHRtxt = T('Show reviews')
	if with_comments:
		btnSHCtxt = T('Hide user comments')
	else:
		btnSHCtxt = T('Show user comments')
	myUpperBtn = DIV(
					IMG(_src=URL(r=request,c='static',f='images/small-background.png'), _height="100"),
					A(SPAN(T('Printable page'), _class='buttontext btn btn-info  pci-ArticleTopButton'), 
						pdf if pdf else '',
						_href=URL(c='articles', f='rec_printable', vars=dict(articleId=articleId, reviews=with_reviews, comments=with_comments), user_signature=True),
						_class='button'),
					(A(SPAN(btnSHRtxt, _class='buttontext btn btn-default  pci-ArticleTopButton'), 
						_href=URL(c='articles', f='rec', vars=dict(articleId=articleId, reviews=not(with_reviews), comments=with_comments), user_signature=True),
						_class='button')) if (nbReviews>0) else '',
					(A(SPAN(btnSHCtxt, _class='buttontext btn btn-default  pci-ArticleTopButton'), 
						_href=URL(c='articles', f='rec', vars=dict(articleId=articleId, reviews=with_reviews, comments=not(with_comments)), user_signature=True),
						_class='button')),
					mkCloseButton(),
					_class="pci-ArticleTopButtons",
				)
	myTitle=None
	
	finalRecomm = db( (db.t_recommendations.article_id==art.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=db.t_recommendations.id).last()
	if finalRecomm:
		response.title = (finalRecomm.recommendation_title or myconf.take('app.longname'))
	else:
		response.title = myconf.take('app.longname')
	if len(response.title)>64:
		response.title = response.title[:64]+'...'
	if len(myMeta)>0:
		response.meta = myMeta
		#for k in myMeta:
			#if type(myMeta[k]) is list:
				#response.meta[k] = ' ; '.join(myMeta[k]) # syntax as in: http://dublincore.org/documents/2000/07/16/usageguide/#usinghtml
			#else:
				#response.meta[k] = myMeta[k]
	return dict(
				statusTitle=myTitle,
				myContents=myContents,
				myUpperBtn=myUpperBtn,
				shareButtons=True,
			)
			
def rec_printable():
	response.view='default/recommended_article_printable.html'
	printable = True

	if 'reviews' in request.vars and request.vars['reviews']=='True':
		with_reviews = True
	else:
		with_reviews = False
	if 'comments' in request.vars and request.vars['comments']=='True':
		with_comments = True
	else:
		with_comments = False
	if 'asPDF' in request.vars and request.vars['asPDF']=='True':
		as_pdf = True
	else:
		as_pdf = False
	
	if ('articleId' in request.vars):
		articleId = request.vars['articleId']
	elif ('id' in request.vars):
		articleId = request.vars['id']
	else:
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
	# NOTE: check id is numeric!
	if (not articleId.isdigit()):
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
		
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
	# NOTE: security hole possible by articleId injection: Enforced checkings below.
	elif art.status != 'Recommended':
		session.flash = T('Forbidden access')
		redirect(URL('articles', 'recommended_articles', user_signature=True))

	if (as_pdf):
		pdfQ = db( (db.t_pdf.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == art.id) ).select(db.t_pdf.id, db.t_pdf.pdf)
		if len(pdfQ) > 0:
			redirect(URL('default', 'download', args=pdfQ[0]['pdf']))
		else:
			session.flash = T('Unavailable')
			redirect(redirect(request.env.http_referer))

	myFeaturedRecommendation = mkFeaturedRecommendation(auth, db, art, printable=printable, with_reviews=with_reviews, with_comments=with_comments)
	myContents = myFeaturedRecommendation['myContents']
	nbReviews = myFeaturedRecommendation['nbReviews']
	pdf = myFeaturedRecommendation['pdf']
	myMeta = myFeaturedRecommendation['myMeta']
	
	myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png'), _height="100"))
	myUpperBtn = ''
	
	finalRecomm = db( (db.t_recommendations.article_id==art.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=db.t_recommendations.id).last()
	if finalRecomm:
		response.title = (finalRecomm.recommendation_title or myconf.take('app.longname'))
	else:
		response.title = myconf.take('app.longname')
	if len(response.title)>64:
		response.title = response.title[:64]+'...'
	if len(myMeta)>0:
		response.meta = myMeta
		#for k in myMeta:
			#if type(myMeta[k]) is list:
				#response.meta[k] = ' ; '.join(myMeta[k]) # syntax as in: http://dublincore.org/documents/2000/07/16/usageguide/#usinghtml
			#else:
				#response.meta[k] = myMeta[k]
	return dict(
				statusTitle=myTitle,
				myContents=myContents,
				myUpperBtn=myUpperBtn,
				shareButtons=True,
			)

######################################################################################################################################################################
def tracking():
	response.view='default/myLayout.html'

	tracking = myconf.get('config.tracking', default=False)
	if tracking is False:
		session.flash = T('Unavailable')
		redirect(redirect(request.env.http_referer))
	else:
		myContents = TABLE(_class='web2py_grid pci-tracking pci-lastArticles-table') # 
		
		query = db(db.t_articles.already_published==False).select(orderby=~db.t_articles.last_status_change)
		
		for myArticle in query:
			tr = mkTrackRow(auth, db, myArticle)
			if tr:
				myContents.append(TR(tr, _class='pci-lastArticles-row'))
		
		resu = dict(
			myHelp=getHelp(request, auth, db, '#Tracking'),
			myTitle=getTitle(request, auth, db, '#TrackingTitle'),
			myText=getText(request, auth, db, '#TrackingText'),
			grid = myContents
				)
		return resu


# (gab) not working ? 
# STRANGE ERROR : local variable 'myContents' referenced before assignment
######################################################################################################################################################################
def pubReviews():
	response.view='default/myLayout.html'

	myContents = DIV()
	tracking = myconf.get('config.tracking', default=False)
	if tracking is False:
		session.flash = T('Unavailable')
		redirect(redirect(request.env.http_referer))
	elif ('articleId' in request.vars):
		articleId = request.vars['articleId']
	elif ('id' in request.vars):
		articleId = request.vars['id']
	else:
		session.flash = T('Unavailable')
		redirect(redirect(request.env.http_referer))
	# NOTE: check id is numeric!
	if (not articleId.isdigit()):
		session.flash = T('Unavailable')
		redirect(redirect(request.env.http_referer))
		
	art = db.t_articles[articleId]
	if art is None:
		session.flash = T('Unavailable')
		redirect(redirect(request.env.http_referer))
	elif art.status != 'Cancelled':
		session.flash = T('Unavailable')
		redirect(redirect(request.env.http_referer))
	else:
		myContents = DIV(reviewsOfCancelled(auth, db, art))
	
	resu = dict(
			myHelp=getHelp(request, auth, db, '#TrackReviews'),
			myTitle=getTitle(request, auth, db, '#TrackReviewsTitle'),
			myText=getText(request, auth, db, '#TrackReviewsText'),
			grid = myContents
		)
	return resu




######################################################################################################################################################################
@cache.action(time_expire=30, cache_model=cache.ram, quick='V')
def last_recomms():
	if 'maxArticles' in request.vars:
		maxArticles = int(request.vars['maxArticles'])
	else:
		maxArticles = 10
	myVars = copy.deepcopy(request.vars)
	myVars['maxArticles'] = (myVars['maxArticles'] or 10)
	myVarsNext = copy.deepcopy(myVars)
	myVarsNext['maxArticles'] = int(myVarsNext['maxArticles'])+10

	query = None
	#if 'qyThemaSelect' in request.vars:
		#thema = request.vars['qyThemaSelect']
		#if thema and len(thema)>0:
			#query = db( 
					#(db.t_articles.status=='Recommended') 
				  #& (db.t_recommendations.article_id==db.t_articles.id) 
				  #& (db.t_recommendations.recommendation_state=='Recommended')
				  #& (db.t_articles.thematics.contains(thema)) 
				#).iterselect(db.t_articles.id, db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.doi, db.t_articles.picture_rights_ok, db.t_articles.uploaded_picture, db.t_articles.abstract, db.t_articles.upload_timestamp, db.t_articles.user_id, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.already_published, db.t_articles.i_am_an_author, db.t_articles.is_not_reviewed_elsewhere, db.t_articles.auto_nb_recommendations, limitby=(0, maxArticles), orderby=~db.t_articles.last_status_change)
	if query is None:
		query = db( 
					(db.t_articles.status=='Recommended') 
				  & (db.t_recommendations.article_id==db.t_articles.id) 
				  & (db.t_recommendations.recommendation_state=='Recommended')
			).iterselect(db.t_articles.id, db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.doi, db.t_articles.picture_rights_ok, db.t_articles.uploaded_picture, db.t_articles.abstract, db.t_articles.upload_timestamp, db.t_articles.user_id, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.already_published, db.t_articles.i_am_an_author, db.t_articles.is_not_reviewed_elsewhere, db.t_articles.auto_nb_recommendations, limitby=(0, maxArticles), orderby=~db.t_articles.last_status_change)
	myRows = []
	for row in query:
		r = mkRecommArticleRow(auth, db, row, withDate=True)
		if r:
			myRows.append(r)
	
	if len(myRows) == 0:
		return DIV(I(T('Coming soon...')))
	
	if len(myRows) < maxArticles:
		moreState = ' disabled'
	else:
		moreState = ''
	return DIV(
			TABLE(
				TBODY(myRows), 
				_class='web2py_grid pci-lastArticles-table'), 
			DIV(
				A(current.T('More...'), _id='moreLatestBtn',
					_onclick="ajax('%s', ['qyThemaSelect', 'maxArticles'], 'lastRecommendations')"%(URL('articles', 'last_recomms', vars=myVarsNext, user_signature=True)),
					_class='btn btn-default'+moreState, _style='margin-left:8px; margin-bottom:8px;'
				),
				A(current.T('See all recommendations'), _href=URL('articles', 'all_recommended_articles'), _class='btn btn-default', _style='margin-left:32px; margin-bottom:8px;'),
				_style='text-align:center;'
			),
			_class='pci-lastArticles-div',
		)