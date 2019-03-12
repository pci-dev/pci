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
	return XML("""<div style="background-color:#f0f0f0; padding:8px; margin-top:8px; margin-left:8px; margin-right:8px;"> 
<i>%(appname)s</i> is one of the communities of the parent project Peer Community In. 
It is a community of researchers in %(appthematics)s dedicated to the recommendation of preprints publicly available from open archives (such as bioRxiv, arXiv, PaleorXiv, etc.), based on a high-quality peer-review process.
This project was driven by a desire to establish a free, transparent and public scientific publication system based on the review and recommendation of preprints. More information can be found on the website of <i>%(appname)s</i>&nbsp;  (<a href="%(baseurl)s">%(baseurl)s</a>).<br>
In case of any questions or queries, please use the following e-mail: <a href="mailto:%(contact)s">%(contact)s</a>.<br>
If you wish to modify your profile or the fields and frequency of alerts, please click on 'Profile' in the top-right 'Welcome' menu or follow this link: <a href="%(profileurl)s">%(profileurl)s</a>.</div>""" % locals())


######################################################################################################################################################################
# TEST MAIL
def do_send_email_to_test(session, auth, db, userId):
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
	content = """
Dear %(destPerson)s,<p>
This is a test message; please ignore.<p>""" % locals()
	try:
		myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
		mail_resu = mail.send(to=[destAddress],
					subject=mySubject,
					message=myMessage,
				)
	except Exception, e :
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
	unconsider_limit_days=myconf.get('config.unconsider_limit_days', default=20)
	recomm_limit_days=myconf.get('config.recomm_limit_days', default=50)
	article = db.t_articles[articleId]
	if article and article.user_id is not None:
		destPerson = mkUser(auth, db, article.user_id)
		destAddress = db.auth_user[article.user_id]['email']
		articleTitle = article.title
		recommendation = None
		
		#if article.status=='Pending' and newStatus=='Cancelled':
			#mySubject = '%s: Cancellation of your preprint' % (appname)
			#linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			#content = """Dear %(destPerson)s,<p>
#Your submission, on behalf of all the authors, of your preprint entitled <b>%(articleTitle)s</b>, to <i>%(appdesc)s</i> (<i>%(appname)s</i>) is now cancelled.<p>
#Yours sincerely,<p>
#<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
#""" % locals()

		if article.status=='Pending' and newStatus=='Awaiting consideration':
			mySubject = '%s: Submission of your preprint' % (appname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			if article.parallel_submission:
				content = """Dear %(destPerson)s,<p>
Thank you for submitting your preprint entitled <b>%(articleTitle)s</b>, to <i>%(appdesc)s</i> (<i>%(appname)s</i>).<p>
If you have not already done so, you can suggest recommenders who could initiate the evaluation of your preprint. A recommender is very similar to a journal editor (responsible for finding reviewers, collecting reviews, and making editorial decisions based on reviews), and may eventually recommend your preprint after one or several rounds of reviews.<p>
Please remember that <i>%(appname)s</i> is under no obligation to consider your preprint. We cannot guarantee that your preprint will be reviewed, but all possible efforts will be made to make this possible. You will be notified by e-mail if a <i>%(appname)s</i> recommender decides to start the peer-review process for your preprint.<p>
If after one or several rounds of reviews, the recommender handling your preprint reaches a favorable conclusion, all the editorial correspondence (reviews, recommender’s decisions, authors’ replies) and a recommendation text will be published by <i>%(appname)s</i> under the license CC-BY-ND. If recommended by <i>%(appname)s</i>, your preprint will become an article that may be used and cited like any ‘classic’ article published in a peer-reviewed journal.<p>
Alternatively, if the recommender decides not to recommend your article, the reviews and the decision will be sent to you, but they will not be published or publicly released by <i>%(appname)s</i>. They will be safely stored in our database, to which only the Managing Board has access. You will be notified by e-mail at each stage of the procedure.<p>
You have selected the option of submitting elsewhere in parallel. We encourage you to finish the peer-review process with <i>%(appname)s</i> even if your manuscript is accepted for publication elsewhere. Please note that if this does happen and you abandon the process with <i>%(appname)s</i> after reviewers have contributed their time toward evaluation, we will post the reviewers' reports on the <i>%(appname)s</i> website as recognition of the reviewers' work and in order to enable critical discussion. If you do not agree with this, please consider cancelling your submission now, before reviewers are recruited.<p>
To view your recommendation request, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a> or log onto the <i>%(appname)s</i> website and go to 'Your contributions —> Your submitted preprints' in the top menu.<p>
We thank you again for your submission.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
			else:
				content = """Dear %(destPerson)s,<p>
Thank you for your submission, on behalf of all the authors, of your preprint entitled <b>%(articleTitle)s</b>, to <i>%(appdesc)s</i> (<i>%(appname)s</i>).<p>
We remind you that this preprint must not be published or submitted for publication elsewhere. If this preprint is sent out for review, you must not submit it to a journal until the evaluation process is complete (ie until it has been rejected or recommended by <i>%(appname)s</i>).<p>
If you have not already done so, you need to suggest recommenders who could initiate the evaluation of your preprint. A recommender is very similar to a journal editor (responsible for finding reviewers, collecting reviews, and making editorial decisions based on reviews), and may eventually recommend your preprint after one or several rounds of reviews.<p>
Please remember that <i>%(appname)s</i> is under no obligation to consider your preprint. We cannot guarantee that your preprint will be reviewed, but all possible efforts will be made to make this possible. By submitting your preprint to <i>%(appname)s</i>, you agree to wait until a recommender initiates the evaluation process, within a maximum of %(unconsider_limit_days)s days. You will be notified by e-mail if a recommender of the <i>%(appname)s</i> decides to start the peer-review process for your preprint.<p>
If after one or several rounds of reviews, the <i>%(appname)s</i> recommender handling your preprint reaches a favorable conclusion, all the editorial correspondence (reviews, recommender’s decisions, authors’ replies) and a recommendation text will be published by <i>%(appname)s</i> under the license CC-BY-ND. If recommended by <i>%(appname)s</i> your preprint would become an article that may be used and cited like any ‘classic’ article published in a peer-reviewed journal.<p>
Alternatively, if the recommender decides not to recommend your article, the reviews and the decision will be sent to you, but they will not be published or publicly released by <i>%(appname)s</i>. They will be safely stored in our database, to which only the Managing Board has access. You will be notified by e-mail at each stage in the procedure.<p>
To view or cancel your recommendation request, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a> or logging onto the <i>%(appname)s</i> website and go to 'Your contributions —> Your submitted preprints' in the top menu.<p>
We thank you again for your submission.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
		
		elif article.status=='Awaiting consideration' and newStatus=='Under consideration':
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			mySubject = '%s: Consideration of your preprint' % (appname)
			if article.parallel_submission:
				content = """Dear %(destPerson)s,<p>
You have submitted your preprint entitled <b>%(articleTitle)s</b> to <i>%(appname)s</i>. We are pleased to inform you that a <i>%(appname)s</i> recommender has initiated the evaluation process.<p>
At this stage of the process, your article will be sent to several referees, to ensure that at least two high-quality reviews are obtained. Based on this review, the recommender will reject, recommend or ask you to modify your article and to respond to the questions and points raised by the reviewers. The mean time to this first decision is about %(recomm_limit_days)s days.<p>
If after one or several rounds of reviews, the recommender handling your preprint reaches a favorable conclusion, all the editorial correspondence (reviews, recommender’s decisions, authors’ replies) and a recommendation text will be published by <i>%(appname)s</i> under the license CC-BY-ND. If recommended by <i>%(appname)s</i>, your preprint will become an article that may be used and cited like any ‘classic’ article published in a peer-reviewed journal.<p>
Alternatively, if the recommender decides not to recommend your article, the reviews and the decision will be sent to you, but they will not be published or publicly released by <i>%(appname)s</i>. They will be safely stored in our database, to which only the Managing Board has access. You will be notified by e-mail at each stage of the procedure.<p>
You have selected the option of submitting elsewhere in parallel. We encourage you to finish the peer-review process with <i>%(appname)s</i> even if your manuscript is accepted for publication elsewhere. Please note that if this does happen and you abandon the process with <i>%(appname)s</i> after reviewers have contributed their time toward evaluation, we will post the reviewers' reports on the <i>%(appname)s</i> website as recognition of the reviewers' work and in order to enable critical discussion. If you do not agree with this, please consider cancelling your submission now, before reviewers are recruited.<p>
To view your recommendation request, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a> or log onto the <i>%(appname)s</i> website and go to 'Your contributions —> Your submitted preprints' in the top menu.<p>
We thank you again for your submission.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()

			else:
				content = """Dear %(destPerson)s,<p>
You have submitted your preprint entitled <b>%(articleTitle)s</b> to <i>%(appname)s</i>. We are pleased to inform you that a <i>%(appname)s</i> recommender has initiated the evaluation process.<p>
At this stage of the process, your article will be sent to several referees, to ensure that at least two high-quality reviews are obtained. Based on this review, the recommender will reject, recommend or ask you to modify your article and to respond to the questions and points raised by the reviewers. The mean time to this first decision is about %(recomm_limit_days)s days.<p>
We remind you that this preprint must not be submitted for publication elsewhere until its evaluation by <i>%(appname)s</i> is complete.<p>
If after one or several rounds of reviews, the recommender handling your preprint reaches a favorable conclusion, all the editorial correspondence (reviews, recommender’s decisions, authors’ replies) and a recommendation text will be published by <i>%(appname)s</i> under the license CC-BY-ND. If recommended by <i>%(appname)s</i> your preprint will become an article that may be used and cited like any ‘classic’ article published in a peer-reviewed journal.<p>
Alternatively, if the recommender decides not to recommend your article, the reviews and the decision will be sent to you, but they will not be published or publicly released by <i>%(appname)s</i>. They will be safely stored in our database, to which only the Managing Board has access. You will be notified by e-mail at each stage in the procedure.<p>
To view or cancel your recommendation request, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a> or logging onto the <i>%(appname)s</i> website and go to 'Your contributions —> Your submitted preprints' in the top menu.<p>
We thank you again for your submission.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()



		elif article.status!=newStatus and newStatus=='Cancelled':
			linkTarget=URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			mySubject = '%s: Cancellation of your submission' % (appname)
			if article.parallel_submission:
				content = """Dear %(destPerson)s,<p>
The submission of your preprint entitled <b>%(articleTitle)s</b> has been cancelled. We respect your decision, and hope that you will submit other preprints to <i>%(appdesc)s</i> (<i>%(appname)s</i>) in the near future.<p> If your manuscript was sent to reviewers and evaluated, we will add a link to the reports on our progress log page. This is because you chose the parallel submission option and we do not wish to waste the effort that went into evaluating your work. This provides reviewers a possibility to claim credit for their evaluation work and, in addition to being useful to your team, we hope the reports are useful discussion points for other researchers in the field.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()

			else:
				content = """Dear %(destPerson)s,<p>
The submission of your preprint entitled <b>%(articleTitle)s</b> has been cancelled. We respect your decision, and hope that you will submit other preprints to <i>%(appdesc)s</i> (<i>%(appname)s</i>) in the near future.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus and newStatus=='Rejected':
			mySubject = '%s: Decision concerning your submission' % (appname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=scheme, host=host, port=port)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
Your preprint entitled <b>%(articleTitle)s</b> has been evaluated by at least two referees. On the basis of these reviews, we regret to inform you that the <i>%(appname)s</i> recommender in charge of this evaluation has decided not to recommend it.<p>
The reviews and the recommender’s decision are shown below. These reviews and the decision will not be published or publicly released by <i>%(appname)s</i>. They will be safely stored in our database, to which only the Managing Board has access.<p>
We are sorry to bring disappointing news and hope that you will consider submitting other preprints to <i>%(appname)s</i> in the future.<p>
We thank you again for your submission.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus and newStatus=='Not considered':
			mySubject = '%s: Decision concerning your submission' % (appname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=scheme, host=host, port=port)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
You have submitted your preprint entitled <b>%(articleTitle)s</b> to <i>%(appname)s</i>.<p>
Unfortunately, no recommender has initiated the evaluation of your preprint since the request was made %(unconsider_limit_days)s days ago. This does not mean that your preprint is not of sufficient quality and/or interest. However, we suggest that you do not wait any longer for a return from us at this stage.<p>
We are sorry to bring disappointing news and hope that that you will consider submitting other preprints to <i>%(appname)s</i> in the future.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus and newStatus=='Awaiting revision':
			mySubject = '%s: Decision concerning your submission' % (appname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			recommTarget = URL(c='user', f='recommendations', vars=dict(articleId=articleId), scheme=scheme, host=host, port=port)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
Your article, entitled <b>%(articleTitle)s</b>, has now been reviewed. The referees' comments and the recommender’s decision are shown below. As you can see, the recommender found your article very interesting, but suggests certain revisions.<p>
We shall, in principle, be happy to recommend your article as soon as it has been revised in response to the points raised by the referees.<p>
When revising your article, we remind you that: <p>
1) Data must be available to readers, either in the text or through an open data repository such as Zenodo (free), Dryad (to pay) or some other institutional repository. Data must be reusable, thus metadata or accompanying text must carefully describe the data;<p>
2) Details on quantitative analyses (e.g., data treatment and statistical scripts in R, bioinformatic pipeline scripts, etc.) and details concerning simulations (scripts, codes) must be available to readers in the text, as appendices, or through an open data repository, such as Zenodo, Dryad or some other institutional repository. The scripts or codes must be carefully described so that they can be reused;<p>
3) Details on experimental procedures must be available to readers in the text or as appendices;<p>
4) Authors must have no financial conflict of interest relating to the article. The article must contain a "Conflict of interest disclosure" paragraph before the reference section containing this sentence: "The authors of this article declare that they have no financial conflict of interest with the content of this article.";<p>
5) This disclosure has to be completed by a sentence indicating, if appropriate, that some of the authors are PCI recommenders: “XY is one of the <i>%(appname)s</i> recommenders.”.<p>
When your revised article is ready, please:<p>
1) Upload the new version of your manuscript onto your favorite open archive;<p>
2) Follow this link <a href="%(linkTarget)s">%(linkTarget)s</a> or logging onto the <i>%(appname)s</i> website and go to 'your contributions' section and then to 'Your submitted preprints' subsection in the top menu;<p>
3) Make your changes to the title, summary, link to the article (or its DOI) and keywords if necessary by clicking on the 'Edit Article' button. If not already done, you also need to upload a picture or an illustration for which you own the rights – this picture will be used to illustrate your article, if recommended;<p>
4) Write, copy/paste or upload (as a PDF file) your reply to the recommender's and reviewers' comments by clicking on the 'Write, edit or upload your reply to recommender' button. You can also upload (as a PDF file) a revised version of your article, with the modifications indicated in TrackChanges mode;<p>
5) When you are ready to submit your new version, click on the 'Save & submit your reply' button.<p>
Once the recommender has read the revised version, he/she may decide to recommend it directly, in which case the editorial correspondence (reviews, recommender’s decisions, authors’ replies) and a recommendation text will be published by <i>%(appname)s</i> under the license CC-BY-ND.<p>
Alternatively, other rounds of reviews may be needed before the recommender reaches a favorable conclusion. He/she may also reject your article, in which case the reviews and decision will be sent to you, but they will not be published or publicly released by <i>%(appname)s</i>. They will be safely stored in our database, to which only the Managing Board has access. You will be notified by e-mail at each stage in the procedure.<p>
We thank you in advance for submitting your revised version.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
			
		elif article.status!=newStatus and newStatus=='Pre-recommended':
			return # patience!
	
		elif article.status!=newStatus and newStatus=='Recommended':
			mySubject = '%s: Recommendation of your preprint' % (appname)
			linkTarget = URL(c='public', f='rec', vars=dict(id=articleId), scheme=scheme, host=host, port=port)
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			lastRecomm = db( (db.t_recommendations.article_id==article.id) & (db.t_recommendations.recommendation_state == 'Recommended') ).select().last() 
			#whoDidItCite = mkWhoDidIt4Recomm(auth, db, lastRecomm, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)
			#citeNum = ''
			#if lastRecomm.recommendation_doi:
				#citeNumSearch = re.search('([0-9]+$)', lastRecomm.recommendation_doi, re.IGNORECASE)
				#if citeNumSearch:
					#citeNum = citeNumSearch.group(1)
			#myCitation = SPAN(SPAN(whoDidItCite), ' ', lastRecomm.last_change.strftime('(%Y)'), ' ', lastRecomm.recommendation_title, '. ', I(appname)+', '+citeNum).flatten()
			myRefArticle = mkArticleCitation(auth, db, myRecomm)
			myRefRecomm  = mkRecommCitation(auth, db, myRecomm)
			linkRecomm = URL(c='public', f='rec', vars=dict(id=articleId))
			doiRecomm = mkLinkDOI(lastRecomm.recommendation_doi)
			recommVersion = lastRecomm.version
			whoDidIt1 = mkWhoDidIt4Recomm(auth, db, lastRecomm, with_reviewers=False, linked=False)
			whoDidIt2 = mkReviewersString(auth, db, articleId)
			content = """Dear %(destPerson)s,<p>
We are pleased to inform you that the peer-review process concerning your article entitled <b>%(articleTitle)s</b> has reached a favorable conclusion. A recommendation text written by the recommender has now been published by <i>%(appname)s</i>. The editorial correspondence (reviews, author’s responses and recommender’ decisions) has also been published by <i>%(appname)s</i>. The recommendation text and the editorial correspondence are shown below.<p>
Because it has been reviewed and recommended, the reference of your article has changed and is now:<p>
%(myRefArticle)s<p>
<p>
The reference of the recommendation of your article is:<p>
%(myRefRecomm)s<p>
<p>
You can find it there: %(doiRecomm)s<p>
And there: %(linkTarget)s<p>
<p>
Do not hesitate to share the news as much as possible: social networks if you are on them, mailing, websites, CV, quotation, etc...<p>
<p>
If you intend to submit your article to a journal, we strongly advise you to include the following statement in the cover letter:<p>
"This manuscript has not been submitted for publication in another journal, but has already been peer-reviewed and recommended by <i>%(appname)s</i>. %(whoDidIt1)s evaluated this manuscript and %(whoDidIt2)s recommended it based on these reviews. The reviewers and the recommender have no conflict of interests with us or with the content of the manuscript. The reviews and the recommendation text are publicly available at the following address: %(doiRecomm)s"<p>
If you want to fully play the game and support the work already done by PCI, you can add the following:<p>
"If you consider that PCI's evaluation and recommendation are not of sufficient quality to make a decision, please let me know and I will cancel my submission. Indeed, as my manuscript has already received an in-depth peer-review, and been modified accordingly, I am not willing to wait for a new round of reviews. I therefore hope that you will make your decision to publish this work on the basis of PCI's evaluation alone, without further peer-review"<p>
If the journal is a PCI-friendly journal (cf list there https://peercommunityin.org/who-supports-peer-community-in/), you may also add this sentence to the cover letter:
"For your information, the Editor-in-Chief has indicated that the journal's editorial board will consider submissions of PCI recommended articles and will use the reviews and recommendations performed by PCI for its own review process, when possible."<p>
In the case of an anonymous review, you may add the following to the cover letter:<p>
"If you would like to know the identity of anonymous PCI reviewers of the manuscript, simply send a message requesting this information to <a href="mailto:%(contact)s">%(contact)s</a>. The managing board of <i>%(appname)s</i> will provide you with this information, if the reviewer concerned agrees."<p>
<b>In order to reach a better referencing and greater visibility of your recommended article, we suggest you to make the following modifications and then to post a new version of your article on the open archive:<b><p>
1) Add the following sentence in the acknowledgements: "Version %(recommVersion)s of this article has been peer-reviewed and recommended by <i>%(appname)s</i> (%(doiRecomm)s)";<p>
2) Remove line numbering from the article and ensure that tables and figures are located in the main text, not at the end of the manuscript;<p>
Please be careful to correctly update all text in these templates (doi, authors’ names, address, title, date, …). In the "cite as" box, indicate that version %(recommVersion)s of the article has been peer reviewed and recommended by <i>%(appname)s</i>. The Recommender is %(whoDidIt2)s, the reviewers are %(whoDidIt1)s. The DOI of the recommendation is %(doiRecomm)s<p>
3) Use templates (word docx templates and a latex template) to format your article in a PCI style, <a href="https://peercommunityin.org/templates"> here</a>.
Doing so is very important because it would:<p>
- indicate to readers that, unlike many other articles in this server, your article has been peer-reviewed and recommended<p>
- make visible this information in Google Scholar search (which is quite important).<p>
4) We strongly encourage you to also deposit your article in the ZENODO archive (https://zenodo.org/deposit/new?c=peer_community_in). This second deposit will ensure the safe storage of your work in a non commercial European institutional open archive. The DOI of your article will remain unchanged.<p>
Thank you for using <i>%(appname)s</i>. We hope that you will submit other preprints in the future and will tell your colleagues about <i>%(appname)s</i>.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
		
		elif article.status!=newStatus:
			tOldStatus = current.T(article.status)
			tNewStatus = current.T(newStatus)
			mySubject = '%s: Change in the status of your preprint' % (appname)
			linkTarget = URL(c='user', f='my_articles', scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
The status of your preprint entitled <b>%(articleTitle)s</b> has changed from "%(tOldStatus)s" to "%(tNewStatus)s".<p>
You can view, edit or cancel your request by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Your contributions —> Your submitted preprints' in the top menu.<p>
We thank you again for your submission.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
		linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=True))
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
			content = """
Dear %(destPerson)s,<p>
You have submitted your recommendation of the postprint article entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s).<p>
The status of this article has changed from "%(tOldStatus)s" to "%(tNewStatus)s".<p>
You can view and manage your evaluation process by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Your contribtions —> Your recommendations of postprints' in the top menu.<p>
We thank you for managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
	mail_resu = False
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	appname=myconf.take('app.name')
	appdesc=myconf.take('app.description')
	recomm_limit_days=myconf.get('config.recomm_limit_days', default=50)
	article = db.t_articles[articleId]
	if article:
		linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
		for myRecomm in db(db.t_recommendations.article_id == articleId).select(db.t_recommendations.recommender_id, distinct=True):
			recommender_id = myRecomm['recommender_id']
			destPerson = mkUser(auth, db, recommender_id)
			destAddress = db.auth_user[myRecomm.recommender_id]['email']
			articleAuthors = article.authors
			articleTitle = article.title
			articleDoi = mkDOI(article.doi)
			tOldStatus = current.T(article.status)
			tNewStatus = current.T(newStatus)
			#if article.status == 'Awaiting consideration' and newStatus == 'Under consideration':
				#mySubject = '%s: Thank you for initiating a recommendation!' % (appname)
				#if article.parallel_submission:
					#content = """Dear %(destPerson)s,<p>
#You have agreed to be the recommender handling the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s). Thank you very much for your contribution.<p>
#We remind you that the role of a recommender is very similar to that of a journal editor (finding reviewers, collecting reviews, making editorial decisions based on reviews) and may eventually lead to recommendation of the preprint after one or several rounds of review. The evaluation should guide the decision as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by <i>%(appname)s</i> is an article that may be used and cited just like a ‘classic’ article published in a journal.<p>
#If after one or several rounds of review you decide to recommend this preprint, you will need to write a “recommendation”, which will have its own DOI and will be published by <i>%(appname)s</i> under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (citing, at least, the preprint being recommended). All the editorial correspondence (reviews, your decisions, authors’ replies) will also be published by <i>%(appname)s</i>.<p>
#As you have agreed to handle this preprint, you will manage its evaluation until you reach a final decision (recommend or reject).<p>
#All preprints must be reviewed by at least two referees. If you have not already done so, you need to invite reviewers (either from the <i>%(appname)s</i> database or from your own network). We remind you that additional experiments suggested by reviewers should only be deemed essential if the conclusions of the preprint are not sufficiently supported by the currently presented data e.g. extra control experiments, increasing statistical power, etc... It is up to you as recommender to decide which experiments are necessary for a recommendation, and which may simply be suggested but remain optional. You can invite potential reviewers to review the preprint via the <i>%(appname)s</i> website:<p>
#1) Using this link <a href="%(linkTarget)s">%(linkTarget)s</a> - you can also log onto the <i>%(appname)s</i> website and go to 'Your contributions —> Your recommendations of preprints' in the top menu, and<p>
#2) Click on the 'invite a reviewer' button.<p>
#We strongly advise you to invite at least five potential reviewers to review the preprint, and to set a deadline of no more than three weeks. Your first decision (reject, recommend or revise) should ideally be reached within <b>%(recomm_limit_days)s days</b>. Please do not invite reviewers for whom there might be a conflict of interest. Specifically, researchers are not allowed to review preprints written by close colleagues (with whom they have published in the last four years, with whom they have received joint funding in the last four years, or with whom they are currently writing a manuscript, or submitting a grant proposal), or by family members, friends, or anyone for whom bias might affect the nature of the evaluation - please see the code of conduct.
#Details about the recommendation process can be found by watching this short video on how to start and manage a preprint recommendation <a href="https://youtu.be/u5greO-q8-M">video</a>.<p>
#The authors have chosen to submit elsewhere in parallel. As there is a chance that the manuscript is accepted for publication elsewhere and consequently the authors might abandon the process at <i>%(appname)s</i>, we have the following mechanism to ensure reviewers’ work is respected and documented. If the authors abandon the process at <i>%(appname)s</i> after reviewers have written their reports, you should post the reviewers' reports on the <i>%(appname)s</i> website as recognition of the reviewers' work and in order to enable critical discussion. Note that there remains the outcome of rejection by you, wherein reports are not made public.<p>
#If you need assistance in any way please do not hesitate to ask us.<p>
#We thank you again for initiating and managing this evaluation.<p>
#Yours sincerely,<p>
#<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span><p>
#""" % locals()

				#else:
					#content = """Dear %(destPerson)s,<p>
#You have agreed to be the recommender handling the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s). Thank you very much for your contribution.<p>
#We remind you that the role of a recommender is very similar to that of a journal editor (finding reviewers, collecting reviews, making editorial decisions based on reviews) and may eventually lead to recommendation of the preprint after one or several rounds of review. The evaluation should guide the decision as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by <i>%(appname)s</i> is an article that may be used and cited just like a ‘classic’ article published in a journal.<p>
#If after one or several rounds of review you decide to recommend this preprint, you will need to write a “recommendation”, which will have its own DOI and will be published by <i>%(appname)s</i> under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (citing, at least, the preprint being recommended). All the editorial correspondence (reviews, your decisions, authors’ replies) will also be published by <i>%(appname)s</i>.<p>
#As you have agreed to handle this preprint, you will manage its evaluation until you reach a final decision (recommend or reject).<p>
#All preprints must be reviewed by at least two referees. If you have not already done so, you need to invite reviewers (either from the <i>%(appname)s</i> database or not included in this database). You can invite potential reviewers to review the preprint via the <i>%(appname)s</i> website:<p>
#1) Using this link <a href="%(linkTarget)s">%(linkTarget)s</a> - you can also log onto the <i>%(appname)s</i> website and go to 'Your contributions —> Your recommendations of preprints' in the top menu, and<p>
#2) Click on the 'invite a reviewer' button.<p>
#We strongly advise you to invite at least five potential reviewers to review the preprint, and to set a deadline of no more than three weeks. Your first decision (reject, recommend or revise) should ideally be reached within %(recomm_limit_days)s days (J+%(recomm_limit_days)s)</b>
#Please do not invite reviewers for whom there might be a conflict of interest. Indeed, researchers are not allowed to review preprints written by close colleagues (with whom they have published in the last four years, with whom they have received joint funding in the last four years, or with whom they are currently writing a manuscript, or submitting a grant proposal), or by family members, friends, or anyone for whom bias might affect the nature of the evaluation - see the code of conduct.
#Details about the recommendation process can be found by watching this short video on how to start and manage a preprint recommendation <a href="https://youtu.be/u5greO-q8-M">video</a>.<p>
#If you need assistance in any way please do not hesitate to ask us.<p>
#We thank you again for initiating and managing this evaluation.<p>
#Yours sincerely,<p>
#<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span><p>
#""" % locals()
			
			if article.status == 'Awaiting revision' and newStatus == 'Under consideration':
				mySubject = '%s: Revised version' % (appname)
				mailManagers = A(myconf.take('contacts.managers'), _href='mailto:'+myconf.take('contacts.managers'))
				deadline = (datetime.date.today() + datetime.timedelta(weeks=1)).strftime('%a %b %d')
				content = """Dear %(destPerson)s,
<p>
The authors of the preprint entitled <b>%(articleTitle)s</b> and submitted by %(articleAuthors)s have posted their revised version and their replies to your comments and those of the reviewers. They may also have uploaded (as a PDF or Word file) a revised version of their preprint, with the modifications indicated in TrackChanges mode and a clean version of their PDF at this address <a href="%(linkTarget)s">%(linkTarget)s</a>.
<p>
For this new round of evaluation, you must reach a decision to ‘Revise’, ‘Recommend’ or ‘Reject’ the article.
<p>
Please send us a message at %(mailManagers)s within one week – i.e. before %(deadline)s – <b>to let us know whether you wish to send it out again for peer review or whether you will make your decision without further review within the next 10 days</b> (and preferentially within a week). If you need more time, please let us know by return mail.
<p>
Finally, note that we asked the authors to make the following compulsory changes on their article. We would be happy if you could check that they have been done:<p>
1) Data must be available to readers after recommendation, either in the text or through an open data repository such as Zenodo (free), Dryad (to pay) or some other institutional repository. Data must be reusable, thus metadata or accompanying text must carefully describe the data;<p>
2) Details on quantitative analyses (e.g., data treatment and statistical scripts in R, bioinformatic pipeline scripts, etc.) and details concerning simulations (scripts, codes) must be available to readers in the text, as appendices, or through an open data repository, such as Zenodo, Dryad or some other institutional repository. The scripts or codes must be carefully described so that they can be reused;<p>
3) Details on experimental procedures must be available to readers in the text or as appendices;<p>
4) Authors must have no financial conflict of interest relating to the article. The article must contain a "Conflict of interest disclosure" paragraph before the reference section containing this sentence: "The authors of this article declare that they have no financial conflict of interest with the content of this article.";<p>
5) This disclosure has to be completed by a sentence indicating that some of the authors are PCI recommenders: “XY is one of the <i>%(appname)s</i> recommenders.”<p>
We look forward to your decision. Thanks in advance!
<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
			elif article.status == 'Recommended':
				mySubject = '%s: Article recommended' % (appname)
				#whoDidItCite = mkWhoDidIt4Recomm(auth, db, myRecomm, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)
				#citeNum = ''
				#if myRecomm.recommendation_doi:
					#citeNumSearch = re.search('([0-9]+$)', myRecomm.recommendation_doi, re.IGNORECASE)
					#if citeNumSearch:
						#citeNum = citeNumSearch.group(1)
				#citeRecomm = SPAN(SPAN(whoDidItCite), ' ', myRecomm.last_change.strftime('(%Y)'), ' ', myRecomm.recommendation_title, '. ', I(appname)+', '+citeNum).flatten()
				citeRecomm = mkRecommCitation(auth, db, myRecomm).flatten()
				citeArticle  = mkArticleCitation(auth, db, myRecomm).flatten()
				linkRecomm = URL(c='public', f='rec', vars=dict(id=article.id))
				doiRecomm = mkLinkDOI(myRecomm.recommendation_doi)
				content = """Dear %(destPerson)s,
Your recommendation - along with the reviews - is now posted on the <i>%(appname)s</i> website.<p>
The reference of your recommendation is:<p>
%(citeRecomm)s<p>
The reference of the recommended article is:<p>
%(citeArticle)s<p>
You can find it there: %(doiRecomm)s<p>
And there: %(linkRecomm)s<p>
Do not hesitate to share the news as much as possible: social networks if you are on them, mailing, websites, CV, quotation, etc...<p>
Thanks again for recommending this article for <i>%(appname)s</i>.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
			
				
			else:
				mySubject = '%s: Change in article status' % (appname)
				content = """
Dear %(destPerson)s,<p>
You have initiated the evaluation of the article entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s).<p>
The status of this article has changed from "%(tOldStatus)s" to "%(tNewStatus)s".<p>
You can view and manage your evaluation process by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Your contribtions —> Your recommendations of preprints' in the top menu.<p>
We thank you for managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
	print 'do_send_email_to_suggested_recommenders_useless'
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
		mySubject = '%s: About our request to act as recommender for a preprint' % (appname)
		#TODO: removing auth.user_id is not the best solution... Should transmit recommender_id
		suggestedQy = db( (db.t_suggested_recommenders.article_id==articleId) & (db.t_suggested_recommenders.suggested_recommender_id!=auth.user_id) & (db.t_suggested_recommenders.declined==False) & (db.t_suggested_recommenders.suggested_recommender_id==db.auth_user.id) ).select(db.t_suggested_recommenders.ALL, db.auth_user.ALL)
		for theUser in suggestedQy:
			destPerson = mkUser(auth, db, theUser['auth_user.id'])
			destAddress = db.auth_user[theUser['auth_user.id']]['auth_user.email']
			mailManagers = A(myconf.take('contacts.managers'), _href='mailto:'+myconf.take('contacts.managers'))
			#linkTarget=URL(c='recommender', f='my_awaiting_articles', scheme=scheme, host=host, port=port)
			#helpurl=URL(c='about', f='help_practical', scheme=scheme, host=host, port=port)
			# TODO: parallel submission
			content = """Dear %(destPerson)s,<p>
You have been suggested as recommender for a preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s).
This preprint has also attracted the attention of another <i>%(appname)s</i> recommender, who has initiated its evaluation. Consequently, this preprint no longer appears in your list of requests to act as a recommender on the <i>%(appname)s</i> webpage.<p>
If you would still like to participate in the evaluation of this preprint, please send us an e-mail at %(mailManagers)s.
We will inform the recommender handling the evaluation process of your willingness to participate and he/she may then contact you.<p>
We hope that, in the near future, you will have the opportunity to initiate the evaluation of another preprint.<p>
Thank you for your support.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>"""  % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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
		mySubject = '%s: Request to act as recommender for a preprint' % (appname)
		suggestedQy = db.executesql('SELECT DISTINCT au.*, sr.id AS sr_id FROM t_suggested_recommenders AS sr JOIN auth_user AS au ON sr.suggested_recommender_id=au.id WHERE sr.email_sent IS FALSE AND sr.declined IS FALSE AND article_id=%s;', placeholders=[article.id], as_dict=True)
		for theUser in suggestedQy:
			destPerson = mkUser(auth, db, theUser['id'])
			destAddress = db.auth_user[theUser['id']]['email']
			linkTarget=URL(c='recommender', f='article_details', vars=dict(articleId=article.id), scheme=scheme, host=host, port=port)
			helpurl=URL(c='about', f='help_generic', scheme=scheme, host=host, port=port)
			ethicsurl=URL(c='about', f='ethics', scheme=scheme, host=host, port=port)
			content = """Dear %(destPerson)s,<p>
You have been suggested as recommender for a preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s). You can obtain information about this request and accept or decline this invitation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging on to the <i>%(appname)s</i> website and going to 'Requests for input —> Do you agree to initiate a recommendation?' in the top menu.
<p>
<b>Important information before accepting to become the recommender for this preprint:</b>
The role of a recommender is very similar to that of a journal editor (finding reviewers, collecting reviews, taking editorial decisions based on reviews), and may lead to the recommendation of the preprint after several rounds of reviews. The evaluation forms the basis of the decision to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by <i>%(appname)s</i> is an article that may be used and cited like the ‘classic’ articles published in peer-reviewed journals. Details about the recommendation process can be found <a href="%(helpurl)s">here</a>. You can also watch this short video: <a href="https://youtu.be/u5greO-q8-M"> How to start and manage a preprint recommendation</a>.
<p>
Agreeing to become the recommender for this preprint means that <b>you find the preprint interesting</b> and therefore worth sending out for peer-review. Then, you will need to meet the following <b>requirements</b>:<br>
1- <b>to send invitations to 5-10 potential reviewers within the next 24 hours</b> and then to send reminders and/or new invitations until you find at least two reviewers willing to review the preprint. This process of finding reviews should take no more than a week.

<br>
2- <b>to post your decision</b> or to write your recommendation text <b>within 10 days</b> of receiving the reviews.<br>
3- <b>to write a recommendation text</b> if you decide to recommend this preprint for <i>%(appname)s</i> at the end of the evaluation process. Indeed, if after one or several rounds of review, you decide to recommend this preprint, you will need to write a “recommendation” that will have its own DOI and be published by <i>%(appname)s</i> under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (citing, at least, the preprint being recommended). All the editorial correspondence (reviews, your decisions, authors’ replies) will also be published by <i>%(appname)s</i>.<br>
4- <b>to declare that you have no conflict of interest with the authors or the content of the article.</b> Indeed, you should not handle articles written by close colleagues (with whom I have published in the last four years, with whom I have received joint funding in the last four years, or with whom I am currently writing a manuscript, or submitting a grant proposal), or written by family members, friends, or anyone for whom bias might affect the nature of my evaluation. See the <a href="%(ethicsurl)s">code of ethical conduct</a>.
Bear in mind that if you do not respect these commitments, the managing board of <i>%(appname)s</i> reserves the right to pass responsibility for the evaluation of this article to someone else.
<p>
Thank you for your help.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>"""  % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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
			linkTarget=URL(c='recommender', f='article_details', vars=dict(articleId=article.id), scheme=scheme, host=host, port=port)
			helpurl=URL(c='about', f='help_generic', scheme=scheme, host=host, port=port)
			theUser = db.auth_user[suggRecomm.suggested_recommender_id]
			mySubject = '%s: Request to act as recommender for a preprint (reminder)' % (appname)
			if theUser:
				destPerson = mkUser(auth, db, theUser['id'])
				destAddress = db.auth_user[theUser['id']]['email']
				content = """Dear %(destPerson)s,<p>
A few days ago, you were suggested as recommender for a preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s). You can obtain information about this request and accept or decline this invitation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging on to the <i>%(appname)s</i> website and going to 'Requests for input —> Do you agree to initiate a recommendation?' in the top menu.<p>
The role of a recommender is very similar to that of a journal editor (finding reviewers, collecting reviews, taking editorial decisions based on reviews), and may lead to the recommendation of the preprint after several rounds of reviews. The evaluation forms the basis of the decision to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by <i>%(appname)s</i> is an article that may be used and cited like the ‘classic’ articles published in peer-reviewed journals.<p>
If after one or several rounds of review, you decide to recommend this preprint, you will need to write a “recommendation” that will have its own DOI and be published by <i>%(appname)s</i> under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (citing, at least, the preprint being recommended). All the editorial correspondence (reviews, your decisions, authors’ replies) will also be published by <i>%(appname)s</i>.<p>
If you agree to handle this preprint, you will be responsible for managing the evaluation process until you reach a final decision (i.e. to recommend or reject this preprint). You will be able to invite, through the <i>%(appname)s</i> website, reviewers included in the <i>%(appname)s</i> database or from your own network.<p>
Details about the recommendation process can be found here <a href="%(helpurl)s">%(helpurl)s</a>. You can also watch this short video: <a href="https://youtu.be/u5greO-q8-M">How to start and manage a preprint recommendation</a>.<p>
Thanks again for your help.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>"""  % locals()
				try:
					myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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
## Do send email to all recommenders for a given available article
#def do_send_email_to_all_recommenders(session, auth, db, articleId):
	#print 'do_send_email_to_all_recommenders'
	#report = []
	#mail = getMailer(auth)
	#mail_resu = False
	#scheme=myconf.take('alerts.scheme')
	#host=myconf.take('alerts.host')
	#port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	#applongname=myconf.take('app.longname')
	#appdesc=myconf.take('app.description')
	#article = db.t_articles[articleId]
	#if article and article.status in ('Awaiting consideration'):
		#articleTitle = article.title
		#articleAuthors = article.authors
		#articleDoi = mkDOI(article.doi)
		#mySubject = '%s: Request to act as recommender for a preprint' % (appname)
		#suggestedQy = db.executesql("""SELECT DISTINCT au.*
			#FROM auth_user AS au 
			#JOIN auth_membership AS am ON au.id = am.user_id 
			#JOIN auth_group AS ag ON am.group_id = ag.id AND ag.role LIKE 'recommender'
			#WHERE au.id NOT IN (
				#SELECT sr.suggested_recommender_id
				#FROM t_suggested_recommenders AS sr
				#WHERE sr.email_sent IS TRUE AND sr.article_id=%s
			#);""", placeholders=[articleId], as_dict=True)
		#for theUser in suggestedQy:
			#destPerson = mkUser(auth, db, theUser['id'])
			#destAddress = db.auth_user[theUser['id']]['email']
			#linkTarget=URL(c='recommender', f='fields_awaiting_articles', scheme=scheme, host=host, port=port)
			#helpurl=URL(c='about', f='help_practical', scheme=scheme, host=host, port=port)
			#content = """Dear %(destPerson)s,<p>
#A preprint by %(articleAuthors)s and entitled <b>%(articleTitle)s</b> (DOI %(articleDoi)s) submitted to <i>%(appname)s</i> is requiring a recommender. We send you this alert because your profile has keywords in common with those of this preprint.<p>
#You can obtain information about this preprint and accept this invitation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Requests for input —> Consider preprint recommendation requests' in the top menu. If you cannot see the preprint in the list of preprints still requiring a recommender it means that another recommender has, in the meantime, taken charge of its evaluation.<p>
#As <i>%(appname)s</i> is a very recent initiative requiring as much support as possible, we would be extremely grateful if you would accept the role of recommender for this preprint (unless you do not consider it sufficiently interesting to merit initiation of the evaluation process of course). At this early stage in the project, it is vital that we find recommenders for as many valuable preprints as possible. We understand that this may require a little extra effort from you that you may not have anticipated, but it would provide significant assistance to a deserving initiative.<p>
#The role of a recommender is very similar to that of a journal editor (finding reviewers, collecting reviews, taking editorial decisions based on reviews), and may lead to the recommendation of the preprint after several rounds of review. The evaluation forms the basis of the decision to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by <i>%(appname)s</i> is an article that may be used and cited like the ‘classic’ articles published in peer-reviewed journals.<p>
#If after one or several rounds of review, you decide to recommend this preprint, you will need to write a “recommendation” that will have its own DOI and be published by <i>%(appname)s</i> under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (at least the reference of the preprint recommended). All the editorial correspondence (reviews, your decisions, authors’ replies) will also be published by <i>%(appname)s</i>.<p>
#If you agree to handle this preprint, you will be responsible for managing the evaluation process until you reach a final decision (i.e. recommend or reject this preprint). You will be able to invite, through the <i>%(appname)s</i> website, reviewers included in the <i>%(appname)s</i> database or not already present in this database.<p>
#Details about the recommendation process can be found here <a href="%(helpurl)s">%(helpurl)s</a>. You can also watch this short video: <a href="https://youtu.be/u5greO-q8-M">How to start and manage a preprint recommendation</a>.<p>
#Thanks again for your help.<p>
#Yours sincerely,<p>
#<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>"""  % locals()
			#try:
				#myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
				#mail_resu = mail.send(to=[destAddress],
							#subject=mySubject,
							#message=myMessage,
						#)
			#except:
				#pass
			#if mail_resu:
				#report.append( 'email sent to %s' % destPerson.flatten() )
			#else:
				#report.append( 'email NOT SENT to %s' % destPerson.flatten() )
			#time.sleep(mail_sleep)
		#print '\n'.join(report)
		#if session.flash is None:
			#session.flash = '; '.join(report)
		#else:
			#session.flash += '; ' + '; '.join(report)


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
			linkTarget = URL(c='user', f='my_reviews', scheme=scheme, host=host, port=port)
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
				content = """Dear %(destPerson)s,<p>
%(recommenderPerson)s, the recommender managing the evaluation process for the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s has made your review concerning this preprint available for modification.<p>
You can now access this review, and edit it if necessary.<p>
You can view and edit your reviews by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appame)s</i> website and going to 'Your contributions —> My reviews' in the top menu.<p>
We thank you again for agreeing to review this preprint.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
				try:
					myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: Review completed' % (appname)
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				destPerson = mkUser(auth, db, recomm.recommender_id)
				destAddress = db.auth_user[recomm.recommender_id]['email']
				reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
				content = """Dear %(destPerson)s,<p>
The review by %(reviewerPerson)s of the preprint entitled <b>%(articleTitle)s</b> is now available.
<p>
You can view and/or upload this review and manage your recommendation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Your contributions —> Your recommendations of preprints' in the top menu.
<p>
<b>If all the reviews have now been completed</b> and returned, <b>we now expect you</b>, according to your commitment as a recommender of the preprint, <b>to make a decision within a few days</b>.
If you need more time, please let us know by return mail.
<p>
We remind you that this decision must be: ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint.
<p>
If you decide to recommend this preprint, you will need to write a "recommendation" that will have its own DOI and will be published by <i>%(appname)s</i> under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (citing, at least, the preprint being recommended). All the editorial correspondence (reviews, your decisions, authors’ replies) relating to the preprint will also be published by <i>%(appname)s</i>.
<p>
We thank you again for managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: co-recommender accepted the recommendation' % (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
%(contributorPerson)s has accepted to co-sign the recommendation of the postprint entitled <b>%(articleTitle)s</b>.<p>
You may check your recommendation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging on to the <i>%(appname)s</i> website and going to 'Your contributions —> Your recommendations of postprints' in the top menu.<p>
We thank you again for writing this recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: co-recommender declined the recommendation' % (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
%(contributorPerson)s has declined your invitation to co-sign the recommendation of the postprint entitled <b>%(articleTitle)s</b>.<p>
You may check your recommendation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging to the <i>%(appname)s</i> website and going to 'Your contributions —> Your recommendations of postprints' in the top menu. You may invite another recommender to co-sign your recommendation if you wish.<p>
We thank you again for writing this recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: co-recommender agreed with the recommendation of the postprint' % (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			contributorPerson = mkUserWithMail(auth, db, press.contributor_id)
			content = """Dear %(destPerson)s,<p>
%(contributorPerson)s has agreed with the recommendation of the postprint entitled <b>%(articleTitle)s</b>.<p>
You may check your recommendation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Your contributions —> Your recommendations of postprints' in the top menu.<p>
We thank you again for writing this recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: Request to review accepted'% (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
			expectedDuration = datetime.timedelta(days=21) # three weeks
			dueTime = str((datetime.datetime.now() + expectedDuration).date())
			content = """Dear %(destPerson)s,<p>
%(reviewerPerson)s has accepted your invitation to review the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s), and has been sent a message indicating that this review must be posted or uploaded on the <i>%(appname)s</i> website before %(dueTime)s.<p>
You will receive a message notifying you of the posting of this review. If the review is not posted by the deadline, you can send the reviewer a reminder by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging on to the <i>%(appname)s</i> website and going to 'Your contributions —> Your recommendations of preprints' in the top menu.<p>
We thank you again for managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: Request to review declined' % (appname)
			destPerson = mkUser(auth, db, recomm.recommender_id)
			destAddress = db.auth_user[recomm.recommender_id]['email']
			reviewerPerson = mkUserWithMail(auth, db, rev.reviewer_id)
			content = """Dear %(destPerson)s,<p>
%(reviewerPerson)s has declined your invitation to review the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s).<p>
You will need to find another reviewer to obtain the two high-quality reviews required. You can invite additional reviewers by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Your contributions —> Your recommendations of preprints' in the top menu.<p>
We thank you again for managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
						content = """Dear %(destPerson)s,<p>
I have agreed to handle the evaluation of a preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s, for potential recommendation by <i>%(appdesc)s</i> (<i>%(appname)s</i>). This article can be visualized and downloaded at the following address (doi %(articleDoi)s).<p>
At first glance, this preprint appears to me to be potentially interesting, but I would like to have your expert opinion. I would therefore like to invite you to review this preprint for <i>%(appname)s</i>.<p>
If you have already reviewed a previous version of this MS, please consider this message as an invitation to review a new version of the preprint for a new round of evaluation.<p>
The evaluation process should guide the decision as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by <i>%(appname)s</i> is an article that may be used and cited like any ‘classic’ article published in a peer-reviewed journals.<p>
If I eventually reach a favorable conclusion, all the editorial correspondence (reviews, recommender’s decisions, authors’ replies) and a recommendation text will be published by <i>%(appname)s</i>, under the license CC-BY-ND. If after one or several rounds of review, I eventually reject the preprint, the editorial correspondence (and specifically your review) will be sent to the authors but will NOT published. You will be notified by e-mail at each stage in the procedure.<p>
Please let me know as soon as possible whether you are willing to accept my invitation to review this article, or whether you would prefer to decline, by clicking on the link below or by logging on to the <i>%(appname)s</i> website and going to 'Requests for input —> Do you agree to review a preprint?' in the top menu.<p>
If you agree, you will then be able to copy/paste, write or upload your review onto the <i>%(appname)s</i> website.<p>
Thanks in advance for your help.<p>
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
				destPerson = mkUser(auth, db, rev.reviewer_id)
				destAddress = db.auth_user[rev.reviewer_id]['email']
				recommenderPerson = mkUserWithMail(auth, db, lastRecomm.recommender_id)
				content = """Dear %(destPerson)s,<p>
The submission of the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s has been cancelled by the author.
Therefore, the recommendation process is closed. 
Thank you anyway for your help.<p>
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
		


#def do_send_email_to_reviewer_review_suggested(session, auth, db, reviewId):
	#report = []
	#mail = getMailer(auth)
	#mail_resu = False
	#scheme=myconf.take('alerts.scheme')
	#host=myconf.take('alerts.host')
	#port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	#applongname=myconf.take('app.longname')
	#appname=myconf.take('app.name')
	#appdesc=myconf.take('app.description')
	#rev = db.t_reviews[reviewId]
	#if rev and rev.review_state is None:
		#recomm = db.t_recommendations[rev.recommendation_id]
		#if recomm:
			#if recomm.recommender_id != rev.reviewer_id:
				#article = db.t_articles[recomm['article_id']]
				#if article:
					#articleTitle = article.title
					#articleDOI = article.doi
					#linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), scheme=scheme, host=host, port=port)
					#mySubject = '%s: Request to review a preprint' % (appname)
					#destPerson = mkUser(auth, db, rev.reviewer_id)
					#destAddress = db.auth_user[rev.reviewer_id]['email']
					#recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id)
					#content = """Dear %(destPerson)s,<p>
#I have agreed to handle the evaluation of a preprint entitled <b>%(articleTitle)s</b>, with a view to its recommendation by <i>%(appdesc)s</i> (<i>%(appname)s</i>). This article can be visualized and downloaded at the following address (doi %(articleDOI)s).<p>
#At first glance, it appears particularly interesting but I would like to have your expert opinion. I would therefore like to invite you to review this preprint for <i>%(appname)s</i>.<p>
#Note that you may have already reviewed a previous version of this preprint as several rounds of reviews might be necessary before a final decision is reached. In case you already reviewed a previous version of this MS, please consider this message as an invitation to review a new version of the preprint for a new round of evaluation.<p>
#Please let me know as soon as possible whether you are willing to accept my invitation to review this article, by clicking on this link: <a href="%(linkTarget)s">%(linkTarget)s</a> or by login to the <i>%(appname)s</i> website and go to 'Requests for input —> Do you agree to review a preprint?' in the top menu.<p>
#If you agree you will then be able to write or upload your review on the <i>%(appname)s</i> website.<p>
#Thanks in advance for your help.<p>
#Yours sincerely,<p>
#<span style="padding-left:1in;">%(recommenderPerson)s</span>
#""" % locals()
					#try:
						#myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
						#mail_resu = mail.send(to=[destAddress],
									#subject=mySubject,
									#message=myMessage,
								#)
					#except:
						#pass
					#if mail_resu:
						#report.append( 'email sent to reviewer %s' % destPerson.flatten() )
					#else:
						#report.append( 'email NOT SENT to reviewer %s' % destPerson.flatten() )
					#rev.review_state = 'Pending'
					#rev.update_record()
				#else:
					#print 'do_send_email_to_reviewer_review_suggested: Article not found'
			#else:
				#print 'do_send_email_to_reviewer_review_suggested: recommender = reviewer'
		#else:
			#print 'do_send_email_to_reviewer_review_suggested: Recommendation not found'
	#else:
		#print 'do_send_email_to_reviewer_review_suggested: Review not found'
	#print '\n'.join(report)
	#if session.flash is None:
		#session.flash = '; '.join(report)
	#else:
		#session.flash += '; ' + '; '.join(report)




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
		content = """Dear administrators,<p>
A new user has joined <i>%(appname)s</i>: %(userTxt)s (%(userMail)s).<p>
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
			content = """Dear %(destPerson)s,<p>
You have recently joined <i>%(applongname)s</i>. Thank you for your interest and for registering with us.<p>
More information about <i>%(appname)s</i> can be found here <a href="%(baseurl)s">%(baseurl)s</a> and in this <a href="https://www.youtube.com/watch?v=4PZhpnc8wwo">video</a>.<p>
As a user, you can submit your preprints to <i>%(appname)s</i> for evaluation and recommendation - and find five good reasons to do so in this short <a href="https://www.youtube.com/watch?v=jMhVl__gupg">video</a>. Briefly, your preprints must first be deposited on a preprint server, such as bioRxiv, and you must choose between A) exclusive submission to <i>%(appname)s</i>, or B) parallel submission with journals. Please go to <a href="%(infourl)s">%(infourl)s</a> for more information on these options. <p>
When submitting your preprints, you are allowed to suggest recommenders. A recommender is very similar to a journal editor (responsible for finding reviewers, collecting reviews, and making editorial decisions based on reviews), and may eventually recommend your preprint after one or several rounds of reviews. A preprint recommended by <i>%(applongname)s</i> is an article that may be used and cited like any ‘classic’ article published in a peer-reviewed journal.<p>
Once you have submitted your preprint, one of the recommenders you suggest, or any other recommenders from the community may express an interest in initiating the evaluation process for your preprint, which will involve sending your preprint out for peer review.<p>
If you wish to submit a preprint, please click on the "Submit a preprint" button on the home page of the <i>%(appname)s</i> website.<p>
As a user, you will also receive alerts every %(days)s concerning recommendations in the following fields published on the <i>%(applongname)s</i> web site: %(thematics)s.<p>
Finally, if you are interested in becoming a recommender for <i>%(appname)s</i> - <a href="https://www.youtube.com/watch?v=2BDrPoHGkn0">see video</a> - please contact a current recommender in your field via this link <a href="%(recommurl)s">%(recommurl)s</a>.<p>
Thanks again for your interest and for joining <i>%(applongname)s</i>.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(applongname)s</i></span>
""" % locals()
		else:
			content = """Dear %(destPerson)s,<p>
You have recently joined <i>%(appname)s</i>. Thank you for your interest and for registering with us.<p>
More information about <i>%(appname)s</i> can be found here <a href="%(baseurl)s">%(baseurl)s</a> and in this <a href="https://www.youtube.com/watch?v=4PZhpnc8wwo">video</a>.<p>
As a user, you can submit your preprints <i>%(appname)s</i> for evaluation and recommandation - and find five good reasons to do so in this short <a href="https://www.youtube.com/watch?v=jMhVl__gupg">video</a>. Briefly, your preprints must first be deposited on a preprint server, such as bioRxiv, and must not already be under review for publication in a traditional journal.<p>
When submitting your preprints, you are allowed to suggest recommenders. A recommender is very similar to a journal editor (responsible for finding reviewers, collecting reviews, and making editorial decisions based on reviews), and may eventually recommend your preprint after one or several rounds of reviews. A preprint recommended by <i>%(appname)s</i> is an article that may be used and cited like any ‘classic’ article published in a peer-reviewed journal.<p>
Once you have submitted your preprint, one of the recommenders you suggest, or any other recommenders from the community may express an interest in initiating the evaluation process for your preprint, which will involve sending your preprint out for peer review.<p>
If you wish to submit a preprint, please click on the "Submit a preprint" button on the home page of the <i>%(appname)s</i> website.<p>
As a user, you will also receive alerts every %(days)s concerning recommendations in the following fields published on the <i>%(appname)s</i> web site: %(thematics)s.<p>
Finally, if you are interested in becoming a recommender for <i>%(appname)s</i> - <a href="https://www.youtube.com/watch?v=2BDrPoHGkn0">see video</a> - please contact a current recommender in your field via this link <a href="%(recommurl)s">%(recommurl)s</a>.<p>
Thanks again for your interest and for joining <i>%(appname)s</i>.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
			content = """Dear %(destPerson)s,<p>
You are now a recommender of <i>%(appname)s</i>. We thank you for your time and support.<p>
The role of a recommender is very similar to that of a journal editor (finding reviewers, collecting reviews, making editorial decisions based on reviews), with the possibility of recommending the preprints you have chosen to handle after one or after several rounds of reviews. The evaluation process is designed to guide decisions as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint.<p>
A preprint recommended by <i>%(appname)s</i> is an article that may be used and cited like any ‘classic’ article published in a peer-reviewed journal. If you decide to recommend a preprint, you will need to write a “recommendation”, which will have its own DOI and be published by <i>%(appname)s</i> under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (citing, at least, the preprint being recommended). All the editorial correspondence (reviews, your decisions, authors’ replies) will also be published by <i>%(appname)s</i>.<p>
As a recommender for <i>%(appname)s</i>, <ul>
<li> You can recommend up to five articles per year. Details about the recommendation process can be found here <a href="%(helpurl)s">%(helpurl)s</a> and in this short <a href="https://youtu.be/u5greO-q8-M">video</a>.
<li> You will be expected to comply with the code of conduct of <i>%(appname)s</i>, which can be found here: <a href="%(ethicsurl)s">%(ethicsurl)s</a>
<li> You are eligible for selection as a member of the Managing Board for a period of two years. 
<li> You will be notified about new articles recommended by <i>%(appname)s</i>, according to your requested notification frequency and fields of interest. 
<li> You will also receive requests to intiate preprint evaluations in your fields of interest with a view to recommending them.
<li> You can propose the nomination of new recommenders to the Managing Board.<p>
Thanks again for your interest, your help and your support.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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
			content = """Dear %(destPerson)s,<p>
You have recently joined the Managing Board of <i>%(appname)s</i>. We thank you warmly for agreeing to join the Board and for your time and support for this community.<p>
The members of the Managing Board of <i>%(appname)s</i> are responsible for accepting/rejecting new recommenders. They also deal with any problems arising between authors and the recommenders who have evaluated/recommended their articles. They detect and deal with dysfunctions of <i>%(appname)s</i>, and may exclude recommenders, if necessary. They also rapidly check the quality of formatting and deontology for the reviews and recommendations published by <i>%(appname)s</i>. Finally, members of the Managing Board of <i>%(appname)s</i> are members of the non-profit organization “Peer Community in”. This non-profit organization is responsible for the creation and functioning of the various Peer Communities in….<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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
			linkTarget = URL(c='manager', f='pending_articles', scheme=scheme, host=host, port=port)
			content = """Dear members of the Managing Board,<p>
<i>%(appname)s</i> has received a submission of a preprint by %(submitterPerson)s.<p>
To validate or delete this submission, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Have a nice day!
""" % locals()
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
		
		elif newStatus.startswith('Pre-'):
			recomm = db( (db.t_recommendations.article_id == articleId) ).select(orderby=db.t_recommendations.id).last()
			recommenderPerson = mkUser(auth, db, recomm.recommender_id) or '' # recommender
			mySubject = '%s: Decision or recommendation requiring validation' % (appname)
			linkTarget = URL(c='manager', f='pending_articles', scheme=scheme, host=host, port=port)
			content = """Dear members of the Managing Board,<p>
A decision or a recommendation has been written by %(recommenderPerson)s for <i>%(appname)s</i>.<p>
To validate and/or manage this recommendation or decision, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Have a nice day!
""" % locals()
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
		
		elif newStatus=='Under consideration':
			recomm = db( (db.t_recommendations.article_id == articleId) ).select(orderby=db.t_recommendations.id).last()
			recommenderPerson = mkUser(auth, db, recomm.recommender_id) or '' # recommender
			linkTarget = URL(c='manager', f='ongoing_articles', scheme=scheme, host=host, port=port)
			if article.status == 'Awaiting revision':
				mySubject = '%s: Article resubmitted' % (appname)
				content = """Dear members of the Managing Board,<p>
A new version of the article entitled "%(articleTitle)s" is under consideration by %(recommenderPerson)s for <i>%(appname)s</i>.<p>
To manage this recommendation, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Have a nice day!
""" % locals()
			else:
				mySubject = '%s: Article considered for recommendation' % (appname)
				content = """Dear members of the Managing Board,<p>
A new recommendation is under consideration by %(recommenderPerson)s for <i>%(appname)s</i>.<p>
To manage this recommendation, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Have a nice day!
""" % locals()
			recommendation = mkFeaturedArticle(auth, db, article, printable=True, scheme=scheme, host=host, port=port)
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter(), recommendation=recommendation))
		
		elif newStatus=='Cancelled':
			mySubject = '%s: Article cancelled' % (appname)
			linkTarget = URL(c='manager', f='completed_articles', scheme=scheme, host=host, port=port)
			content = """Dear members of the Managing Board,<p>
The submission of the article entitled "%(articleTitle)s" has been cancelled by the author.<p>
To manage this recommendation, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Have a nice day!
""" % locals()
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
		else:
			mySubject = '%s: Article status changed' % (appname)
			linkTarget = URL(c='manager', f='all_articles', scheme=scheme, host=host, port=port)
			tOldStatus = current.T(article.status)
			tNewStatus = current.T(newStatus)
			content = """Dear members of the Managing Board,<p>
The status of the article entitled "%(articleTitle)s" changed from "%(tOldStatus)s" to "%(tNewStatus)s".<p>
To manage this recommendation, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
Have a nice day!
""" % locals()
			myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))

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
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=article.already_published))
			mySubject = '%s: Thank you for initiating a recommendation!' % (appname)
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				#recommender = mkUser(auth, db, recomm.recommender_id)
				destPerson = mkUser(auth, db, recomm.recommender_id)
				if article.already_published:
					content = """Dear %(destPerson)s,<p>
You have decided to recommend a postprint entitled <b>%(articleTitle)s</b>. To view and/or manage your recommendation, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a> or logging onto the <i>%(appname)s</i> website and going to 'Your contributions —> Your recommendations of postprints' in the top menu.<p>
We thank you in advance for writing this recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
				#else:
					#nbRecomms = db(db.t_recommendations.article_id==article.id).count()
					#if nbRecomms > 1 and article.status == 'Under consideration': 
						#content = """Dear %(destPerson)s,<p>
#You have agreed to be the recommender handling the preprint by %(articleAuthors)s and entitled <b>%(articleTitle)s</b> (DOI %(articleDoi)s). Thank you very much for your contribution.<p>
#An revised version of this manuscript have been submitted by the author.<p>
#Yours sincerely,<p>
#<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span><p>
#""" % locals()
					#else:
				try:
					myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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
			linkTarget = URL(c='recommender', f='my_recommendations', scheme=scheme, host=host, port=port, vars=dict(pressReviews=False))
			mySubject = '%s: Thank you for initiating a recommendation!' % (appname)
			recomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
			theUser = db.auth_user[recomm.recommender_id]
			if theUser:
				destPerson = mkUser(auth, db, theUser.id)
				if article.parallel_submission:
					content = """Dear %(destPerson)s,<p>
You have agreed to be the recommender handling the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s). Thank you very much for your contribution.
<p>
<b>We remind you that you have agreed to send out 5-10 invitations to review this preprint within the next 24 h</b>, and to send out reminders and/or new invitations, over a period of one week if necessary, until you find at least two reviewers willing to review this preprint within three weeks. We thank you in advance for respecting this commitment.
<p>
Invitations to review can be sent using this link <a href="%(linkTarget)s">%(linkTarget)s</a> – 
You can also log on to the <i>%(appname)s</i> website and go to 'Your contributions —> Your recommendations of preprints' in the top menu, and click on the 'choose a reviewer' button.
<p>
The reviews you receive should guide your decision – <b>within 10 days of receiving the last review</b> – as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint.
<p>
If your decision is to ‘Recommend’ this preprint, you will need to write a “recommendation”, which will have its own DOI and be published by <i>%(appname)s</i> under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (citing, at least, the preprint being recommended). All editorial correspondence (reviews, your decisions, authors' replies) relating to the preprint will also be published by <i>%(appname)s</i>.
<p>
The authors have chosen to submit elsewhere in parallel. As there is a chance that the manuscript is accepted for publication elsewhere and consequently the authors might abandon the process at <i>%(appname)s</i>, we have the following mechanism to ensure reviewers’ work is respected and documented. If the authors abandon the process at <i>%(appname)s</i> after reviewers have written their reports, you should post the reviewers' reports on the <i>%(appname)s</i> website as recognition of the reviewers' work and in order to enable critical discussion. Note that there remains the outcome of rejection by you, wherein reports are not made public.<p>
<p>
If you need assistance in any way do not hesitate to ask us.<p>
We thank you again for initiating and managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span><p>
""" % locals()
				else:
					content = """Dear %(destPerson)s,<p>
You have agreed to be the recommender handling the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s). Thank you very much for your contribution.
<p>
<b>We remind you that you have agreed to send out 5-10 invitations to review this preprint within the next 24 h</b>, and to send out reminders and/or new invitations, over a period of one week if necessary, until you find at least two reviewers willing to review this preprint within three weeks. We thank you in advance for respecting this commitment.
<p>
Invitations to review can be sent using this link <a href="%(linkTarget)s">%(linkTarget)s</a> – 
You can also log on to the <i>%(appname)s</i> website and go to 'Your contributions —> Your recommendations of preprints' in the top menu, and click on the 'choose a reviewer' button.
<p>
The reviews you receive should guide your decision – <b>within 10 days of receiving the last review</b> – as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint.
<p>
If your decision is to ‘Recommend’ this preprint, you will need to write a “recommendation”, which will have its own DOI and be published by <i>%(appname)s</i> under the license CC-BY-ND. The recommendation is a short article, similar to a News & Views piece. It has its own title, contains between about 300 and 1500 words, describes the context and explains why the preprint is particularly interesting. The limitations of the preprint can also be discussed. This text also contains references (citing, at least, the preprint being recommended). All editorial correspondence (reviews, your decisions, authors' replies) relating to the preprint will also be published by <i>%(appname)s</i>.
<p>
If you need assistance in any way do not hesitate to ask us.<p>
We thank you again for initiating and managing this evaluation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span><p>
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
				linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=scheme, host=host, port=port)
				mySubject = '%s: Thank you for agreeing to review a preprint!' % (appname)
				theUser = db.auth_user[rev.reviewer_id]
				if theUser:
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
					destPerson = mkUser(auth, db, rev.reviewer_id)
					expectedDuration = datetime.timedelta(days=21) # three weeks
					dueTime = str((datetime.datetime.now() + expectedDuration).date())
					content = """Dear %(destPerson)s,<p>
Thank you very much for agreeing to review the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s (DOI %(articleDoi)s). Please complete your review within three weeks, hence before <b>%(dueTime)s</b>. If this dealine is too short, please let me know as soon as possible. Otherwise, thank you in advance for respecting this deadline.<p>
To view, write, upload and manage your review, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a> or log onto the <i>%(appname)s</i> website and go to ‘Your contributions —> Your reviews’ in the top menu.<p>
When you have written or uploaded your review, you can:<p>
1) save a draft version of your review for future modification by clicking on the ‘Save’ button; this allows you to make changes or to complete your review later;<p>
or<p>
2) save and send me your review by clicking on the ‘Save & submit your review’ button.<p>
If you have saved a draft version of your review, you can come back to it for modification or completion by clicking on ‘Your contributions —> Your reviews’ in the top menu, and then on the black ‘View/Edit’ button to the right on the corresponding line. Don’t forget to click on the ‘Save & submit your review’ button to send your completed review to me.<p>
Thanks in advance for the time spent evaluating this preprint.<p>
I look forward to reading your review.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The recommender, %(recommenderPerson)s</span>
""" % locals()
					try:
						myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
						if newForm['emailing']:
							emailing0 = newForm['emailing']
						else:
							emailing0= ''
						emailing = '<h2>'+str(datetime.datetime.now())+'</h2>'
						emailing += myMessage
						emailing += '<hr>'
						emailing += emailing0
						newForm['emailing'] = emailing
						#rev.update_record()
						mail_resu = mail.send(to=[theUser['email']],
									subject=mySubject,
									message=myMessage,
								)
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
				linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=scheme, host=host, port=port)
				mySubject = '%s: Thank you for evaluating a preprint' % (appname)
				theUser = db.auth_user[rev.reviewer_id]
				if theUser:
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
					destPerson = mkUser(auth, db, rev.reviewer_id)
					content = """Dear %(destPerson)s,<p>
Thank you for evaluating the preprint entitled <b>%(articleTitle)s</b> by %(articleAuthors)s. Your evaluation has been sent to the recommender (%(recommenderPerson)s) handling this preprint. Your contribution is greatly appreciated.<p>
You can use this message as proof of your work for <i>%(appname)s</i> and you can view your review at <a href="%(linkTarget)s">%(linkTarget)s</a>. Your review, together with the other reviews of this preprint, will guide the decision of the recommender (%(recommenderPerson)s) as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ this preprint.<p>
Remember that if the recommender eventually comes to a favorable conclusion, all of the editorial correspondence (reviews, including yours, the decisions reached by the recommender, and the authors’ replies) and a recommendation text will be published by <i>%(appname)s</i>, under the license CC-BY-ND. If, after one or several rounds of review, the recommender eventually rejects the preprint, the editorial correspondence will be sent to the authors but will NOT be published. You will be notified by e-mail at each stage in the procedure. If the recommender asks the authors to revise their preprint, he/she may invite you to evaluate their responses and the changes they have made to the preprint. If required, we therefore hope that you will be willing to take part in a second round of review.<p>
If you decided NOT to remain anonymous, your name will be passed on to the authors and, if the recommender decides to recommend this preprint, your name will be visible and associated with your review on the %(appname)s website. If you wish to change your mind and remain anonymous, please send a message to %(contactMail)s, to let the members of the Managing Board know (they will make the necessary changes).<p>
In the meantime, thank you again for conducting this evaluation. We really appreciate it.<p>
Best wishes,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span><p>""" % locals()

					try:
						myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
						if newForm['emailing']:
							emailing0 = newForm['emailing']
						else:
							emailing0= ''
						emailing = '<h2>'+str(datetime.datetime.now())+'</h2>'
						emailing += myMessage
						emailing += '<hr>'
						emailing += emailing0
						newForm['emailing'] = emailing
						#rev.update_record()
						mail_resu = mail.send(to=[theUser['email']],
									subject=mySubject,
									message=myMessage,
								)
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
					content = """Dear %(destPerson)s,<p>
A recommendation text for the %(articlePrePost)s by <i>%(articleAuthors)s</i> and entitled <b>%(articleTitle)s</b> (DOI %(articleDoi)s) is under consideration.<p>
You have been removed from co-recommender of this %(articlePrePost)s.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
					linkTarget = URL(c='recommender', f='my_co_recommendations', scheme=scheme, host=host, port=port)
					mySubject = '%(appname)s: Your co-recommendation of a %(articlePrePost)s' % locals()
					destPerson = mkUser(auth, db, contrib.contributor_id)
					destAddress = db.auth_user[contrib.contributor_id]['email']
					recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
					ethicsLink = URL('about', 'ethics', scheme=scheme, host=host, port=port)
					if article.status in ('Under consideration', 'Pre-recommended'):
						if article.already_published:
							content = """Dear %(destPerson)s,<p>
A recommendation text for the %(articlePrePost)s by <i>%(articleAuthors)s</i> and entitled <b>%(articleTitle)s</b> (DOI %(articleDoi)s) is under consideration. You have been declared as a co-recommender of this %(articlePrePost)s. You can view the recommendation by following this link <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Your contributions —> Your co-recommendations' in the top menu.<p>
We are currently handling this recommendation; it will probably be rapidly posted on the <i>%(appname)s</i> website.<p>
If you do not wish to co-author this recommendation, please contact us as soon as possible. Otherwise, we thank you for co-writing this recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
						else:
							content = """Dear %(destPerson)s,<p>
 A peer-review evaluation of a preprint by <i>%(articleAuthors)s</i> and entitled <b>%(articleTitle)s</b> (DOI %(articleDoi)s) is currenlty handled by the recommender %(recommenderPerson)s. This recommender declared you as a co-recommender and, as such, as a co-author of the recommendation if he/she decides to recommend this preprint. The reviews and the recommendation text can be viewed by clicking on this link: <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Your contributions —> Your co-recommendations' in the top menu.<p>
We remind you that a preprint is recommended if, and only if it is scientifically valid and of high quality and the code of conduct has been followed. The decision to recommend a preprint must be based on high-quality reviews. We also remind you that, the recommendation text, all the editorial correspondence (reviews, decisions, your recommendation and authors’ replies) will be published by <i>%(appname)s</i>. Being a co-recommender for this preprint means that you share full responsibility with the recommender for the public recommendation of this preprint.<p>
If you do not wish to be a co-recommender of this preprint, please contact us as soon as possible. Otherwise, we thank you for this contribution to <i>%(appname)s</i>.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
		linkTarget = URL(c='recommender', f='my_co_recommendations', scheme=scheme, host=host, port=port)
		recommenderPerson = mkUserWithMail(auth, db, recomm.recommender_id) or ''
		mySubject = '%(appname)s: Your co-recommendation of a %(articlePrePost)s' % locals()
		for contrib in contribs:
			destPerson = mkUser(auth, db, contrib.contributor_id)
			destAddress = db.auth_user[contrib.contributor_id]['email']
			
			if newStatus == 'Recommended':
				linkTarget = URL(c='default', f='index', scheme=scheme, host=host, port=port)
				content = """Dear %(destPerson)s,<p>
The recommendation for the %(articlePrePost)s by <i>%(articleAuthors)s</i> and entitled <b>%(articleTitle)s</b> (doi %(articleDoi)s) is now published on <i>%(appname)s</i> website: <a href="%(linkTarget)s">%(linkTarget)s</a>.<p>
We thank you for co-writing this recommendation.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
			
			else:
				content = """Dear %(destPerson)s,<p>
You are co-recommender of the article by %(articleAuthors)s entitled <b>%(articleTitle)s</b> (DOI %(articleDoi)s).<p>
The status of this article has changed from "%(tOldStatus)s" to "%(tNewStatus)s".<p>
You can view the evaluation process by following this link: <a href="%(linkTarget)s">%(linkTarget)s</a> or by logging onto the <i>%(appname)s</i> website and going to 'Your contribtions —> Your co-recommendations' in the top menu.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
			
			try:
				myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
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
	content = """Dear %(destPerson)s,<p>
We are pleased to inform you that the following recommendations have recently been published by <i>%(appname)s</i>.<p>
We hope you will appreciate them and share them through your social networks.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
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
def do_send_email_decision_to_reviewer(session, auth, db, articleId, newStatus):
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
			linkTarget = URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), scheme=scheme, host=host, port=port)
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
					linkRecomm = URL(c='public', f='rec', vars=dict(id=article.id), scheme=scheme, host=host, port=port)
					content = """Dear %(destPerson)s,<p>
The article that you kindly reviewed for <i>%(appname)s</i> is now recommended. The recommendation of this article - along with your reviews - is now posted on the posted on the <i>%(appname)s</i> website.<p>
The reference of your recommendation is:<p>
%(myRefRecomm)s<p>
The reference of the recommended article is:<p>
%(myRefArticle)s<p>
You can find it there: %(recommDOI)s<p>
And there: %(linkRecomm)s<p>
Do not hesitate to share the news as much as possible: social networks if you are on them, mailing, websites, CV, quotation, etc...<p>
Thanks again for reviewing this article for <i>%(appname)s</i>.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
				else:
					content = """Dear %(destPerson)s,<p>
You have agreed to review the preprint entitled <b>%(articleTitle)s</b>.
The status of this preprint is now: %(articleStatus)s.
To view your review, the reviews of the other referees and the decision taken by the recommender, please follow this link <a href="%(linkTarget)s">%(linkTarget)s</a> or login to the <i>%(appname)s</i> website and go to 'Your contributions —> My reviews' in the top menu.<p>
We thank you for the time spent evaluating this preprint.<p>
Yours sincerely,<p>
<span style="padding-left:1in;">The Managing Board of <i>%(appname)s</i></span>
""" % locals()
				try:
					myMessage = render(filename=filename, context=dict(content=XML(content), footer=mkFooter()))
					mail_resu = mail.send(to=[rev.auth_user.email],
								subject=mySubject,
								message=myMessage,
							)
					if review.emailing:
						emailing0 = review.emailing
					else:
						emailing0= ''
					emailing = '<h2>'+str(datetime.datetime.now())+'</h2>'
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
						link = URL(c='default', f='user', args='reset_password', vars=dict(key=reset_password_key, _next=linkTarget), scheme=scheme, host=host, port=port)
					else:
						link = URL(c='default', f='user', args='reset_password', vars=dict(key=reset_password_key), scheme=scheme, host=host, port=port)
					myMessage.append(P())
					myMessage.append(P(B(current.T('Please, follow this link in order to validate your account:'))))
					myMessage.append(A(link, _href=link))
				elif linkTarget:
					myMessage.append(P())
					if review.review_state is None or review.review_state == 'Pending' or review.review_state == '':
						myMessage.append(P(B(current.T('TO ACCEPT OR DECLINE CLICK ON THE FOLLOWING LINK:'))))
						myMessage.append(A(linkTarget, _href=linkTarget))
					elif review.review_state == 'Under consideration':
						myMessage.append(P(B(current.T('TO WRITE, EDIT OR UPLOAD YOUR REVIEW CLICK ON THE FOLLOWING LINK:'))))
						myMessage.append(A(linkTarget, _href=linkTarget))
				try:
					myRenderedMessage = render(filename=filename, context=dict(content=XML(myMessage), footer=mkFooter()))
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

