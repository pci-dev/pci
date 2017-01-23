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


def loading():
	return DIV(IMG(_alt='Loading...', _src=URL(c='static', f='images/loading.gif')), _id="loading", _style='text-align:center;')

# Home page (public)
def index():
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
			<script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>""" 
			% locals() ) 
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
				H3(T('Latest recommendations')),
				DIV(
					loading(),
					_id='lastRecommendations',
				),
			)
	myScript = SCRIPT("""window.onload=function() {
	ajax('%s', ['qyThemaSelect', 'maxArticles'], 'lastRecommendations');
	if ($.cookie('PCiHideHelp') == 'On') $('DIV.pci-helptext').hide(); else $('DIV.pci-helptext').show();
}""" % (URL('public', 'last_recomms', vars=myVars, user_signature=True)), 
				_type='text/javascript'
		)
	response.view='default/index.html'
	if request.user_agent().is_mobile:
		return dict(
			smallSearch=mkSearchForm(auth, db, myVars, allowBlank=True, withThematics=False),
			myTitle=getTitle(request, auth, db, '#HomeTitle'),
			myText=getText(request, auth, db, '#HomeInfo'),
			myTopPanel=mkTopPanel(myconf, auth),
			myHelp=getHelp(request, auth, db, '#Home'),
			form=form,
			myBottomPanel=DIV(myPanel, _class='tweeterBottomPanel'),
			shareable=True,
			script=myScript,
		)
	else:
		return dict(
			smallSearch=mkSearchForm(auth, db, myVars, allowBlank=True, withThematics=False),
			myTitle=getTitle(request, auth, db, '#HomeTitle'),
			myText=getText(request, auth, db, '#HomeInfo'),
			myTopPanel=mkTopPanel(myconf, auth),
			myHelp=getHelp(request, auth, db, '#Home'),
			form=form,
			panel=DIV(myPanel, _class='tweeterPanel'),
			shareable=True,
			script=myScript,
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
	if request.args[0] == 'login':
		myHelp = getHelp(request, auth, db, '#LogIn')
		myTitle = getTitle(request, auth, db, '#LogInTitle')
		myText = getText(request, auth, db, '#LogInText')
	elif request.args[0] == 'register':
		myHelp = getHelp(request, auth, db, '#CreateAccount')
		myTitle = getTitle(request, auth, db, '#CreateAccountTitle')
		myText = getText(request, auth, db, '#CreateAccountText')
	elif request.args[0] == 'profile':
		myHelp = getHelp(request, auth, db, '#Profile')
		myTitle = getTitle(request, auth, db, '#ProfileTitle')
		myText = getText(request, auth, db, '#ProfileText')
	else:
		myHelp = ''
		myTitle = ''
		myText = ''
	db.auth_user.registration_key.writable = False
	db.auth_user.registration_key.readable = False
	#response.view='default/index.html'
	response.view='default/myLayout.html'
	return dict(
		myTitle=myTitle,
		myText=myText,
		myHelp=myHelp,
		form=auth(),
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
