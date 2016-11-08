# -*- coding: utf-8 -*-

import re
from gluon.custom_import import track_changes; track_changes(True) # reimport module if changed; disable in production
#from common import mkPanel
from helper import *

csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)



def about():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#AboutTitle'),
		myText=getText(request, auth, dbHelp, '#AboutInfo'),
		shareable=True,
	)



def ethics():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#EthicsTitle'),
		myText=getText(request, auth, dbHelp, '#EthicsInfo'),
		shareable=True,
	)



def contact():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#ContactTitle'),
		myText=getText(request, auth, dbHelp, '#ContactInfo'),
		shareable=True,
	)



def buzz():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#BuzzTitle'),
		myText=getText(request, auth, dbHelp, '#BuzzInfo'),
		shareable=True,
	)


def faq():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#FAQTitle'),
		myText=getText(request, auth, dbHelp, '#FAQInfo'),
		shareable=True,
	)


def help_generic():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#GenericHelpTitle'),
		myText=getText(request, auth, dbHelp, '#GenericHelpInfo'),
		shareable=True,
	)



def help_user():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#UserHelpTitle'),
		myText=getText(request, auth, dbHelp, '#UserHelpInfo'),
	)



def help_recommender():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#RecommenderHelpTitle'),
		myText=getText(request, auth, dbHelp, '#RecommenderHelpInfo'),
	)



def help_manager():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#ManagerHelpTitle'),
		myText=getText(request, auth, dbHelp, '#ManagerHelpInfo'),
	)


def help_admin():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, dbHelp, '#AdministratorHelpTitle'),
		myText=getText(request, auth, dbHelp, '#AdministratorHelpInfo'),
	)


def test():
	response.view='default/test.html'
	return dict(
		myTitle='TEST FB + tweeter',
		myText='',
		shareable=True,
	)