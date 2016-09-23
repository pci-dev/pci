# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import re
import copy

from gluon.contrib.markdown import WIKI
from common import *
from helper import *

# -------------------------------------------------------------------------
# This is a sample controller
# - index is the default action of any application
# - user is required for authentication and authorization
# - download is for downloading files uploaded in the db (does streaming)
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# app configuration made easy. Look inside private/appconfig.ini
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4



#def _mkViewArticleButton(row):
	#anchor = A(SPAN(T('View'), _class='buttontext btn btn-default'), _href=URL(c='default', f='under_consideration_one_article', args=[row.article_id], user_signature=True), _class='button')
	#return anchor


# Home page (public)
def index():
	form = mkSearchForm(auth, db, None)
	if form.process().accepted:
		redirect(URL('public','recommended_articles', user_signature=True, vars=request.post_vars))
	elif form.errors:
		response.flash = 'form has errors'
	
	return dict(
		message=T('Welcome to ')+myconf.take('app.name'),
		content= DIV(
					#SPAN(T("A free recommendation process of published and unpublished scientific papers in Evolutionary Biology based on peer reviews.")),
					HR(),
					H3(T("Search recommended articles"), _class="pci-searchTitle"),
			),
		form=form,
		panel=mkPanel(myconf, auth),
		shareable=True,
		myHelp=getHelp(request, auth, dbHelp, '#WelcomingMessage'),
	)



def user():
	"""
	exposes:
	http://..../[app]/default/user/login
	http://..../[app]/default/user/logout
	http://..../[app]/default/user/register
	http://..../[app]/default/user/profile
	http://..../[app]/default/user/retrieve_password
	http://..../[app]/default/user/change_password
	http://..../[app]/default/user/bulk_register
	use @auth.requires_login()
		@auth.requires_membership('group name')
		@auth.requires_permission('read','table name',record_id)
	to decorate functions that need access control
	also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
	"""
	myMessage = T('Log In')
	db.auth_user.registration_key.writable = False
	db.auth_user.registration_key.readable = False
	response.view='default/index.html'
	return dict(
		message = myMessage,
		form=auth(),
		panel='',
		myHelp=getHelp(request, auth, dbHelp, '#LogIn'),
	)


@cache.action()
def download():
	"""
	allows downloading of uploaded files
	http://..../[app]/default/download/[filename]
	"""
	return response.download(request, db)


def call():
	"""
	exposes services. for example:
	http://..../[app]/default/call/jsonrpc
	decorate with @services.jsonrpc the functions to expose
	supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
	"""
	return service()



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
	response.view='default/recommLayout.html'
	return dict(grid=grid, 
			 myTitle=T('Suggested recommenders'),
			 myHelp=getHelp(request, auth, dbHelp, '#SuggestedRecommenders'),
			)
	


@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager') or auth.has_membership(role='administrator'))
def under_consideration_one_article():
	db.t_articles._id.readable = False
	record = db.t_articles(request.args(0))
	if record:
		form = SQLFORM(db.t_articles, record, readonly=True)
	else:
		form = None
	response.view='default/myLayout.html'
	return dict(form=form, 
			 myTitle=T('Article'),
			 myHelp=getHelp(request, auth, dbHelp, '#ViewArticleUnderConsideration'),
			)



#@auth.requires_login()
#def under_review_one_article():
	##WARNING: security hole --> check reviewer or recommender (etc.) attribution
	#db.t_articles._id.readable = False
	#record = db.t_articles(request.args(0))
	#if record:
		#form = SQLFORM(db.t_articles, record, readonly=True)
	#else:
		#form = None
	#response.view='default/myLayout.html'
	#return dict(form=form, 
			 #myTitle=T('Reviewed article'),
			 #myHelp=getHelp(request, auth, dbHelp, '#ViewArticleUnderReview'),
			 #)



