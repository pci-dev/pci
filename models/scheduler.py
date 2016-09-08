# -*- coding: utf-8 -*-

from gluon.scheduler import Scheduler

# -------------------------------------------------------------------------
# app configuration made easy. Look inside private/appconfig.ini
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)


def test_mail():
	if 'user_id' not in pvars:
		raise 'No user id'
	userId = pvars['user_id']
	user = db.auth_user[userId]
	if user is None:
		raise 'No user'
	mail_resu = mail.send(to=[user.email],
					subject=myconf.take('app.name'),
					message='hi there',
					html=I('coucou'),
				)
	if mail_resu:
		print 'email sent'
	else:
		print 'email not sent'
	#db.commit()
	return

scheduler = Scheduler(db, heartbeat=60, tasks=dict(test=test_mail))

#example: scheduler.queue_task(test_mail, pvars=dict(user_id=auth.user_id), period=3600)

