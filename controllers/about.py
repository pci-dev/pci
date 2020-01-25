# -*- coding: utf-8 -*-
import os
#import os.path
import re
from gluon.custom_import import track_changes; track_changes(True) # reimport module if changed; disable in production
#from app_modules.common import mkPanel
from app_modules.helper import *
from app_modules import common_forms

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)



######################################################################################################################################################################
## Actions
######################################################################################################################################################################
@auth.requires_login()
def validate_ethics():
	theUser = db.auth_user[auth.user_id]
	if 'ethics_approved' in request.vars:
		theUser.ethical_code_approved = True
		theUser.update_record()
	_next = None
	if '_next' in request.vars:
		_next = request.vars['_next']
	if _next:
		redirect(_next)
	else:
		redirect(URL('default','index'))


######################################################################################################################################################################
## Routes
######################################################################################################################################################################
def ethics():
	response.view='default/info.html'
	myTitle=getTitle(request, auth, db, '#EthicsTitle')
	myText=getText(request, auth, db, '#EthicsInfo')
	message = ''
	if auth.user_id:
		if db.auth_user[auth.user_id].ethical_code_approved:
			message = DIV(B(T('You have agreed to comply with this code of conduct'), _style='color:green;'), _style='text-align:center; margin:32px;')
		else:
			myTitle = DIV(
					H1('Before login, you must agree to comply with the code of conduct'),
					myTitle,
				)
			message = FORM(
					DIV(SPAN(INPUT(_type="checkbox", _name="ethics_approved", _id="ethics_approved", _value="yes", value=False), LABEL(T('Yes, I agree to comply with this code of conduct'))), _style='padding:16px;'),
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



######################################################################################################################################################################
def rss_info():
	response.view='default/info.html'

	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	url = URL(c='public', f='rss', scheme=scheme, host=host, port=port)
	fname = os.path.dirname(os.path.abspath(__file__)) + '/../static/images/RSS_datamatrix.png'
	if os.path.isfile(fname):
		datamImg = IMG(_src=URL(c='static', f='images/RSS_datamatrix.png'), _alt='datamatrix', _style='margin-left:32px;')
	else:
		datamImg = ''
	aurl = DIV(A(url, _href=url), datamImg, _style='text-align:center')

	return dict(
		myTitle=getTitle(request, auth, db, '#RssTitle'),
		myText=getText(request, auth, db, '#RssInfo'),
		message=aurl,
	)


######################################################################################################################################################################
## Keep for future use?
def social():
	response.view='default/info.html'

	frames = []
	tweeterAcc = myconf.get('social.tweeter')
	if tweeterAcc:
		frames.append(H2('Tweeter'))
		frames.append(DIV(XML('<a class="twitter-timeline" href="https://twitter.com/%(tweeterAcc)s">Tweets by %(tweeterAcc)s</a> <script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>' % ( locals())), _class='tweeterPanel'))

	#facebookAcc = myconf.get('social.facebook')
	#if facebookAcc:
		#frames.append(H2('Facebook'))
		#frames.append(DIV(XML('<div class="fb-page" data-href="https://www.facebook.com/%s" data-tabs="timeline" data-width=500 data-small-header="true" data-hide-cover="false" data-show-facepile="true"><blockquote cite="https://www.facebook.com/%s" class="fb-xfbml-parse-ignore"><a href="https://www.facebook.com/%s">%s</a></blockquote></div>' % (facebookAcc,facebookAcc,facebookAcc,myconf.get('app.description'))), _class='facebookPanel'))
	
	return dict(
		myTitle=getTitle(request, auth, db, '#SocialTitle'),
		myText=getText(request, auth, db, '#SocialInfo'),
		message=DIV(frames, _class='pci-socialDiv'),
		facebook=True,
		shareable=True,
	)


######################################################################################################################################################################
def supports():
	response.view='default/info.html'
	
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


######################################################################################################################################################################
def resources():
	response.view='default/info.html'
	resources = db(db.t_resources).select(db.t_resources.resource_name, db.t_resources.resource_description, db.t_resources.resource_logo, db.t_resources.resource_document, db.t_resources.resource_category, orderby=db.t_resources.resource_rank)
	myTable = []
	myCategory = ''
	for resource in resources:
		if (resource.resource_category or '') != myCategory:
			myCategory = (resource.resource_category or '')
			myTable.append(TR(TD(H1(myCategory)),TD()))
		myRow = TR(
				TD( SPAN(resource.resource_name) ),
				TD (IMG(_src=URL('default', 'download', args=resource.resource_logo), _width=120)  if (resource.resource_logo is not None and resource.resource_logo != '') else ('')),
				TD( SPAN(resource.resource_description) ),
				TD( A(T("Download"), _href=URL('default', 'download', args=resource.resource_document)) if (resource.resource_document is not None and resource.resource_document != '') else ('')),
			)
		myTable.append(myRow)
	return dict(
		myTitle=getTitle(request, auth, db, '#ResourcesTitle'),
		myText=TABLE(myTable, _class='pci-resources'),
		shareable=True,
	)


######################################################################################################################################################################
def recommenders():
	response.view='default/gab_list_layout.html'

	myVars = request.vars
	qyKw = ''
	qyTF = []
	excludeList = []
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (re.match('^qy_', myVar) and myValue == 'on'):
			qyTF.append(re.sub(r'^qy_', '', myVar))
	qyKwArr = qyKw.split(' ')
	
	searchForm = common_forms.getSearchForm(auth, db, myVars)
	if searchForm.process(keepvalues=True).accepted:
		response.flash = None
	else:
		qyTF = []
		for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
			qyTF.append(thema.keyword)
	
	filtered = db.executesql('SELECT * FROM search_recommenders(%s, %s, %s) ORDER BY last_name, first_name;', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
	myRows = []
	my1 = ''
	myIdx = []
	nbRecomm = len(filtered)
	for fr in filtered:
		sfr = Storage(fr)
		if sfr.last_name[0].upper() != my1:
			my1 = sfr.last_name[0].upper()
			myRows.append(TR(TD( my1, A(_name=my1)), TD(''), _class='pci-capitals'))
			myIdx.append(A(my1, _href='#%s'%my1, _style='margin-right:20px;'))
		myRows.append(mkUserRow(auth, db, sfr, withMail=False, withRoles=False, withPicture=False))
	grid = DIV(
			HR(),
			DIV(nbRecomm + T(' recommenders selected'), _style='text-align:center; margin-bottom:20px;'),
			LABEL(T('Quick access: '), _style='margin-right:20px;'), SPAN(myIdx, _class='pci-capitals'),
			HR(),
			TABLE(
				THEAD(TR(TH(T('Name')), TH(T('Affiliation')) )), 
				TBODY(myRows), 
				_class="web2py_grid pci-UsersTable"
			)
		)
	resu = dict(
				myTitle=getTitle(request, auth, db, '#PublicRecommendationBoardTitle'),
				myText=getText(request, auth, db, '#PublicRecommendationBoardText'),
				myHelp=getHelp(request, auth, db, '#PublicRecommendationBoardDescription'),
				searchForm=searchForm, 
				grid=grid, 
			)
	return resu

######################################################################################################################################################################
def gtu():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#GtuTitle'),
		myText=getText(request, auth, db, '#GtuInfo'),
		shareable=True,
	)


######################################################################################################################################################################
def about():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#AboutTitle'),
		myText=getText(request, auth, db, '#AboutInfo'),
		shareable=True,
	)


######################################################################################################################################################################
def contact():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#ContactTitle'),
		myText=getText(request, auth, db, '#ContactInfo'),
		shareable=True,
	)


######################################################################################################################################################################
def buzz():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#BuzzTitle'),
		myText=getText(request, auth, db, '#BuzzInfo'),
		shareable=True,
	)

######################################################################################################################################################################
def thanks_to_reviewers():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#ThanksToReviewersTitle'),
		myText=getText(request, auth, db, '#ThanksToReviewersInfo'),
	)




# (gab) is this unused ? i put it in about from public
######################################################################################################################################################################
def managers():
	response.view='default/myLayout.html'

	query = db( (db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group._id) & (db.auth_group.role.belongs('manager', 'administrator')) ).select(db.auth_user.ALL, distinct=db.auth_user.last_name|db.auth_user.id, orderby=db.auth_user.last_name|db.auth_user.id)
	myRows = []
	for user in query:
		myRows.append(mkUserRow(auth, db, user, withMail=False, withRoles=True, withPicture=True))
	grid = DIV(
			TABLE(
			THEAD(TR(
					TH(T('')), 
					TH(T('Name')), 
					TH(T('Affiliation')), 
					TH(T('Roles'))
				)), 
			myRows, 
			_class="web2py_grid pci-UsersTable")
		)
	return dict(
				#mkBackButton = mkBackButton(),
				myTitle=getTitle(request, auth, db, '#PublicManagingBoardTitle'),
				myText=getText(request, auth, db, '#PublicManagingBoardText'),
				myHelp=getHelp(request, auth, db, '#PublicManagingBoardDescription'),
				grid=grid, 
			)