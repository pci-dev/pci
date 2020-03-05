# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import re
import copy

from gluon.contrib.markdown import WIKI
from app_modules.common import *
from app_modules.helper import *
from gluon.utils import web2py_uuid

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


def loading():
	return DIV(IMG(_alt='Loading...', _src=URL(c='static', f='images/loading.gif')), _id="loading", _style='text-align:center;')



# Home page (public)
def index():
	response.view='default/index.html'

	#NOTE: do not delete: kept for later use
	#thematics = db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword)
	#options = [OPTION('--- All thematic fields ---', _value='')]
	#for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
		#options.append(OPTION(thema.keyword, _value=thema.keyword))
	
	myPanel = []
	tweeterAcc = myconf.get('social.tweeter')
	tweetHash = myconf.get('social.tweethash')
	tweeterId = myconf.get('social.tweeter_id')
	if tweeterAcc:
		myPanel.append(XML("""<a class="twitter-timeline" href="https://twitter.com/%(tweeterAcc)s">Tweets by %(tweeterAcc)s</a> 
			<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
			""" % locals() ) 
		)
	#if tweetHash and tweeterId:
		#myPanel.append(DIV(XML('<a class="twitter-timeline"  href="https://twitter.com/hashtag/%(tweetHash)s" data-widget-id="%(tweeterId)s">Tweets about #%(tweeterAcc)s</a><script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?\'http\':\'https\'; if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+"://platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);} }(document,"script","twitter-wjs");</script>' % locals() ), _class='tweeterPanel'))
		
	nbMax = db( 
			  (db.t_articles.status=='Recommended') 
			& (db.t_recommendations.article_id==db.t_articles.id) 
			& (db.t_recommendations.recommendation_state=='Recommended')
		).count()
	myVars = copy.deepcopy(request.vars)
	myVars['maxArticles'] = (myVars['maxArticles'] or 10)
	myVarsNext = copy.deepcopy(myVars)
	myVarsNext['maxArticles'] = myVarsNext['maxArticles']+10

	form = FORM (
				H3( T('Latest recommendations'), 
					A(SPAN(
						IMG(_alt='rss', _src=URL(c='static', f='images/rss.png'), _style='margin-right:8px;'), 
					), _href=URL('about', 'rss_info'), _class='btn btn-default pci-rss-btn', _style='float:right;')
				),
				DIV( loading(), _id='lastRecommendations', ),
			)
	myScript = SCRIPT("""window.onload=function() {
	ajax('%s', ['qyThemaSelect', 'maxArticles'], 'lastRecommendations');
	if ($.cookie('PCiHideHelp') == 'On') $('DIV.pci-helptext').hide(); else $('DIV.pci-helptext').show();
}""" % (URL('articles', 'last_recomms', vars=myVars, user_signature=True)), 
				_type='text/javascript'
		)
	
	#if auth.user_id:
		#theUser = db.auth_user[auth.user_id]
		#if theUser.ethical_code_approved is False:
			#redirect(URL('about','ethics'))

	if request.user_agent().is_mobile:
		return dict(
			myTitle=getTitle(request, auth, db, '#HomeTitle'),
			myText=getText(request, auth, db, '#HomeInfo'),
			myHelp=getHelp(request, auth, db, '#Home'),
			form=form,
			myBottomPanel=DIV(myPanel, _class='tweeterBottomPanel'),
			shareable=True,
			script=myScript,
		)
	else:
		return dict(
			myTitle=getTitle(request, auth, db, '#HomeTitle'),
			myText=getText(request, auth, db, '#HomeInfo'),
			myHelp=getHelp(request, auth, db, '#Home'),
			form=form,
			panel=DIV(myPanel, _class='tweeterPanel'),
			shareable=True,
			script=myScript,
		)



def user():
	response.view='default/myLayoutBot.html'

	# """
	# exposes:
	# http://..../[app]/default/user/login
	# http://..../[app]/default/user/logout
	# http://..../[app]/default/user/register
	# http://..../[app]/default/user/profile
	# http://..../[app]/default/user/retrieve_password
	# http://..../[app]/default/user/change_password
	# http://..../[app]/default/user/bulk_register
	# use @auth.requires_login()
	# 	@auth.requires_membership('group name')
	# 	@auth.requires_permission('read','table name',record_id)
	# to decorate functions that need access control
	# also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
	# """
	
	if '_next' in request.vars:
		suite = request.vars['_next']
		if len(suite)<4:
			suite = None
	else:
		suite = None
	if isinstance(suite, list):
		suite = suite[1]
	
	if 'key' in request.vars:
		vkey = request.vars['key']
	else:
		vkey = None
	if isinstance(vkey, list):
		vkey = vkey[1]
	if (vkey==''):
		vkey = None
	
	if '_formkey' in request.vars:
		fkey = request.vars['_formkey']
	else:
		fkey = None
	if isinstance(fkey, list):
		fkey = fkey[1]
	if (fkey==''):
		fkey = None
	
	myHelp = ''
	myTitle = ''
	myText = ''
	myBottomText = ''
	myContent = ''
	myScript = ''
	#print(request.args)
	
	db.auth_user.registration_key.writable = False
	db.auth_user.registration_key.readable = False
	if request.args and len(request.args)>0:
		#print(request.args)
		
		if request.args[0] == 'login':
			myHelp = getHelp(request, auth, db, '#LogIn')
			myTitle = getTitle(request, auth, db, '#LogInTitle')
			myText = getText(request, auth, db, '#LogInText')
			myContent = DIV(A(T('Lost password?'), _href=URL(c='default', f='user', args=['request_reset_password']), _class="buttontext btn btn-info"), _class="pci-infotextbox")
			if suite:
				auth.settings.login_next = suite
		elif request.args[0] == 'register':
			myHelp = getHelp(request, auth, db, '#CreateAccount')
			myTitle = getTitle(request, auth, db, '#CreateAccountTitle')
			myText = getText(request, auth, db, '#ProfileText')
			myBottomText = getText(request, auth, db, '#ProfileBottomText')
			db.auth_user.ethical_code_approved.requires=IS_IN_SET(['on'])
			if suite:
				auth.settings.register_next = suite
		elif request.args[0] == 'profile':
			myHelp = getHelp(request, auth, db, '#Profile')
			myTitle = getTitle(request, auth, db, '#ProfileTitle')
			myText = getText(request, auth, db, '#ProfileText')
			myBottomText = getText(request, auth, db, '#ProfileBottomText')
			if suite:
				auth.settings.profile_next = suite
		
		elif request.args[0] == 'request_reset_password':
			myHelp = getHelp(request, auth, db, '#ResetPassword')
			myTitle = getTitle(request, auth, db, '#ResetPasswordTitle')
			myText = getText(request, auth, db, '#ResetPasswordText')
			user = db(db.auth_user.email==request.vars['email']).select().last()
			if ((fkey is not None) and (user is not None)):
				reset_password_key = str(int(time.time())) + '-' + web2py_uuid()
				user.update_record(reset_password_key = reset_password_key)
				do_send_email_to_reset_password(session, auth, db, user.id)
				if suite:
					redirect(URL('default', 'index', vars=dict(_next=suite))) # squeeze normal functions
				else:
					redirect(URL('default', 'index')) # squeeze normal functions
			if suite:
				auth.settings.request_reset_password_next = suite
			
		elif request.args[0] == 'reset_password':
			myHelp = getHelp(request, auth, db, '#ResetPassword')
			myTitle = getTitle(request, auth, db, '#ResetPasswordTitle')
			myText = getText(request, auth, db, '#ResetPasswordText')
			user = db(db.auth_user.reset_password_key==vkey).select().last()
			if ((vkey is not None) and (suite is not None) and (user is None)):
				redirect(suite)
			if suite:
				auth.settings.reset_password_next = suite

	form = auth()
		
	return dict(
		myTitle=myTitle,
		myText=myText,
		myBottomText=myBottomText,
		myHelp=myHelp,
		content=myContent,
		form=form,
	)


# (gab) is this used ?
@cache.action()
def download():
	"""
	allows downloading of uploaded files
	http://..../[app]/default/download/[filename]
	"""
	return response.download(request, db)



# (gab) is this used ?
def call():
	"""
	exposes services. for example:
	http://..../[app]/default/call/jsonrpc
	decorate with @services.jsonrpc the functions to expose
	supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
	"""
	return service()
