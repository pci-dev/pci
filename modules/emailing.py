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


# Footer for all mails
def mkFooter():
	appdesc=myconf.take('app.description')
	appname=myconf.take('app.name')
	applongname=myconf.take('app.longname')
	appthematics=myconf.take('app.thematics')
	baseurl=URL(c='default', f='index', scheme=True, host=True)
	profileurl=URL(c='default', f='user', args=['profile'], scheme=True, host=True)
	return XML("""<div style="background-color:#f0f0f0; padding:8px; margin:8px;">
<i>%(applongname)s</i> is the first community of the parent project <a href="https://peercommunityin.org/">Peer Community In</a>.<br>
It is a community of researchers in %(appthematics)s dedicated to review and recommend manuscripts publicly available in pre-print servers (such as bioRxiv).<br>
The motivation behind this project is the establishment of a high-profile, free, public recommendation system for identifying high-quality manuscripts.<br>
More information can be found on the web site of <i>%(applongname)s</i> (<a href="%(baseurl)s">%(baseurl)s</a>).<p>
If you want to modify your profile or the fields and periodicity for the alerts, follow this link: <a href="%(profileurl)s">%(profileurl)s</a>
</div>""" % locals())


# common view for all emails
filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'mail.html')


# TEST MAIL
def do_send_email_to_test(session, auth, db, userId):
	mail = getMailer(auth)
	report = []
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	destPerson = mkUser(auth, db, userId)
	destAddress = db.auth_user[userId]['email']
	mySubject = "%s: TEST MAIL" % (applongname)
	siteName = I(applongname)
	linkTarget = URL(c='default', f='index', scheme=True, host=True)
	content = """
Dear %(destPerson)s,<p>
This is a test mail; please ignore.<p>
You may visit %(siteName)s on: <a href="%(linkTarget)s">%(linkTarget)s</a><p>""" % locals()
	myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
	print myMessage
	mail_resu = mail.send(to=[destAddress],
					subject=mySubject,
					message=myMessage,
				)
	if mail_resu:
		report.append( 'email to %s sent' % destPerson.flatten() )
	else:
		report.append( 'email to %s NOT SENT' % destPerson.flatten() )
	print ''.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



# Send email to the requester (if any)
def do_send_email_to_requester(session, auth, db, articleId, newStatus):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article and article.user_id is not None:
		destPerson = mkUser(auth, db, article.user_id)
		destAddress = db.auth_user[article.user_id]['email']
		articleTitle = article.title
		recommendation = None
		
		if article.status=='Pending' and newStatus=='Awaiting consideration':
			mySubject = '%s: Recommendation request validated' % (applongname)
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_validated.html')
			content = """Dear %(destPerson)s,<p>
You have requested a recommendation to <i>%(appdesc)s</i> (<i>%(applongname)s</i>) for your manuscript entitled <b>%(articleTitle)s</b> on behalf of all authors. We thank you for that.<p>
We remind you that this request is not a submission, as <i>%(applongname)s</i> has no obligation to consider your manuscript.<br>
We will try our best but we cannot guaranty that your manuscript will be reviewed.<p>
We also remind you that, by soliciting <i>%(applongname)s</i>, you agree to wait at least 20 days before submitting this manuscript to a journal or request a recommendation to another Peer Community in.<br>
This delay will allow <i>%(applongname)s</i> to initiate a recommendation process and if so to avoid a simultaneous review process – i.e. one performed by <i>%(applongname)s</i> and one undertaken by a traditional scientific journal or another <a href="https://peercommunityin.org/">Peer Community In</a>.<p>
You will be notified by e-mail if a member of the <i>%(applongname)s</i> chooses/decides to start a peer-review process of your manuscript.<br>
You will then be asked if you agree to engage in the peer review process, and in case of a positive answer your manuscript will be sent to at least two reviewers.<br>
You may then be asked to modify you manuscript and to reply to the questions and points raised by the reviewers.<p>
In case of a favorable conclusion of the member of <i>%(applongname)s</i> in charge of your MS, a recommendation will be published on the web site of <i>%(applongname)s</i> and widely publicized trough social and scientific networks.<br>
Alternatively, a second round of reviews may be needed or a decision to not recommend your manuscript may be made.<br>
You will be notified by e-mail at each step of the procedure.<p>
To view your recommendation request or to cancel it, follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you again for your recommendation request.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status=='Awaiting consideration' and newStatus=='Under consideration':
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			mySubject = '%s: Recommendation request considered' % (applongname)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_considered.html')
			content = """Dear %(destPerson)s,<p>
You have requested a recommendation to <i>%(appdesc)s</i> (<i>%(applongname)s</i>) for your manuscript entitled <b>%(articleTitle)s</b> on behalf of all authors. 
We have the pleasure to inform you that a member of <i>%(applongname)s</i> has read your manuscript and is about to send it in review.<p>
We remind you that this request is not a submission, as <i>%(applongname)s</i> has no obligation to consider your manuscript.<br>
We will try our best but we cannot guaranty that your manuscript will be reviewed.<p>
At this step of the process we have to verify that you are still willing to engage your manuscript in the peer-review process.<p>
In case of a positive answer, you will have to wait the completion of the reviewing process (or no more than 50 days) before you submit this manuscript to a journal or request a recommendation to another <i>Peer Community in</i>.<p>
Your manuscript will be sent to several referees in order to obtain at least two reviews of high quality.<br>
You may then be asked to modify you manuscript and to reply to the questions and points raised by the reviewers.<br> 
In case of a favorable conclusion of the member of <i>%(applongname)s</i> in charge of your MS, a recommendation will be published on the web site of <i>%(applongname)s</i>.<br>
Alternatively, a second round of reviews may be needed or a decision to not recommend your manuscript may be made.<br>
You will be notified by e-mail at each step of the procedure.<p>
Having read this information, are you still willing to engage your manuscript entitled <b>%(articleTitle)s</b> in the peer-review process?<br>
If not, for cancelling your recommendation request, follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>, then click on the "VIEW" button.<p>
We thank you again for your recommendation request.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus and newStatus=='Cancelled':
			linkTarget=URL(c='user', f='my_articles', scheme=True, host=True)
			mySubject = '%s: Recommendation request cancelled' % (applongname)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_cancelled.html')
			content = """Dear %(destPerson)s,<p>
We regret that you declined to engage your manuscript entitled <b>%(articleTitle)s</b> in a peer-review process of <i>%(appdesc)s</i> (<i>%(applongname)s</i>) and we hope that you would request other recommendations in the future.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			
		elif article.status!=newStatus and newStatus=='Rejected':
			mySubject = '%s: Recommendation request rejected' % (applongname)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_rejected.html')
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True)
			content = """Dear %(destPerson)s,<p>
Your manuscript entitled <b>%(articleTitle)s</b> has been evaluated by at least two referees. 
On the basis of these reviews, the member of <i>%(applongname)s</i> in charge of the evaluation of your manuscript has decided not to recommend it.<p>
You will find through this following link <a href="%(recommTarget)s">%(recommTarget)s</a>, and below, the reviews and the commentary of the member of <i>%(applongname)s</i> in charge of the evaluation of your manuscript.<p>
These reviews and commentary will not be published on the <i>%(applongname)s</i> website and will not be publicly released.<br>
They will safely be stored in our database and no one except the managing board can have access to them.<p>
We hope that you would request new recommendations in the future.<p>
We thank you again for your recommendation request.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			
		elif article.status!=newStatus and newStatus=='Awaiting revision':
			mySubject = '%s: Recommendation request awaiting revision' % (applongname)
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_askrevision.html')
			content = """Dear %(destPerson)s,<p>
Your manuscript entitled <b>%(articleTitle)s</b> has now been reviewed.<br>
Referee’s comments are enclosed and available through the following link: <a href="%(recommTarget)s">%(recommTarget)s</a>.<p>
As you will see, the recommender and the other referees found your manuscript very interesting and suggested it for recommendation, providing you make some revisions.<p>
We shall in principle be happy to recommend your manuscript as soon as you revise it in response to the points raised by the referees.<br>
We hope to hear from you within two weeks; please let us know if the delay you need to revise your manuscript is likely to be much longer than this.<p>
When your revised manuscript is ready and when you have replied the reviewers’ questions, follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
After reading your revision, I may recommend it and publish this recommendation on the web site of <i>%(applongname)s</i>.<br>
Alternatively, a second round of reviews may be needed or a decision to not recommend your manuscript may be made.<br>
You will be notified by e-mail at each step of the procedure.<p>
We thank you again for your recommendation request.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			
		elif article.status!=newStatus and newStatus=='Pre-recommended':
			return # patience!
		
		elif article.status!=newStatus and newStatus=='Recommended':
			mySubject = '%s: Recommendation request recommended!' % (applongname)
			linkTarget = URL(c='public', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_recommended.html')
			content = """Dear %(destPerson)s,<p>
We are pleased to inform you that the peer-review process concerning your manuscript entitled <b>%(articleTitle)s</b> has led to a favorable conclusion.<p>
As a consequence, a recommendation has now been published on the web site of <i>%(applongname)s</i>: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you again for your recommendation request.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			
		elif article.status!=newStatus:
			oldStatus = article.status
			mySubject = '%s: Request status changed' % (applongname)
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_status_changed.html')
			content = """Dear %(destPerson)s,<p>
The status of your article entitled <b>%(articleTitle)s</b> changed from "%(oldStatus)s" to "%(newStatus)s".<p>
You may visit your request on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
		
		else:
			return
		myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
		if destAddress:
			mail_resu = mail.send(to=[destAddress],
						subject=mySubject,
						message=myMessage,
					)
		if mail_resu:
			report.append( 'email to requester %s sent' % destPerson.flatten() )
		else:
			report.append( 'email to requester %s NOT SENT' % destPerson.flatten() )
	print ''.join(report)
	if session.flash is None:
		session.flash = '\n'.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


# Send email to the recommenders (if any)
def do_send_email_to_recommender_status_changed(session, auth, db, articleId, newStatus):
	print 'do_send_email_to_recommender_status_changed'
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article:
		mySubject = '%s: Article status changed' % (applongname)
		linkTarget = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
		for myRecomm in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, distinct=True):
			recommender_id = myRecomm['recommender_id']
			destPerson = mkUser(auth, db, recommender_id)
			destAddress = db.auth_user[myRecomm.recommender_id]['email']
			articleAuthors = article.authors
			articleTitle = article.title
			oldStatus = article.status 
			content = """
Dear %(destPerson)s,<p>
The status of article authored by %(articleAuthors)s entitled <b>%(articleTitle)s</b> changed from "%(oldStatus)s" to "%(newStatus)s".<p>
You may visit your request on: <a href="%(linkTarget)s">%(linkTarget)s</a><p>
""" % locals()
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			if mail_resu: 
				report.append( 'email to recommender %s sent' % destPerson.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % destPerson.flatten() )
	print ''.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



# Do send email to suggested recommenders for a given article
def do_send_email_to_suggested_recommenders(session, auth, db, articleId):
	print 'do_send_email_to_suggested_recommenders'
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article and article.status == 'Awaiting consideration':
		articleTitle = article.title
		mySubject = '%s: Recommendation request suggested' % (applongname)
		suggestedQy = db.executesql('SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND article_id=%s;', placeholders=[article.id], as_dict=True)
		for theUser in suggestedQy:
			destPerson = mkUser(auth, db, theUser['id'])
			destAddress = db.auth_user[theUser['id']]['email']
			linkTarget=URL(c='recommender', f='my_awaiting_articles', scheme=True, host=True)
			content = """
Dear %(destPerson)s,<p>
You have been proposed for being in charge of the evaluation of the manuscript entitled %(articleTitle)s.<p>
You can get information about this recommendation request and details on the recommendation process through the following link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you again for your recommendation request.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>"""  % locals()
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			if mail_resu:
				db.executesql('UPDATE t_suggested_recommenders SET email_sent=true WHERE id=%s', placeholders=[theUser['sr_id']])
				report.append( 'email to suggested recommender %s sent' % destPerson.flatten() )
			else:
				db.executesql('UPDATE t_suggested_recommenders SET email_sent=false WHERE id=%s', placeholders=[theUser['sr_id']])
				report.append( 'email to suggested recommender %s NOT SENT' % destPerson.flatten() )
		print '\n'.join(report)
		if session.flash is None:
			session.flash = '; '.join(report)
		else:
			session.flash += '; ' + '; '.join(report)



# Do send email to recommender when a review is re-opened
def do_send_email_to_reviewer_review_reopened(session, auth, db, reviewId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			linkTarget = URL(c='user', f='my_reviews', scheme=True, host=True)
			mySubject = '%s: Review re-opened' % (applongname)
			articleTitle = B(article.title )
			theUser = db.auth_user[rev.reviewer_id]
			if theUser:
				recommPerson = mkUser(auth, db, recomm.recommender_id)
				destPerson = mkUserWithMail(auth, db, rev.reviewer_id)
				destAddress = db.auth_user[rev.reviewer_id]['email']
				content = """Dear %(destPerson)s,<p>
Your review concerning the article entitled %(articleTitle)s have been re-opened by the recommender %(recommPerson)s.<p>
You may visit your reviews on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
				#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'mail.html')
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
				if mail_resu:
					report.append( 'email to reviewer %s sent' % destPerson.flatten() )
				else:
					report.append( 'email to reviewer %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)




# Do send email to recommender when a review is closed
def do_send_email_to_recommenders_review_closed(session, auth, db, reviewId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Review terminated' % (applongname)
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				destPerson = mkUser(auth, db, recomm.recommender_id)
				destAddress = db.auth_user[recomm.recommender_id]['email']
				reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
				content = """Dear %(destPerson)s,<p>
A review by %(reviewerPerson)s concerning the article entitled %(articleTitle)s is terminated.<p>
You may visit your recommendation on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
				#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_done.html')
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
							)
				if mail_resu:
					report.append( 'email to recommender %s sent' % destPerson.flatten() )
				else:
					report.append( 'email to recommender %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


# Do send email to recommender when a press review is accepted for consideration
def do_send_email_to_recommenders_press_review_considerated(session, auth, db, pressId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Press review considered' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
The contribution to the recommendation of the article entitled %(articleTitle)s is considered by the contributor %(contributorPerson)s.<p>
You may visit your recommendation on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_considerated.html')
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			if mail_resu:
				report.append( 'email to recommender %s sent' % destPerson.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_email_to_recommenders_press_review_declined(session, auth, db, pressId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Press review declined' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
The contribution to the recommendation of the article entitled %(articleTitle)s have been declined by the contributor %(contributorPerson)s.<p>
You may visit your recommendation on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_declined.html')
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			if mail_resu:
				report.append( 'email to recommender %s sent' % destPerson.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


def do_send_email_to_recommenders_press_review_agreement(session, auth, db, pressId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Press review agreed' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
The contribution to the recommendation of the article entitled %(articleTitle)s have been agreed by the contributor %(contributorPerson)s.<p>
You may visit your recommendation on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_agreed.html')
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			if mail_resu:
				report.append( 'email to recommender %s sent' % destPerson.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


# Do send email to recommender when a review is accepted for consideration
def do_send_email_to_recommenders_review_considered(session, auth, db, reviewId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Review considered'% (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
			content = """Dear %(destPerson)s,<p>
The review for the recommendation of the article entitled %(articleTitle)s is considered by the reviewer %(reviewerPerson)s.<p>
You may visit your recommendation on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_considerated.html')
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			if mail_resu:
				report.append( 'email to recommender %s sent' % destPerson.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_email_to_recommenders_review_declined(session, auth, db, reviewId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Review declined' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
			content = """Dear %(destPerson)s,<p>
The review for the recommendation of the article entitled %(articleTitle)s have been declined by the reviewer %(reviewerPerson)s.<p>
You may visit your recommendation on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_declined.html')
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			if mail_resu:
				report.append( 'email to recommender %s sent' % destPerson.flatten() )
			else:
				report.append( 'email to recommender %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_email_to_reviewer_review_suggested(session, auth, db, reviewId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	if rev:
		recomm = db.t_recommendations[rev.recommendation_id]
		if recomm:
			article = db.t_articles[recomm['article_id']]
			if article:
				articleTitle = article.title
				articleDOI = article.doi
				linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=True, host=True)
				mySubject = '%s: Review suggested' % (applongname)
				destPerson = mkUser(auth, db, rev.reviewer_id)
				destAddress = db.auth_user[rev.reviewer_id]['email']
				recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
				content = """Dear %(destPerson)s,<p>
I invite you to review a preprint manuscript entitled <b>%(articleTitle)s</b> with the perspective to recommend it to <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<br>
This MS can be downloaded from this adress (doi %(articleDOI)s).<br>
Please let me know as soon as possible if you will be able to accept my invitation to review by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Thanks in advance.<br>
Sincerely yours,<p>
<span style="padding-left:1in;">%(recommenderPerson)s</span>
""" % locals()
				#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_suggested.html')
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
							)
				if mail_resu:
					report.append( 'email to reviewer %s sent' % destPerson.flatten() )
				else:
					report.append( 'email to reviewer %s NOT SENT' % destPerson.flatten() )
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



#def do_send_email_to_reviewer_contribution_suggested(session, auth, db, pressId):
	#report = []
	#mail = getMailer(auth)
	#mail_resu = False
	#applongname=myconf.take('app.longname')
	#appdesc=myconf.take('app.description')
	#press = db.t_press_reviews[pressId]
	#recomm = db.t_recommendations[press.recommendation_id]
	#if recomm:
		#article = db.t_articles[recomm['article_id']]
		#if article:
			#articleTitle = article.title
			#articleAuthors = article.authors
			#articleDOI = article.doi
			#linkTarget = URL(c='user', f='my_press_reviews', scheme=True, host=True)
			#mySubject = '%s: Contribution to recommendation suggested' % (applongname)
			#destPerson = mkUser(auth, db, press.contributor_id)
			#destAddress = db.auth_user[press.contributor_id]['email']
			#recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
			#content = """Dear %(destPerson)s,<p>
#I invite you to jointly write a recommendation on a manuscript written by <i>%(articleAuthors)s</i> and entitled <b>%(articleTitle)s</b> (doi %(articleDOI)s).<br>
#This recommendation will appear in the <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<p>
#Because this MS has already been peer-reviewed we do not need to write reviews.  
#We rather simply need to write together a short text (between half a page and a page). 
#This text should explain the reasons for which this article is of particular interest. 
#There are no constraints on format.<p>
#The goal is to highlight the scientific qualities of the article (crucial, original or previously untested hypothesis, scientific rigour, refinement of the demonstration, outstanding quality of the data and methodology, noteworthy scientific consequences, etc.).<br>
#The only absolute rule is that we must not be directly associated with the authors of the recommended article or have any other conflict of interest.<p>
#Writing a recommendation of this type should not take us too much time and energy, given the short format and the fact that no detailed reviewing is required.<p>
#If you agree, I can start a first draft of this recommendation and send it to you.<p>
#Please let me know as soon as possible if you will accept to co-recommend this paper by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a><p>
#Thanks in advance.<p>
#Sincerely yours,
#<span style="padding-left:1in;">%(recommenderPerson)s</span>
#""" % locals()
			##filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_press_review_suggested.html')
			#myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			#mail_resu = mail.send(to=[db.auth_user[press.contributor_id]['email']],
								#subject=mySubject,
								#message=myMessage,
							#)
			#if mail_resu:
				#report.append( 'email to contributor %s sent' % destPerson.flatten() )
			#else:
				#report.append( 'email to contributor %s NOT SENT' % destPerson.flatten() )
	#print '\n'.join(report)
	#if session.flash is None:
		#session.flash = '; '.join(report)
	#else:
		#session.flash += '; ' + '; '.join(report)



def do_send_mail_new_user(session, auth, db, userId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	user = db.auth_user[userId]
	if user:
		destPerson = mkUser(auth, db, userId)
		destAddress = db.auth_user[userId]['email']
		baseurl=URL(c='default', f='index', scheme=True, host=True), 
		thematics = ', '.join(user.thematics),
		days = ', '.join(user.alerts),
		mySubject = 'Welcome to %s' % (applongname)
		content = """Dear %(destPerson)s,<p>
You recently became a user of <i>%(applongname)s</i>. Thank for registering and your interest.<p>
As a user you will be able to use an alert system to inform <i>%(applongname)s</i> that you like one of your preprints to be considered for recommendation (a dedicated webpage will serve this purpose). 
This will require that this preprint is not under consideration for publication in a traditional journal or for recommendation by another Peer Community in.<br>
If you sollicit <i>%(applongname)s</i> for a recommendation and if a member of this community is interested by evaluating the manuscript he/she will contact you to <ol>
<li> ensure that the manuscript is still not under review elsewhere and if so 
<li> let you know that the manuscript, if you agree, will enter in the recommendation process.</ol>
More information on <i>%(applongname)s</i> can be found here: <a href="%(baseurl)s">%(baseurl)s</a>.
<p>
As a user, you will receive alerts each %(days)s in the following fields when recommendations are published in <i>{{=applongname}}</i> web site: %(thematics)s.<p>
We thank you again for your recommendation request.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_user.html')
		myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
		mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
		if mail_resu:
			report.append( 'email to new user %s sent' % destPerson.flatten() )
		else:
			report.append( 'email to new user %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_mail_new_membreship(session, auth, db, membershipId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	user = db.auth_user[db.auth_membership[membershipId].user_id]
	group = db.auth_group[db.auth_membership[membershipId].group_id]
	if user and group:
		destPerson = mkUser(auth, db, user.id)
		destAddress = db.auth_user[user.id]['email']
		if group.role == 'recommender':
			thematics = ', '.join(user.thematics)
			days = ', '.join(user.alerts)
			baseurl=URL(c='default', f='index', scheme=True, host=True)
			helpurl=URL(c='about', f='help_recommender', scheme=True, host=True)
			ethicsurl=URL(c='about', f='ethics', scheme=True, host=True)
			mySubject = '%s: Welcome to recommendation board' % (applongname)
			content = """Dear %(destPerson)s,<p>
You recently became a member of <i>%(applongname)s</i>. We thank you for your investment and your support.<p>
As a member of <i>%(applongname)s</i> recommendation board, <ul>
<li> you will be asked to recommend 1 or 2 manuscripts per year in average and no more than 5 manuscripts per year. 
	Details on the recommendation process can be found here <a href="%(helpurl)s">%(helpurl)s</a>. 
<li> you will have to comply with the code of ethical conduct of <i>%(applongname)s</i> that can be found here: <a href="%(ethicsurl)s">%(ethicsurl)s</a>
<li> you may be elected as a member of the Managing Board for two years
<li> you will receive alerts each %(days)s in the following fields when recommendations are published in <i>%(applongname)s</i> web site: %(thematics)s
<li> you will also receive by default alerts when <i>%(applongname)s</i> receives recommendations requests in the same fields and with the same periodicity as above.</ul>
If you want to take in charge new recommendation requests, to request a recommendation for one of your preprints, visit <a href="%(baseurl)s">%(baseurl)s</a>.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_recommender.html')
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
							)
			if mail_resu:
				report.append( 'email to new recommender %s sent' % destPerson.flatten() )
			else:
				report.append( 'email to new recommender %s NOT SENT' % destPerson.flatten() )
			
		elif group.role == 'manager':
			mySubject = '%s: Welcome to management board' % (applongname)
			#TODO #WARNING
			content = """Dear %(destPerson)s,<p>
You recently became a member of the Managing Board of <i>%(applongname)s</i>. <br>
We warmly thank you for agreeing, for your support and your investment for this community.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_manager.html')
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[user['email']],
								subject=mySubject,
								message=myMessage,
							)
			if mail_resu:
				report.append( 'email to new manager %s sent' % destPerson.flatten() )
			else:
				report.append( 'email to new manager %s NOT SENT' % destPerson.flatten() )
			
		else:
			return



def do_send_email_to_managers(session, auth, db, articleId, newStatus='Pending'):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	managers = db( (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == 'manager') ).select(db.auth_user.ALL)
	dest = []
	for manager in managers:
		dest.append(manager.email)
	linkTarget = URL(c='manager', f='pending_articles', scheme=True, host=True)
	article = db.t_articles[articleId]
	if article:
		articleTitle = article.title
		articleDOI = article.doi
		if article.user_id:
			if article.status == 'Pending' or newStatus=='Pending':
				submitterPerson = mkUser(auth, db, article.user_id) # submitter
				mySubject = '%s: New recommendation request' % (applongname)
				content = """Dear members of the Managing board,<p>
A new request has been submitted by %(submitterPerson)s to <i>%(applongname)s</i> for the recommandation of the preprint entitled <b>%(articleTitle)s</b> (doi %(articleDOI)s).<p>
To validate (or not) this request, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
""" % locals()
				#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_request.html')
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			elif article.status == 'Pre-recommended' or newStatus=='Pre-recommended':
				recomm = db( (db.t_recommendations.article_id == articleId) ).select(orderby=db.t_recommendations.id).last()
				recommenderPerson = mkUser(auth, db, recomm.recommender_id) # recommender
				mySubject = '%s: New recommendation' % (applongname)
				content = """Dear members of the Managing board,<p>
A new recommendation has been written by %(recommenderPerson)s for <i>%(applongname)s</i>.<p>
To validate or decline this recommendation enclosed below, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
""" % locals()
				recommendation = mkFeaturedArticle(auth, db, article, printable=True)
				#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_recommendation.html')
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
			else:
				return
			mail_resu = mail.send(to=dest,
								subject=mySubject,
								message=myMessage,
							)
	if mail_resu:
		report.append( 'email to new managers sent' )
	else:
		report.append( 'email to new managers NOT SENT' )



def do_send_email_to_thank_recommender(session, auth, db, recommId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	recomm = db.t_recommendations[recommId]
	if recomm:
		article = db.t_articles[recomm.article_id]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=True, host=True)
			mySubject = '%s: Thank you!' % (applongname)
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				#recommender = mkUser(auth, db, recomm.recommender_id)
				destPerson = mkUserWithMail(auth, db, recomm.recommender_id)
				content = """Dear %(destPerson)s,<p>
You accepted the evaluation of the manuscript entitled <b>%(articleTitle)s</b>. 
You can get information about this recommendation and details on the recommendation process through the following link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you for accepting your recommendation.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
				#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_recommendation_accepted.html')
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[theUser['email']],
								subject=mySubject,
								message=myMessage,
							)
				if mail_resu:
					report.append( 'email to recommender %s sent' % destPerson.flatten() )
				else:
					report.append( 'email to recommender %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_email_to_thank_reviewer(session, auth, db, reviewId):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	if rev:
		recomm = db.t_recommendations[rev.recommendation_id]
		if recomm:
			article = db.t_articles[recomm['article_id']]
			if article:
				articleTitle = article.title
				linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=True, host=True)
				mySubject = '%s: Thank you!' % (applongname)
				theUser = db.auth_user[rev.reviewer_id]
				if theUser:
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
					destPerson = mkUserWithMail(auth, db, rev.reviewer_id)
					content = """Dear %(destPerson)s,<p>
You accepted the review of the manuscript entitled <b>%(articleTitle)s</b>. 
You can get information about this recommendation and details on the recommendation process through the following link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you for accepting this review.<p>
Sincerely yours,<p>
<span style="padding-left:1in;">The recommender, %(recommenderPerson)s</span>
""" % locals()
					#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_review_accepted.html')
					myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[theUser['email']],
									subject=mySubject,
									message=myMessage,
								)
					if mail_resu:
						report.append( 'email to recommender %s sent' % destPerson.flatten() )
					else:
						report.append( 'email to recommender %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_email_to_contributors(session, auth, db, articleId):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	managers=myconf.take('contacts.managers')
	article = db.t_articles[articleId]
	recomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
	contribs = db(db.t_press_reviews.recommendation_id==recomm.id).select()
	for contrib in contribs:
		articleTitle = article.title
		articleAuthors = article.authors
		articleDOI = article.doi
		linkTarget = URL(c='recommender', f='my_press_reviews', scheme=True, host=True)
		mySubject = '%s: Contribution to recommendation' % (applongname)
		destPerson = mkUser(auth, db, contrib.contributor_id)
		destAddress = db.auth_user[contrib.contributor_id]['email']
		recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
		content = """Dear %(destPerson)s,<p>
The recommendation about the manuscript written by <i>%(articleAuthors)s</i> and entitled <b>%(articleTitle)s</b> (doi %(articleDOI)s) is almost published.<br>
You are co-author of this recommendation.<br>
You can see this recommendation by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a><p>
In case you do not agree with this recommendation, or not co-authored it, please write to the managing board <a href="mailto:%(managers)s">%(managers)s</a> in order to suspend the publication.<br>
Otherwise, this recommendation will soon appear in <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<p>
Sincerely yours,<p>
<span style="padding-left:1in;">%(recommenderPerson)s</span>
""" % locals()
		myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
		mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
		if mail_resu:
			report.append( 'email to contributor %s sent' % destPerson.flatten() )
		else:
			report.append( 'email to contributor %s NOT SENT' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)

