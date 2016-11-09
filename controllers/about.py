# -*- coding: utf-8 -*-

import re
from gluon.custom_import import track_changes; track_changes(True) # reimport module if changed; disable in production
#from common import mkPanel
from helper import *

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)



def about():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#AboutTitle'),
		myText=getText(request, auth, db, '#AboutInfo'),
		shareable=True,
	)



def ethics():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#EthicsTitle'),
		myText=getText(request, auth, db, '#EthicsInfo'),
		shareable=True,
	)



def contact():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#ContactTitle'),
		myText=getText(request, auth, db, '#ContactInfo'),
		shareable=True,
	)


def social():
	frames = []
	tweeterAcc = myconf.get('social.tweeter')
	if tweeterAcc:
		frames.append(H2('Tweeter'))
		frames.append(DIV(XML('<a class="twitter-timeline" href="https://twitter.com/%s">Tweets by %s</a> <script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>' % (tweeterAcc, tweeterAcc)), _class='tweeterPanel'))

	facebookAcc = myconf.get('social.facebook')
	if facebookAcc:
		frames.append(H2('Facebook'))
		frames.append(DIV(XML('<div class="fb-page" data-href="https://www.facebook.com/%s" data-tabs="timeline" data-width=500 data-small-header="true" data-hide-cover="false" data-show-facepile="true"><blockquote cite="https://www.facebook.com/%s" class="fb-xfbml-parse-ignore"><a href="https://www.facebook.com/%s">%s</a></blockquote></div>' % (facebookAcc,facebookAcc,facebookAcc,myconf.get('app.description'))), _class='facebookPanel'))
	
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#SocialTitle'),
		myText=getText(request, auth, db, '#SocialInfo'),
		message=DIV(frames, _class='pci-socialDiv'),
		facebook=True,
		shareable=True,
	)

def buzz():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#BuzzTitle'),
		myText=getText(request, auth, db, '#BuzzInfo'),
		shareable=True,
	)


def faq():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#FAQTitle'),
		myText=getText(request, auth, db, '#FAQInfo'),
		shareable=True,
	)


def help_generic():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#GenericHelpTitle'),
		myText=getText(request, auth, db, '#GenericHelpInfo'),
		shareable=True,
	)



def help_user():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#UserHelpTitle'),
		myText=getText(request, auth, db, '#UserHelpInfo'),
	)



def help_recommender():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#RecommenderHelpTitle'),
		myText=getText(request, auth, db, '#RecommenderHelpInfo'),
	)



def help_manager():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#ManagerHelpTitle'),
		myText=getText(request, auth, db, '#ManagerHelpInfo'),
	)


def help_admin():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#AdministratorHelpTitle'),
		myText=getText(request, auth, db, '#AdministratorHelpInfo'),
	)


def test():
	response.view='default/test.html'
	return dict(
		myTitle='TEST FB + tweeter',
		myText='',
		shareable=True,
	)
