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
from common import *
import socket

myconf = AppConfig(reload=True)

mail_sleep = 1.0 # in seconds

# common view for all emails
filename = os.path.join(os.path.dirname(__file__), '..', 'views', 'mail', 'mail.html')


def getMailer(auth):
	mail = auth.settings.mailer
	mail.settings.server = myconf.take('smtp.server')
	mail.settings.sender = myconf.take('smtp.sender')
	mail.settings.login = myconf.take('smtp.login')
	mail.settings.tls = myconf.take('smtp.tls') or False
	mail.settings.ssl = myconf.take('smtp.ssl') or False
	return mail

# Footer for all mails
def mkFooter():
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	appdesc=myconf.take('app.description')
	appname=myconf.take('app.name')
	applongname=myconf.take('app.longname')
	appthematics=myconf.take('app.thematics')
	contact=myconf.take('contacts.managers') #TODO
	baseurl=URL(c='default', f='index', scheme=scheme, host=host, port=port)
	profileurl=URL(c='default', f='user', args=['profile'], scheme=scheme, host=host, port=port)
	#return XML("""<div style="background-color:#f0f0f0; padding:8px; margin:8px;">
#<i>%(applongname)s</i> is the first community of the parent project Peer Community In…. It is a community of researchers in %(appthematics)s dedicated to both 1) the review and recommendation of preprints publicly available in preprint servers (such as bioRxiv) and 2) the recommendation of postprints published in traditional journals. This project was driven by a desire to establish a free, transparent and public recommendation system for reviewing and identifying remarkable articles. More information can be found on the website of <i>%(applongname)s</i> (<a href="%(baseurl)s">%(baseurl)s</a>).<p>
#If you wish to modify your profile or the fields and frequency of alerts, please follow this link <a href="%(profileurl)s">%(profileurl)s</a>
#</div>""" % locals())
	return XML("""<div style="background-color:#f0f0f0; padding:8px; margin:8px;"> <i>%(applongname)s</i> is the first community of the parent project Peer Community In. It is a community of researchers in %(appthematics)s dedicated to both 1) the review and recommendation of preprints publicly available in preprint servers (such as bioRxiv) and 2) the recommendation of postprints published in traditional journals. This project was driven by a desire to establish a free, transparent and public recommendation system for reviewing and identifying remarkable articles. More information can be found on the website of <i>%(applongname)s</i> (<a href="%(baseurl)s">%(baseurl)s</a>).<p>In case of any questions or queries, please use the following e-mail: <a href="mailto:%(contact)s">%(contact)s</a>.<p> If you wish to modify your profile or the fields and frequency of alerts, please follow this link: <a href="%(profileurl)s">%(profileurl)s</a>.</div>""" % locals())


# TEST MAIL
def do_send_email_to_test(session, auth, db, userId):
	#do_send_mail_new_user(session, auth, db, userId)
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
	mySubject = "%s: TEST MAIL" % (applongname)
	siteName = I(applongname)
	linkTarget = URL(c='default', f='index', scheme=scheme, host=host, port=port)
	content = """
Dear %(destPerson)s,<p>
This is a test mail; please ignore.<p>
You may visit %(siteName)s on: <a href="%(linkTarget)s">%(linkTarget)s</a><p>""" % locals()
	try:
		myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
		mail_resu = mail.send(to=[destAddress],
					subject=mySubject,
					message=myMessage,
				)
	except Exception as e :
		print "%s" % traceback.format_exc()
	if mail_resu:
		report.append( 'email sent to %s' % destPerson.flatten() )
	else:
		report.append( 'email NOT SENT to %s' % destPerson.flatten() )
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
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
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
Thank you for your request, on behalf of all the authors, for recommendation of your preprint entitled <b>%(articleTitle)s</b>, by <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<p>
Please remember that <i>%(applongname)s</i> is under no obligation to consider your preprint. We cannot guarantee that your preprint will be reviewed, but all possible efforts will be made to achieve this end. We also remind you that, by sending this request to <i>%(applongname)s</i>, you agree to wait at least 20 days before submitting this preprint to a journal. This delay will allow <i>%(applongname)s</i> to initiate the recommendation process, thereby avoiding simultaneous reviewing by <i>%(applongname)s</i> and a traditional scientific journal.<p>
You will be notified by e-mail if a recommender of the <i>%(applongname)s</i> decides to start the peer-review process for your article. If so, your preprint will be sent to at least two reviewers. You may then be asked to modify your article and to respond to the questions and points raised by the reviewers. If the recommender of <i>%(applongname)s</i> responsible for handling your article reaches a favorable conclusion, a recommendation will be published on the website of <i>%(applongname)s</i> and widely publicized through social and scientific networks. Alternatively, a second round of reviews may be required or the decision may be taken not to recommend your article. You will be notified by e-mail at each stage in the procedure.<p>
To view or cancel your recommendation request, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p> 
We thank you again for your request for recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status=='Awaiting consideration' and newStatus=='Under consideration':
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			mySubject = '%s: Consideration of your preprint' % (applongname)
			content = """Dear %(destPerson)s,<p>
You have requested, on behalf of all the authors, a recommendation for your preprint entitled <b>%(articleTitle)s</b> from <i>%(appdesc)s</i> (<i>%(applongname)s</i>). We are pleased to inform you that a recommender of <i>%(applongname)s</i> has read this preprint and agreed to start the peer-review process.<p>
At this stage of the process, we expect you to wait until completion of the reviewing process (no more than 50 days) before submitting this article to a journal. Your article will be sent to several referees, to ensure that at least two high-quality reviews are obtained. You may then be asked to modify your article and to respond to the questions and points raised by the reviewers. If the recommender of <i>%(applongname)s</i> responsible for handling your preprint reaches a favorable conclusion, a recommendation will be published on the website of <i>%(applongname)s</i> and widely publicized through social and scientific networks. Alternatively, a second round of reviews may be required or the decision may be taken not to recommend your article. You will be notified by e-mail at each stage in the procedure.<p>
To view or cancel your recommendation request, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p> 
We thank you again for your request for recommendation.<p> 
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
#OK		
		elif article.status!=newStatus and newStatus=='Cancelled':
			linkTarget=URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			mySubject = '%s: Cancellation of request for recommendation' % (applongname)
			content = """Dear %(destPerson)s,<p>
Your request for recommendation of your preprint entitled <b>%(articleTitle)s</b> has been cancelled. We respect your choice, but we hope that you will request other recommendations from <i>%(appdesc)s</i> (<i>%(applongname)s</i>) for your preprints in the near future.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus and newStatus=='Rejected':
			mySubject = '%s: Decision concerning your recommendation request' % (applongname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=scheme, host=host, port=port)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
Your manuscript entitled <b>%(articleTitle)s</b> has been evaluated by at least two referees. On the basis of these reviews, the recommender of <i>%(applongname)s</i> in charge of the evaluation of your manuscript has decided not to recommend it.<p>
You will find through this following link <a href="%(recommTarget)s">%(recommTarget)s</a>, and below, the reviews and the commentary of the recommender of <i>%(applongname)s</i> in charge of the evaluation of your manuscript. These reviews and commentary will not be published on the <i>%(applongname)s</i> website and will not be publicly released. They will safely be stored in our database and no one except the Managing Board can have access to them.<p>
We hope that you would request new recommendations in the future.<p>
We thank you again for your recommendation request.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus and newStatus=='Awaiting revision':
			mySubject = '%s: Decision concerning your recommendation request' % (applongname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=scheme, host=host, port=port)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
Your preprint, entitled <b>%(articleTitle)s</b>, has now been reviewed. The referees’ comments are enclosed. As you can see, we found your article very interesting and have suggested its recommendation, subject to certain revisions.<p>
We shall, in principle, be happy to recommend your article as soon as it has been revised in response to the points raised by the referees. We hope to hear from you as soon as possible to reduce the delays of recommendation.<p>
When your revised article is ready and you have responded to the reviewers’ questions, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a>. Once we have read the revised version, we may decide to recommend it directly, in which case, the recommendation will be published on the <i>%(applongname)s</i> website. Alternatively, a second round of reviews may be needed or it may be decided not to recommend your article. You will be notified by e-mail at each stage in the procedure.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			
		elif article.status!=newStatus and newStatus=='Pre-recommended':
			return # patience!
	
		elif article.status!=newStatus and newStatus=='Recommended':
			mySubject = '%s: Recommendation of your preprint' % (applongname)
			linkTarget = URL(c='public', f='rec', vars=dict(id=articleId), scheme=scheme, host=host, port=port)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
We are pleased to inform you that the peer-review process concerning your preprint entitled <b>%(articleTitle)s</b> has reached a favorable conclusion. A recommendation has now been published on the <i>%(applongname)s</i> website.<p>
Thank you for requesting a recommendation for this very interesting preprint from <i>%(applongname)s</i>. We hope that you will make request recommendations for other preprints in the future and will tell your colleagues about this project.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus:
			oldStatus = article.status
			mySubject = '%s: Change in the status of your preprint' % (applongname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
The status of your preprint entitled <b>%(articleTitle)s</b> has changed from "%(oldStatus)s" to "%(newStatus)s".<p>
You can view, edit or cancel your request using this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you again for your recommendation request.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		
		else:
			return
		if destAddress:
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
				mail_resu = mail.send(to=[destAddress],
						subject=mySubject,
						message=myMessage,
					)
			except:
				pass
		if mail_resu:
			report.append( 'email sent to requester %s' % destPerson.flatten() )
		else:
			report.append( 'email NOT SENT to requester %s' % destPerson.flatten() )
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article:
		mySubject = '%s: Change in article status' % (applongname)
		linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
		for myRecomm in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, distinct=True):
			recommender_id = myRecomm['recommender_id']
			destPerson = mkUser(auth, db, recommender_id)
			destAddress = db.auth_user[myRecomm.recommender_id]['email']
			articleAuthors = article.authors
			articleTitle = article.title
			oldStatus = article.status 
			content = """
Dear %(destPerson)s,<p>
You have intiated the recommendation of the article by %(articleAuthors)s entitled <b>%(articleTitle)s</b>. The status of this article has changed from "%(oldStatus)s" to "%(newStatus)s".<p>
You can view and manage your recommendation process by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a><p>
We thank you for managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu: 
				report.append( 'email sent to recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
			time.sleep(mail_sleep)
	print ''.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



# Do send email to suggested recommenders for a given NO MORE available article
def do_send_email_to_suggested_recommenders_useless(session, auth, db, articleId):
	print 'do_send_email_to_suggested_recommenders_useless'
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article:
		articleTitle = article.title
		articleDoi = mkDOI(article.doi)
		mySubject = '%s: Cancellation of a request to act as recommender for a preprint' % (applongname)
		#TODO: removing auth.user_id is not the best solution... Should transmit recommender_id
		suggestedQy = db( (db.t_suggested_recommenders.article_id==articleId) & (db.t_suggested_recommenders.suggested_recommender_id!=auth.user_id) & (db.t_suggested_recommenders.suggested_recommender_id==db.auth_user.id) ).select(db.auth_user.ALL)
		for theUser in suggestedQy:
			destPerson = mkUser(auth, db, theUser['id'])
			destAddress = db.auth_user[theUser['id']]['email']
			mailManagers = A(myconf.take('contacts.managers'), _href='mailto:'+myconf.take('contacts.managers'))
			#linkTarget=URL(c='recommender', f='my_awaiting_articles', scheme=scheme, host=host, port=port)
			#helpurl=URL(c='about', f='help_recommender', scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
You have been proposed as the recommender for a preprint entitled <b>%(articleTitle)s</b> (DOI %(articleDoi)s). 
This preprint has also attracted the attention of another recommender of <i>%(applongname)s</i>, who has initiated its evaluation. 
Consequently, this preprint no longer appears in your list of requests to act as a recommender on the <i>%(applongname)s</i> webpage.<p>
If you are willing to participate in the evaluation/recommendation of this preprint, please send us an e-mail at %(mailManagers)s. 
We will send an e-mail to inform the recommender handling the recommendation process of your willingness to participate and he/she may then contact you.<p>
We hope that, in the near future, you will have the opportunity to initiate the recommendation of another preprint.<p>
Thanks for your support.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>"""  % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
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
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article:# and article.status in ('Pending', 'Awaiting consideration'):
		articleTitle = article.title
		mySubject = '%s: Request to act as recommender for a preprint' % (applongname)
		suggestedQy = db.executesql('SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND article_id=%s;', placeholders=[article.id], as_dict=True)
		for theUser in suggestedQy:
			destPerson = mkUser(auth, db, theUser['id'])
			destAddress = db.auth_user[theUser['id']]['email']
			linkTarget=URL(c='recommender', f='my_awaiting_articles', scheme=scheme, host=host, port=port)
			helpurl=URL(c='about', f='help_recommender', scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
You have been proposed as the recommender for a preprint entitled <b>%(articleTitle)s</b>. You can obtain information about this request and accept or decline this invitation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Details about the recommendation process can be found here <a href="%(helpurl)s">%(helpurl)s</a>.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>"""  % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				db.executesql('UPDATE t_suggested_recommenders SET email_sent=true WHERE id=%s', placeholders=[theUser['sr_id']])
				report.append( 'email sent to suggested recommender %s' % destPerson.flatten() )
			else:
				db.executesql('UPDATE t_suggested_recommenders SET email_sent=false WHERE id=%s', placeholders=[theUser['sr_id']])
				report.append( 'email NOT SENT to suggested recommender %s' % destPerson.flatten() )
			time.sleep(mail_sleep)
		print '\n'.join(report)
		if session.flash is None:
			session.flash = '; '.join(report)
		else:
			session.flash += '; ' + '; '.join(report)

# Do send email to all recommenders for a given available article
def do_send_email_to_all_recommenders(session, auth, db, articleId):
	print 'do_send_email_to_all_recommenders'
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	article = db.t_articles[articleId]
	if article and article.status in ('Awaiting consideration'):
		articleTitle = article.title
		mySubject = '%s: Request to act as recommender for a preprint' % (applongname)
		suggestedQy = db.executesql("""SELECT DISTINCT au.*
			FROM auth_user AS au 
			JOIN auth_membership AS am ON au.id = am.user_id 
			JOIN auth_group AS ag ON am.group_id = ag.id AND ag.role LIKE 'recommender'
			WHERE au.id NOT IN (
				SELECT sr.suggested_recommender_id
				FROM t_suggested_recommenders AS sr
				WHERE sr.email_sent IS TRUE AND sr.article_id=%s
			);""", placeholders=[articleId], as_dict=True)
		for theUser in suggestedQy:
			destPerson = mkUser(auth, db, theUser['id'])
			destAddress = db.auth_user[theUser['id']]['email']
			linkTarget=URL(c='recommender', f='fields_awaiting_articles', scheme=scheme, host=host, port=port)
			helpurl=URL(c='about', f='help_recommender', scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
A preprint entitled <b>%(articleTitle)s</b> is still requesting a recommender. You can obtain information about this request and accept this invitation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
If you have already declined a previous invitation to become the recommender of this preprint, please do not take this message into account and accept our apologies for multiple mailing.<p>
Details about the recommendation process can be found here <a href="%(helpurl)s">%(helpurl)s</a>.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>"""  % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
			time.sleep(mail_sleep)
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			linkTarget = URL(c='user', f='my_reviews', scheme=scheme, host=host, port=port)
			mySubject = '%s: Review re-opened' % (applongname)
			articleTitle = B(article.title )
			theUser = db.auth_user[rev.reviewer_id]
			if theUser:
				recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
				destPerson = mkUser(auth, db, rev.reviewer_id)
				destAddress = db.auth_user[rev.reviewer_id]['email']
				content = """Dear %(destPerson)s,<p>
Your review concerning the preprint entitled <b>%(articleTitle)s</b> has been re-opened by %(recommenderPerson)s, the recommender who agreed to initiate and manage the recommendation process for this preprint.<p>
You can view and edit your reviews by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you again for agreeing to review this preprint.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The recommender, %(recommenderPerson)s</span>
""" % locals()
				try:
					myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
				except:
					pass
				if mail_resu:
					report.append( 'email sent to reviewer %s' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to reviewer %s' % destPerson.flatten() )
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: Review completed' % (applongname)
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				destPerson = mkUser(auth, db, recomm.recommender_id)
				destAddress = db.auth_user[recomm.recommender_id]['email']
				reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
				content = """Dear %(destPerson)s,<p>
The review by %(reviewerPerson)s concerning the preprint entitled <b>%(articleTitle)s</b> is now completed.<p>
You can view this review and manage your recommendation by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you again for managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
				try:
					myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
							)
				except:
					pass
				if mail_resu:
					report.append( 'email sent to recommender %s' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: co-recommender accepted the recommendation' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
%(contributorPerson)s has accepted to co-sign the recommendation of the postprint entitled <b>%(articleTitle)s</b>.<p>
You may check your recommendation: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: co-recommender declined the recommendation' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
%(contributorPerson)s has declined to co-sign the recommendation of the postprint entitled <b>%(articleTitle)s</b>.<p>
You may check your recommendation: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	press = db.t_press_reviews[pressId]
	recomm = db.t_recommendations[press.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: co-recommender agreed with the recommendation of the postprint' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
%(contributorPerson)s has agreed with the recommendation of the postprint entitled <b>%(articleTitle)s</b>.<p>
You may check your recommendation on: <a href="%(linkTarget)s">%(linkTarget)s</a>.
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: Request to review accepted'% (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
			content = """Dear %(destPerson)s,<p>
%(reviewerPerson)s has accepted your invitation to review the preprint entitled <b>%(articleTitle)s</b>.<p>
You can view and manage the recommendation and the reviewing processes by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you again for managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)



def do_send_email_to_recommenders_review_declined(session, auth, db, reviewId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	recomm = db.t_recommendations[rev.recommendation_id]
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: Request to review declined' % (applongname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
			content = """Dear %(destPerson)s,<p>
%(reviewerPerson)s has declined your invitation to review the preprint entitled <b>%(articleTitle)s</b>.<p>
You will probably need to find another reviewer to obtain the two high-quality reviews required. To view and manage the recommendation and the reviewing processes for this preprint, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a><p>
We thank you again for managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)





def do_send_email_to_reviewers_review_suggested(session, auth, db, reviewsList):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	for rev in db( (db.t_reviews.id.belongs(reviewsList)) & (db.t_reviews.review_state==None) ).select():
		if rev and rev.review_state is None:
			recomm = db.t_recommendations[rev.recommendation_id]
			if recomm:
				if recomm.recommender_id != rev.reviewer_id:
					article = db.t_articles[recomm['article_id']]
					if article:
						articleTitle = article.title
						articleDOI = mkDOI(article.doi)
						linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
						mySubject = '%s: Request to review a preprint' % (applongname)
						destPerson = mkUser(auth, db, rev.reviewer_id)
						destAddress = db.auth_user[rev.reviewer_id]['email']
						recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
						content = """Dear %(destPerson)s,<p>
I have agreed to handle the evaluation of a preprint entitled <b>%(articleTitle)s</b>, with a view to its recommendation by <i>%(appdesc)s</i> (<i>%(applongname)s</i>). This article can be visualized and downloaded at the following address (doi %(articleDOI)s).<p>
At first glance, it appears particularly interesting but I would like to have your expert opinion. I would therefore like to invite you to review this preprint for <i>%(applongname)s</i>.<p>
Please let me know as soon as possible whether you are willing to accept my invitation to review this article, by clicking on this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Thanks in advance.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">%(recommenderPerson)s</span>
""" % locals()
						try:
							myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
							mail_resu = mail.send(to=[destAddress],
										subject=mySubject,
										message=myMessage,
									)
						except:
							pass
						if mail_resu:
							report.append( 'email sent to reviewer %s' % destPerson.flatten() )
							rev.review_state = 'Pending'
							rev.update_record()
						else:
							report.append( 'email NOT SENT to reviewer %s' % destPerson.flatten() )
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




def do_send_email_to_reviewer_review_suggested(session, auth, db, reviewId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	if rev and rev.review_state is None:
		recomm = db.t_recommendations[rev.recommendation_id]
		if recomm:
			if recomm.recommender_id != rev.reviewer_id:
				article = db.t_articles[recomm['article_id']]
				if article:
					articleTitle = article.title
					articleDOI = article.doi
					linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
					mySubject = '%s: Request to review a preprint' % (applongname)
					destPerson = mkUser(auth, db, rev.reviewer_id)
					destAddress = db.auth_user[rev.reviewer_id]['email']
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
					content = """Dear %(destPerson)s,<p>
I have agreed to handle the evaluation of a preprint entitled <b>%(articleTitle)s</b>, with a view to its recommendation by <i>%(appdesc)s</i> (<i>%(applongname)s</i>). This article can be visualized and downloaded at the following address (doi %(articleDOI)s).<p>
At first glance, it appears particularly interesting but I would like to have your expert opinion. I would therefore like to invite you to review this preprint for <i>%(applongname)s</i>.<p>
Please let me know as soon as possible whether you are willing to accept my invitation to review this article, by clicking on this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Thanks in advance.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">%(recommenderPerson)s</span>
""" % locals()
					try:
						myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
						mail_resu = mail.send(to=[destAddress],
									subject=mySubject,
									message=myMessage,
								)
					except:
						pass
					if mail_resu:
						report.append( 'email sent to reviewer %s' % destPerson.flatten() )
					else:
						report.append( 'email NOT SENT to reviewer %s' % destPerson.flatten() )
					rev.review_state = 'Pending'
					rev.update_record()
				else:
					print 'do_send_email_to_reviewer_review_suggested: Article not found'
			else:
				print 'do_send_email_to_reviewer_review_suggested: recommender = reviewer'
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
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
		mySubject = '%s: A new user has signed up' % (applongname)
		content = """Dear administrators,<p>
A new user has joined <i>%(applongname)s</i>: %(userTxt)s (%(userMail)s).<p>
If this user can act as a recommender, you should change his/her status.<p>
Have a nice day!
""" % locals()
		if len(dest)>0: #TODO: also check elsewhere
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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



# 
def do_send_mail_new_user(session, auth, db, userId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	user = db.auth_user[userId]
	if type(user.thematics) is list:
		thema = user.thematics
	else:
		thema = [user.thematics]
	if type(user.alerts) is list:
		alerts = user.alerts
	else:
		alerts = [user.alerts]
	print thema, alerts
	if user:
		destPerson = mkUser(auth, db, userId)
		destAddress = db.auth_user[userId]['email']
		baseurl=URL(c='default', f='index', scheme=scheme, host=host, port=port)
		recommurl=URL(c='public', f='recommenders', scheme=scheme, host=host, port=port)
		thematics = ', '.join(thema)
		days = ', '.join(alerts)
		mySubject = 'Welcome to %s' % (applongname)
		content = """Dear %(destPerson)s,<p>
You have recently joined <i>%(applongname)s</i>. Thank you for your interest and for registering with us.<p>
As a user, you can request a recommendation for a preprint. This preprint must first be deposited in a preprint server, such as bioRxiv and must not already be under review for publication in a traditional journal. Once you have requested a recommendation, a recommender of the community may express an interest in initiating the recommendation process for your article, which will involve sending your article out for peer review.<p>
More information about <i>%(applongname)s</i> can be found here: <a href="%(baseurl)s">%(baseurl)s</a>.
<p>
As a user, you will receive alerts every %(days)s concerning recommendations in the following fields published on the <i>%(applongname)s</i> web site: %(thematics)s.
<p>
If you wish to request a recommendation for a preprint, please follow this link <a href="%(baseurl)s">%(baseurl)s</a>.
<p>
Finally, if you want to become a recommender <i>%(applongname)s</i> please contact a current recommender in your field via this link <a href="%(recommurl)s">%(recommurl)s</a>. New recommenders are nominated by current recommenders and approved by the Managing Board. As indicated in the website, recommenders of <i>%(applongname)s</i> can recommend up to five preprints and postprints per year. They are expected to comply with the code of ethical conduct of <i>%(applongname)s</i>, are eligible for selection as a member of the Managing Board for a period of two years. Finally, they can propose the nomination of new recommenders to the Managing Board. 
<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		try:
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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



def do_send_mail_new_membreship(session, auth, db, membershipId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
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
			baseurl=URL(c='default', f='index', scheme=scheme, host=host, port=port)
			helpurl=URL(c='about', f='help_recommender', scheme=scheme, host=host, port=port)
			ethicsurl=URL(c='about', f='ethics', scheme=scheme, host=host, port=port)
			mySubject = 'Welcome to %s' % (applongname)
			content = """Dear %(destPerson)s,<p>
You are now a recommender of <i>%(applongname)s</i>. We thank you for your time and support.
As a recommender of <i>%(applongname)s</i>, <ul>
<li> You can recommend up to five articles per year. Details about the recommendation process can be found here <a href="%(helpurl)s">%(helpurl)s</a>. 
<li> You will be expected to comply with the code of ethical conduct of <i>%(applongname)s</i>, which can be found here: <a href="%(ethicsurl)s">%(ethicsurl)s</a>
<li> You are eligible for selection as a member of the Managing Board for a period of two years. 
<li> You will be notified about new articles recommended by <i>%(applongname)s</i>, according to your requested notification frequency and fields of interest. 
<li> You will also receive alerts, by default and with the same frequency as above, when <i>%(applongname)s</i> receives requests for preprint recommendations in your fields of interest.
<li> You can propose the nomination of new recommenders to the Managing Board.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[destAddress],
								subject=mySubject,
								message=myMessage,
							)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to new recommender %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to new recommender %s' % destPerson.flatten() )
			
		elif group.role == 'manager':
			mySubject = '%s: Welcome to The Managing Board' % (applongname)
			content = """Dear %(destPerson)s,<p>
You have recently joined the Managing Board of <i>%(applongname)s</i>. We thank you warmly for agreeing to join the Board and for your time and support for this community.<p>
The members of the Managing Board of <i>%(applongname)s</i> are responsible for accepting/rejecting new recommenders of <i>%(applongname)s</i>. They also deal with any problems arising between authors and the recommenders of the community who have evaluated/recommended their articles. They detect and deal with dysfunctions of <i>%(applongname)s</i>, and may exclude recommenders, if necessary. They also rapidly check the quality of formatting and deontology for the reviews and recommendations published by <i>%(applongname)s</i>. Finally, members of the Managing Board of <i>%(applongname)s</i> are members of the non-profit organization “Peer Community in”. This non-profit organization is responsible for the creation and functioning of the various specific Peer Communities in….<p>
The Managing Board of <i>%(applongname)s</i> consists of six individuals randomly chosen from the recommenders of this community. Half the Managing Board is replaced each year. The founders of <i>%(applongname)s</i> will also be included, as additional members of the Managing Board during its first two years of existence. After this period, the Managing Board will have only six members.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				mail_resu = mail.send(to=[user['email']],
								subject=mySubject,
								message=myMessage,
							)
			except:
				pass
			if mail_resu:
				report.append( 'email sent to new manager %s' % destPerson.flatten() )
			else:
				report.append( 'email NOT SENT to new manager %s' % destPerson.flatten() )
			
		else:
			return


#OK
def do_send_email_to_managers(session, auth, db, articleId, newStatus='Pending'):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	managers = db( (db.auth_user.id == db.auth_membership.user_id) & (db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role == 'manager') ).select(db.auth_user.ALL)
	linkTarget = URL(c='manager', f='pending_articles', scheme=scheme, host=host, port=port)
	article = db.t_articles[articleId]
	if article:
		articleTitle = article.title
		articleDOI = mkDOI(article.doi)
		if article.user_id:
			if article.status == 'Pending' or newStatus=='Pending':
				submitterPerson = mkUser(auth, db, article.user_id) # submitter
				mySubject = '%s: Preprint recommendation request requiring validation' % (applongname)
				content = """Dear members of the Managing Board,<p>
<i>%(applongname)s</i> has received a request for the recommendation of a preprint by %(submitterPerson)s.<p>
To validate or delete this request, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Have a nice day!
""" % locals()
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			elif article.status == 'Pre-recommended' or newStatus=='Pre-recommended':
				recomm = db( (db.t_recommendations.article_id == articleId) ).select(orderby=db.t_recommendations.id).last()
				recommenderPerson = mkUser(auth, db, recomm.recommender_id) # recommender
				mySubject = '%s: Recommendation requiring validation' % (applongname)
				content = """Dear members of the Managing Board,<p>
A new recommendation has been written by %(recommenderPerson)s for <i>%(applongname)s</i>.<p>
To validate and/or manage this recommendation, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Have a nice day!
""" % locals()
				recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
			elif article.status == 'Under consideration' or newStatus=='Under consideration':
				recomm = db( (db.t_recommendations.article_id == articleId) ).select(orderby=db.t_recommendations.id).last()
				recommenderPerson = mkUser(auth, db, recomm.recommender_id) # recommender
				mySubject = '%s: Article considered for recommendation' % (applongname)
				content = """Dear members of the Managing Board,<p>
A new recommendation is under consideration by %(recommenderPerson)s for <i>%(applongname)s</i>.<p>
To manage this recommendation, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Have a nice day!
""" % locals()
				recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
		else:
			return
		for manager in managers:
			try:
				mail_resu = mail.send(to=[manager.email],
							subject=mySubject,
							message=myMessage,
						)
			except:
				pass
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



#ok mais j'ai pas su s'il s'agissait des articles en général ou que des preprints
# si que preprints, remplacer article par preprint
def do_send_email_to_thank_recommender(session, auth, db, recommId):
	report = []
	mail = getMailer(auth)
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	recomm = db.t_recommendations[recommId]
	if recomm:
		article = db.t_articles[recomm.article_id]
		if article:
			articleTitle = article.title
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: Thank you for initiating a recommendation!' % (applongname)
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				#recommender = mkUser(auth, db, recomm.recommender_id)
				destPerson = mkUser(auth, db, recomm.recommender_id)
				if article.already_published:
					content = """Dear %(destPerson)s,<p>
You have decided to recommend a postprint entitled <b>%(articleTitle)s</b>. To view and/or manage your recommendation, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you in advance for writing this recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
				else:
					nbRecomms = db(db.t_recommendations.article_id==article.id).count()
					if nbRecomms > 1: return # follow-up after resubmission
					content = """Dear %(destPerson)s,<p>
You have initiated the evaluation of a preprint entitled <b>%(articleTitle)s</b>. To view or manage the recommendation process for this preprint, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you for initiating this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
				try:
					myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[theUser['email']],
								subject=mySubject,
								message=myMessage,
							)
				except:
					pass
				if mail_resu:
					report.append( 'email sent to recommender %s' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	rev = db.t_reviews[reviewId]
	if rev:
		recomm = db.t_recommendations[rev.recommendation_id]
		if recomm:
			article = db.t_articles[recomm['article_id']]
			if article:
				articleTitle = article.title
				linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=scheme, host=host, port=port)
				mySubject = '%s: Thank you for agreeing to review a preprint!' % (applongname)
				theUser = db.auth_user[rev.reviewer_id]
				if theUser:
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
					destPerson = mkUser(auth, db, rev.reviewer_id)
					content = """Dear %(destPerson)s,<p>
You have agreed to review the preprint entitled <b>%(articleTitle)s</b>. To view, write and manage your review, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
I thank you in advance for the time spent evaluating this preprint.<p>
Looking forward reading your review.
Yours sincerely,<p>
<span style="padding-left:1in;">The recommender, %(recommenderPerson)s</span>
""" % locals()
					try:
						myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
						mail_resu = mail.send(to=[theUser['email']],
									subject=mySubject,
									message=myMessage,
								)
					except:
						pass
					if mail_resu:
						report.append( 'email sent to recommender %s' % destPerson.flatten() )
					else:
						report.append( 'email NOT SENT to recommender %s' % destPerson.flatten() )
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
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
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
		linkTarget = URL(c='recommender', f='my_press_reviews', scheme=scheme, host=host, port=port)
		mySubject = '%s: Your co-recommendation of a postprint for %s' % (applongname, applongname)
		destPerson = mkUser(auth, db, contrib.contributor_id)
		destAddress = db.auth_user[contrib.contributor_id]['email']
		recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
		content = """Dear %(destPerson)s,<p>
A recommendation for the postprint by <i>%(articleAuthors)s</i> and entitled <b>%(articleTitle)s</b> (doi %(articleDOI)s) has been sent to the Managing Board of <i>%(appdesc)s</i> (<i>%(applongname)s</i>). You have been declared as a co-recommender of this postprint. You can view the recommendation by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a><p>
The recommendation is currently being handled by the Managing Board. It will probably be rapidly posted on the website of <i>%(appdesc)s</i> (<i>%(applongname)s</i>).<p>
If you do not agree with this recommendation or did not co-author it, please contact the Managing Board <a href="mailto:%(managers)s">%(managers)s</a> as soon as possible to suspend the publication of the recommendation. Otherwise, we warmly thank you for co-writing this recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">%(recommenderPerson)s</span>
""" % locals()
		try:
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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

#ok
def alert_new_recommendations(session, auth, db, userId, msgArticles):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	destPerson = mkUser(auth, db, userId)
	destAddress = db.auth_user[userId]['email']
	mySubject = '%s: New recommendations of %s' % (applongname, applongname)
	 #TODO: (in the fields for which you have requested alerts)
	content = """Dear %(destPerson)s,<p>
We are pleased to inform you that the following recommendations have recently been posted on the <i>%(applongname)s</i> website.<p>
We hope you will appreciate them and share them through your social networks.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
<hr>
%(msgArticles)s
<hr>
""" % locals()
	if destAddress:
		try:
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
			mail_resu = mail.send(to=[destAddress],
							subject=mySubject,
							message=myMessage,
						)
		except:
			pass
		if mail_resu:
			report.append( 'email sent to %s' % destPerson.flatten() )
			print 'INFO email sent to %s' % destPerson.flatten() 
		else:
			report.append( 'email NOT SENT to %s' % destPerson.flatten() )
			print 'INFO email NOT SENT to %s' % destPerson.flatten() 
		#print '\n'.join(report)
	if session:
		if session.flash is None:
			session.flash = '; '.join(report)
		else:
			session.flash += '; ' + '; '.join(report)
	

def do_send_email_decision_to_reviewer(session, auth, db, articleId, newStatus):
	report = []
	mail_resu = False
	mail = getMailer(auth)
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appdesc=myconf.take('app.description')
	recomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
	if recomm:
		article = db.t_articles[recomm['article_id']]
		if article:
			articleTitle = article.title
			articleStatus = current.T(newStatus)
			linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=scheme, host=host, port=port)
			mySubject = '%s: Decision on preprint you reviewed' % (applongname)
			reviewers = db( (db.auth_user.id == db.t_reviews.reviewer_id) & (db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state=='Terminated') ).select(db.auth_user.ALL)
			for rev in reviewers:
				destPerson = mkUser(auth, db, rev.id)
				content = """Dear %(destPerson)s,<p>
You have agreed to review the preprint entitled <b>%(articleTitle)s</b>.
The status of this preprint is now: %(articleStatus)s.
To view your review, please follow this link: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
I thank you for the time spent evaluating this preprint.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
				try:
					myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[rev['email']],
								subject=mySubject,
								message=myMessage,
							)
				except:
					pass
				if mail_resu:
					report.append( 'email sent to reviewer %s' % destPerson.flatten() )
				else:
					report.append( 'email NOT SENT to reviewer %s' % destPerson.flatten() )
				time.sleep(mail_sleep)
	print '\n'.join(report)
	if session.flash is None:
		session.flash = '; '.join(report)
	else:
		session.flash += '; ' + '; '.join(report)


