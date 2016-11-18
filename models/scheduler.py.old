# -*- coding: utf-8 -*-

# -------------------------------------------------------------------------
# app configuration made easy. Look inside private/appconfig.ini
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

from common import *
from emailing import alert_new_recommendations
from datetime import date, datetime
import calendar

#import logging
#logger = logging.getLogger("web2py.app."+myconf.take('app.name'))
#logger.setLevel(logging.DEBUG)
#logger.debug('test')

## dummy test
#def test_mail():
	#if 'userId' not in pvars:
		#raise 'No user id'
	#userId = pvars['userId']
	#user = db.auth_user[userId]
	#if user is None:
		#raise 'No user'
	#mail_resu = mail.send(to=[user.email],
					#subject=myconf.take('app.name'),
					#message='hi there',
					#html=I('coucou'),
				#)
	#if mail_resu:
		#print 'email to %s sent' % (user.email)
		##logger.debug('email to %s sent' % (user.email))
	#else:
		#print 'email to %s NOT sent' % (user.email)
		##logger.debug('email to %s NOT sent' % (user.email))
	#return



## function called daily
#def alertUsersLastRecommendations():
	#my_date = date.today()
	#my_day = calendar.day_name[my_date.weekday()]
	#usersQy = db( db.auth_user.alerts.contains(my_day, case_sensitive=False) ).select()
	#for user in usersQy:
		#userId = user.id
		#if userId != 1: continue #WARNING Only me for debug!!
		#articleIdsQy = db.executesql('SELECT * FROM alert_last_recommended_article_ids_for_user(%s);', placeholders=[userId])
		#if len(articleIdsQy) > 0: # yes, new stuff to display
			#artIds = articleIdsQy[0][0]
			#query = db( (db.t_articles.id.belongs(artIds)) ).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)
			#n = len(query)
			#myRows = []
			#odd = True
			#for row in query:
				#myRows.append(mkArticleRowForEmail(Storage(row), odd))
				#odd = not(odd)
			#msgContents = DIV(
						#TABLE(
							#TBODY(myRows), 
							#_style='width:100%; background-color:transparent; border-collapse: separate; border-spacing: 0 8px;'
							#), 
						#)
			#alert_new_recommendations(session, auth, db, userId, msgContents)
		##user.last_alert = datetime.datetime.now()
		##user.update_record()
		##db.commit()

#from gluon.scheduler import Scheduler
##scheduler = Scheduler(db, heartbeat=60, tasks=dict(test=test_mail))
#scheduler = Scheduler(db, heartbeat=30)

@auth.requires(auth.has_membership(role='developper'))
def queueTasks():
	scheduler.resume()
	#NOTE: 86400 seconds for 1 day
	scheduler.queue_task(test_mail, pvars=dict(userId=1), repeats=0, period=600, timeout=60, prevent_drift=True) 

@auth.requires(auth.has_membership(role='developper'))
def terminateScheduler():
	scheduler.terminate()

@auth.requires(auth.has_membership(role='developper'))
def killScheduler():
	scheduler.kill()
