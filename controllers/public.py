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
		elif (re.match('^qy_', myVar)) and not('qyThemaSelect' in myVars):
			qyTF.append(re.sub(r'^qy_', '', myVar))
			myVars2[myVar] = myValue
	qyKwArr = qyKw.split(' ')

	searchForm =  mkSearchForm(auth, db, myVars2)
	filtered = db.executesql('SELECT * FROM search_articles(%s, %s, %s, %s);', placeholders=[qyTF, qyKwArr, 'Recommended', trgmLimit], as_dict=True)
	n = len(filtered)
	myRows = []
	for row in filtered:
		r = mkArticleRow(auth, db, Storage(row), withScore=True, withDate=True)
		print r
		myRows.append(r)
	grid = DIV(DIV(
				DIV(T('%s records found')%(n), _class='pci-nResults'),
				TABLE(
					THEAD(TR(TH(T('Score')), TH(T('Article')), TH(T('Recommended')), _class='pci-lastArticles-row')),
					TBODY(myRows),
				_class='web2py_grid pci-lastArticles-table'), 
			_class='pci-lastArticles-div'), _class='searchRecommendationsDiv')
	response.view='default/myLayout.html'
	return dict(
				panel=mkPanel(myconf, auth, inSearch=True),
				grid=grid, 
				searchForm=searchForm, 
				myTitle=T('Recommended Articles'), 
				#myBackButton = mkBackButton(),
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
			query = db( (db.t_articles.status=='Recommended') & (db.t_articles.thematics.contains(thema)) ).select(db.t_articles.ALL, limitby=(0, maxArticles), orderby=~db.t_articles.last_status_change)
	if query == None:
		query = db( (db.t_articles.status=='Recommended') ).select(db.t_articles.ALL, limitby=(0, maxArticles), orderby=~db.t_articles.last_status_change)
	#n = len(query)
	myRows = []
	for row in query:
		myRows.append(mkArticleRow(auth, db, Storage(row), withDate=True))
	return DIV(
			#DIV(T('%s records found')%(n), _class='pci-nResults'),
			TABLE(TBODY(myRows), _class='web2py_grid pci-lastArticles-table'), 
			_class='pci-lastArticles-div',
		)




# Recommendations of an article (public)
def recommendations():
	printable = 'printable' in request.vars
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

	myContents = mkFeaturedArticle(auth, db, art, printable)
	myContents.append(HR())
	
	if printable:
		myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png'), _height="100"),
				DIV(
					DIV(T('Recommended Article'), _class='pci-ArticleText printable'),
					_class='pci-ArticleHeaderIn recommended printable'
				))
		myUpperBtn = ''
		response.view='default/recommended_article_printable.html' #OK
	else:
		myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png'), _height="100"),
				DIV(
					DIV(I(myconf.take('app.longname')+': ')+T('Recommended Article'), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn recommended'
				))
		myUpperBtn = A(SPAN(T('Printable page'), _class='buttontext btn btn-info'), 
			_href=URL(c='public', f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
			_class='button')
		response.view='default/recommended_articles.html' #OK
	
	response.title = (art.title or myconf.take('app.longname'))
	return dict(
				statusTitle=myTitle,
				myContents=myContents,
				myUpperBtn=myUpperBtn,
				myCloseButton=mkCloseButton(),
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
		myRows.append(mkUserRow(Storage(fr), withMail=False))
	grid = TABLE(
			THEAD(TR(TH(T('First & Last names')), TH(T('Lab, institution, city, country')), TH(T('Picture')) )), 
			myRows, 
			_class="web2py_grid pci-UsersTable")
	
	content = SPAN(T('Send an e-mail to managing board:')+' ', A(myconf.take('contacts.managers'), _href='mailto:%s' % myconf.take('contacts.managers')))
	#response.view='default/myLayout.html' #TODO
	response.view='default/recommenders.html'
	return dict(
				myHelp=getHelp(request, auth, dbHelp, '#PublicManagingBoardDescription'),
				myTitle=T('Managing board'), 
				mkBackButton = mkBackButton(),
				#searchForm=searchForm, 
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
			elif (re.match('^qy_', myVar)):
				qyTF.append(re.sub(r'^qy_', '', myVar))
		qyKwArr = qyKw.split(' ')
		filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s);', placeholders=[qyTF, qyKwArr], as_dict=True)
		myRows = []
		for fr in filtered:
			myRows.append(mkUserRow(Storage(fr), withMail=False))
		grid = TABLE(
			THEAD(TR(TH(T('First & Last names')), TH(T('Lab, institution, city, country')), TH(T('Picture')) )), 
			myRows, 
			_class="web2py_grid pci-UsersTable")

		## We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
		#temp_db = DAL('sqlite:memory')
		#qy_recomm = temp_db.define_table('qy_recomm',
			#Field('id', type='integer'),
			#Field('num', type='integer'),
			#Field('score', type='double', label=T('Score'), default=0),
			#Field('first_name', type='string', length=128, label=T('First name')),
			#Field('last_name', type='string', length=128, label=T('Last name')),
			#Field('email', type='string', length=128, label=T('email')),
			#Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
			#Field('city', type='string', label=T('City')),
			#Field('country', type='string', label=T('Country')),
			#Field('laboratory', type='string', label=T('Laboratory')),
			#Field('institution', type='string', label=T('Institution')),
			#Field('thematics', type='list:string', label=T('Thematic fields')),
		#)
		#for fr in filtered:
			#qy_recomm.insert(**fr)
		#temp_db.qy_recomm._id.readable = False
		#temp_db.qy_recomm.uploaded_picture.represent = lambda text, row: (IMG(_src=URL('default', 'download', args=text), _class='pci-userPicture')) if (text is not None and text != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _class='pci-userPicture'))
		#grid = SQLFORM.grid( qy_recomm
							#,editable = False,deletable = False,create = False,details=False,searchable=False
							#,maxtextlength=250,paginate=1
							#,csv=csv,exportclasses=expClass
							#,fields=[temp_db.qy_recomm.num, temp_db.qy_recomm.score, temp_db.qy_recomm.first_name, temp_db.qy_recomm.last_name, temp_db.qy_recomm.laboratory, temp_db.qy_recomm.institution, temp_db.qy_recomm.city, temp_db.qy_recomm.country, temp_db.qy_recomm.thematics, temp_db.qy_recomm.uploaded_picture]
							#,orderby=temp_db.qy_recomm.num
							#,args=request.args
							#,user_signature=True
		#)
	#else:
		#grid = ''
	response.view='default/myLayout.html'
	resu = dict(
				myHelp=getHelp(request, auth, dbHelp, '#PublicRecommendationBoardDescription'),
				myTitle=T('Recommendation board'),
				myBackButton = mkBackButton(),
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
				#myHelp=getHelp(request, auth, dbHelp, '#PublicRecommendationBoardDescription'),
				myTitle=T('User card'),
				myBackButton = mkBackButton(),
				#searchForm=searchForm, 
				#grid=grid, 
				myText = myContents
			)
	return resu


