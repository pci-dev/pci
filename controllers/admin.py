# -*- coding: utf-8 -*-

import re
import copy

from gluon.contrib.markdown import WIKI
from common import *


# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4



@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def list_users():
	if len(request.args)==0 or (len(request.args)==1 and request.args[0]=='auth_user'):
		links = [
				dict(header=T('Picture'), body=lambda row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100))),
			]
	else:
		links = None
	db.auth_user.uploaded_picture.readable = False
	grid = SQLFORM.smartgrid(db.auth_user
				,fields=[db.auth_user.id, db.auth_user.uploaded_picture, db.auth_user.user_title, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.laboratory, db.auth_user.institution, db.auth_user.city, db.auth_user.country, db.auth_user.thematics, db.auth_user.alerts, db.auth_membership.user_id, db.auth_membership.group_id]
				,linked_tables=['auth_user', 'auth_membership']
				,csv=csv, exportclasses=dict(auth_user=expClass, auth_membership=expClass)
				,editable=dict(auth_user=True, auth_membership=False)
				,details=dict(auth_user=True, auth_membership=False)
				,links=links
				,maxtextlength=250
				,paginate=25
			)
	response.view='default/myLayout.html'
	return dict(grid=grid, myTitle=T('Users'))




# Display the list of thematic fields
# Can be modified only by developper and administrator
@auth.requires_login()
def thematics_list():
	write_auth = auth.has_membership('administrator') or auth.has_membership('developper')
	grid = SQLFORM.grid(db.t_thematics
		,details=False,editable=False,deletable=write_auth,create=write_auth,searchable=False
		,maxtextlength = 250,paginate=100
		,csv = csv, exportclasses = expClass
		,fields=[db.t_thematics.keyword]
		,orderby=db.t_thematics.keyword
	)
	response.view='default/myLayout.html'
	return dict(grid=grid, myTitle=T('Thematic fields'))




# Lists article status
# writable by developpers only!!
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager') or auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def article_status():
	write_auth = auth.has_membership('developper')
	db.t_status_article.status.represent = lambda text, row: SPAN(T(text).replace('-','- '), _class='buttontext btn fake-btn pci-button '+row.color_class, _title=T(row.explaination or ''))
	grid = SQLFORM.grid( db.t_status_article
		,searchable=False, create=False, details=False
		,deletable=write_auth
		,editable=write_auth
		,maxtextlength=500,paginate=100
		,csv=csv, exportclasses=expClass
		,fields=[db.t_status_article.status, db.t_status_article.color_class, db.t_status_article.explaination]
		#,links=[dict(header=T('Button'), body=lambda row: SPAN(T(row.status), _class='buttontext btn fake-btn pci-button '+row.color_class))]
		)
	myBackButton = mkBackButton()
	response.view='default/myLayout.html'
	return dict(grid=grid, myTitle=T('Article status'), myBackButton=myBackButton)





