# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import re

#from gluon.contrib.markdown import WIKI
from common import *
from emailing import *
from datetime import date, datetime
import calendar
from time import sleep

#import socket
#host=socket.getfqdn()
from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'mail.html')

#auth.settings.allow_basic_login = True


def _mkArticleRowForEmail(row, odd):
	resu = mkRecommArticleRow(auth, db, row, withImg=False, withScore=False, withDate=True, fullURL=True)
	if odd:
		return TR(resu)
	else:
		return TR(resu, _style='background-color:#f7f7f7;')
		



# dummy tests
# TEST MAIL
#@auth.requires_login()
def _do_send_email_to_test(userId):
	mail = getMailer(auth)
	report = []
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	destPerson = mkUser(auth, db, userId)
	destAddress = db.auth_user[userId]['email']
	mySubject = "%s: TEST MAIL" % (applongname)
	siteName = I(applongname)
	linkTarget = URL(c='default', f='index', scheme=myconf.take('alerts.scheme'), host=myconf.take('alerts.host'), port=myconf.take('alerts.port', cast=lambda v: takePort(v) ) )
	content = """
Dear %(destPerson)s,<p>
This is a test mail; please ignore.<p>
You may visit %(siteName)s on: <a href="%(linkTarget)s">%(linkTarget)s</a><p>""" % locals()
	myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
	mail_resu = mail.send(to=[destAddress],
					subject=mySubject,
					message=myMessage,
				)
	if mail_resu:
		report.append( 'email to %s sent' % destPerson.flatten() )
	else:
		report.append( 'email to %s NOT SENT' % destPerson.flatten() )
	print ''.join(report)



def test_flash():
	session.flash = 'Coucou !'
	redirect(request.env.http_referer)


#@auth.requires(auth.user_id==1)
#@auth.requires_login()
def test_mail_piry():
	if 'client' not in request:
		_do_send_email_to_test(1)


#@auth.requires_login()
def testUserRecommendedAlert():
	if 'userId' in request.vars:
		userId = request.vars['userId']
	#auth.basic()
	#if auth.user:
	conditions = ['client' not in request, auth.user]
	if any(conditions):
		if userId:
			userId = auth.user_id
			user = db.auth_user[userId]
			if user:
				articleIdsQy = db.executesql('SELECT * FROM alert_last_recommended_article_ids_for_user(%s);', placeholders=[userId])
				if len(articleIdsQy)>0:
					artIds = articleIdsQy[0][0]
					query = db( (db.t_articles.id.belongs(artIds)) ).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)
					n = len(query)
					myRows = []
					odd = True
					for row in query:
						myRows.append(_mkArticleRowForEmail(Storage(row), odd))
						odd = not(odd)
					msgContents = DIV(
								TABLE(
									TBODY(myRows), 
									_style='width:100%; background-color:transparent; border-collapse: separate; border-spacing: 0 8px;'
									), 
								)
					if len(myRows)>0:
						alert_new_recommendations(session, auth, db, userId, msgContents)
				
			redirect(request.env.http_referer)
		else:
			raise HTTP(404, "404: "+T('Unavailable'))
	else:
		raise HTTP(403, "403: "+T('Unauthorized'))




# function called daily
#@auth.requires_login()
def alertUsersLastRecommendations():
	conditions = ['client' not in request, auth.has_membership(role='manager')]
	if any(conditions):
		my_date = date.today()
		my_day = calendar.day_name[my_date.weekday()]
		usersQy = db( db.auth_user.alerts.contains(my_day, case_sensitive=False) ).select()
		for user in usersQy:
			userId = user.id
			articleIdsQy = db.executesql('SELECT * FROM alert_last_recommended_article_ids_for_user(%s);', placeholders=[userId])
			if len(articleIdsQy) > 0: # yes, new stuff to display
				artIds = articleIdsQy[0][0]
				query = db( 
						  (db.t_articles.id.belongs(artIds)) 
						& (db.t_recommendations.article_id==db.t_articles.id) 
						& (db.t_recommendations.recommendation_state=='Recommended')
					).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)
				n = len(query)
				myRows = []
				odd = True
				for row in query:
					myRows.append(_mkArticleRowForEmail(Storage(row), odd))
					odd = not(odd)
				msgContents = DIV(
							TABLE(
								TBODY(myRows), 
								_style='width:100%; background-color:transparent; border-collapse: separate; border-spacing: 0 8px;'
								), 
							)
				if len(myRows)>0:
					alert_new_recommendations(session, auth, db, userId, msgContents)
					user.last_alert = datetime.datetime.now()
					user.update_record()
					db.commit()
			sleep(3) # try to avoid mailer black-listing

