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


myconf = AppConfig(reload=True)

def getMailer(auth):
	mail = auth.settings.mailer
	mail.settings.server = myconf.get('smtp.server')
	mail.settings.sender = myconf.get('smtp.sender')
	mail.settings.login = myconf.get('smtp.login')
	mail.settings.tls = myconf.get('smtp.tls') or False
	mail.settings.ssl = myconf.get('smtp.ssl') or False
	return mail

# Send email to the requester (if any)
def do_send_email_to_requester(session, auth, db, articleId, newStatus):
	report = []
	mail_resu = False
	article = db.t_articles[articleId]
	if article:
		mail = getMailer(auth)
		mySubject = '%s: Request status changed' % (myconf.take('app.name'))
		target = URL(c='user', f='my_articles', scheme=True, host=True)
		person = mkUser(auth, db, article.user_id)
		context = dict(article=article, newStatus=newStatus, target=target, person=person)
		filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_status_changed.html')
		myMessage = render(filename=filename, context=context)
		destId = article['user_id']
		if destId is None: return
		destEmail = db.auth_user[destId]['email']
		if destEmail:
			mail_resu = mail.send(to=[destEmail],
					subject=mySubject,
					message=myMessage,
				)
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
		mySubject = '%s: Request status changed' % (myconf.take('app.name'))
		target = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
		for myRecomm in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, distinct=True):
			recommender_id = myRecomm['recommender_id']
			person = mkUser(auth, db, recommender_id)
			context = dict(article=article, newStatus=newStatus, target=target, person=person)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_status_changed.html')
			myMessage = render(filename=filename, context=context)
			mail_resu = mail.send(to=[db.auth_user[recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
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
	report = []
	mail_resu = False
	article = db.t_articles[articleId]
	if article:
		mail = getMailer(auth)
		target = URL(c='recommender', f='my_awaiting_articles', scheme=True, host=True)
		mySubject = '%s: Recommendation request suggested' % (myconf.take('app.name'))
		suggestedQy = db.executesql('SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND article_id=%s;', placeholders=[article.id], as_dict=True)
		for theUser in suggestedQy:
			person = mkUser(auth, db, theUser['id'])
			context = dict(article=article, abstract=WIKI(article.abstract or ''), target=target, person=person)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_suggest_recommendation.html')
			myMessage = render(filename=filename, context=context)
			mail_resu = mail.send(to=[theUser['email']],
							subject=mySubject,
							message=myMessage,
						)
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
			mySubject = '%s: Review terminated' % (myconf.take('app.name'))
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				person = mkUser(auth, db, recomm.recommender_id)
				context = dict(article=article, target=target, person=person, reviewer=mkUserWithMail(auth, db, rev.reviewer_id))
				filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_done.html')
				myMessage = render(filename=filename, context=context)
				mail_resu = mail.send(to=[theUser['email']],
								subject=mySubject,
								message=myMessage,
							)
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
			mySubject = '%s: Press review considered' % (myconf.take('app.name'))
			person = mkUser(auth, db, recomm.recommender_id)
			contributor = mkUserWithMail(auth, db, press.contributor_id)
			context = dict(article=article, target=target, person=person, contributor=contributor)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_considerated.html')
			myMessage = render(filename=filename, context=context)
			mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
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
			mySubject = '%s: Press review declined' % (myconf.take('app.name'))
			person = mkUser(auth, db, recomm.recommender_id)
			contributor = mkUserWithMail(auth, db, press.contributor_id)
			context = dict(article=article, target=target, person=person, contributor=contributor)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_declined.html')
			myMessage = render(filename=filename, context=context)
			mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
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
			mySubject = '%s: Press review agreed' % (myconf.take('app.name'))
			person = mkUser(auth, db, recomm.recommender_id)
			contributor = mkUserWithMail(auth, db, press.contributor_id)
			context = dict(article=article, target=target, person=person, contributor=contributor)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_agreed.html')
			myMessage = render(filename=filename, context=context)
			mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
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
			mySubject = '%s: Review considered'% (myconf.take('app.name'))
			person = mkUser(auth, db, recomm.recommender_id)
			reviewer = mkUserWithMail(auth, db, rev.reviewer_id)
			context = dict(article=article, target=target, person=person, reviewer=reviewer)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_considerated.html')
			myMessage = render(filename=filename, context=context)
			mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
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
			mySubject = '%s: Review declined' % (myconf.take('app.name'))
			person = mkUser(auth, db, recomm.recommender_id)
			reviewer = mkUserWithMail(auth, db, rev.reviewer_id)
			context = dict(article=article, target=target, person=person, reviewer=reviewer)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_declined.html')
			myMessage = render(filename=filename, context=context)
			mail_resu = mail.send(to=[db.auth_user[recomm.recommender_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
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
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			mail = getMailer(auth)
			target = URL(c='user', f='my_reviews', scheme=True, host=True)
			mySubject = '%s: Review suggested' % (myconf.take('app.name'))
			person = mkUser(auth, db, rev.reviewer_id)
			recommender = mkUserWithMail(auth, db, recomm.recommender_id)
			context = dict(article=article, target=target, person=person, recommender=recommender)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_suggested.html')
			myMessage = render(filename=filename, context=context)
			mail_resu = mail.send(to=[db.auth_user[rev.reviewer_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
			if mail_resu:
				report.append( 'email to reviewer %s sent' % person.flatten() )
			else:
				report.append( 'email to reviewer %s NOT SENT' % person.flatten() )
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
			mySubject = '%s: Contribution to press review suggested' % (myconf.take('app.name'))
			person = mkUser(auth, db, press.contributor_id)
			recommender = mkUserWithMail(auth, db, recomm.recommender_id)
			context = dict(article=article, target=target, person=person, recommender=recommender)
			filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_suggested.html')
			try:
				myMessage = render(filename=filename, context=context)
			except:
				print 'planté !'
			mail_resu = mail.send(to=[db.auth_user[press.contributor_id]['email']],
							subject=mySubject,
							message=myMessage,
						)
			if mail_resu:
				report.append( 'email to contributor %s sent' % person.flatten() )
			else:
				report.append( 'email to contributor %s NOT SENT' % person.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)
