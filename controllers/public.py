# -*- coding: utf-8 -*-

import re
import copy

from gluon.contrib.markdown import WIKI
from common import *

# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4



# Recommended articles search & list (public)
def recommended_articles():
	# We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
	temp_db = DAL('sqlite:memory')
	qy_art = temp_db.define_table('qy_art',
		Field('id', type='integer'),
		Field('num', type='integer'),
		Field('score', type='double', label=T('Score'), default=0),
		Field('title', type='text', label=T('Title')),
		Field('authors', type='text', label=T('Authors')),
		Field('article_source', type='string', label=T('Source')),
		Field('doi', type='string', label=T('DOI')),
		Field('abstract', type='text', label=T('Abstract')),
		Field('upload_timestamp', type='date', default=request.now, label=T('Submission date/time')),
		Field('thematics', type='string', length=1024, label=T('Thematic fields')),
		Field('keywords', type='text', label=T('Keywords')),
		Field('auto_nb_recommendations', type='integer', label=T('Number of recommendations'), default=0),
		Field('status', type='string', length=50, default='Pending', label=T('Status')),
		Field('last_status_change', type='date', default=request.now, label=T('Recommendation date')),
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
	filtered = db.executesql('SELECT * FROM search_articles(%s, %s, %s, %s);', placeholders=[qyTF, qyKwArr, 'Recommended', trgmLimit], as_dict=True)
	for fr in filtered:
		qy_art.insert(**fr)
	temp_db.qy_art._id.readable = False
	temp_db.qy_art.auto_nb_recommendations.readable = False
	temp_db.qy_art.status.readable = False
	#temp_db.qy_art.title.readable = False
	temp_db.qy_art.title.represent = lambda text, row: mkArticleCell(auth, db, row)
	temp_db.qy_art.authors.readable = False
	temp_db.qy_art.keywords.readable = False
	temp_db.qy_art.thematics.readable = False
	temp_db.qy_art.article_source.readable = False
	temp_db.qy_art.upload_timestamp.readable = False
	temp_db.qy_art.doi.readable = False
	#temp_db.qy_art.doi.represent = lambda text, row: mkDOI(text)
	temp_db.qy_art.abstract.represent=lambda text, row: WIKI(text[:700]+'...') if len(text or '')>500 else WIKI(text or '')
	temp_db.qy_art.title.label = T('Article')
	grid = SQLFORM.grid(temp_db.qy_art
		,searchable=False,editable=False,deletable=False,create=False,details=False
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,links=[
			dict(header='', body=lambda row: A(SPAN(T('View'), _class='buttontext btn btn-success'), _href=URL(c='public', f='recommendations', vars=dict(articleId=row.id), user_signature=True), _target='blank', _class='button')),
		]
		,orderby=temp_db.qy_art.num
		,args=request.args
	)
	response.view='default/recommended_articles.html'
	return dict(grid=grid, searchForm=searchForm, myTitle=H1(T('Recommended Articles')), shareable=True)





# Recommendations of an article (public)
def recommendations():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.status != 'Recommended':
		raise HTTP(403, "403: "+T('Forbidden access')) # Forbidden access

	myContents = mkRecommendedArticle(auth, db, art, printable)
	myContents.append(HR())
	
	if printable:
		myTitle=H1(myconf.take('app.name')+' '+T('Recommended Article'), _class='pci-recommendation-title-printable')
		myAcceptBtn = ''
		response.view='default/recommended_article_printable.html'
	else:
		myTitle=H1(myconf.take('app.name')+' '+T('Recommended Article'), _class='pci-recommendation-title')
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



def managers():
	query = db((db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role == 'manager'))
	db.auth_user.uploaded_picture.readable = False
	grid = SQLFORM.grid( query
		,editable=False,deletable=False,create=False,details=False,searchable=False
		,maxtextlength=250,paginate=100
		,csv=csv,exportclasses=expClass
		,fields=[db.auth_user.uploaded_picture, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.laboratory, db.auth_user.institution, db.auth_user.city, db.auth_user.country]
		,links=[
				dict(header=T('Picture'), body=lambda row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100))),
		]
	)
	content = SPAN(T('Send an e-mail to managing board:')+' ', A(myconf.take('contacts.managers'), _href='mailto:%s' % myconf.take('contacts.managers')))
	response.view='default/myLayout.html'
	return dict(grid=grid, myTitle=T('Managing board'), content=content)






def recommenders():
	# We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
	temp_db = DAL('sqlite:memory')
	qy_recomm = temp_db.define_table('qy_recomm',
		Field('id', type='integer'),
		Field('num', type='integer'),
		Field('score', type='double', label=T('Score'), default=0),
		#Field('user_title', type='string', length=10, label=T('Title')),
		Field('first_name', type='string', length=128, label=T('First name')),
		Field('last_name', type='string', length=128, label=T('Last name')),
		Field('email', type='string', length=128, label=T('email')),
		Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
		Field('city', type='string', label=T('City')),
		Field('country', type='string', label=T('Country')),
		Field('laboratory', type='string', label=T('Laboratory')),
		Field('institution', type='string', label=T('Institution')),
		Field('thematics', type='list:string', label=T('Thematic fields')),
	)
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
	qyKwArr = qyKw.split(' ')
	searchForm =  mkSearchForm(auth, db, myVars)
	filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s);', placeholders=[qyTF, qyKwArr], as_dict=True)
	for fr in filtered:
		qy_recomm.insert(**fr)
			
	temp_db.qy_recomm._id.readable = False
	temp_db.qy_recomm.uploaded_picture.readable = False
	links = [
				dict(header=T('Picture'), body=lambda row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100)))
		]
	grid = SQLFORM.grid( qy_recomm
		,editable = False,deletable = False,create = False,details=False,searchable=False
		,maxtextlength=250,paginate=100
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_recomm.num, temp_db.qy_recomm.score, temp_db.qy_recomm.uploaded_picture, temp_db.qy_recomm.first_name, temp_db.qy_recomm.last_name, temp_db.qy_recomm.laboratory, temp_db.qy_recomm.institution, temp_db.qy_recomm.city, temp_db.qy_recomm.country, temp_db.qy_recomm.thematics]
		,links=links
		,orderby=temp_db.qy_recomm.num
		,args=request.args
	)
	response.view='default/recommenders.html'
	return dict(searchForm=searchForm, grid=grid, myTitle=T('Recommendation board'))


