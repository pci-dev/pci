# -*- coding: utf-8 -*-

from gluon import current
from gluon.tools import Auth
from gluon.html import *
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)
description = myconf.take('app.description')
appname = myconf.take('app.name')
shortname = myconf.take('app.name')
longname = myconf.take('app.longname')
contact = myconf.take('contacts.managers')

def getHelp(request, auth, db, myHashtag, myLanguage='default'):
	r0 = []
	c = ''
	query = (db.help_texts.hashtag==myHashtag) & (db.help_texts.lang==myLanguage)
	h = db( query ).select().first()
	if h:
		i = h.id
		try:
			c = (h.contents or '') % globals()
		except:
			c = (h.contents or '')
	else:
		i = db.help_texts.insert(hashtag=myHashtag, lang=myLanguage)
	
	r0 += [A(SPAN(current.T('show/hide help')), 
			_onclick="""jQuery(function(){ if ($.cookie('PCiHideHelp') == 'On') {
												$('DIV.pci-helptext').show(); 
												$.cookie('PCiHideHelp', 'Off', {expires:365, path:'/'});
											} else {
												$('DIV.pci-helptext').hide(); 
												$.cookie('PCiHideHelp', 'On', {expires:365, path:'/'});
											}
									})""", 
			_class='pci-help-button'),]
	
	if auth.has_membership(role='administrator') or auth.has_membership(role='developper'):
		r0 += [A(SPAN(current.T('edit help')), _href=URL(c='help', f='help_texts', args=['edit', 'help_texts', i], user_signature=True), _class='pci-help-button-edit')]

	return DIV(
				DIV(r0, _class='pci-help-buttons'), 
				DIV(WIKI(c, safe_mode=False), 
					_class='pci-helptext', 
					_style='display:none;',
					), 
				_class='pci-helper',
			)


def getText(request, auth, db, myHashtag, myLanguage='default'):
	r0 = ''
	c = ''
	query = (db.help_texts.hashtag==myHashtag) & (db.help_texts.lang==myLanguage)
	h = db( query ).select().first()
	if h:
		i = h.id
		try:
			c = (h.contents or '') % globals()
		except:
			c = (h.contents or '')
	else:
		i = db.help_texts.insert(hashtag=myHashtag, lang=myLanguage)
	
	if auth.has_membership(role='administrator') or auth.has_membership(role='developper'):
		r0 = A(current.T('edit text'), _href=URL(c='help', f='help_texts', args=['edit', 'help_texts', i], user_signature=True), _class='pci-text-button-edit pci-admin')

	return DIV(
				DIV(r0, _class='pci-text-buttons'), 
				DIV(WIKI(c, safe_mode=False), _class='pci-infotext', ), 
				_class='pci-infotextbox',
			)


def getTitle(request, auth, db, myHashtag, myLanguage='default'):
	r0 = ''
	c = ''
	query = (db.help_texts.hashtag==myHashtag) & (db.help_texts.lang==myLanguage)
	h = db( query ).select().first()
	if h:
		i = h.id
		try:
			c = (h.contents or '') % globals()
			c = (h.contents or '') % globals()
		except:
			c = (h.contents or '')
	else:
		i = db.help_texts.insert(hashtag=myHashtag, lang=myLanguage)
	
	if auth.has_membership(role='administrator') or auth.has_membership(role='developper'):
		r0 = A(current.T('edit title'), _href=URL(c='help', f='help_texts', args=['edit', 'help_texts', i], user_signature=True), _class='pci-text-button-edit pci-admin')

	return DIV(
				DIV(r0, _class='pci-text-buttons'), 
				DIV(c,  _class='pci-text-title'), 
				_class='pci-infotextbox',
			)


