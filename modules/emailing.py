# -*- coding: utf-8 -*-

import os
import datetime
from re import sub, match
#from copy import deepcopy
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
import socket

myconf = AppConfig(reload=True)


def getMailer(auth):
	mail = auth.settings.mailer
	mail.settings.server = myconf.get('smtp.server')
	mail.settings.sender = myconf.get('smtp.sender')
	mail.settings.login = myconf.get('smtp.login')
	mail.settings.tls = myconf.get('smtp.tls') or False
	mail.settings.ssl = myconf.get('smtp.ssl') or False
	return mail

#TG: OK
# Footer for all mails
def mkFooter():
	appdesc=myconf.take('app.description')
	appname=myconf.take('app.name')
	applongname=myconf.take('app.longname')
	appthematics=myconf.take('app.thematics')
	baseurl=URL(c='default', f='index', scheme=myconf.take('alerts.scheme'), host=myconf.take('alerts.host'), port=myconf.take('alerts.port'))
	profileurl=URL(c='default', f='user', args=['profile'], scheme=myconf.take('alerts.scheme'), host=myconf.take('alerts.host'), port=myconf.take('alerts.port'))
	return XML("""<div style="background-color:#f0f0f0; padding:8px; margin:8px;">
<i>%(applongname)s</i> is the first community of the parent project Peer Community In…. It is a community of researchers in %(appthematics)s dedicated to both 1) the review and recommendation of preprints publicly available in preprint servers (such as bioRxiv) and 2) the recommendation of postprints published in traditional journals. This project was driven by a desire to establish a free, transparent and public recommendation system for reviewing and identifying remarkable articles. More information can be found on the website of <i>%(applongname)s</i> (<a href="%(baseurl)s">%(baseurl)s</a>).<p>
If you wish to modify your profile or the fields and frequency of alerts, please follow this link <a href="%(profileurl)s">%(profileurl)s</a>
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


#TG: OK
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
			mySubject = '%s: Request for recommendation of your preprint' % (applongname)
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_validated.html')
			content = """Dear %(destPerson)s,<p>
Thank you for your request, on behalf of all the authors, for recommendation of your preprint entitled <b>%(articleTitle)s</b>, by <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<p>
Please remember that <i>%(applongname)s</i> is under no obligation to consider your preprint.<br> We cannot guarantee that your preprint will be reviewed, but all possible efforts will be made to achieve this end.<p>
We also remind you that, by sending this request to <i>%(applongname)s</i>, you agree to wait at least 20 days before submitting this preprint to a journal. This delay will allow <i>%(applongname)s</i> to initiate the recommendation process, thereby avoiding simultaneous reviewing by <i>%(applongname)s</i> and a traditional scientific journal.<p>
You will be notified by e-mail if a member of the <i>%(applongname)s</i> decides to start the peer-review process for your article.<br> If so, your preprint will be sent to at least two reviewers. You may then be asked to modify your article and to respond to the questions and points raised by the reviewers.<br> If the member of <i>%(applongname)s</i> responsible for handling your article reaches a favorable conclusion, a recommendation will be published on the website of <i>%(applongname)s</i> and widely publicized through social and scientific networks.<br> Alternatively, a second round of reviews may be required or the decision may be taken not to recommend your article.<br> You will be notified by e-mail at each stage in the procedure.<p>
To view or cancel your recommendation request, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p> 
We thank you again for your request for recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status=='Awaiting consideration' and newStatus=='Under consideration':
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			mySubject = '%s: Consideration of your preprint' % (applongname)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_considered.html')
			content = """Dear %(destPerson)s,<p>
You have requested, on behalf of all the authors, a recommendation for your preprint entitled <b>%(articleTitle)s</b> from <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<br> We are pleased to inform you that a member of <i>%(applongname)s</i> has read this preprint and agreed to start the peer-review process.<p> 
At this stage of the process, we expect you to wait until completion of the reviewing process (no more than 50 days) before submitting this article to a journal.<br> Your article will be sent to several referees, to ensure that at least two high-quality reviews are obtained.<br> You may then be asked to modify your article and to respond to the questions and points raised by the reviewers.<br> If the member of <i>%(applongname)s</i> responsible for handling your preprint reaches a favorable conclusion, a recommendation will be published on the website of <i>%(applongname)s</i> and widely publicized through social and scientific networks.<br> Alternatively, a second round of reviews may be required or the decision may be taken not to recommend your article. You will be notified by e-mail at each stage in the procedure.<p> 
To view or cancel your recommendation request, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p> 
We thank you again for your request for recommendation.<p> 
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
#OK		
		elif article.status!=newStatus and newStatus=='Cancelled':
			linkTarget=URL(c='user', f='my_articles', scheme=True, host=True)
			mySubject = '%s: Cancellation of request for recommendation' % (applongname)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_cancelled.html')
			content = """Dear %(destPerson)s,<p>
Your request for recommendation of your preprint entitled <b>%(articleTitle)s</b> has been cancelled.<br> We respect your choice, but we hope that you will request other recommendations from <i>%(appdesc)s</i> (<i>%(applongname)s</i>) for your preprints in the near future.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus and newStatus=='Rejected':
			mySubject = '%s: Decision concerning your recommendation request' % (applongname)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_rejected.html')
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=True, host=True)
			content = """Dear %(destPerson)s,<p>
Your manuscript entitled <b>%(articleTitle)s</b> has been evaluated by at least two referees.<p> 
On the basis of these reviews, the member of <i>%(applongname)s</i> in charge of the evaluation of your manuscript has decided not to recommend it.<p>
You will find through this following link <a href="%(recommTarget)s">%(recommTarget)s</a>, and below, the reviews and the commentary of the member of <i>%(applongname)s</i> in charge of the evaluation of your manuscript.<p>
These reviews and commentary will not be published on the <i>%(applongname)s</i> website and will not be publicly released.<br>
They will safely be stored in our database and no one except the managing board can have access to them.<p>
We hope that you would request new recommendations in the future.<p>
We thank you again for your recommendation request.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus and newStatus=='Awaiting revision':
			mySubject = '%s: Decision concerning your recommendation request' % (applongname)
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=True, host=True)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_askrevision.html')
			content = """Dear %(destPerson)s,<p>
Your preprint, entitled <b>%(articleTitle)s</b>, has now been reviewed. The referees’ comments are enclosed.<br> As you can see, we found your article very interesting and have suggested its recommendation, subject to certain revisions.<p>
We shall, in principle, be happy to recommend your article as soon as it has been revised in response to the points raised by the referees.<br> We hope to hear from you within two weeks. Please let us know if you are likely to need much longer than this to make your revisions.<p> 
When your revised article is ready and you have responded to the reviewers’ questions, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>.
Once we have read the revised version, we may decide to recommend it directly, in which case, the recommendation will be published on the <i>%(applongname)s</i> website.<br> Alternatively, a second round of reviews may be needed or it may be decided not to recommend your article. You will be notified by e-mail at each stage in the procedure.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			
		elif article.status!=newStatus and newStatus=='Pre-recommended':
			return # patience!
	
		elif article.status!=newStatus and newStatus=='Recommended':
			mySubject = '%s: Recommendation of your preprint' % (applongname)
			linkTarget = URL(c='public', f='recommendations', vars=dict(articleId=articleId), scheme=True, host=True)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=True, host=True)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_recommended.html')
			content = """Dear %(destPerson)s,<p>
We are pleased to inform you that the peer-review process concerning your preprint entitled <b>%(articleTitle)s</b> has reached a favorable conclusion.<br> A recommendation has now been published on the <i>%(applongname)s</i> website.<p>
Thank you for requesting a recommendation for this very interesting preprint from <i>%(applongname)s</i>.<br> We hope that you will make request recommendations for other preprints in the future and will tell your colleagues about this project.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus:
			oldStatus = article.status
			mySubject = '%s: Request status changed' % (applongname)
			linkTarget = URL(c='user', f='my_articles', scheme=True, host=True)
			#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_request_status_changed.html')
			content = """Dear %(destPerson)s,<p>
The status of your article entitled <b>%(articleTitle)s</b> changed from "%(oldStatus)s" to "%(newStatus)s".<p>
You may check your request: <a href="%(linkTarget)s">%(linkTarget)s</a>.
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

#TG: OK
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
The status of the article authored by %(articleAuthors)s entitled <b>%(articleTitle)s</b> changed from "%(oldStatus)s" to "%(newStatus)s".<p>
You may check the request: <a href="%(linkTarget)s">%(linkTarget)s</a><p>
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


#TG: OK
# Do send email to suggested recommenders for a given article
def do_send_email_to_suggested_recommenders(session, auth, db, articleId):
	print 'do_send_email_to_suggested_recommenders'
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article:# and article.status in ('Pending', 'Awaiting consideration'):
		articleTitle = article.title
		mySubject = '%s: Request to act as recommender for a preprint' % (applongname)
		suggestedQy = db.executesql('SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND article_id=%s;', placeholders=[article.id], as_dict=True)
		for theUser in suggestedQy:
			destPerson = mkUser(auth, db, theUser['id'])
			destAddress = db.auth_user[theUser['id']]['email']
			linkTarget=URL(c='recommender', f='my_awaiting_articles', scheme=True, host=True)
			helpurl=URL(c='about', f='help_recommender', scheme=True, host=True)
			content = """
Dear %(destPerson)s,<p>
You have been proposed as the recommender for a preprint entitled %(articleTitle)s.<br> You can obtain information about this request and accept or decline this invitation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p> 
Details about the recommendation process can be found here <a href="%(helpurl)s">%(helpurl)s</a>.<p>
Yours sincerely,<p>
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


#TG: OK
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
Your review concerning the article entitled %(articleTitle)s has been re-opened by %(recommPerson)s acting as a recommender.<p>
You may check your reviews: <a href="%(linkTarget)s">%(linkTarget)s</a>.
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



#TG: OK
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
The review by %(reviewerPerson)s concerning the article entitled %(articleTitle)s is terminated.<p>
You may check your recommendation: <a href="%(linkTarget)s">%(linkTarget)s</a>.
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

#OK
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
			mySubject = '%s: co-recommender accepted the recommendation' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
%(contributorPerson)s has accepted to co-sign the recommendation of the postprint entitled %(articleTitle)s.<p>
You may check your recommendation: <a href="%(linkTarget)s">%(linkTarget)s</a>.
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


#OK
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
			mySubject = '%s: co-recommender declined the recommendation' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
%(contributorPerson)s has declined to co-sign the recommendation of the postprint entitled %(articleTitle)s.<p>
You may check your recommendation: <a href="%(linkTarget)s">%(linkTarget)s</a>.
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

#OK
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
			mySubject = '%s: co-recommender agreed with the recommendation of the postprint' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
%(contributorPerson)s has agreed with the recommendation of the postprint entitled %(articleTitle)s.<p>
You may check your recommendation on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
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
%(reviewerPerson)s has accepted to review the preprint entitled %(articleTitle)s.<p>
You may check your recommendation: <a href="%(linkTarget)s">%(linkTarget)s</a>.
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
%(reviewerPerson)s has declined to review the preprint entitled %(articleTitle)s.<p>
You may check your recommendation: <a href="%(linkTarget)s">%(linkTarget)s</a>.
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
				mySubject = '%s: Request to review a preprint' % (applongname)
				destPerson = mkUser(auth, db, rev.reviewer_id)
				destAddress = db.auth_user[rev.reviewer_id]['email']
				recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
				content = """Dear %(destPerson)s,<p>
I have agreed to handle the evaluation of a preprint entitled <b>%(articleTitle)s</b>, with a view to its recommendation by <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<br> This article can be visualized and downloaded at the following address (doi %(articleDOI)s).<p> 
At first glance, it appears particularly interesting but I would like to have your expert opinion.<br> I would therefore like to invite you to review this preprint for <i>%(applongname)s</i>.<p> 
Please let me know as soon as possible whether you are willing to accept my invitation to review this article, by clicking on this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Thanks in advance.<br>
Yours sincerely,<p>
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




def do_send_mail_admin_new_user(session, auth, db, userId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	admins = db( (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == 'administrator') ).select(db.auth_user.ALL)
	dest = []
	for admin in admins:
		dest.append(admin.email)
	user = db.auth_user[userId]
	if user:
		userTxt = mkUser(auth, db, userId)
		userMail = user.email
		mySubject = '%s: New registred user' % (applongname)
		content = """Dear administrators,<p>
A new user joined <i>%(applongname)s</i>: %(userTxt)s (%(userMail)s).<p>
""" % locals()
		myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
		mail_resu = mail.send(to=dest,
							subject=mySubject,
							message=myMessage,
						)
	if mail_resu:
		report.append( 'email to administrators sent' )
	else:
		report.append( 'email to administrators NOT SENT' )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



# 
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
You have recently joined <i>%(applongname)s</i>. Thank you for your interest and for registering with us.<p>
As a user, you can request a recommendation for a preprint. This preprint must first be deposited in a preprint server, such as bioRxiv and must not already be under review for publication in a traditional journal. Once you have requested a recommendation, a member of the community may express an interest in initiating the recommendation process for your article, which will involve sending your article out for peer review.<p>
More information about <i>%(applongname)s</i> can be found here : <a href="%(baseurl)s">%(baseurl)s</a>.
<p>
As a user, you will receive alerts every %(days)s concerning recommendations in the following fields published on the <i>{{=applongname}}</i> web site: %(thematics)s.<p>
If you wish to request a recommendation for a preprint, please follow this link <a href="%(baseurl)s">%(baseurl)s</a>.<p>
Yours sincerely,<p>
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
			mySubject = 'Welcome to %s' % (applongname)
			content = """Dear %(destPerson)s,<p>
You are now a member of <i>%(applongname)s</i>. We thank you for your time and support.
As a member of <i>%(applongname)s</i>, <ul>
<li> You can recommend up to five articles per year. Details about the recommendation process can be found here <a href="%(helpurl)s">%(helpurl)s</a>. 
<li> You will be expected to comply with the code of ethical conduct of <i>%(applongname)s</i>, which can be found here: <a href="%(ethicsurl)s">%(ethicsurl)s</a>
<li> You are eligible for selection as a member of the Managing Board for a period of two years. 
<li> You will be notified about new articles recommended by <i>%(applongname)s</i>, according to your requested notification frequency and fields of interest. 
<li> You will also receive alerts, by default and with the same frequency as above, when <i>%(applongname)s</i> receives requests for preprint recommendations in your fields of interest.
<li> You can propose the nomination of new members to the Managing Board.<p>
Yours sincerely,<p>
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
			mySubject = '%s: Welcome to The Managing Board' % (applongname)
			#TODO #WARNING
			content = """Dear %(destPerson)s,<p>
You have recently joined the Managing Board of <i>%(applongname)s</i>. We thank you warmly for agreeing to join the Board and for your time and support for this community.<p>
The members of the Managing Board of <i>%(applongname)s</i> are responsible for accepting/rejecting new members of <i>%(applongname)s</i>. They also deal with any problems arising between authors and the members of the community who have evaluated/recommended their articles. They detect and deal with dysfunctions of <i>%(applongname)s</i>, and may exclude members, if necessary. They also rapidly check the quality of formatting and deontology for the reviews and recommendations published by <i>%(applongname)s</i>. Finally, members of the Managing Board of <i>%(applongname)s</i> are members of the non-profit organization “Peer Community in”. This non-profit organization is responsible for the creation and functioning of the various specific Peer Communities in….<p>
The Managing Board of <i>%(applongname)s</i> consists of six individuals randomly chosen from the members of this community. Half the Managing Board is replaced each year. The founders of <i>%(applongname)s</i> will also be included, as additional members of the Managing Board during its first two years of existence. After this period, the Managing Board will have only six members.<p>
Yours sincerely,<p>
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


#OK
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
				mySubject = '%s: Recommendation request requiring validation' % (applongname)
				content = """Dear members of the Managing board,<p>
A recommendation request for a preprint has been sent by %(submitterPerson)s to <i>%(applongname)s</i>.<p>
To validate or reject this request, please, click on this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
""" % locals()
				#filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'email_new_request.html')
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			elif article.status == 'Pre-recommended' or newStatus=='Pre-recommended':
				recomm = db( (db.t_recommendations.article_id == articleId) ).select(orderby=db.t_recommendations.id).last()
				recommenderPerson = mkUser(auth, db, recomm.recommender_id) # recommender
				mySubject = '%s: Recommendation requiring validation by the Managing Board' % (applongname)
				content = """Dear members of the Managing board,<p>
A new recommendation has been written by %(recommenderPerson)s for <i>%(applongname)s</i>.<p>
To validate or block this recommendation, please click on the following link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
""" % locals()
				recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=True, host=True)
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


#ok mais j'ai pas su s'il s'agissait des articles en général ou que des preprints
# si que preprints, remplacer article par preprint
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
			mySubject = '%s: Thank you to initiate an article evaluation!' % (applongname)
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				#recommender = mkUser(auth, db, recomm.recommender_id)
				destPerson = mkUserWithMail(auth, db, recomm.recommender_id)
				if article.already_published:
					content = """Dear %(destPerson)s,<p>
You initiated the evaluation of the article entitled <b>%(articleTitle)s</b>.<br>
You can get information about this article and details on the recommendation process through the following link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you for initiating this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
				else:
					content = """Dear %(destPerson)s,<p>
You accepted to evaluate the article entitled <b>%(articleTitle)s</b>.<br>
You can get information about this article and details on the recommendation process through the following link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you for accepting to initiate this evaluation.<p>
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


#ok
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
				mySubject = '%s: Thank you to accept to review a preprint!' % (applongname)
				theUser = db.auth_user[rev.reviewer_id]
				if theUser:
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
					destPerson = mkUserWithMail(auth, db, rev.reviewer_id)
					content = """Dear %(destPerson)s,<p>
You accepted to review the preprint entitled <b>%(articleTitle)s</b>. 
You can get information about this preprint and details on the recommendation process through the following link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you for accepting to review this preprint.<p>
Yours sincerely,<p>
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


#ok
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
		mySubject = '%s: Co-signed recommendation about to be published' % (applongname)
		destPerson = mkUser(auth, db, contrib.contributor_id)
		destAddress = db.auth_user[contrib.contributor_id]['email']
		recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
		content = """Dear %(destPerson)s,<p>
The recommendation about the postprint written by <i>%(articleAuthors)s</i> and entitled <b>%(articleTitle)s</b> (doi %(articleDOI)s) is about to be sent to the Managing board of <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<br>
You have previously declared that you were willing to co-sign this recommendation.<p>
You can see the recommendation by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a><p>
The recommendation will soon appear in the website of <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<p>
In case you do not agree with this recommendation, or not co-authored it, please write to the Managing Board <a href="mailto:%(managers)s">%(managers)s</a> in order to suspend the publication of the recommendation.<br>
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

#ok
def alert_new_recommendations(session, auth, db, userId, msgArticles):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	destPerson = mkUser(auth, db, userId)
	destAddress = db.auth_user[userId]['email']
	mySubject = '%s: Posting of new recommendations' % (applongname)
	content = """Dear %(destPerson)s,<p>

We are pleased to inform you that the following recommendations have recently been posted on the <i>%(applongname)s</i> website (in the fields for which you have requested alerts).<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
<hr>
%(msgArticles)s
<hr>
""" % locals()
	if destAddress:
		myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
		mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
		if mail_resu:
			report.append( 'email to %s sent' % destPerson.flatten() )
		else:
			report.append( 'email to %s NOT SENT' % destPerson.flatten() )
		print '\n'.join(report)
	if session:
		if session.flash is None:
			session.flash = '; '.join(report)
		else:
			session.flash += '; ' + '; '.join(report)
	
