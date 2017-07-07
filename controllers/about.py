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
	myTitle=getTitle(request, auth, db, '#EthicsTitle')
	myText=getText(request, auth, db, '#EthicsInfo')
	message = ''
	if auth.user_id:
		if db.auth_user[auth.user_id].ethical_code_approved:
			message = DIV(B(T('You agreed to comply with this code of ethical conduct'), _style='color:green;'), _style='text-align:center; margin:32px;')
		else:
			myTitle = DIV(
					H1('Before login, you must agree to comply with the code of ethical conduct'),
					myTitle,
				)
			message = FORM(
					DIV(SPAN(INPUT(_type="checkbox", _name="ethics_approved", _id="ethics_approved", _value="yes", value=False), LABEL(T('Yes, I agree to comply with this code of ethical conduct'))), _style='padding:16px;'),
					INPUT(_type='submit', _value=T("Set in my profile"), _class="btn btn-info"), 
					_action=URL('about', 'validate_ethics', vars=request.vars),
					_style='text-align:center;',
				)

	return dict(
		myTitle=myTitle,
		myText=myText,
		message=message,
		shareable=True,
	)


@auth.requires_login()
def validate_ethics():
	theUser = db.auth_user[auth.user_id]
	if 'ethics_approved' in request.vars:
		theUser.ethical_code_approved = True
		theUser.update_record()
	redirect(request.env.http_referer)



def contact():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#ContactTitle'),
		myText=getText(request, auth, db, '#ContactInfo'),
		shareable=True,
	)


## Keep for future use?
def social():
	frames = []
	tweeterAcc = myconf.get('social.tweeter')
	if tweeterAcc:
		frames.append(H2('Tweeter'))
		frames.append(DIV(XML('<a class="twitter-timeline" href="https://twitter.com/%(tweeterAcc)s">Tweets by %(tweeterAcc)s</a> <script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>' % ( locals())), _class='tweeterPanel'))

	#facebookAcc = myconf.get('social.facebook')
	#if facebookAcc:
		#frames.append(H2('Facebook'))
		#frames.append(DIV(XML('<div class="fb-page" data-href="https://www.facebook.com/%s" data-tabs="timeline" data-width=500 data-small-header="true" data-hide-cover="false" data-show-facepile="true"><blockquote cite="https://www.facebook.com/%s" class="fb-xfbml-parse-ignore"><a href="https://www.facebook.com/%s">%s</a></blockquote></div>' % (facebookAcc,facebookAcc,facebookAcc,myconf.get('app.description'))), _class='facebookPanel'))
	
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#SocialTitle'),
		myText=getText(request, auth, db, '#SocialInfo'),
		message=DIV(frames, _class='pci-socialDiv'),
		facebook=True,
		shareable=True,
	)


def supports():
	response.view='default/info.html' #OK
	supports = db(db.t_supports).select(db.t_supports.support_name, db.t_supports.support_url, db.t_supports.support_logo, db.t_supports.support_category, orderby=db.t_supports.support_rank)
	myTable = []
	myCategory = ''
	for support in supports:
		if (support.support_category or '') != myCategory:
			myCategory = (support.support_category or '')
			myTable.append(TR(TD(H1(myCategory)),TD()))
		myRow = TR(
				TD( A(support.support_name or '', _target='blank', _href=support.support_url) if support.support_url else SPAN(support.support_name) ),
				TD(IMG(_src=URL('default', 'download', args=support.support_logo), _width=120) if (support.support_logo is not None and support.support_logo != '') else ('')),
			)
		myTable.append(myRow)
	return dict(
		myTitle=getTitle(request, auth, db, '#SupportsTitle'),
		#myText=getText(request, auth, db, '#SupportsInfo'),
		myText=TABLE(myTable, _class='pci-supports'),
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


def cite():
	response.view='default/info.html' #OK
	return dict(
		myTitle=getTitle(request, auth, db, '#CiteTitle'),
		myText=getText(request, auth, db, '#CiteInfo'),
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


