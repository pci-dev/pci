# -*- coding: utf-8 -*-

from gluon import current
from gluon.tools import Auth
from gluon.html import *
from gluon.contrib.markdown import WIKI

def getHelp(request, auth, dbHelp, myHashtag, myLanguage='default'):
	#print myHashtag
	r0 = []
	c = ''
	query = (dbHelp.help_texts.hashtag==myHashtag) & (dbHelp.help_texts.language==myLanguage)
	h = dbHelp( query ).select().first()
	if h:
		i = h.id
		c = h.contents or ''
	else:
		i = dbHelp.help_texts.insert(hashtag=myHashtag, language=myLanguage)
	
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
				DIV(WIKI(c), 
					_class='pci-helptext', 
					_style='display:none;',
					), 
				_class='pci-helper',
			)

