# -*- coding: utf-8 -*-

import re
import copy

from gluon.storage import Storage
from gluon.contrib.markdown import WIKI
from common import *
from helper import *
from datetime import datetime, timedelta

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4



# Recommended articles search & list (public)
def recommended_articles():
	myVars = request.vars
	qyKw = ''
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
		elif (myVar == 'qyThemaSelect') and myValue:
			qyTF=[myValue]
			myVars2['qy_'+myValue] = True
		elif (re.match('^qy_', myVar) and myValue=='on' and not('qyThemaSelect' in myVars)):
			qyTF.append(re.sub(r'^qy_', '', myVar))
			myVars2[myVar] = myValue
	qyKwArr = qyKw.split(' ')

	searchForm =  mkSearchForm(auth, db, myVars2)
	filtered = db.executesql('SELECT * FROM search_articles(%s, %s, %s, %s, %s);', placeholders=[qyTF, qyKwArr, 'Recommended', trgmLimit, True], as_dict=True)
	n = len(filtered)
	myRows = []
	for row in filtered:
		r = mkRecommArticleRow(auth, db, Storage(row), withImg=True, withScore=False, withDate=True)
		if r:
			myRows.append(r)
	grid = DIV(DIV(
				DIV(T('%s records found')%(n), _class='pci-nResults'),
				TABLE(
					#THEAD(TR(TH(T('Score')), TH(T('Recommendation')), TH(T('Article')), _class='pci-lastArticles-row')),
					TBODY(myRows),
				_class='web2py_grid pci-lastArticles-table'), 
			_class='pci-lastArticles-div'), _class='searchRecommendationsDiv')
	response.view='default/myLayout.html'
	return dict(
				grid=grid, 
				searchForm=searchForm, 
				myTitle=getTitle(request, auth, db, '#RecommendedArticlesTitle'),
				myText=getText(request, auth, db, '#RecommendedArticlesText'),
				myHelp=getHelp(request, auth, db, '#RecommendedArticles'),
				shareable=True,
			)



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
		return DIV(I(T('Soon...')))
	
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
					_onclick="ajax('%s', ['qyThemaSelect', 'maxArticles'], 'lastRecommendations')"%(URL('public', 'last_recomms', vars=myVarsNext, user_signature=True)),
					_class='btn btn-default'+moreState, _style='margin-left:8px; margin-bottom:8px;'
				),
				_style='text-align:center;'
			),
			_class='pci-lastArticles-div',
		)



# Recommendations of an article (public)
def rec():
	if 'printable' in request.vars and request.vars['printable']=='True':
		printable = True
	else:
		printable = False
	if 'reviews' in request.vars and request.vars['reviews']=='True':
		with_reviews = True
	else:
		with_reviews = False
	if 'comments' in request.vars and request.vars['comments']=='True':
		with_comments = True
	else:
		with_comments = False
		
	if ('articleId' in request.vars):
		articleId = request.vars['articleId']
	elif ('id' in request.vars):
		articleId = request.vars['id']
	else:
		session.flash = T('Unavailable')
		redirect(URL('public', 'recommended_articles', user_signature=True))
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('public', 'recommended_articles', user_signature=True))
	# NOTE: security hole possible by articleId injection: Enforced checkings below.
	elif art.status != 'Recommended':
		session.flash = T('Forbidden access')
		redirect(URL('public', 'recommended_articles', user_signature=True))

	myFeaturedRecommendation = mkFeaturedRecommendation(auth, db, art, printable=printable, with_reviews=with_reviews, with_comments=with_comments)
	myContents = myFeaturedRecommendation['myContents']
	nbReviews = myFeaturedRecommendation['nbReviews']
	pdf = myFeaturedRecommendation['pdf']
	myMeta = myFeaturedRecommendation['myMeta']
	
	if printable:
		myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png'), _height="100"))
		myUpperBtn = ''
		response.view='default/recommended_article_printable.html' #OK
	else:
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
						_href=URL(c='public', f='rec', vars=dict(articleId=articleId, printable=True, reviews=with_reviews, comments=with_comments), user_signature=True),
						_class='button'),
						(A(SPAN(btnSHRtxt, _class='buttontext btn btn-default  pci-ArticleTopButton'), 
							_href=URL(c='public', f='rec', vars=dict(articleId=articleId, printable=printable, reviews=not(with_reviews), comments=with_comments), user_signature=True),
							_class='button')) if (nbReviews>0) else '',
						(A(SPAN(btnSHCtxt, _class='buttontext btn btn-default  pci-ArticleTopButton'), 
							_href=URL(c='public', f='rec', vars=dict(articleId=articleId, printable=printable, reviews=with_reviews, comments=not(with_comments)), user_signature=True),
							_class='button')),
						mkCloseButton(),
						_class="pci-ArticleTopButtons",
					)
		myTitle=None
		response.view='default/recommended_articles.html' #OK
	
	finalRecomm = db( (db.t_recommendations.article_id==art.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=db.t_recommendations.id).last()
	if finalRecomm:
		response.title = (finalRecomm.recommendation_title or myconf.take('app.longname'))
	else:
		response.title = myconf.take('app.longname')
	if len(response.title)>64:
		response.title = response.title[:64]+'...'
	if len(myMeta)>0:
		for k in myMeta:
			if type(myMeta[k]) is list:
				response.meta[k] = ' ; '.join(myMeta[k]) # syntax as in: http://dublincore.org/documents/2000/07/16/usageguide/#usinghtml
			else:
				response.meta[k] = myMeta[k]
	return dict(
				statusTitle=myTitle,
				myContents=myContents,
				myUpperBtn=myUpperBtn,
				shareButtons=True,
			)



def managers():
	query = db( (db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role.belongs('manager', 'administrator')) ).select(db.auth_user.ALL, distinct=db.auth_user.last_name|db.auth_user.id, orderby=db.auth_user.last_name|db.auth_user.id)
	myRows = []
	for user in query:
		myRows.append(mkUserRow(auth, db, user, withMail=False, withRoles=True, withPicture=True))
	grid = DIV(
			TABLE(
			THEAD(TR(
					TH(T('')), 
					TH(T('Name')), 
					TH(T('Affiliation')), 
					TH(T('Roles'))
				)), 
			myRows, 
			_class="web2py_grid pci-UsersTable")
		)
	response.view='default/myLayout.html'
	return dict(
				#mkBackButton = mkBackButton(),
				myTitle=getTitle(request, auth, db, '#PublicManagingBoardTitle'),
				myText=getText(request, auth, db, '#PublicManagingBoardText'),
				myHelp=getHelp(request, auth, db, '#PublicManagingBoardDescription'),
				grid=grid, 
			)




def recommenders():
	myVars = request.vars
	#print(request.vars)
	qyKw = ''
	qyTF = []
	excludeList = []
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (re.match('^qy_', myVar) and myValue == 'on'):
			qyTF.append(re.sub(r'^qy_', '', myVar))
	qyKwArr = qyKw.split(' ')
	searchForm = mkSearchForm(auth, db, myVars)
	#print(qyTF, qyKwArr)
	if searchForm.process(keepvalues=True).accepted:
		response.flash = None
	else:
		qyTF = []
		for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
			qyTF.append(thema.keyword)
	filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s, %s) ORDER BY last_name, first_name;', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
	myRows = []
	my1 = ''
	myIdx = []
	nbRecomm = len(filtered)
	for fr in filtered:
		sfr = Storage(fr)
		if sfr.last_name[0].upper() != my1:
			my1 = sfr.last_name[0].upper()
			myRows.append(TR(TD( my1, A(_name=my1)), TD(''), _class='pci-capitals'))
			myIdx.append(A(my1, _href='#%s'%my1, _style='margin-right:20px;'))
		myRows.append(mkUserRow(auth, db, sfr, withMail=False, withRoles=False, withPicture=False))
	grid = DIV(
			HR(),
			DIV(nbRecomm + T(' recommenders selected'), _style='text-align:center; margin-bottom:20px;'),
			LABEL(T('Quick access: '), _style='margin-right:20px;'), SPAN(myIdx, _class='pci-capitals'),
			HR(),
			TABLE(
				THEAD(TR(TH(T('Name')), TH(T('Affiliation')) )), 
				TBODY(myRows), 
				_class="web2py_grid pci-UsersTable"
			)
		)
	response.view='default/myLayout.html'
	resu = dict(
				myTitle=getTitle(request, auth, db, '#PublicRecommendationBoardTitle'),
				myText=getText(request, auth, db, '#PublicRecommendationBoardText'),
				myHelp=getHelp(request, auth, db, '#PublicRecommendationBoardDescription'),
				searchForm=searchForm, 
				grid=grid, 
			)
	return resu




def viewUserCard():
	myContents = ''
	if not('userId' in request.vars):
		session.flash = T('Unavailable')
		redirect(request.env.http_referer)
	else:
		userId = request.vars['userId']
		hasRoles = (db( (db.auth_membership.user_id==userId) ).count() > 0) or auth.has_membership(role='administrator') or auth.has_membership(role='developper')
		if not(hasRoles):
			session.flash = T('Unavailable')
			redirect(request.env.http_referer)
		else:
			myContents = mkUserCard(auth, db, userId, withMail=False)
	response.view='default/info.html'
	resu = dict(
				myHelp=getHelp(request, auth, db, '#PublicUserCard'),
				myTitle=getTitle(request, auth, db, '#PublicUserCardTitle'),
				myText = myContents
			)
	return resu


# sub function called by cache.ram below
def _rss_cacher(maxArticles):
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	title=myconf.take('app.longname')
	contact=myconf.take('contacts.managers')
	managingEditor='%(contact)s (%(title)s contact)' % locals()
	description=T('Articles recommended by ')+myconf.take('app.description')
	favicon = XML(URL(c='static', f='images/favicon.png', scheme=scheme, host=host, port=port))
	#link = URL(c='default', f='index', scheme=scheme, host=host, port=port)
	#thisLink = URL(c='public', f='rss', scheme=scheme, host=host, port=port)
	link = URL(c='public', f='rss', scheme=scheme, host=host, port=port)

	query = db( 
					(db.t_articles.status=='Recommended') 
				  & (db.t_recommendations.article_id==db.t_articles.id) 
				  & (db.t_recommendations.recommendation_state=='Recommended')
			).iterselect(db.t_articles.id, db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.doi, db.t_articles.picture_rights_ok, db.t_articles.uploaded_picture, db.t_articles.abstract, db.t_articles.upload_timestamp, db.t_articles.user_id, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.already_published, db.t_articles.i_am_an_author, db.t_articles.is_not_reviewed_elsewhere, db.t_articles.auto_nb_recommendations, limitby=(0, maxArticles), orderby=~db.t_articles.last_status_change)
	myRows = []
	most_recent = None
	for row in query:
		try:
			r = mkRecommArticleRss(auth, db, row)
			if r:
				myRows.append(r)
				if most_recent is None or row.last_status_change > most_recent:
					most_recent = row.last_status_change
		except Exception, e:
			#raise e
			pass
	if len(myRows) == 0:
		myRows.append(dict(title=T(u'Coming soon..'), link=link, description=T(u'patience!')))
	
	return dict(
			title=title,
			link=link,
			#thisLink=thisLink,
			managingEditor=managingEditor,
			created_on=most_recent,
			description=description,
			image=favicon.xml(),
			entries=myRows,
		)



#WARNING - DO NOT ACTIVATE cache.action 
def rss():
	#maxArticles = int(myconf.take('rss.number') or "20")
	#timeExpire  = int(myconf.take('rss.cache') or "60")
	maxArticles = 20
	timeExpire = 60
	response.headers['Content-Type'] = 'application/rss+xml'
	response.view='rsslayout.rss'
	d = cache.ram('rss_content', lambda: _rss_cacher(maxArticles), time_expire=timeExpire)
	return(d)

