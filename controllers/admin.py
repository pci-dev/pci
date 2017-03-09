# -*- coding: utf-8 -*-

import re
import copy

# sudo pip install tweepy
#import tweepy

from gluon.contrib.markdown import WIKI
from common import *
from emailing import *
from helper import *

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

# frequently used constants
csv = False # no export allowed
expClass = dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4



@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
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
def resizeAllUserImages():
	for userId in db(db.auth_user.uploaded_picture != None).select(db.auth_user.id):
		makeUserThumbnail(auth, db, userId, size=(150,150))
	redirect(request.env.http_referer)



@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def resizeAllArticleImages():
	for articleId in db(db.t_articles.uploaded_picture != None).select(db.t_articles.id):
		makeArticleThumbnail(auth, db, articleId, size=(150,150))
	redirect(request.env.http_referer)



@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def resizeUserImages(ids):
	for userId in ids:
		makeUserThumbnail(auth, db, userId, size=(150,150))


@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def list_users():
	selectable = None
	links = None
	if len(request.args)==0 or (len(request.args)==1 and request.args[0]=='auth_user'):
		#selectable = [  (T('Deny login to selected users'), lambda ids: [deny_login(ids)], 'class1')  ]
		links = [  dict(header=T('Roles'), body=lambda row: mkRoles(row))  ]
	db.auth_user.registration_datetime.readable = True
	
	db.auth_user.uploaded_picture.represent = lambda text,row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100))
	db.auth_user.email.represent = lambda text, row: A(text, _href='mailto:%s'%text)
	
	fields = [
			db.auth_user.id, db.auth_user.registration_key, db.auth_user.uploaded_picture, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email, db.auth_user.registration_datetime, db.auth_user.laboratory, db.auth_user.institution, db.auth_user.city, db.auth_user.country, db.auth_user.thematics, db.auth_user.alerts, 
			db.auth_membership.user_id, db.auth_membership.group_id,
			db.t_articles.id, db.t_articles.title, db.t_articles.authors, db.t_articles.already_published, db.t_articles.status, 
			db.t_recommendations.id, db.t_recommendations.article_id, db.t_recommendations.recommender_id, db.t_recommendations.recommendation_state, db.t_recommendations.recommendation_title, 
			db.t_reviews.id, db.t_reviews.recommendation_id, db.t_reviews.review_state, db.t_reviews.review,
			db.t_press_reviews.id, db.t_press_reviews.recommendation_id,
			db.t_comments.id, db.t_comments.article_id, db.t_comments.user_comment, db.t_comments.comment_datetime, db.t_comments.parent_id,
		]
	db.auth_user._id.readable=True
	db.auth_user._id.represent=lambda i,row: mkUserId(auth, db, i, linked=True)
	db.auth_user.registration_key.represent = lambda text,row: SPAN(text, _class="pci-blocked") if (text=='blocked' or text=='disabled') else text
	grid = SQLFORM.smartgrid(db.auth_user
				,fields=fields
				,linked_tables=['auth_user', 'auth_membership', 't_articles', 't_recommendations', 't_reviews', 't_press_reviews', 't_comments']
				,links=links
				,csv=False, exportclasses=dict(auth_user=expClass, auth_membership=expClass)
				,editable=dict(auth_user=True, auth_membership=False)
				,details=dict(auth_user=True, auth_membership=False)
				,searchable=dict(auth_user=True, auth_membership=False)
				,create=dict(auth_user=False, auth_membership=True)
				,selectable=selectable
				,maxtextlength=250
				,paginate=25
			)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#AdministrateUsersText'),
				myTitle=getTitle(request, auth, db, '#AdministrateUsersTitle'),
				myHelp=getHelp(request, auth, db, '#AdministrateUsers'),
				grid=grid, 
			 )


# Prepares lists of email addresses by role
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def mailing_lists():
	content = DIV()
	for theRole in db(db.auth_group.role).select():
		content.append(H1(theRole.role))
		emails = []
		query = db( (db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == theRole.id) ).select(db.auth_user.email, orderby=db.auth_user.email)
		for user in query:
			if user.email:
				emails.append(user.email)
		list_emails = ', '.join(emails)
		content.append(list_emails)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#EmailsListsUsersText'),
				myTitle=getTitle(request, auth, db, '#EmailsListsUsersTitle'),
				myHelp=getHelp(request, auth, db, '#EmailsListsUsers'),
				content=content, 
				grid='',
			 )


#@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
#def memberships():
	#userId = request.args(1)
	#query = db.auth_membership.user_id == userId
	#db.auth_membership.user_id.default = userId
	#db.auth_membership.user_id.writable = False
	#db.auth_membership._id.readable = False
	#grid = SQLFORM.grid( query
				#,deletable=True, create=True, editable=False, details=False, searchable=False
				#,csv=csv, exportclasses=expClass
				#,maxtextlength=250
				#,paginate=25
			#)
	#response.view='admin/memberships.html'
	#return dict(
				#myTitle=getTitle(request, auth, db, '#AdministrateMembershipsTitle'),
				#myHelp=getHelp(request, auth, db, '#AdministrateMemberships'),
				#grid=grid, 
		#)



#@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
#def deny_login(ids):
	#for myId in ids:
		#db.executesql("UPDATE auth_user SET registration_key='blocked' WHERE id=%s;", placeholders=[myId])



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
	return dict(
				myHelp=getHelp(request, auth, db, '#AdministrateThematicFields'),
				myText=getText(request, auth, db, '#AdministrateThematicFieldsText'),
				myTitle=getTitle(request, auth, db, '#AdministrateThematicFieldsTitle'),
				grid=grid, 
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
	return dict(
				myHelp=getHelp(request, auth, db, '#AdministrateArticleStatus'),
				myText=getText(request, auth, db, '#AdministrateArticleStatusText'),
				myTitle=getTitle(request, auth, db, '#AdministrateArticleStatusTitle'),
				grid=grid, 
			 )


# PDF management
@auth.requires(auth.has_membership(role='manager') or auth.has_membership(role='administrator'))
def manage_pdf():
	grid = SQLFORM.grid( db.t_pdf
		,details=False, editable=True, deletable=True, create=True, searchable=False
		,maxtextlength=250, paginate=20
		,csv=csv, exportclasses=expClass
		,fields=[db.t_pdf.recommendation_id, db.t_pdf.pdf]
		#,fields=[db.t_articles.uploaded_picture, db.t_articles._id, db.t_articles.already_published, db.t_articles.upload_timestamp, db.t_articles.status, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations, db.t_articles.user_id, db.t_articles.thematics]
		#,links=links
		,orderby=~db.t_pdf.id
	)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#AdminPdfText'),
				myTitle=getTitle(request, auth, db, '#AdminPdfTitle'),
				grid=grid, 
			)






#@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
#def test_tweet():
	#message = ''
	#scheme=myconf.take('alerts.scheme')
	#host=myconf.take('alerts.host')
	#port=eval(myconf.take('alerts.port'))
	#link = URL(c='about', f='social', scheme=scheme, host=host, port=port)
	#print 'To be tweeted:', A(link, _href=link)
	#tweeterAcc = myconf.get('social.tweeter')
	#consumer_key = myconf.get('social.tweeter_consumer_key')
	#consumer_secret = myconf.get('social.tweeter_consumer_secret')
	#access_token = myconf.get('social.tweeter_access_token')
	#access_token_secret = myconf.get('social.tweeter_access_token_secret')
	#if consumer_key and consumer_secret and access_token and access_token_secret :
		#try:
			#twAuth = tweepy.OAuthHandler(consumer_key, consumer_secret)
			#twAuth.set_access_token(access_token, access_token_secret)
			#api = tweepy.API(twAuth)
			#api.update_status(status="Test: "+datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')+" "+link)
			#if tweeterAcc:
				#frames = []
				#frames.append(H2('Tweeter'))
				#frames.append(DIV(XML('<a class="twitter-timeline" href="https://twitter.com/%s">Tweets by %s</a> <script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>' % (tweeterAcc, tweeterAcc)), _class='tweeterPanel'))
				#message = DIV(frames, _class='pci-socialDiv')
		#except:
			#message = T('Failure!')
			#pass
	#else:
		#message = T('Configure private/appconfig.ini')
	#response.view='default/info.html'
	#return dict(
				#myHelp=getHelp(request, auth, db, '#AdministrateTestTweet'),
				#myText=getText(request, auth, db, '#AdministrateTestTweetText'),
				#myTitle=getTitle(request, auth, db, '#AdministrateTestTweetTitle'),
				#message=message,
			 #)
