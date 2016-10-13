# -*- coding: utf-8 -*-

import os
import datetime
from re import sub, match
from copy import deepcopy
import datetime
from dateutil.relativedelta import *

from gluon import current
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail

from gluon.custom_import import track_changes; track_changes(True)
from common import *

myconf = AppConfig(reload=True)

def getMailer(auth):
	mail = auth.settings.mailer
	mail.settings.server = myconf.get('smtp.server')
	mail.settings.sender = myconf.get('smtp.sender')
	mail.settings.login = myconf.get('smtp.login')
	mail.settings.tls = myconf.get('smtp.tls') or False
	mail.settings.ssl = myconf.get('smtp.ssl') or False
	return mail


#TODO : make a footer function instead of copying all the stuff in views


# Send email to the requester (if any)
def do_send_email_to_requester(session, auth, db, articleId, newStatus):
	report = []
	mail_resu = False
	article = db.t_articles[articleId]
	if article:
		mail = getMailer(auth)
		person = mkUser(auth, db, article.user_id)
		context = dict(
						appname=myconf.take('app.name'), 
						applongname=myconf.take('app.longname'), 
						appdesc=myconf.take('app.description'),
						appthematics=myconf.take('app.thematics'),
						baseurl=URL(c='default', f='index', scheme=True, host=True), 
						helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
						ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
						profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
						target='', 
						article=article,
						doi=mkDOI(article.doi),
						person=person,
						newStatus=newStatus,
					)
		context['target']=URL(c='user', f='my_articles', scheme=True, host=True) # default
		if article.status=='Pending' and newStatus=='Awaiting consideration':
			mySubject = '%s: New recommendation request' % (myconf.take('app.longname'))
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_validated.html')
		elif article.status=='Awaiting consideration' and newStatus=='Under consideration':
			context['target']=URL(c='user', f='my_articles', scheme=True, host=True)
			mySubject = '%s: Recommendation request considered' % (myconf.take('app.longname'))
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_considered.html')
		elif article.status!=newStatus and newStatus=='Cancelled':
			context['target']=URL(c='user', f='my_articles', scheme=True, host=True)
			mySubject = '%s: Recommendation request cancelled' % (myconf.take('app.longname'))
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_cancelled.html')
		elif article.status!=newStatus and newStatus=='Rejected':
			mySubject = '%s: Recommendation request rejected' % (myconf.take('app.longname'))
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_rejected.html')
			context['target']=URL(c='user', f='my_articles', scheme=True, host=True)
			context['recommurl'] = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			context['recommendation'] = mkRecommendedArticle(auth, db, article, True) or ''
		elif article.status!=newStatus and newStatus=='Awaiting revision':
			mySubject = '%s: Recommendation request awaiting revision' % (myconf.take('app.longname'))
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_askrevision.html')
			context['target']=URL(c='user', f='my_articles', scheme=True, host=True)
			context['recommurl'] = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			context['recommendation'] = mkRecommendedArticle(auth, db, article, True) or ''
		elif article.status!=newStatus and newStatus=='Pre-recommended':
			return # patience!
		elif article.status!=newStatus and newStatus=='Recommended':
			mySubject = '%s: Recommendation request recommended!' % (myconf.take('app.longname'))
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_recommended.html')
			context['target']=URL(c='public', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			context['recommurl'] = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			context['recommendation'] = mkRecommendedArticle(auth, db, article, True) or ''
		elif article.status!=newStatus:
			mySubject = '%s: Request status changed' % (myconf.take('app.longname'))
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_status_changed.html')
		else:
			return
		myMessage = render(filename=filename, context=context)
		destId = article['user_id']
		if destId is None: return
		destEmail = db.auth_user[destId]['email']
		if destEmail:
			try:
				mail_resu = mail.send(to=[destEmail],
						subject=mySubject,
						message=myMessage,
					)
			except:
				print 'planté !'
				pass
		if mail_resu:
			report.append( 'email to requester %s sent' % person.flatten() )
		else:
			report.append( 'email to requester %s NOT SENT' % person.flatten() )
	print ''.join(report)
	if session.flash is None:
		session.flash = '\n'.join(report)
	else:
		session.flash += '\n'.join(report)




# Send email to the recommenders (if any)
def do_send_email_to_recommender(session, auth, db, articleId, newStatus):
	report = []
	mail_resu = False
	article = db.t_articles[articleId]
	if article:
		mail = getMailer(auth)
		mySubject = '%s: Request status changed' % (myconf.take('app.longname'))
		target = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
		for myRecomm in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, distinct=True):
			recommender_id = myRecomm['recommender_id']
			person = mkUser(auth, db, recommender_id)
			context = dict(
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
							newStatus=newStatus, 
						)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_status_changed.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[db.auth_user[recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
			except:
				print 'planté !'
				pass
			if mail_resu:
				report.append( 'email to recommender %s sent' % person.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % person.flatten() )
	print ''.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



# Do send email to suggested recommenders for a given article
def do_send_email_to_suggested_recommenders(session, auth, db, articleId):
	print 'do_send_email_to_suggested_recommenders'
	report = []
	mail_resu = False
	article = db.t_articles[articleId]
	if article:
		mail = getMailer(auth)
		mySubject = '%s: Recommendation request suggested' % (myconf.take('app.longname'))
		suggestedQy = db.executesql('SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND article_id=%s;', placeholders=[article.id], as_dict=True)
		for theUser in suggestedQy:
			person = mkUser(auth, db, theUser['id'])
			target=URL(c='recommender', f='my_awaiting_articles', scheme=True, host=True)
			context = dict(
						appname=myconf.take('app.name'), 
						applongname=myconf.take('app.longname'), 
						appdesc=myconf.take('app.description'),
						appthematics=myconf.take('app.thematics'),
						baseurl=URL(c='default', f='index', scheme=True, host=True), 
						helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
						ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
						profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
						target=target, 
						article=article,
						doi=mkDOI(article.doi),
						person=person,
				)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_suggest_recommendation.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[theUser['email']],
							subject=mySubject,
							message=myMessage,
						)
			except:
				print 'planté !'
				pass
			if mail_resu:
				db.executesql('UPDATE t_suggested_recommenders SET email_sent=true WHERE id=%s', placeholders=[theUser['sr_id']])
				report.append( 'email to suggested recommender %s sent' % person.flatten() )
			else:
				db.executesql('UPDATE t_suggested_recommenders SET email_sent=false WHERE id=%s', placeholders=[theUser['sr_id']])
				report.append( 'email to suggested recommender %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



# Do send email to recommender when a review is re-opened
def do_send_email_to_reviewer_review_reopened(session, auth, db, reviewId):
	report = []
	mail_resu = False
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			mail = getMailer(auth)
			target = URL(c='user', f='my_reviews', scheme=True, host=True)
			mySubject = '%s: Review re-opened' % (myconf.take('app.longname'))
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				recommender = mkUser(auth, db, recomm.recommender_id)
				person=mkUserWithMail(auth, db, rev.reviewer_id)
				context = dict(
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
						)
				filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_reopened.html')
				myMessage = render(filename=filename, context=context)
				try:
					mail_resu = mail.send(to=[theUser['email']],
								subject=mySubject,
								message=myMessage,
							)
				except:
					print 'planté !'
					pass
				if mail_resu:
					report.append( 'email to reviewer %s sent' % person.flatten() )
				else:
					report.append( 'email to reviewer %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)




# Do send email to recommender when a review is closed
def do_send_email_to_recommenders_review_closed(session, auth, db, reviewId):
	report = []
	mail_resu = False
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			mail = getMailer(auth)
			target = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Review terminated' % (myconf.take('app.longname'))
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				person = mkUser(auth, db, recomm.recommender_id)
				reviewer=mkUserWithMail(auth, db, rev.reviewer_id)
				context = dict(
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
							reviewer=reviewer,
						)
				filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_done.html')
				myMessage = render(filename=filename, context=context)
				try:
					mail_resu = mail.send(to=[theUser['email']],
								subject=mySubject,
								message=myMessage,
							)
				except:
					print 'planté !'
					pass
				if mail_resu:
					report.append( 'email to recommender %s sent' % person.flatten() )
				else:
					report.append( 'email to recommender %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


# Do send email to recommender when a press review is accepted for consideration
def do_send_email_to_recommenders_press_review_considerated(session, auth, db, pressId):
	report = []
	mail_resu = False
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			mail = getMailer(auth)
			target = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Press review considered' % (myconf.take('app.longname'))
			person = mkUser(auth, db, recomm.recommender_id)
			contributor = mkUserWithMail(auth, db, press.contributor_id)
			context = dict(
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
							#recommender=recommender,
							contributor=contributor,
						)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_considerated.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
			except:
				print 'planté !'
				pass
			if mail_resu:
				report.append( 'email to recommender %s sent' % person.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)

def do_send_email_to_recommenders_press_review_declined(session, auth, db, pressId):
	report = []
	mail_resu = False
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			mail = getMailer(auth)
			target = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Press review declined' % (myconf.take('app.longname'))
			person = mkUser(auth, db, recomm.recommender_id)
			contributor = mkUserWithMail(auth, db, press.contributor_id)
			context = dict(
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
							recommender=recommender,
							contributor=contributor,
						)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_declined.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
			except:
				print 'planté !'
				pass
			if mail_resu:
				report.append( 'email to recommender %s sent' % person.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


def do_send_email_to_recommenders_press_review_agreement(session, auth, db, pressId):
	report = []
	mail_resu = False
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			mail = getMailer(auth)
			target = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Press review agreed' % (myconf.take('app.longname'))
			person = mkUser(auth, db, recomm.recommender_id)
			contributor = mkUserWithMail(auth, db, press.contributor_id)
			context = dict(
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
							#recommender=recommender,
							contributor=contributor,
						)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_agreed.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
			except:
				print 'planté !'
				pass
			if mail_resu:
				report.append( 'email to recommender %s sent' % person.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


# Do send email to recommender when a review is accepted for consideration
def do_send_email_to_recommenders_review_considered(session, auth, db, reviewId):
	report = []
	mail_resu = False
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			mail = getMailer(auth)
			target = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Review considered'% (myconf.take('app.longname'))
			person = mkUser(auth, db, recomm.recommender_id)
			reviewer = mkUserWithMail(auth, db, rev.reviewer_id)
			context = dict(
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
							#recommender=recommender,
							reviewer=reviewer,
						)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_considerated.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
			except:
				print 'planté !'
				pass
			if mail_resu:
				report.append( 'email to recommender %s sent' % person.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_email_to_recommenders_review_declined(session, auth, db, reviewId):
	report = []
	mail_resu = False
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			mail = getMailer(auth)
			target = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Review declined' % (myconf.take('app.longname'))
			person = mkUser(auth, db, recomm.recommender_id)
			reviewer = mkUserWithMail(auth, db, rev.reviewer_id)
			context = dict(
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
							recommender=recommender,
							reviewer=reviewer,
						)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_declined.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
			except:
				print 'planté !'
				pass
			if mail_resu:
				report.append( 'email to recommender %s sent' % person.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_email_to_reviewer_review_suggested(session, auth, db, reviewId):
	report = []
	mail_resu = False
	print ''
	rev = db.t_reviews[reviewId]
	if rev:
		recomm = db.t_recommendations[rev.recommendation_id]
		if recomm:
			article = db.t_articles[recomm['article_id']]
			if article:
				mail = getMailer(auth)
				target = URL(c='user', f='my_reviews', scheme=True, host=True)
				mySubject = '%s: Review suggested' % (myconf.take('app.longname'))
				person = mkUser(auth, db, rev.reviewer_id)
				recommender = mkUserWithMail(auth, db, recomm.recommender_id)
				context = dict(
								appname=myconf.take('app.name'), 
								applongname=myconf.take('app.longname'), 
								appdesc=myconf.take('app.description'),
								appthematics=myconf.take('app.thematics'),
								baseurl=URL(c='default', f='index', scheme=True, host=True), 
								helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
								ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
								profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
								target=target, 
								article=article,
								doi=mkDOI(article.doi),
								person=person,
								recommender=recommender,
							)
				filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_suggested.html')
				myMessage = render(filename=filename, context=context)
				try:
					mail_resu = mail.send(to=[db.auth_user[rev.reviewer_id]['email']],
								subject=mySubject,
								message=myMessage,
							)
				except:
					print 'planté !'
					pass
				if mail_resu:
					report.append( 'email to reviewer %s sent' % person.flatten() )
				else:
					report.append( 'email to reviewer %s NOT SENT' % person.flatten() )
			else:
				print 'do_send_email_to_reviewer_review_suggested: Article not found'
		else:
			print 'do_send_email_to_reviewer_review_suggested: Recommendation not found'
	else:
		print 'do_send_email_to_reviewer_review_suggested: Review not found'
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


def do_send_email_to_reviewer_contribution_suggested(session, auth, db, pressId):
	report = []
	mail_resu = False
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			mail = getMailer(auth)
			target = URL(c='user', f='my_press_reviews', scheme=True, host=True)
			mySubject = '%s: Contribution to press review suggested' % (myconf.take('app.longname'))
			person = mkUser(auth, db, press.contributor_id)
			recommender = mkUserWithMail(auth, db, recomm.recommender_id)
			context = dict(
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
							recommender=recommender,
						)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_suggested.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[db.auth_user[press.contributor_id]['email']],
								subject=mySubject,
								message=myMessage,
							)
			except:
				print 'planté !'
				pass
			if mail_resu:
				report.append( 'email to contributor %s sent' % person.flatten() )
			else:
				report.append( 'email to contributor %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_mail_new_user(session, auth, db, userId):
	report = []
	mail_resu = False
	user = db.auth_user[userId]
	if user:
		mail = getMailer(auth)
		person = mkUser(auth, db, userId)
		mySubject = 'Welcome to %s' % (myconf.take('app.longname'))
		context = dict(
						person = person,
						baseurl=URL(c='default', f='index', scheme=True, host=True), 
						profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
						appname=myconf.take('app.name'), 
						applongname=myconf.take('app.longname'), 
						appdesc=myconf.take('app.description'),
						appthematics=myconf.take('app.thematics'),
						thematics = ', '.join(user.thematics),
						days = ', '.join(user.alerts),
					)
		filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_user.html')
		myMessage = render(filename=filename, context=context)
		try:
			mail_resu = mail.send(to=[user['email']],
							subject=mySubject,
							message=myMessage,
						)
		except:
			print 'planté !'
			pass
		if mail_resu:
			report.append( 'email to new user %s sent' % person.flatten() )
		else:
			report.append( 'email to new user %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_mail_new_membreship(session, auth, db, membershipId):
	report = []
	mail_resu = False
	user = db.auth_user[db.auth_membership[membershipId].user_id]
	group = db.auth_group[db.auth_membership[membershipId].group_id]
	if user and group:
		mail = getMailer(auth)
		person = mkUser(auth, db, user.id)
		if group.role == 'recommender':
			mySubject = '%s: Welcome to recommendation board' % (myconf.take('app.longname'))
			context = dict (
							person = person,
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_recommender', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							thematics = ', '.join(user.thematics),
							days = ', '.join(user.alerts),
						)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_recommender.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[user['email']],
								subject=mySubject,
								message=myMessage,
							)
			except:
				print 'planté !'
				pass
			if mail_resu:
				report.append( 'email to new recommender %s sent' % person.flatten() )
			else:
				report.append( 'email to new recommender %s NOT SENT' % person.flatten() )
			
		elif group.role == 'manager':
			mySubject = '%s: Welcome to management board' % (myconf.take('app.longname'))
			context = dict (
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							person = person,
							thematics = ', '.join(user.thematics),
							days = ', '.join(user.alerts),
						)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_manager.html')
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=[user['email']],
								subject=mySubject,
								message=myMessage,
							)
			except:
				print 'planté !'
				pass
			if mail_resu:
				report.append( 'email to new manager %s sent' % person.flatten() )
			else:
				report.append( 'email to new manager %s NOT SENT' % person.flatten() )
			
		else:
			return



def do_send_email_to_managers(session, auth, db, articleId):
	report = []
	mail_resu = False
	managers = db( (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == 'manager') ).select(db.auth_user.ALL)
	dest = []
	for manager in managers:
		dest.append(manager.email)
	article = db.t_articles[articleId]
	if article:
		if article.user_id:
			mail = getMailer(auth)
			if article.status == 'Pending':
				person = mkUser(auth, db, article.user_id) # submitter
				mySubject = '%s: New recommendation request' % (myconf.take('app.longname'))
				filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_request.html')
			elif article.status == 'Pre-recommended':
				recomm = db( (db.t_recommendations.article_id == articleId) & (db.t_recommendations.is_closed == False) ).select().first()
				person = mkUser(auth, db, recomm.recommender_id) # submitter
				mySubject = '%s: New recommendation' % (myconf.take('app.longname'))
				filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_recommendation.html')
			target = URL(c='manage', f='pending_articles', scheme=True, host=True)
			context = dict (
							appname=myconf.take('app.name'), 
							applongname=myconf.take('app.longname'), 
							appdesc=myconf.take('app.description'),
							appthematics=myconf.take('app.thematics'),
							baseurl=URL(c='default', f='index', scheme=True, host=True), 
							helpurl=URL(c='about', f='help_manager', scheme=True, host=True), 
							ethicsurl=URL(c='about', f='ethics', scheme=True, host=True), 
							profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True),
							target=target, 
							article=article,
							doi=mkDOI(article.doi),
							person=person,
						)
			myMessage = render(filename=filename, context=context)
			try:
				mail_resu = mail.send(to=dest,
								subject=mySubject,
								message=myMessage,
							)
			except:
				print 'planté !'
				pass
	if mail_resu:
		report.append( 'email to new managers sent' )
	else:
		report.append( 'email to new managers NOT SENT' )

