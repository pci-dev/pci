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


# Home page (public)
def index():
	nbs = [
			OPTION('10', _value=10),
			OPTION('20', _value=20),
			OPTION('50', _value=50),
			OPTION('100', _value=100),
		]
	#NOTE: do not delete: kept for later use
	#thematics = db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword)
	#options = [OPTION('--- All thematic fields ---', _value='')]
	#for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
		#options.append(OPTION(thema.keyword, _value=thema.keyword))
	vars=dict(qyThemaSelect='')
	form = FORM (
				LABEL(T('Show')+' '),
				SELECT(nbs, _name='maxArticles',
					_onChange="ajax('%s', ['qyThemaSelect', 'maxArticles'], 'lastRecommendations')"%(URL('public', 'last_recomms', 
									vars=vars, 
									user_signature=True))
						, _style='margin-left:8px; margin-right:8px;'),
				LABEL(' '+T('last recommendations')+' '), 
				#NOTE: do not delete: kept for later use
				#LABEL(' '+T('last recommendations in:')+' '), 
				#SELECT(options, _name='qyThemaSelect', 
					#_onChange="ajax('%s', ['qyThemaSelect', 'maxArticles'], 'lastRecommendations')"%(URL('public', 'last_recomms', 
									#vars=vars, 
									#user_signature=True))),
			)
	
	return dict(
		myTitle=T('Welcome to ')+myconf.take('app.longname'),
		form=form,
		script=SCRIPT("window.onload=ajax('%s', ['qyThemaSelect', 'maxArticles'], 'lastRecommendations');"%(URL('public', 'last_recomms', 
											vars=vars, 
											user_signature=True)), _type='text/javascript'),
		panel=mkPanel(myconf, auth),
		shareable=True,
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



