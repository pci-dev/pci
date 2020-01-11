# -*- coding: utf-8 -*-

import os
import datetime
import time
from re import sub, match
#from copy import deepcopy
import datetime
from dateutil.relativedelta import *
import traceback

from gluon import current
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail

from gluon.custom_import import track_changes; track_changes(True)
from app_modules.common import *
import socket

from uuid import uuid4
from contextlib import closing
import shutil

myconf = AppConfig(reload=True)
parallelSubmissionAllowed = myconf.get('config.parallel_submission', default=False)

mail_sleep = 1.5 # in seconds

# common view for all emails
mail_layout = os.path.join(os.path.dirname(__file__), '../../views/mail', 'mail.html')
def get_mail_template(templateName):
	with open(os.path.join(os.path.dirname(__file__), '../../templates/mail', templateName), 'r') as myfile:
  		data = myfile.read()
	return data

######################################################################################################################################################################
def getMailer(auth):
	mail = auth.settings.mailer
	mail.settings.server = myconf.take('smtp.server')
	mail.settings.sender = myconf.take('smtp.sender')
	mail.settings.login = myconf.take('smtp.login')
	mail.settings.tls = myconf.get('smtp.tls', default=False)
	mail.settings.ssl = myconf.get('smtp.ssl', default=False)
	return mail

# Get list of emails for all users with role 'manager'
######################################################################################################################################################################
def get_MB_emails(session, auth, db):
	managers = []
	for mm in db( (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == 'manager') ).select(db.auth_user.email):
		managers.append(mm["email"])
	return managers

######################################################################################################################################################################
# Footer for all mails
def mkFooter():
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	appdesc=myconf.take('app.description')
	appname=myconf.take('app.name')
	applongname=myconf.take('app.longname')
	appthematics=myconf.take('app.thematics')
	contact=myconf.take('contacts.managers')
	baseurl=URL(c='default', f='index', scheme=scheme, host=host, port=port)
	profileurl=URL(c='default', f='user', args=('login'), vars=dict(_next=URL(c='default', f='user', args=('profile'))), scheme=scheme, host=host, port=port)
	return XML(get_mail_template('mail_footer.html') % locals())


######################################################################################################################################################################
# TEST MAIL
def do_send_email_to_test(session, auth, db, userId):
	print('Entering test mail')
	mail = getMailer(auth)
	report = []
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	destPerson = mkUser(auth, db, userId)
	destAddress = db.auth_user[userId]['email']
	mySubject = "%s: Test Mail" % (appname)
	siteName = I(appname)
	linkTarget = URL(c='default', f='index', scheme=scheme, host=host, port=port)

	content = get_mail_template('test_mail.html') % locals()

	try:
		myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
		mail_resu = mail.send(to=[destAddress],
					subject=mySubject,
					message=myMessage,
				)
	except Exception, e :
		#print "%s" % traceback.format_exc()
		traceback.print_exc()
		pass

	session.flash_status = ''
	if mail_resu:
		report.append( 'email sent to %s' % destPerson.flatten() )
	else:
		session.flash_status = 'warning'
		report.append( 'email NOT SENT to %s' % destPerson.flatten() )

	print ''.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
# Send email to the requester (if any)
def do_send_email_to_requester(session, auth, db, articleId, newStatus):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	contact=myconf.take('contacts.managers')
	unconsider_limit_days=myconf.get('config.unconsider_limit_days', default=20)
	recomm_limit_days=myconf.get('config.recomm_limit_days', default=50)
	article = db.t_articles[articleId]
	if article and article.user_id is not None:
		destPerson = mkUser(auth, db, article.user_id)
		destAddress = db.auth_user[article.user_id]['email']
		articleTitle = article.title
		recommendation = None
		
		if article.status=='Pending' and newStatus=='Awaiting consideration':
			mySubject = '%s: Submission of your preprint' % (appname)
			linkTarget = XML(URL(c='user', f='my_articles', scheme=scheme, host=host, port=port))
			if article.parallel_submission:
				content = get_mail_template('requester_parallel_submitted_preprint.html') % locals()
			else:
				parallelText = ""
				if parallelSubmissionAllowed:
					parallelText += """Please note that if you abandon the process with %(appname)s after reviewers have contributed their time toward evaluation and before the end of the evaluation, we will post the reviewers' reports on the %(appname)s website as recognition of their work and in order to enable critical discussion.<p>""" % locals()
				content =  get_mail_template('requester_submitted_preprint.html') % locals()
		

		elif article.status=='Awaiting consideration' and newStatus=='Under consideration':
			linkTarget = XML(URL(c='user', f='my_articles', scheme=scheme, host=host, port=port))
			mySubject = '%s: Consideration of your preprint' % (appname)
			if article.parallel_submission:
				content = get_mail_template('requester_parallel_preprint_under_consideration.html') % locals()

			else:
				content = get_mail_template('requester_preprint_under_consideration.html') % locals()


		elif article.status!=newStatus and newStatus=='Cancelled':
			linkTarget=URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			mySubject = '%s: Cancellation of your submission' % (appname)
			content = get_mail_template('requester_cancelled_submission.html') % locals()
			# (gab) SAME CONTENT :
			# if article.parallel_submission:
			# else:
			# 	content = """Dear %(destPerson)s,<p>
			# The submission of your preprint entitled <b>%(articleTitle)s</b> has been cancelled. We respect your decision, and hope that you will submit other preprints to <i>%(appdesc)s</i> (<i>%(appname)s</i>) in the near future.<p>
			# Yours sincerely,<p>
			# <span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
			# """ % locals()
		
		elif article.status!=newStatus and newStatus=='Rejected':
			mySubject = '%s: Decision concerning your submission' % (appname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=scheme, host=host, port=port)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = get_mail_template('requester_rejected_submission.html') % locals()
		
		elif article.status!=newStatus and newStatus=='Not considered':
			mySubject = '%s: Decision concerning your submission' % (appname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=scheme, host=host, port=port)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = get_mail_template('requester_not_considered_submission.html') % locals()
		
		elif article.status!=newStatus and newStatus=='Awaiting revision':
			mySubject = '%s: Decision concerning your submission' % (appname)
			linkTarget = XML(URL(c='user', f='my_articles', scheme=scheme, host=host, port=port))
			recommTarget = XML(URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=scheme, host=host, port=port))
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = get_mail_template('requester_awaiting_submission.html') % locals()
			
		elif article.status!=newStatus and newStatus=='Pre-recommended':
			return # patience!
	
		elif article.status!=newStatus and newStatus=='Recommended':
			mySubject = '%s: Recommendation of your preprint' % (appname)
			linkTarget = XML(URL(c='articles', f='rec', vars=dict(id=articleId), scheme=scheme, host=host, port=port))
			recommendation = None # mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			lastRecomm = db( (db.t_recommendations.article_id==article.id) & (db.t_recommendations.recommendation_state == 'Recommended') ).select().last() 
			doiRecomm = XML(mkLinkDOI(lastRecomm.recommendation_doi))
			recommVersion = lastRecomm.ms_version
			recommsList = SPAN(mkWhoDidIt4Recomm(auth, db, lastRecomm, with_reviewers=False, linked=False)).flatten()
			contact = A(myconf.take('contacts.contact'), _href='mailto:'+myconf.take('contacts.contact'))
			content = get_mail_template('requester_recommended_preprint.html') % locals()
		
		elif article.status!=newStatus:
			tOldStatus = current.T(article.status)
			tNewStatus = current.T(newStatus)
			mySubject = '%s: Change in the status of your preprint' % (appname)
			linkTarget = XML(URL(c='user', f='my_articles', scheme=scheme, host=host, port=port))
			content = get_mail_template('requester_preprint_status_changed.html') % locals()
		
		else:
			return
		
		if destAddress:
			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
				mail_resu = mail.send(to=[destAddress],
						subject=mySubject,
						message=myMessage,
					)
			except:
				pass
		if mail_resu:
			report.append( 'email sent to submitter %s' % destPerson.flatten() )
		else:
			report.append( 'email NOT SENT to submitter %s' % destPerson.flatten() )
	print ''.join(report)
	if session.flash is None:
		session.flash = '\n'.join(report)
	else:
		session.flash += '; ' + '; '.join(report)

######################################################################################################################################################################
# Send email to the recommenders (if any) for postprints
def do_send_email_to_recommender_postprint_status_changed(session, auth, db, articleId, newStatus):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article:
		linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=True)))
		for myRecomm in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, distinct=True):
			recommender_id = myRecomm['recommender_id']
			destPerson = mkUser(auth, db, recommender_id)
			destAddress = db.auth_user[myRecomm.recommender_id]['email']
			articleAuthors = article.authors
			articleTitle = article.title
			articleDoi = mkDOI(article.doi)
			tOldStatus = current.T(article.status)
			tNewStatus = current.T(newStatus)
			mySubject = '%s: Change in article status' % (appname)
			content = get_mail_template('recommender_postprint_status_changed.html') % locals()
			
			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu: 
				report.append( 'email sent to %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to %s' % destPerson.flatten() )
			time.sleep(mail_sleep)
	print ''.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
# Send email to the recommenders (if any)
def do_send_email_to_recommender_status_changed(session, auth, db, articleId, newStatus):
	#print 'do_send_email_to_recommender_status_changed'
	report = []
	mail = getMailer(auth)
	attach = []
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	recomm_limit_days=myconf.get('config.recomm_limit_days', default=50)
	article = db.t_articles[articleId]
	if article is not None:
		linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published)))
		for myRecomm0 in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, distinct=True):
			recommender_id = myRecomm0.recommender_id
			myRecomm = db((db.t_recommendations.article_id == articleId) & (db.t_recommendations.recommender_id==recommender_id)).select(orderby=db.t_recommendations.id).last()
			destPerson = mkUser(auth, db, recommender_id)
			destAddress = db.auth_user[myRecomm.recommender_id]['email']
			articleAuthors = article.authors
			articleTitle = article.title
			articleDoi = XML(mkSimpleDOI(article.doi))
			tOldStatus = current.T(article.status)
			tNewStatus = current.T(newStatus)
			if article.status == 'Awaiting revision' and newStatus == 'Under consideration':
				mySubject = '%s: Revised version' % (appname)
				mailManagers = A(myconf.take('contacts.managers'), _href='mailto:'+myconf.take('contacts.managers'))
				deadline = (datetime.date.today() + datetime.timedelta(weeks=1)).strftime('%a %b %d')
				# NOTE: include answer & track-change (append to "attach")
				closedRecomm = db((db.t_recommendations.article_id == articleId) & (db.t_recommendations.recommender_id==recommender_id) & (db.t_recommendations.is_closed==True)).select(orderby=db.t_recommendations.id).last()
				# write fields to temp files
				directory = os.path.join(os.path.dirname(__file__), '../../tmp/attachments')
				if not os.path.exists(directory):
					os.makedirs(directory)
				if closedRecomm:
					if closedRecomm.reply is not None and closedRecomm.reply != '':
						tmpR0 = os.path.join(directory, "Answer_%d.txt" % closedRecomm.id)
						f0=open(tmpR0, 'w+')
						f0.write(closedRecomm.reply)
						f0.close()					
						attach.append(mail.Attachment(tmpR0, content_id='Answer'))
						try:
							os.unlink(tmpR0)
						except:
							print('unable to delete temp file %s' % tmpR0)
							pass
					if closedRecomm.reply_pdf is not None and closedRecomm.reply_pdf != '':
						(fnR1, stream) = db.t_recommendations.reply_pdf.retrieve(closedRecomm.reply_pdf)
						tmpR1 = os.path.join(directory, str(uuid4()))
						with closing(stream) as src, closing(open(tmpR1, 'wb')) as dest:
							shutil.copyfileobj(src, dest)
						attach.append(mail.Attachment(tmpR1, fnR1))
						try:
							os.unlink(tmpR1)
						except:
							print('unable to delete temp file %s' % tmpR1)
							pass
					if closedRecomm.track_change is not None and closedRecomm.track_change != '':
						(fnTr, stream) = db.t_recommendations.track_change.retrieve(closedRecomm.track_change)
						tmpTr = os.path.join(directory, str(uuid4()))
						with closing(stream) as src, closing(open(tmpTr, 'wb')) as dest:
							shutil.copyfileobj(src, dest)
						attach.append(mail.Attachment(tmpTr, fnTr))
						try:
							os.unlink(tmpTr)
						except:
							print('unable to delete temp file %s' % tmpTr)
							pass

				content = get_mail_template('recommender_status_changed_to_under_consideration.html') % locals()

			elif newStatus == 'Recommended':
				mySubject = '%s: Article recommended' % (appname)
				myRefRecomm = mkRecommCitation(auth, db, myRecomm).flatten()
				myRefArticle  = mkArticleCitation(auth, db, myRecomm).flatten()
				linkRecomm = XML(URL(c='articles', f='rec', scheme=scheme, host=host, port=port, vars=dict(id=article.id)))
				doiRecomm = mkLinkDOI(myRecomm.recommendation_doi)
				content = get_mail_template('recommender_status_changed_under_to_recommended.html') % locals()
				
			else:
				mySubject = '%s: Change in article status' % (appname)
				content = get_mail_template('recommender_article_status_changed.html') % locals()

			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				if len(attach) > 0:
					mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
								attachments=attach,
							)
					# NOTE: delete attachment files -> see below
				else:
					mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
							)
			except:
				pass
			if mail_resu: 
				report.append( 'email sent to %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to %s' % destPerson.flatten() )
			time.sleep(mail_sleep)
	print ''.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



######################################################################################################################################################################
# Do send email to suggested recommenders for a given NO MORE available article
def do_send_email_to_suggested_recommenders_useless(session, auth, db, articleId):
	#print 'do_send_email_to_suggested_recommenders_useless'
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article:
		articleTitle = article.title
		if article.anonymous_submission:
			articleAuthors = current.T('[undisclosed]')
		else:
			articleAuthors = article.authors
		articleDoi = mkDOI(article.doi)
		mySubject = '%s: About our request to act as a recommender for a preprint' % (appname)
		#TODO: removing auth.user_id is not the best solution... Should transmit recommender_id
		suggestedQy = db( (db.t_suggested_recommenders.article_id==articleId) & (db.t_suggested_recommenders.suggested_recommender_id!=auth.user_id) & (db.t_suggested_recommenders.declined==False) & (db.t_suggested_recommenders.suggested_recommender_id==db.auth_user.id) ).select(db.t_suggested_recommenders.ALL, db.auth_user.ALL)
		for theUser in suggestedQy:
			destPerson = mkUser(auth, db, theUser['auth_user.id'])
			destAddress = db.auth_user[theUser['auth_user.id']]['auth_user.email']
			mailManagers = A(myconf.take('contacts.managers'), _href='mailto:'+myconf.take('contacts.managers'))
			#linkTarget=URL(c='recommender', f='my_awaiting_articles', scheme=scheme, host=host, port=port)
			#helpurl=URL(c='about', f='help_practical', scheme=scheme, host=host, port=port)
			# TODO: parallel submission
			content = get_mail_template('recommender_suggestion_not_needed_anymore.html')  % locals()
			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			
			suggRecom = db.t_suggested_recommenders[theUser['t_suggested_recommenders.id']]
			if suggRecom.emailing:
				emailing0 = suggRecom.emailing
			else:
				emailing0 = ''
			if mail_resu:
				emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="green">SENT</font></h2>'
			else:
				emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="red">NOT SENT</font></h2>'
			emailing += myMessage
			emailing += '<hr>'
			emailing += emailing0
			suggRecom.emailing = emailing
			suggRecom.update_record()
			
			if mail_resu:
				report.append( 'email sent to suggested recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to suggested recommender %s' % destPerson.flatten() )
			time.sleep(mail_sleep)
		print '\n'.join(report)
		if session.flash is None:
			session.flash = '; '.join(report)
		else:
			session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
# Do send email to suggested recommenders for a given available article
def do_send_email_to_suggested_recommenders(session, auth, db, articleId):
	print 'do_send_email_to_suggested_recommenders'
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article:
		articleTitle = article.title
		if article.anonymous_submission:
			articleAuthors = current.T('[undisclosed]')
		else:
			articleAuthors = article.authors
		articleDoi = mkDOI(article.doi)
		mySubject = '%s: Request to act as a recommender for a preprint' % (appname)
		suggestedQy = db.executesql('SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND sr.declined IS FALSE AND article_id=%s;', placeholders=[article.id], as_dict=True)
		for theUser in suggestedQy:
			destPerson = mkUser(auth, db, theUser['id'])
			destAddress = db.auth_user[theUser['id']]['email']
			linkTarget=XML(URL(c='recommender', f='article_details', vars=dict(articleId=article.id), scheme=scheme, host=host, port=port))
			helpurl=URL(c='about', f='help_generic', scheme=scheme, host=host, port=port)
			ethicsurl=URL(c='about', f='ethics', scheme=scheme, host=host, port=port)
			if article.parallel_submission:
				addNote = "<b>Note:</b> The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(appname)s, and hope you will agree to manage this preprint. If the authors abandon the process at %(appname)s after reviewers have written their reports, we will post the reviewers' reports on the %(appname)s website as recognition of the reviewers' work and in order to enable critical discussion.<p>" % locals()
			else:
				addNote = ""
			
			content = get_mail_template('recommender_suggested_article.html')  % locals()

			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			
			suggRecom = db.t_suggested_recommenders[theUser['sr_id']]
			if suggRecom.emailing:
				emailing0 = suggRecom.emailing
			else:
				emailing0 = ''
			if mail_resu:
				emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="green">SENT</font></h2>'
				suggRecom.email_sent = True
			else:
				emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="red">NOT SENT</font></h2>'
				suggRecom.email_sent = False
			emailing += myMessage
			emailing += '<hr>'
			emailing += emailing0
			suggRecom.emailing = emailing
			suggRecom.update_record()
			
			if mail_resu:
				#db.executesql('UPDATE t_suggested_recommenders SET email_sent=true WHERE id=%s', placeholders=[theUser['sr_id']])
				report.append( 'email sent to suggested recommender %s' % destPerson.flatten() )
			else:
				#db.executesql('UPDATE t_suggested_recommenders SET email_sent=false WHERE id=%s', placeholders=[theUser['sr_id']])
				report.append( 'email NOT SENT to suggested recommender %s' % destPerson.flatten() )
			time.sleep(mail_sleep)
		print '\n'.join(report)
		if session.flash is None:
			session.flash = '; '.join(report)
		else:
			session.flash += '; ' + '; '.join(report)

######################################################################################################################################################################
# Individual reminder for previous message
def do_send_reminder_email_to_suggested_recommender(session, auth, db, suggRecommId):
	print 'do_send_reminder_email_to_suggested_recommenders'
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	suggRecomm = db.t_suggested_recommenders[suggRecommId]
	if suggRecomm:
		article = db.t_articles[suggRecomm.article_id]
		if article:
			articleTitle = article.title
			if article.anonymous_submission:
				articleAuthors = current.T('[undisclosed]')
			else:
				articleAuthors = article.authors
			articleDoi = mkDOI(article.doi)
			linkTarget=XML(URL(c='recommender', f='article_details', vars=dict(articleId=article.id), scheme=scheme, host=host, port=port))
			helpurl=URL(c='about', f='help_generic', scheme=scheme, host=host, port=port)
			theUser = db.auth_user[suggRecomm.suggested_recommender_id]
			mySubject = '%s: Request to act as a recommender for a preprint (reminder)' % (appname)
			if theUser:
				destPerson = mkUser(auth, db, theUser['id'])
				destAddress = db.auth_user[theUser['id']]['email']
				content = get_mail_template('recommender_suggested_article_reminder.html')  % locals()
				try:
					myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
							)
				except:
					pass

				if suggRecomm.emailing:
					emailing0 = suggRecomm.emailing
				else:
					emailing0 = ''
				if mail_resu:
					emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="green">SENT</font></h2>'
				else:
					emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="red">NOT SENT</font></h2>'
				emailing += myMessage
				emailing += '<hr>'
				emailing += emailing0
				suggRecomm.emailing = emailing
				
				if mail_resu:
					suggRecomm.email_sent = True
					suggRecomm.update_record()
					report.append( 'email sent to suggested recommender %s' % destPerson.flatten() )
				else:
					suggRecomm.email_sent = False
					suggRecomm.update_record()
					report.append( 'email NOT SENT to suggested recommender %s' % destPerson.flatten() )

				time.sleep(mail_sleep)
				print '\n'.join(report)
				if session.flash is None:
					session.flash = '; '.join(report)
				else:
					session.flash += '; ' + '; '.join(report)




######################################################################################################################################################################
# Do send email to recommender when a review is re-opened
def do_send_email_to_reviewer_review_reopened(session, auth, db, reviewId, newForm):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			linkTarget = XML(URL(c='user', f='my_reviews', scheme=scheme, host=host, port=port))
			mySubject = '%s: Review modification' % (appname)
			articleTitle = B(article.title )
			if article.anonymous_submission:
				articleAuthors = current.T('[undisclosed]')
			else:
				articleAuthors = article.authors
			theUser = db.auth_user[rev.reviewer_id]
			if theUser:
				recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
				destPerson = mkUser(auth, db, rev.reviewer_id)
				destAddress = db.auth_user[rev.reviewer_id]['email']
				content = get_mail_template('reviewer_review_reopened.html') % locals()
				try:
					myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
					if newForm['emailing']:
						emailing0 = newForm['emailing']
					else:
						emailing0 = ''
					emailing = '<h2>'+str(datetime.datetime.now())+'</h2>'
					emailing += myMessage
					emailing += '<hr>'
					emailing += emailing0
					newForm['emailing'] = emailing
					#rev.update_record()
				except:
					pass
				if mail_resu:
					report.append( 'email sent to %s' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



######################################################################################################################################################################
# Do send email to recommender when a review is closed
def do_send_email_to_recommenders_review_closed(session, auth, db, reviewId):
	report = []
	attach = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published)))
			mySubject = '%s: Review completed' % (appname)
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				directory = os.path.join(os.path.dirname(__file__), '../../tmp/attachments')
				if not os.path.exists(directory):
					os.makedirs(directory)
				revText = ''
				if rev.review is not None and rev.review != '':
					revText = XML(WIKI(rev.review))
					tmpR0 = os.path.join(directory, "Review_%d.html" % rev.id)
					f0=open(tmpR0, 'w+')
					f0.write(revText.flatten())
					f0.close()					
					attach.append(mail.Attachment(tmpR0, content_id='Review'))
					try:
						os.unlink(tmpR0)
					except:
						print('unable to delete temp file %s' % tmpR0)
						pass
				if rev.review_pdf is not None and rev.review_pdf != '':
					(fnR1, stream) = db.t_reviews.review_pdf.retrieve(rev.review_pdf)
					tmpR1 = os.path.join(directory, str(uuid4()))
					with closing(stream) as src, closing(open(tmpR1, 'wb')) as dest:
						shutil.copyfileobj(src, dest)
					attach.append(mail.Attachment(tmpR1, fnR1))
					try:
						os.unlink(tmpR1)
					except:
						print('unable to delete temp file %s' % tmpR1)
						pass
				destPerson = mkUser(auth, db, recomm.recommender_id)
				destAddress = db.auth_user[recomm.recommender_id]['email']
				reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)

				content = get_mail_template('reviewer_review_closed.html') % locals()

				try:
					myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter(), revText=revText))
					if len(attach) > 0:
						mail_resu = mail.send(to=[destAddress],
									subject=mySubject,
									message=myMessage,
									attachments=attach,
								)
					else:
						mail_resu = mail.send(to=[destAddress],
									subject=mySubject,
									message=myMessage,
						)
				except:
					pass
				if mail_resu:
					report.append( 'email sent to %s' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)

######################################################################################################################################################################
# Do send email to recommender when a press review is accepted for consideration
def do_send_email_to_recommenders_press_review_considerated(session, auth, db, pressId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published)))
			mySubject = '%s: co-recommender accepted the recommendation' % (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = get_mail_template('recommenders_press_review_considerated.html') % locals()
			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
def do_send_email_to_recommenders_press_review_declined(session, auth, db, pressId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published)))
			mySubject = '%s: co-recommender declined the recommendation' % (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)

			content = get_mail_template('recommenders_press_review_declined.html') % locals()

			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)

######################################################################################################################################################################
def do_send_email_to_recommenders_press_review_agreement(session, auth, db, pressId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published)))
			mySubject = '%s: co-recommender agreed with the recommendation of the postprint' % (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)

			content = get_mail_template('recommenders_press_review_agreement.html') % locals()
			
			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
# Do send email to recommender when a review is accepted for consideration
def do_send_email_to_recommenders_review_considered(session, auth, db, reviewId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			if article.anonymous_submission:
				articleAuthors = current.T('[undisclosed]')
			else:
				articleAuthors = article.authors
			articleDoi = mkDOI(article.doi)
			linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published)))
			mySubject = '%s: Request to review accepted'% (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
			expectedDuration = datetime.timedelta(days=21) # three weeks
			dueTime = str((datetime.datetime.now() + expectedDuration).date())

			content = get_mail_template('recommenders_review_considered.html') % locals()
			
			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



######################################################################################################################################################################
def do_send_email_to_recommenders_review_declined(session, auth, db, reviewId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			if article.anonymous_submission:
				articleAuthors = current.T('[undisclosed]')
			else:
				articleAuthors = article.authors
			articleDoi = mkDOI(article.doi)
			linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published)))
			mySubject = '%s: Request to review declined' % (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)

			content = get_mail_template('recommenders_review_declined.html') % locals()

			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)





######################################################################################################################################################################
def do_send_email_to_reviewers_review_suggested(session, auth, db, reviewsList):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	for rev in db( (db.t_reviews.id.belongs(reviewsList)) & (db.t_reviews.review_state==None) ).select():
		if rev and rev.review_state is None:
			recomm = db.t_recommendations[rev.recommendation_id]
			if recomm:
				if recomm.recommender_id != rev.reviewer_id:
					article = db.t_articles[recomm['article_id']]
					if article:
						articleTitle = article.title
						if article.anonymous_submission:
							articleAuthors = current.T('[undisclosed]')
						else:
							articleAuthors = article.authors
						articleDoi = mkDOI(article.doi)
						linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
						mySubject = '%(appname)s: Invitation to review a preprint' % locals()
						destPerson = mkUser(auth, db, rev.reviewer_id)
						destAddress = db.auth_user[rev.reviewer_id]['email']
						recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)

						content = get_mail_template('reviewers_review_suggested.html') % locals()

						try:
							myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
							mail_resu = mail.send(to=[destAddress],
										subject=mySubject,
										message=myMessage,
									)
						except:
							pass
						if mail_resu:
							report.append( 'email sent to %s' % destPerson.flatten() )
							rev.review_state = 'Pending'
							rev.update_record()
						else:
							report.append( 'email NOT SENT to %s' % destPerson.flatten() )
						time.sleep(mail_sleep)
					else:
						print 'do_send_email_to_reviewers_review_suggested: Article not found'
				else:
					print 'do_send_email_to_reviewers_review_suggested: recommender = reviewer'
			else:
				print 'do_send_email_to_reviewers_review_suggested: Recommendation not found'
		else:
			print 'do_send_email_to_reviewers_review_suggested: Review not found'
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



######################################################################################################################################################################
def do_send_email_to_reviewers_cancellation(session, auth, db, articleId, newStatus):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article:
		articleTitle = article.title
		if article.anonymous_submission:
			articleAuthors = current.T('[undisclosed]')
		else:
			articleAuthors = article.authors
		articleDoi = mkDOI(article.doi)
		mySubject = '%s: About our request to act as reviewer for a preprint' % (appname)
		linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
		lastRecomm = db(db.t_recommendations.article_id == article.id).select(orderby=db.t_recommendations.id).last()
		if lastRecomm:
			reviewers = db( (db.t_reviews.recommendation_id == lastRecomm.id) & (db.t_reviews.review_state in ('Pending', 'Under consideration', 'Completed')) ).select()
			for rev in reviewers:
				if rev is not None and rev.reviewer_id is not None:
					destPerson = mkUser(auth, db, rev.reviewer_id)
					destAddress = db.auth_user[rev.reviewer_id]['email']
					recommenderPerson = mkUserWithMail(auth, db, lastRecomm.recommender_id)

					content = get_mail_template('reviewers_cancellation.html') % locals()

					try:
						myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
						mail_resu = mail.send(to=[destAddress],
									subject=mySubject,
									message=myMessage,
								)
					except:
						pass
					
					if rev.emailing:
						emailing0 = rev.emailing
					else:
						emailing0 = ''
					if mail_resu:
						emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="green">SENT</font></h2>'
					else:
						emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="red">NOT SENT</font></h2>'
					emailing += myMessage
					emailing += '<hr>'
					emailing += emailing0
					rev.emailing = emailing
					rev.review_state = 'Cancelled'
					rev.update_record()

					if mail_resu:
						report.append( 'email sent to %s' % destPerson.flatten() )
					else:
						report.append( 'email NOT SENT to %s' % destPerson.flatten() )
					time.sleep(mail_sleep)
		else:
			print 'do_send_email_to_reviewers_cancellation: Recommendation not found'
	else:
		print 'do_send_email_to_reviewers_cancellation: Article not found'

	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)
		



######################################################################################################################################################################
def do_send_mail_admin_new_user(session, auth, db, userId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	admins = db( (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == 'administrator') ).select(db.auth_user.ALL)
	dest = []
	for admin in admins:
		dest.append(admin.email)
	user = db.auth_user[userId]
	if user:
		userTxt = mkUser(auth, db, userId)
		userMail = user.email
		mySubject = '%s: A new user has signed up' % (appname)

		content = get_mail_template('admin_new_user.html') % locals()

		if len(dest)>0: #TODO: also check elsewhere
			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=dest,
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
	if mail_resu:
		report.append( 'email sent to administrators' )
	else:
		report.append( 'email NOT SENT to administrators' )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



######################################################################################################################################################################
def do_send_mail_new_user(session, auth, db, userId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	parallel_submission_allowed=myconf.get('config.parallel_submission', default=False)
	user = db.auth_user[userId]
	if type(user.thematics) is list:
		thema = user.thematics
	else:
		thema = [user.thematics]
	if type(user.alerts) is list:
		alerts = user.alerts
	else:
		if user.alerts:
			alerts = [user.alerts]
		else:
			alerts = ['[no alerts]']
	#print thema, alerts
	if user:
		destPerson = mkUser(auth, db, userId)
		destAddress = db.auth_user[userId]['email']
		baseurl=URL(c='about', f='about', scheme=scheme, host=host, port=port)
		infourl=URL(c='about', f='help_generic', scheme=scheme, host=host, port=port)
		recommurl=URL(c='public', f='recommenders', scheme=scheme, host=host, port=port)
		thematics = ', '.join(thema)
		days = ', '.join(alerts)
		mySubject = 'Welcome to %s' % (appname)

		if parallel_submission_allowed:
			content = get_mail_template('new_user_parallel_submission_allowed.html') % locals()
		else:
			content = get_mail_template('new_user.html') % locals()

		try:
			myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
		except:
			pass
		if mail_resu:
			report.append( 'email sent to new user %s' % destPerson.flatten() )
		else:
			report.append( 'email NOT SENT to new user %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



######################################################################################################################################################################
def do_send_mail_new_membreship(session, auth, db, membershipId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	user = db.auth_user[db.auth_membership[membershipId].user_id]
	group = db.auth_group[db.auth_membership[membershipId].group_id]
	if (user and group):
		destPerson = mkUser(auth, db, user.id)
		destAddress = db.auth_user[user.id]['email']
		if group.role == 'recommender':
			#thematics = ', '.join(user.thematics) if user.thematics and len(user.thematics)>0 else ''
			days = ', '.join(user.alerts)
			baseurl=URL(c='default', f='index', scheme=scheme, host=host, port=port)
			helpurl=URL(c='about', f='help_generic', scheme=scheme, host=host, port=port)
			ethicsurl=URL(c='about', f='ethics', scheme=scheme, host=host, port=port)
			mySubject = 'Welcome as a recommender of %s' % (appname)

			content = get_mail_template('new_membreship_recommender.html') % locals()

			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
							)
				time.sleep(mail_sleep)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to new recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to new recommender %s' % destPerson.flatten() )
			
		elif group.role == 'manager':
			mySubject = '%s: Welcome to The Managing Board' % (appname)
			
			content = get_mail_template('new_membreship_manager.html') % locals()

			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[user['email']],
								subject=mySubject,
								message=myMessage,
							)
				time.sleep(mail_sleep)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to new manager %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to new manager %s' % destPerson.flatten() )
			
		else:
			return
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
def do_send_email_to_managers(session, auth, db, articleId, newStatus):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	managers = db( (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == 'manager') ).select(db.auth_user.ALL)
	article = db.t_articles[articleId]
	if article:
		articleTitle = article.title
		articleAuthors = article.authors
		articleDoi = mkDOI(article.doi)
		if article.user_id:
			submitterPerson = mkUser(auth, db, article.user_id) # submitter
		else:
			submitterPerson = '?'
		
		if newStatus=='Pending':
			mySubject = '%s: Preprint submission requiring validation' % (appname)
			linkTarget = XML(URL(c='manager', f='pending_articles', scheme=scheme, host=host, port=port))
			content = get_mail_template('managers_preprint_submission.html') % locals()
			myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
		
		elif newStatus.startswith('Pre-'):
			recomm = db( (db.t_recommendations.article_id == articleId) ).select(orderby=db.t_recommendations.id).last()
			if recomm is not None:
				recommenderPerson = mkUser(auth, db, recomm.recommender_id) or '' # recommender
			else:
				recommenderPerson = '?'
			mySubject = '%s: Decision or recommendation requiring validation' % (appname)
			linkTarget = XML(URL(c='manager', f='pending_articles', scheme=scheme, host=host, port=port))
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = get_mail_template('managers_recommendation_or_decision.html') % locals()
			myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
		
		elif newStatus=='Under consideration':
			recomm = db( (db.t_recommendations.article_id == articleId) ).select(orderby=db.t_recommendations.id).last()
			if recomm is not None:
				recommenderPerson = mkUser(auth, db, recomm.recommender_id) or '' # recommender
			else:
				recommenderPerson = '?'
			linkTarget = XML(URL(c='manager', f='ongoing_articles', scheme=scheme, host=host, port=port))

			if article.status == 'Awaiting revision':
				mySubject = '%s: Article resubmitted' % (appname)
				content = get_mail_template('managers_article_resubmited.html') % locals()
			else:
				mySubject = '%s: Article considered for recommendation' % (appname)
				content = get_mail_template('managers_article_considered_for_recommendation.html') % locals()

			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
		
		elif newStatus=='Cancelled':
			mySubject = '%s: Article cancelled' % (appname)
			linkTarget = XML(URL(c='manager', f='completed_articles', scheme=scheme, host=host, port=port))
			content = get_mail_template('managers_article_cancelled.html') % locals()
			myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))

		else:
			mySubject = '%s: Article status changed' % (appname)
			linkTarget = XML(URL(c='manager', f='all_articles', scheme=scheme, host=host, port=port))
			tOldStatus = current.T(article.status)
			tNewStatus = current.T(newStatus)
			content = get_mail_template('managers_article_status_changed.html') % locals()

			myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))

		for manager in managers:
			try:
				mail_resu = mail.send(to=[manager.email],
							subject=mySubject,
							message=myMessage,
						)
			except Exception, e:
				raise(e)
			if mail_resu:
				report.append( 'email sent to manager '+(manager.email or '') )
			else:
				report.append( 'email NOT SENT to manager '+(manager.email or '') )
			time.sleep(mail_sleep)
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



######################################################################################################################################################################
#ok mais j'ai pas su s'il s'agissait des articles en général ou que des preprints
# si que preprints, remplacer article par preprint
def do_send_email_to_thank_recommender_postprint(session, auth, db, recommId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	recomm = db.t_recommendations[recommId]
	if recomm:
		article = db.t_articles[recomm.article_id]
		if article:
			articleTitle = article.title
			articleAuthors = article.authors
			articleDoi = mkDOI(article.doi)
			linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published)))
			mySubject = '%s: Thank you for initiating a recommendation!' % (appname)
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				#recommender = mkUser(auth, db, recomm.recommender_id)
				destPerson = mkUser(auth, db, recomm.recommender_id)
				if article.already_published:
					content = get_mail_template('recommender_thank_for_postprint.html') % locals()

				try:
					myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[theUser['email']],
								subject=mySubject,
								message=myMessage,
							)
				except:
					pass
				if mail_resu:
					report.append( 'email sent to %s' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
def do_send_email_to_thank_recommender_preprint(session, auth, db, articleId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	if articleId:
		article = db.t_articles[articleId]
		if article:
			articleTitle = article.title
			articleAuthors = article.authors
			articleDoi = mkDOI(article.doi)
			linkTarget = XML(URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=False)))
			mySubject = '%s: Thank you for initiating a recommendation!' % (appname)
			recomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				destPerson = mkUser(auth, db, theUser.id)
				
				if article.parallel_submission:
					content = get_mail_template('recommender_thank_for_preprint_parallel_submission.html') % locals()
				else:
					content = get_mail_template('recommender_thank_for_preprint.html') % locals()
					
				try:
					myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[theUser['email']],
								subject=mySubject,
								message=myMessage,
							)
				except:
					pass
				if mail_resu:
					report.append( 'email sent to %s' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)





######################################################################################################################################################################
def do_send_email_to_thank_reviewer(session, auth, db, reviewId, newForm):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	if rev:
		recomm = db.t_recommendations[rev.recommendation_id]
		if recomm:
			article = db.t_articles[recomm['article_id']]
			if article:
				articleTitle = article.title
				if article.anonymous_submission:
					articleAuthors = current.T('[undisclosed]')
				else:
					articleAuthors = article.authors
				articleDoi = mkDOI(article.doi)
				linkTarget = XML(URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=scheme, host=host, port=port))
				mySubject = '%s: Thank you for agreeing to review a preprint!' % (appname)
				theUser = db.auth_user[rev.reviewer_id]
				if theUser:
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
					destPerson = mkUser(auth, db, rev.reviewer_id)
					expectedDuration = datetime.timedelta(days=21) # three weeks
					dueTime = str((datetime.datetime.now() + expectedDuration).date())

					content = get_mail_template('reviewer_thank_for_review_acceptation.html') % locals()

					try:
						myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
						mail_resu = mail.send(to=[theUser['email']],
									subject=mySubject,
									message=myMessage,
								)
						if newForm['emailing']:
							emailing0 = newForm['emailing']
						else:
							emailing0= ''
						if mail_resu:
							emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="green">SENT</font></h2>'
						else:
							emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="red">NOT SENT</font></h2>'
						emailing += myMessage
						emailing += '<hr>'
						emailing += emailing0
						newForm['emailing'] = emailing
						#rev.update_record()
					except Exception, e:
						raise(e)
					if mail_resu:
						report.append( 'email sent to %s' % destPerson.flatten() )
					else:
						report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)

######################################################################################################################################################################
def do_send_email_to_thank_reviewer_after(session, auth, db, reviewId, newForm):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	contactMail = myconf.take('contacts.managers')
	rev = db.t_reviews[reviewId]
	if rev:
		recomm = db.t_recommendations[rev.recommendation_id]
		if recomm:
			article = db.t_articles[recomm['article_id']]
			if article:
				articleTitle = article.title
				if article.anonymous_submission:
					articleAuthors = current.T('[undisclosed]')
				else:
					articleAuthors = article.authors
				articleDoi = mkDOI(article.doi)
				linkTarget = XML(URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=scheme, host=host, port=port))
				mySubject = '%s: Thank you for evaluating a preprint' % (appname)
				theUser = db.auth_user[rev.reviewer_id]
				parallelText = ""
				if parallelSubmissionAllowed:
					parallelText += """Note that if the authors abandon the process at %(longname)s after reviewers have written their reports, we will post the reviewers' reports on the %(longname)s website as recognition of their work and in order to enable critical discussion.<p>"""
					if article.parallel_submission:
						parallelText += """Note: The authors have chosen to submit their manuscript elsewhere in parallel. We still believe it is useful to review their work at %(longname)s, and hope you will agree to review this preprint.<p>"""
				if theUser:
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
					destPerson = mkUser(auth, db, rev.reviewer_id)

					content = get_mail_template('reviewer_thank_for_review_done.html') % locals()

					try:
						myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
						mail_resu = mail.send(to=[theUser['email']],
									subject=mySubject,
									message=myMessage,
								)
						if newForm['emailing']:
							emailing0 = newForm['emailing']
						else:
							emailing0= ''
						if mail_resu:
							emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="green">SENT</font></h2>'
						else:
							emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="red">NOT SENT</font></h2>'
						emailing += myMessage
						emailing += '<hr>'
						emailing += emailing0
						newForm['emailing'] = emailing
						#rev.update_record()
					except Exception, e:
						raise(e)
					if mail_resu:
						report.append( 'email sent to %s' % destPerson.flatten() )
					else:
						report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)

######################################################################################################################################################################
def do_send_email_to_delete_one_contributor(session, auth, db, contribId):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	managers=myconf.take('contacts.managers')
	if contribId:
		contrib = db.t_press_reviews[contribId]
		if contrib:
			recomm = db.t_recommendations[contrib.recommendation_id]
			if recomm:
				article = db.t_articles[recomm.article_id]
				if article:
					articleTitle = article.title
					if article.anonymous_submission:
						articleAuthors = current.T('[undisclosed]')
					else:
						articleAuthors = article.authors
					articleDoi = mkDOI(article.doi)
					articlePrePost = 'postprint' if article.already_published else 'preprint'
					linkTarget = URL(c='recommender', f='my_co_recommendations', scheme=scheme, host=host, port=port)
					mySubject = '%(appname)s: Your co-recommendation of a %(articlePrePost)s' % locals()
					destPerson = mkUser(auth, db, contrib.contributor_id)
					destAddress = db.auth_user[contrib.contributor_id]['email']
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''

					content = get_mail_template('contributor_removed_from_article.html') % locals()

					try:
						myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
						mail_resu = mail.send(to=[destAddress],
										subject=mySubject,
										message=myMessage,
									)
					except:
						pass
					if mail_resu:
						report.append( 'email sent to contributor %s' % destPerson.flatten() )
					else:
						report.append( 'email NOT SENT to contributor %s' % destPerson.flatten() )
					time.sleep(mail_sleep)
					print '\n'.join(report)
					if session.flash is None:
						session.flash = '; '.join(report)
					else:
						session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
def do_send_email_to_one_contributor(session, auth, db, contribId):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	managers=myconf.take('contacts.managers')
	if contribId:
		contrib = db.t_press_reviews[contribId]
		if contrib:
			recomm = db.t_recommendations[contrib.recommendation_id]
			if recomm:
				article = db.t_articles[recomm.article_id]
				if article:
					articleTitle = article.title
					if article.anonymous_submission:
						articleAuthors = current.T('[undisclosed]')
					else:
						articleAuthors = article.authors
					articleDoi = mkDOI(article.doi)
					articlePrePost = 'postprint' if article.already_published else 'preprint'
					linkTarget = XML(URL(c='recommender', f='my_co_recommendations', scheme=scheme, host=host, port=port))
					mySubject = '%(appname)s: Your co-recommendation of a %(articlePrePost)s' % locals()
					destPerson = mkUser(auth, db, contrib.contributor_id)
					destAddress = db.auth_user[contrib.contributor_id]['email']
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
					ethicsLink = URL('about', 'ethics', scheme=scheme, host=host, port=port)

					if article.status in ('Under consideration', 'Pre-recommended'):
						if article.already_published:
							content = get_mail_template('contributor_added_on_article_already_published.html') % locals()
						else:
							content = get_mail_template('contributor_added_on_preprint.html') % locals()
						
						try:
							myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
							mail_resu = mail.send(to=[destAddress],
											subject=mySubject,
											message=myMessage,
										)
						except:
							pass
						if mail_resu:
							report.append( 'email sent to contributor %s' % destPerson.flatten() )
						else:
							report.append( 'email NOT SENT to contributor %s' % destPerson.flatten() )
							
						time.sleep(mail_sleep)
						print '\n'.join(report)
						if session.flash is None:
							session.flash = '; '.join(report)
						else:
							session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
def do_send_email_to_contributors(session, auth, db, articleId, newStatus):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	managers=myconf.take('contacts.managers')
	article = db.t_articles[articleId]
	recomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
	if recomm:
		contribs = db(db.t_press_reviews.recommendation_id==recomm.id).select()
		articleTitle = article.title
		if article.anonymous_submission:
			articleAuthors = current.T('[undisclosed]')
		else:
			articleAuthors = article.authors
		articleDoi = mkDOI(article.doi)
		articlePrePost = 'postprint' if article.already_published else 'preprint'
		tOldStatus = current.T(article.status)
		tNewStatus = current.T(newStatus)
		linkTarget = XML(URL(c='recommender', f='my_co_recommendations', scheme=scheme, host=host, port=port))
		recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
		mySubject = '%(appname)s: Your co-recommendation of a %(articlePrePost)s' % locals()
		for contrib in contribs:
			destPerson = mkUser(auth, db, contrib.contributor_id)
			dest = db.auth_user[contrib.contributor_id]
			if dest:
				destAddress = dest['email']
			else:
				destAddress = ''
			
			if newStatus == 'Recommended':
				recommDOI = mkLinkDOI(recomm.recommendation_doi)
				linkRecomm = XML(URL(c='articles', f='rec', vars=dict(id=article.id), scheme=scheme, host=host, port=port))
				content = get_mail_template('contributors_article_recommended.html') % locals()
			
			else:
				content = get_mail_template('contributors_article_status_changed.html') % locals()
		
			try:
				myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
							)
			except Exception, e:
				raise(e)
			if mail_resu:
				report.append( 'email sent to contributor %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to contributor %s' % destPerson.flatten() )
			time.sleep(mail_sleep)
	
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)

######################################################################################################################################################################
def alert_new_recommendations(session, auth, db, userId, msgArticles):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	destPerson = mkUser(auth, db, userId)
	destAddress = db.auth_user[userId]['email']
	mySubject = '%s: New recommendations of %s' % (appname, applongname)
	 #TODO: (in the fields for which you have requested alerts)
	content = get_mail_template('alert_new_recommendations.html') % locals()
	
	if destAddress:
		try:
			myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
		except:
			pass
		if mail_resu:
			report.append( 'email sent to %s' % destPerson.flatten() )
			print 'INFO automatic alert email sent to %s' % destPerson.flatten() 
		else:
			report.append( 'email NOT SENT to %s' % destPerson.flatten() )
			print 'INFO automatic alert email NOT SENT to %s' % destPerson.flatten() 
		#print '\n'.join(report)
	if session:
		if session.flash is None:
			session.flash = '; '.join(report)
		else:
			session.flash += '; ' + '; '.join(report)
	

######################################################################################################################################################################
def do_send_email_decision_to_reviewers(session, auth, db, articleId, newStatus):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	recomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			articleStatus = current.T(newStatus)
			linkTarget = XML(URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=scheme, host=host, port=port))
			myRefArticle = mkArticleCitation(auth, db, recomm)
			myRefRecomm  = mkRecommCitation(auth, db, recomm)
			mySubject = '%s: Decision on preprint you reviewed' % (appname)
			if newStatus == 'Recommended':
				reviewers = db( (db.auth_user.id == db.t_reviews.reviewer_id) & (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == article.id) & (db.t_reviews.review_state=='Completed') ).select(db.t_reviews.id, db.auth_user.ALL)
			else:
				reviewers = db( (db.auth_user.id == db.t_reviews.reviewer_id) & (db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state=='Completed') ).select(db.t_reviews.id, db.auth_user.ALL)
			for rev in reviewers:
				review = db.t_reviews[rev.t_reviews.id]
				destPerson = mkUser(auth, db, rev.auth_user.id)

				if newStatus == 'Recommended':
					recommDOI = mkLinkDOI(recomm.recommendation_doi)
					linkRecomm = XML(URL(c='articles', f='rec', vars=dict(id=article.id), scheme=scheme, host=host, port=port))
					content = get_mail_template('reviewers_article_recommended.html') % locals()
				else:
					content = get_mail_template('reviewers_article_status_changed.html') % locals()

				try:
					myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[rev.auth_user.email],
								subject=mySubject,
								message=myMessage,
							)
					if review.emailing:
						emailing0 = review.emailing
					else:
						emailing0= ''
					#emailing = '<h2>'+str(datetime.datetime.now())+'</h2>'
					if mail_resu:
						emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="green">SENT</font></h2>'
					else:
						emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="red">NOT SENT</font></h2>'
						#review.review_state = ''
					emailing += myMessage
					emailing += '<hr>'
					emailing += emailing0
					review.emailing = emailing
					review.update_record()
				except:
					pass
				if mail_resu:
					report.append( 'email sent to %s' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to %s' % destPerson.flatten() )
				time.sleep(mail_sleep)
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


######################################################################################################################################################################
def do_send_personal_email_to_reviewer(session, auth, db, reviewId, replyto, cc, subject, message, reset_password_key=None, linkTarget=None):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	#managers=myconf.take('contacts.managers')
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	review = db.t_reviews[reviewId]
	if review:
		recomm = db.t_recommendations[review.recommendation_id]
		if recomm:
			rev = db.auth_user[review['reviewer_id']]
			if rev:
				destPerson = mkUser(auth, db, review.reviewer_id)
				myMessage = DIV(WIKI(message))
				if reset_password_key:
					if linkTarget:
						link = URL(a=None, c='default', f='user', args='reset_password', vars=dict(key=reset_password_key, _next=linkTarget), scheme=scheme, host=host, port=port)
					else:
						link = URL(a=None, c='default', f='user', args='reset_password', vars=dict(key=reset_password_key), scheme=scheme, host=host, port=port)
					myMessage.append(P())
					myMessage.append(P(B(current.T('TO ACCEPT OR DECLINE CLICK ON THE FOLLOWING LINK:'))))
					myMessage.append(A(link, _href=link))
					myMessage.append(P(B(current.T('THEN GO TO "Requests for input —> Do you agree to review a preprint?" IN THE TOP MENU'))))
				elif linkTarget:
					myMessage.append(P())
					if review.review_state is None or review.review_state == 'Pending' or review.review_state == '':
						myMessage.append(P(B(current.T('TO ACCEPT OR DECLINE CLICK ON THE FOLLOWING LINK:'))))
						myMessage.append(A(linkTarget, _href=linkTarget))
					elif review.review_state == 'Under consideration':
						myMessage.append(P(B(current.T('TO WRITE, EDIT OR UPLOAD YOUR REVIEW CLICK ON THE FOLLOWING LINK:'))))
						myMessage.append(A(linkTarget, _href=linkTarget))
				try:
					myRenderedMessage = render(filename=mail_layout, context=dict(content=XML(myMessage), footer=mkFooter()))
					mail_resu = mail.send(to=[rev['email']],
								cc=[cc, replyto],
								#bcc=managers,
								reply_to=replyto,
								subject=subject,
								message=myRenderedMessage,
							)
				except Exception, e:
					pass
				if review.emailing:
					emailing0 = review.emailing
				else:
					emailing0 = ''
				if mail_resu:
					emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="green">SENT</font></h2>'
					if (review.review_state is None):
						review.review_state = 'Pending'
				else:
					emailing = '<h2>'+str(datetime.datetime.now())+' -- <font color="red">NOT SENT</font></h2>'
					#review.review_state = ''
				emailing += myRenderedMessage
				emailing += '<hr>'
				emailing += emailing0
				review.emailing = emailing
				review.update_record()
				if mail_resu:
					report.append( 'email sent to "%s"' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to "%s"' % destPerson.flatten() )
				time.sleep(mail_sleep)
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



######################################################################################################################################################################
# RESET PASSWORD EMAIL
def do_send_email_to_reset_password(session, auth, db, userId):
	mail = getMailer(auth)
	report = []
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	destPerson = mkUser(auth, db, userId)
	destAddress = db.auth_user[userId]['email']
	fkey = db.auth_user[userId]['reset_password_key']
	mySubject = "%s: Password changed" % (applongname)
	siteName = I(applongname)
	linkTarget = URL(c='default', f='user', args=['reset_password'], scheme=scheme, host=host, port=port, vars=dict(key=fkey)) # default/user/reset_password?key=1561727068-2946ea7b-54fe-4caa-87af-9c5e459b3487.
	linkTargetA = A(linkTarget, _href=linkTarget)
	content = get_mail_template('user_reset_password.html') % locals()
	try:
		myMessage = render(filename=mail_layout, context=dict(content=XML(content), footer=mkFooter()))
		mail_resu = mail.send(to=[destAddress],
					subject=mySubject,
					message=myMessage,
				)
	except Exception, e :
		print "Traceback: %s" % traceback.format_exc()
	if mail_resu:
		report.append( 'email sent to %s' % destPerson.flatten() )
	else:
		report.append( 'email NOT SENT to %s' % destPerson.flatten() )
	print ''.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


