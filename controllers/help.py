# -*- coding: utf-8 -*-

import re
from gluon.custom_import import track_changes; track_changes(True) # reimport module if changed; disable in production
from gluon.contrib.markdown import WIKI
from common import *
from helper import *

csv = True # export allowed
expClass = dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)


@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def help_texts():
	print session.back
	if session.back:
		redirect_url = session.back
	else:
		redirect_url = URL()
	dbHelp.help_texts.language.writable = False
	dbHelp.help_texts.hashtag.writable = auth.has_membership(role='developper')
	dbHelp.help_texts.contents.represent = lambda text, row: WIKI(text or '')
	dbHelp.help_texts._id.readable=False
	dbHelp.help_texts._id.writable=False
	grid = SQLFORM.grid( dbHelp.help_texts
				,create=auth.has_membership(role='developper')
				,deletable=False
				,paginate=100, maxtextlength=4096
				,csv=csv, exportclasses=expClass
				,orderby=dbHelp.help_texts.hashtag
			)
	if grid.update_form and grid.update_form.process().accepted:
		if redirect_url:
			redirect(redirect_url)
		session.back = None
	else:
		session.back = request.env.http_referer
	response.view='default/myLayout.html'
	return dict(grid=grid, 
			myTitle=getTitle(request, auth, dbHelp, '#HelpTextTitle'),
			myText=getText(request, auth, dbHelp, '#HelpTextText'),
			#content=SPAN("See MARKDOWN syntax for formatting: ", A("https://en.wikipedia.org/wiki/Markdown", _href="https://en.wikipedia.org/wiki/Markdown#Example", _target="blank")),
			#myBackButton=mkBackButton(),
			myHelp=getHelp(request, auth, dbHelp, '#AdministrateHelpTexts'),
		 )


