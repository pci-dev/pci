# -*- coding: utf-8 -*-

import re
from gluon.custom_import import track_changes; track_changes(True) # reimport module if changed; disable in production
from common import mkPanel
from helper import *

csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)



def about():
	response.view='default/info.html'
	return dict(
		message=T("What is %s?") % (myconf.take('app.longname')),
		#content=SPAN(T("Peer Community in Evolutionary Biology is the first community of the parent project")+' ')+A("Peer Community In", _href="https://peercommunityin.org")+SPAN("."),
		panel=mkPanel(myconf, auth),
		myText=getText(request, auth, dbHelp, '#AboutInfo'),
		myBackButton=mkBackButton(),
	)



def ethics():
	response.view='default/info.html'
	return dict(
		myTitle=I(myconf.take('app.longname'))+SPAN(" code of ethical conduct"),
		#content=SPAN(""),
		panel=mkPanel(myconf, auth),
		myText=getText(request, auth, dbHelp, '#EthicsInfo'),
		myBackButton=mkBackButton(),
	)



def help_recommender():
	pass



def help_manager():
	pass
