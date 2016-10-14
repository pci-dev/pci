# -*- coding: utf-8 -*-

import re
import copy

from gluon.contrib.markdown import WIKI
from common import *
from emailing import *
from helper import *


# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4



@auth.requires(auth.has_membership(role='developper'))
def testMail():
	do_send_email_to_test(session, auth, db, auth.user_id)
	redirect(request.env.http_referer)




@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def mkRoles(row):
	resu = ''
	if row.id:
		roles = db.v_roles[row.id]
		if roles:
			resu = SPAN(roles.roles)
	return resu




@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def list_users():
	if len(request.args)==0 or (len(request.args)==1 and request.args[0]=='auth_user'):
		#selectable = [  (T('Deny login to selected users'), lambda ids: [deny_login(ids)], 'class1')  ]
		links = [  dict(header=T('Roles'), body=lambda row: mkRoles(row))  ]
	else:
		#selectable = None
		links = None
	db.auth_user.uploaded_picture.represent = lambda text,row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100))
	db.auth_user.email.represent = lambda text, row: A(text, _href='mailto:%s'%text)
	fields = [db.auth_user.id, db.auth_user.registration_key, db.auth_user.uploaded_picture, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email, db.auth_user.laboratory, db.auth_user.institution, db.auth_user.city, db.auth_user.country, db.auth_user.thematics, db.auth_user.alerts, db.auth_membership.user_id, db.auth_membership.group_id]
	db.auth_user._id.readable=False
	db.auth_user.registration_key.represent = lambda text,row: SPAN(text, _class="pci-blocked") if (text=='blocked' or text=='disabled') else text
	grid = SQLFORM.smartgrid(db.auth_user
				,fields=fields
				,linked_tables=['auth_user', 'auth_membership']
				,links=links
				,csv=csv, exportclasses=dict(auth_user=expClass, auth_membership=expClass)
				,editable=dict(auth_user=True, auth_membership=False)
				,details=dict(auth_user=True, auth_membership=False)
				,searchable=dict(auth_user=True, auth_membership=False)
				,create=dict(auth_user=False, auth_membership=True)
				#,selectable=selectable
				,maxtextlength=250
				,paginate=25
			)
	response.view='admin/list_users.html'
	return dict(grid=grid, 
				myTitle=T('Users'),
				myHelp=getHelp(request, auth, dbHelp, '#AdministrateUsers'),
			 )




@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def memberships():
	userId = request.args(1)
	query = db.auth_membership.user_id == userId
	db.auth_membership.user_id.default = userId
	db.auth_membership.user_id.writable = False
	db.auth_membership._id.readable = False
	grid = SQLFORM.grid( query
				,deletable=True, create=True, editable=False, details=False, searchable=False
				,csv=csv, exportclasses=expClass
				,maxtextlength=250
				,paginate=25
			)
	response.view='admin/memberships.html'
	return dict(grid=grid, 
				myTitle=T('Memberships'), 
				myBackButton=mkBackButton(),
				myHelp=getHelp(request, auth, dbHelp, '#AdministrateMemberships'),
		)



@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def deny_login(ids):
	for myId in ids:
		db.executesql("UPDATE auth_user SET registration_key='blocked' WHERE id=%s;", placeholders=[myId])


# Display the list of thematic fields
# Can be modified only by developper and administrator
@auth.requires_login()
def thematics_list():
	write_auth = auth.has_membership('administrator') or auth.has_membership('developper')
	db.t_thematics._id.readable=False
	grid = SQLFORM.grid(db.t_thematics
		,details=False,editable=True,deletable=write_auth,create=write_auth,searchable=False
		,maxtextlength = 250,paginate=100
		,csv = csv, exportclasses = expClass
		,fields=[db.t_thematics.keyword]
		,orderby=db.t_thematics.keyword
	)
	response.view='default/myLayout.html'
	return dict(grid=grid, 
				myTitle=T('Thematic fields'),
				myHelp=getHelp(request, auth, dbHelp, '#AdministrateThematicFields'),
			 )




# Lists article status
# writable by developpers only!!
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager') or auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def article_status():
	write_auth = auth.has_membership('developper')
	db.t_status_article._id.represent = lambda text, row: SPAN(T(row.status).replace('-','- '), _class='buttontext btn fake-btn pci-button '+row.color_class, _title=T(row.explaination or ''))
	#db.t_status_article.status.represent = lambda text, row: SPAN(T(text).replace('-','- '), _class='buttontext btn fake-btn pci-button '+row.color_class, _title=T(row.explaination or ''))
	grid = SQLFORM.grid( db.t_status_article
		,searchable=False, create=False, details=False, deletable=False
		,editable=write_auth
		,maxtextlength=500,paginate=100
		,csv=csv, exportclasses=expClass
		,fields=[db.t_status_article._id, db.t_status_article.status, db.t_status_article.priority_level, db.t_status_article.color_class, db.t_status_article.explaination]
		,orderby=db.t_status_article.priority_level
		)
	mkStatusArticles(db)
	response.view='default/myLayout.html'
	return dict(grid=grid, myTitle=T('Article status'), 
			myBackButton=mkBackButton(),
			myHelp=getHelp(request, auth, dbHelp, '#AdministrateArticleStatus'),
			 )





