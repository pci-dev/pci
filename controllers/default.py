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
	#durationDays = 30
	maxArticles = 10
	thematics = db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword)
	options = [OPTION('--- All thematic fields ---', _value='')]
	for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
		options.append(OPTION(thema.keyword, _value=thema.keyword))
	form = FORM (
				LABEL(T('Last %s recommendations in:')%(maxArticles)), 
				SELECT(options, _name='qyThemaSelect', 
					_onChange="ajax('%s', ['qyThemaSelect'], 'lastRecommendations')"%(URL('public', 'last_recomms', vars=dict(maxArticles=maxArticles), user_signature=True))),
			)
	
	return dict(
		message=T('Welcome to ')+myconf.take('app.longname'),
		form=form,
		script=SCRIPT("window.onload=ajax('%s', ['qyThemaSelect'], 'lastRecommendations');"%(URL('public', 'last_recomms', vars=dict(maxArticles=maxArticles), user_signature=True)), _type='text/javascript'),
		panel=mkPanel(myconf, auth),
		shareable=True,
		#myHelp=getHelp(request, auth, dbHelp, '#WelcomingMessage'),
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



