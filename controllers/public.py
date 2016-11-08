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
				myTitle=getTitle(request, auth, dbHelp, '#RecommendedArticlesTitle'),
				myText=getText(request, auth, dbHelp, '#RecommendedArticlesText'),
				myHelp=getHelp(request, auth, dbHelp, '#RecommendedArticles'),
				shareable=True,
			)



def last_recomms():
	if 'maxArticles' in request.vars:
		maxArticles = int(request.vars['maxArticles'])
	else:
		maxArticles = 10
	query = None
	if 'qyThemaSelect' in request.vars:
		thema = request.vars['qyThemaSelect']
		if thema and len(thema)>0:
			query = db( 
					(db.t_articles.status=='Recommended') 
				  & (db.t_recommendations.article_id==db.t_articles.id) 
				  & (db.t_recommendations.recommendation_state=='Recommended')
				  & (db.t_articles.thematics.contains(thema)) 
				).iterselect(db.t_articles.id, db.t_articles.title, db.t_articles.authors, db.t_articles.article_source, db.t_articles.doi, db.t_articles.picture_rights_ok, db.t_articles.uploaded_picture, db.t_articles.abstract, db.t_articles.upload_timestamp, db.t_articles.user_id, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.already_published, db.t_articles.i_am_an_author, db.t_articles.is_not_reviewed_elsewhere, db.t_articles.auto_nb_recommendations, limitby=(0, maxArticles), orderby=~db.t_articles.last_status_change)
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
	return DIV(
			TABLE(
				TBODY(myRows), 
				_class='web2py_grid pci-lastArticles-table'), 
			_class='pci-lastArticles-div',
		)




# Recommendations of an article (public)
def recommendations():
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
		
	if not('articleId' in request.vars):
		session.flash = T('Unavailable')
		redirect(URL('public', 'recommended_articles', user_signature=True))
		#raise HTTP(404, "404: "+T('Malformed URL')) # Forbidden access
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('public', 'recommended_articles', user_signature=True))
		#raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	elif art.status != 'Recommended':
		session.flash = T('Forbidden access')
		redirect(URL('public', 'recommended_articles', user_signature=True))
		#raise HTTP(403, "403: "+T('Forbidden access')) # Forbidden access

	#myContents = mkFeaturedArticle(auth, db, art, printable)
	myFeaturedRecommendation = mkFeaturedRecommendation(auth, db, art, printable=printable, with_reviews=with_reviews, with_comments=with_comments)
	myContents = myFeaturedRecommendation['myContents']
	nbReviews = myFeaturedRecommendation['nbReviews']
	myContents.append(HR())
	
	if printable:
		myTitle=DIV(
				IMG(_src=URL(r=request,c='static',f='images/background.png'), _height="100"),
				DIV(
					DIV(T('Recommendation'), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn recommended printable'
				))
		myUpperBtn = ''
		response.view='default/recommended_article_printable.html' #OK
	else:
		myTitle=DIV(
				IMG(_src=URL(r=request,c='static',f='images/small-background.png'), _height="100"),
				DIV(
					DIV(I(T('Recommendation')), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn recommended'
				))
		if with_reviews:
			btnSHRtxt = T('Hide reviews')
		else:
			btnSHRtxt = T('Show reviews')
		if with_comments:
			btnSHCtxt = T('Hide user comments')
		else:
			btnSHCtxt = T('Show user comments')
		myUpperBtn = DIV(
						A(SPAN(T('Printable page'), _class='buttontext btn btn-info  pci-ArticleTopButton'), 
						_href=URL(c='public', f='recommendations', vars=dict(articleId=articleId, printable=True, reviews=with_reviews, comments=with_comments), user_signature=True),
						_class='button'),
						BR(),
						(A(SPAN(btnSHRtxt, _class='buttontext btn btn-default  pci-ArticleTopButton'), 
							_href=URL(c='public', f='recommendations', vars=dict(articleId=articleId, printable=printable, reviews=not(with_reviews), comments=with_comments), user_signature=True),
							_class='button')+BR()) if (nbReviews>0) else '',
						(A(SPAN(btnSHCtxt, _class='buttontext btn btn-default  pci-ArticleTopButton'), 
							_href=URL(c='public', f='recommendations', vars=dict(articleId=articleId, printable=printable, reviews=with_reviews, comments=not(with_comments)), user_signature=True),
							_class='button')+BR()),
						mkCloseButton(),
						_class="pci-ArticleTopButtons",
					)
		response.view='default/recommended_articles.html' #OK
	
	response.title = (art.title or myconf.take('app.longname'))
	return dict(
				statusTitle=myTitle,
				myContents=myContents,
				myUpperBtn=myUpperBtn,
				#myCloseButton=mkCloseButton(),
				shareable=True,
			)



def managers():
	query = db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == 'manager'))
	#db.auth_user.uploaded_picture.readable = False
	#grid = SQLFORM.grid( query
		#,editable=False,deletable=False,create=False,details=False,searchable=False
		#,maxtextlength=250,paginate=100
		#,csv=csv,exportclasses=expClass
		#,fields=[db.auth_user.uploaded_picture, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.laboratory, db.auth_user.institution, db.auth_user.city, db.auth_user.country]
		#,links=[
				#dict(header=T('Picture'), body=lambda row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100))),
		#]
	#)
	myRows = []
	for fr in query.select(db.auth_user.ALL):
		sfr = Storage(fr)
		if sfr.last_name[0] != my1:
			my1 = sfr.last_name[0]
			myRows.append(TR(TD(A(my1, _name=my1, _class='pci-capitals')), TD()))
			myIdx.append(A(my1, _href='#%s'%my1, _class='pci-capitals')+SPAN(' '))
		myRows.append(mkUserRow(sfr, withMail=False))
	grid = DIV(
			SPAN(myIdx),
			TABLE(
			THEAD(TR(TH(T('Name')), TH(T('Affiliation')) )), 
			myRows, 
			_class="web2py_grid pci-UsersTable")
		)
	#myRows.append(mkUserRow(Storage(fr), withMail=False))
	#grid = TABLE(
			#THEAD(TR(TH(T('Name')), TH(T('Affiliation')), TH(T('Picture')) )), 
			#myRows, 
			#_class="web2py_grid pci-UsersTable")
	
	content = SPAN(T('Send an e-mail to managing board:')+' ', A(myconf.take('contacts.managers'), _href='mailto:%s' % myconf.take('contacts.managers')))
	#response.view='default/myLayout.html' #TODO
	response.view='default/recommenders.html'
	return dict(
				mkBackButton = mkBackButton(),
				myTitle=getTitle(request, auth, dbHelp, '#PublicManagingBoardTitle'),
				myText=getText(request, auth, dbHelp, '#PublicManagingBoardText'),
				myHelp=getHelp(request, auth, dbHelp, '#PublicManagingBoardDescription'),
				content=content, 
				grid=grid, 
			)






def recommenders():
	searchForm = mkSearchForm(auth, db, request.vars)
	if searchForm.process(keepvalues=True).validate:
		response.flash = None
		myVars = searchForm.vars
		qyKw = ''
		qyTF = []
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
		filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s) ORDER BY last_name, first_name;', placeholders=[qyTF, qyKwArr], as_dict=True)
		myRows = []
		my1 = ''
		myIdx = []
		for fr in filtered:
			sfr = Storage(fr)
			if sfr.last_name[0].upper() != my1:
				my1 = sfr.last_name[0].upper()
				myRows.append(TR(TD( my1, A(_name=my1)), TD(''), _class='pci-capitals'))
				myIdx.append(A(my1, _href='#%s'%my1, _style='margin-right:20px;'))
			myRows.append(mkUserRow(sfr, withMail=False))
		grid = DIV(
				HR(),
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
				myTitle=getTitle(request, auth, dbHelp, '#PublicRecommendationBoardTitle'),
				myText=getText(request, auth, dbHelp, '#PublicRecommendationBoardText'),
				myHelp=getHelp(request, auth, dbHelp, '#PublicRecommendationBoardDescription'),
				searchForm=searchForm, 
				grid=grid, 
			)
	return resu




def viewUserCard():
	if not('userId' in request.vars):
		session.flash = T('Unavailable')
		redirect(request.env.http_referer)
	else:
		userId = request.vars['userId']
		hasRoles = db( (db.auth_membership.user_id==userId) ).count() > 0
		if not(hasRoles):
			session.flash = T('Unavailable')
			redirect(request.env.http_referer)
		else:
			myContents = mkUserCard(auth, db, userId, withMail=False)
	response.view='default/info.html'
	resu = dict(
				myHelp=getHelp(request, auth, dbHelp, '#PublicUserCard'),
				myTitle=getTitle(request, auth, dbHelp, '#PublicUserCardTitle'),
				myText = myContents
			)
	return resu


