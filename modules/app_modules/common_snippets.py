# -*- coding: utf-8 -*-

import gc
import os
import pytz, datetime
from re import sub, match
from copy import deepcopy
from datetime import datetime, timedelta
from dateutil.relativedelta import *
from collections import OrderedDict

import io
from PIL import Image

from gluon import current, IS_IN_DB
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail
from gluon.sqlhtml import *

import common_small_html
import common_html
import common_tools

myconf = AppConfig(reload=True)


######################################################################################################################################################################
# A Trier
######################################################################################################################################################################
# Builds the right-panel for home page


######################################################################################################################################################################
def getRecommArticleRowCard(auth, db, response, article, withImg=True, withScore=False, withDate=False, fullURL=False):
	if fullURL:
		scheme=myconf.take('alerts.scheme')
		host=myconf.take('alerts.host')
		port=myconf.take('alerts.port', cast=lambda v: common_small_html.takePort(v) )
	else:
		scheme=False
		host=False
		port=False

	# Get Recommendation
	recomm = db( (db.t_recommendations.article_id==article.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=db.t_recommendations.id).last()
	if recomm is None: 
		return None
	
	recommAuthors = common_html.getRecommAndReviewAuthors(auth, db, article, with_reviewers=True, linked=True, host=host, port=port, scheme=scheme)
	
	if withDate:
		date = common_small_html.mkLastChange(article.last_status_change)

	articleImg = ''
	if withImg:
		if (article.uploaded_picture is not None and article.uploaded_picture != ''):
			articleImg = IMG(
				_src=URL('default', 'download', scheme=scheme, host=host, port=port, args=article.uploaded_picture),
				_alt='article picture', 
				_class='pci-articlePicture'
			)
		
	recommShortText = common_tools.getShortText(recomm.recommendation_comments, 500) or ''
	
	authors = common_tools.getShortText(article.authors, 500) or ''
	
	# (gab) Where do i need to place this ?
	# if withScore:
	# 		resu.append(TD(row.score or '', _class='pci-lastArticles-date'))
	
	snippetVars = dict(
		articleDate = date,
		articleUrl = URL(c='articles', f='rec', vars=dict(id=article.id, reviews=True), scheme=scheme, host=host, port=port),
		articleTitle = article.title,
		articleImg = articleImg,
		isAlreadyPublished = article.already_published,
		articleAuthor = authors,
		articleDoi = common_small_html.mkDOI(article.doi),
		recommendationAuthors = SPAN(recommAuthors),
		recommendationTitle = recomm.recommendation_title,
		recommendationShortText = WIKI(recommShortText)
	)

	return XML(
		response.render(
			'snippets/article_row_card.html',
			snippetVars
		)
	)
	

######################################################################################################################################################################
def getArticleTrackcRowCard(auth, db, response, article):
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: common_small_html.takePort(v) )
	applongname=myconf.take('app.longname')

	nbReviews = db( (db.t_recommendations.article_id == article.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_reviews.review_state.belongs('Under consideration', 'Completed')) ).count(distinct=db.t_reviews.id)
	if nbReviews > 0 :
		track = DIV(_class='pci-trackItem')
		link = common_small_html.mkDOI(article.doi)
		firstDate = article.upload_timestamp.strftime('%Y-%m-%d')
		lastDate = article.last_status_change.strftime('%Y-%m-%d')
		title = article.title
		if (article.anonymous_submission):
			authors = '[anonymous submission]'
		else:
			authors = article.authors
		
		# pci-status
		if article.status == 'Recommended':
			#txt = DIV(SPAN(current.T(' is')), SPAN(current.T('RECOMMENDED'), _class='pci-trackStatus success'), SPAN(SPAN('(', firstDate, ' ➜ ', lastDate, ')'), '. ', A('See recommendations and reviews', _href=URL('articles', 'rec', scheme=scheme, host=host, port=port, vars=dict(id=article.id)), _class='btn btn-success')))
			txt = DIV(
			SPAN(current.T(' was')), 
			SPAN(current.T('UNDER REVIEW'), _class='pci-trackStatus default'),
			SPAN(
				SPAN('(', firstDate, ' ➜ ', lastDate, ')'),'. ')
			)

		elif article.status == 'Cancelled':
			txt = DIV(SPAN(current.T(' was')), SPAN(current.T('UNDER REVIEW'), _class='pci-trackStatus default'), SPAN('(', firstDate, ' ➜ ', lastDate, '). '))
			
		elif article.status == 'Under consideration' or article.status == 'Pre-recommended' or article.status == 'Pre-rejected' or article.status == 'Pre-revision':
			txt = DIV(SPAN(current.T(' is')), SPAN(current.T('UNDER REVIEW'), _class='pci-trackStatus info'), SPAN('(', current.T('Submitted on'), ' ', firstDate, ')'))
			
		elif article.status == 'Awaiting revision' :
			txt = DIV(SPAN(current.T(' was')), SPAN(current.T('UNDER REVIEW'), _class='pci-trackStatus default'), SPAN('(', current.T('Submitted on'), ' ', firstDate, ')'))

		else:
			return(None)
	

		snippetVars = dict(
			articleId = article.id,
			articleImg = IMG(_src=URL(c='static', f='images/small-background.png', scheme=scheme, host=host, port=port), _class='pci-trackImg'),
			articleTitle = title,
			articleAuthor = authors,
			articleDoi = link,
			articleStatus = article.status,
			articleStatusText = txt
		)
		
		return XML(
			response.render(
				'snippets/article_track_row_card.html',
				snippetVars
			)
		)
	# no article reviews founded 
	else:
		return None


######################################################################################################################################################################
def getRecommendationHeaderHtml(auth, db, response, art, finalRecomm, fullURL=True):
	if fullURL:
		scheme=myconf.take('alerts.scheme')
		host=myconf.take('alerts.host')
		port=myconf.take('alerts.port', cast=lambda v: common_small_html.takePort(v) )
	else:
		scheme=False
		host=False
		port=False
		
	## NOTE: article facts
	if (art.uploaded_picture is not None and art.uploaded_picture != ''):
		article_img = IMG(_alt='picture', _src=URL('default', 'download', args=art.uploaded_picture))
	else:
		article_img = ''
	
	recomm_altmetric = ''
	if finalRecomm.recommendation_doi:
		recomm_altmetric = XML(
				'''
					<div class='text-right altmetric-embed pci2-altmetric'  data-badge-type='donut' data-badge-details='left' data-hide-no-mentions='true' data-doi='%s'></div>
				''' % sub(r'doi: *', '', finalRecomm.recommendation_doi)
			)

	doi = sub(r'doi: *', '', (art.doi or ''))
	article_altmetric = XML("<div class='altmetric-embed pci2-altmetric' data-badge-type='donut' data-badge-details='right' data-hide-no-mentions='true' data-doi='%s'></div>" % doi)

	headerContent = dict()
	headerContent.update([
		('articleVersion', SPAN(' '+current.T('version')+' '+art.ms_version) if art.ms_version else ''),
		('articleImg', article_img),
		('articleTitle', art.title or ''),
		('articleAuthor', art.authors or ''),
		('articleAbstract', art.abstract or ''),
		('articleDoi', (common_small_html.mkDOI(art.doi)) if (art.doi) else SPAN('')),
		('recomm_altmetric', recomm_altmetric),
		('article_altmetric', article_altmetric),
		('isRecommended', True)
	])
	
	# Last recommendation
	finalRecomm = db( (db.t_recommendations.article_id==art.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=~db.t_recommendations.id).last()

	citeNum = ''
	citeRef = None
	if finalRecomm.recommendation_doi:
		citeNumSearch = re.search('([0-9]+$)', finalRecomm.recommendation_doi, re.IGNORECASE)
		if citeNumSearch:
			citeNum = citeNumSearch.group(1)
		citeRef = common_small_html.mkDOI(finalRecomm.recommendation_doi)
		
	if citeRef:
		citeUrl = citeRef
	else:
		citeUrl = URL(c='articles', f='rec', vars=dict(id=art.id), host=host, scheme=scheme, port=port)
		citeRef = A(citeUrl, _href=citeUrl) # + SPAN(' accessed ', datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))
	
	recommAuthors = common_html.mkWhoDidIt4Recomm(auth, db, finalRecomm, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)
	cite = DIV(
				SPAN(B('Cite this recommendation as:', _class="pci2-main-color-text"), 
				BR(), SPAN(recommAuthors), ' ', finalRecomm.last_change.strftime('(%Y)'), ' ', finalRecomm.recommendation_title, '. ', I(myconf.take('app.description')+', '+(citeNum or '')+'. '), 
				citeRef, 
			), _class='pci-citation')

	whoDidRecomm = common_html.mkWhoDidIt4Recomm(auth, db, finalRecomm, with_reviewers=True, linked=True, as_items=False, host=host, port=port, scheme=scheme)
	
		# PDF (if any)
	pdf_query = db(db.t_pdf.recommendation_id == finalRecomm.id).select(db.t_pdf.id, db.t_pdf.pdf)
	if len(pdf_query) > 0:
		pdfUrl = URL('articles', 'rec', vars=dict(articleId=art.id, asPDF=True), host=host, scheme=scheme, port=port)
		pdfLink = A(SPAN(current.T('PDF recommendation'), ' ', IMG(_alt='pdf', _src=URL('static', 'images/application-pdf.png'))), _href=pdfUrl, _class='btn btn-info pci-public')
	else:
		pdfUrl = None
		pdfLink = None

	headerContent.update([
			('recommTitle', finalRecomm.recommendation_title if ((finalRecomm.recommendation_title or '') != '') else current.T('Recommendation')),
			('recommAuthor', whoDidRecomm),
			('recommDateinfos',(  
				I(art.upload_timestamp.strftime('Submitted: %d %B %Y')) if art.upload_timestamp else '',
				', ',
				I(finalRecomm.last_change.strftime('Recommended: %d %B %Y')) if finalRecomm.last_change else '')
			),
			('cite', cite),
			('recommText', WIKI(finalRecomm.recommendation_comments or '')),
			('pdfLink', pdfLink)
		])
	

	
	headerHtml = XML(
			response.render(
				'snippets/recommendation_header.html',
				headerContent
			)
		) 

	# Get METADATA (see next function)
	recommMetadata = getRecommendationMetadata(auth, db, art, finalRecomm, pdfLink, citeNum, scheme, host, port)

	return dict(headerHtml=headerHtml, recommMetadata=recommMetadata)

def getRecommendationMetadata(auth, db, art, lastRecomm, pdfLink, citeNum, scheme, host, port):
	desc = 'A recommendation of: '+(art.authors or '')+' '+(art.title or '')+' '+(art.doi or '')
	whoDidItMeta = common_html.mkWhoDidIt4Recomm(auth, db, lastRecomm, with_reviewers=False, linked=False, as_list=True, as_items=False)
	
	# META headers
	myMeta = OrderedDict()
	myMeta['citation_title'] = lastRecomm.recommendation_title
	if len(whoDidItMeta)>0:
		# Trick for multiple entries (see globals.py:464)
		for wdi in whoDidItMeta:
			myMeta['citation_author_%s' % wdi] = OrderedDict([('name', 'citation_author'), ('content', wdi)])
	myMeta['citation_journal_title'] = myconf.take("app.description")
	myMeta['citation_publication_date'] = (lastRecomm.last_change.date()).strftime('%Y/%m/%d')
	myMeta['citation_online_date'] = (lastRecomm.last_change.date()).strftime('%Y/%m/%d')
	myMeta['citation_journal_abbrev'] = myconf.take("app.name")
	myMeta['citation_issn'] = myconf.take("app.issn")
	myMeta['citation_volume'] = '1'
	myMeta['citation_publisher'] = 'Peer Community In'
	if lastRecomm.recommendation_doi:
		myMeta['citation_doi'] = sub(r'doi: *', '', lastRecomm.recommendation_doi) # for altmetrics
	if citeNum:
		myMeta['citation_firstpage'] = citeNum
	myMeta['citation_abstract'] = desc
	if pdfLink:
		myMeta['citation_pdf_url'] = pdfLink

	#myMeta['og:title'] = lastRecomm.recommendation_title
	#myMeta['description'] = desc

	# Dublin Core fields
	myMeta['DC.title'] = lastRecomm.recommendation_title
	if len(whoDidItMeta)>0:
		myMeta['DC.creator'] = ' ; '.join(whoDidItMeta) # syntax follows: http://dublincore.org/documents/2000/07/16/usageguide/#usinghtml
	myMeta['DC.issued'] = lastRecomm.last_change.date()
	#myMeta['DC.date'] = lastRecomm.last_change.date()
	myMeta['DC.description'] = desc
	myMeta['DC.publisher'] = myconf.take("app.description")
	myMeta['DC.relation.ispartof'] = myconf.take("app.description")
	if lastRecomm.recommendation_doi:
		myMeta['DC.identifier'] = myMeta['citation_doi']
	if citeNum:
		myMeta['DC.citation.spage'] = citeNum
	myMeta['DC.language'] = 'en'
	myMeta['DC.rights'] = '(C) %s, %d' % (myconf.take("app.description"), lastRecomm.last_change.date().year)

	return myMeta

######################################################################################################################################################################
def getReviewRoundsHtml(auth, db, response, articleId): 
	recomms = db( (db.t_recommendations.article_id==articleId) ).select(orderby=~db.t_recommendations.id)

	recommRound = len(recomms)
	reviewRoundsHtml = DIV()
	
	indentationLeft = 0
	for recomm in recomms:
		roundNumber = recommRound

		lastChanges = ''
		recommendationText = ''
		preprintDoi = ''
		isLastRecomm = False
		if recomms[0].id == recomm.id:
			isLastRecomm = True
		else:
			lastChanges = SPAN(I(recomm.last_change.strftime('%Y-%m-%d')+' ')) if recomm.last_change else ''
			recommendationText = recomm.recommendation_comments or ''
			preprintDoi = DIV(I(current.T('Preprint DOI:')+' '), common_small_html.mkDOI(recomm.doi), BR()) if ((recomm.doi or '')!='') else ''

		reviewsList = db( (db.t_reviews.recommendation_id==recomm.id) & (db.t_reviews.review_state=='Completed') ).select(orderby=db.t_reviews.id)
		reviwesPreparedData = []

		for review in reviewsList:
			if review.anonymously:
				reviewAuthorAndDate = SPAN(
					current.T('Reviewed by')+' '+
					current.T('anonymous reviewer')+
					(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else '')
				)
						
			else:
				reviewAuthorAndDate = SPAN(
					current.T('Reviewed by'),' ',
					common_small_html.mkUser(auth, db, review.reviewer_id, linked=True),
					(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else '')
				)
						
			reviewText = None
			if len(review.review)>2:
				reviewText = DIV(WIKI(review.review), _class='pci-bigtext margin')

			pdfLink = None
			if review.review_pdf:
				pdfLink = DIV(A(current.T('Download the review (PDF file)'), _href=URL('default', 'download', args=review.review_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin')

			reviwesPreparedData.append(dict(
				authorAndDate = reviewAuthorAndDate,
				text = reviewText,
				pdfLink = pdfLink
			))

		authorsReply = None
		if recomm.reply:
			authorsReply = DIV(WIKI(recomm.reply), _class='pci-bigtext')
		
		authorsReplyPdfLink	 = None
		if recomm.reply_pdf:
			authorsReplyPdfLink =  DIV(A(current.T('Download author\'s reply (PDF file)'), _href=URL('default', 'download', args=recomm.reply_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'),
				
		recommRound -= 1

		snippetVars = dict(
			indentationLeft = indentationLeft,
			isLastRecomm = isLastRecomm or False,
			roundNumber = roundNumber,
			lastChanges = lastChanges,
			recommendationText = recommendationText,
			preprintDoi = preprintDoi,
			reviewsList = reviwesPreparedData,
			authorsReply = authorsReply,
			authorsReplyPdfLink = authorsReplyPdfLink
		)

		indentationLeft += 16

		reviewRoundsHtml.append(
			XML(
				response.render(
					'snippets/review_rounds.html',
					snippetVars
				)
			)
		)

	return reviewRoundsHtml


######################################################################################################################################################################
def getRecommCommentListAndForm(auth, db, response, session, articleId, with_reviews=False, parentId=None):
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: common_small_html.takePort(v) )

	isLoggedIn = False
	scrollToCommentForm = False

	if auth.user_id is not None:
		isLoggedIn = True

	# Create New Comment Form
	commentForm = None
	if isLoggedIn:
		if parentId is not None:
			# Scroll to comment form if 'replyTo' se in request.vars (see jquery in 'snippets/comments_tree_and_form.html')
			scrollToCommentForm = True
			fields = ['parent_id', 'user_comment']
		else: 
			fields = ['user_comment']

		db.t_comments.user_id.default = auth.user_id
		db.t_comments.user_id.readable = False
		db.t_comments.user_id.writable = False
		db.t_comments.article_id.default = articleId
		db.t_comments.article_id.writable = False
		db.t_comments.parent_id.default = parentId
		db.t_comments.parent_id.writable = False

		commentForm = SQLFORM(db.t_comments
			,fields = fields
			,showid = False
		)

		if commentForm.process().accepted:
			session.flash = current.T('Comment saved', lazy=False)
			redirect(URL(c='articles', f='rec', vars=dict(id=articleId, comments=True, reviews=with_reviews)))
		elif commentForm.errors:
			response.flash = current.T('Form has errors', lazy=False)

	# Get comments tree
	commentsTree = DIV()
	commentsQy = db( (db.t_comments.article_id == articleId) & (db.t_comments.parent_id==None) ).select(orderby=db.t_comments.comment_datetime)
	if len(commentsQy) > 0:
		for comment in commentsQy:
			commentsTree.append(getCommentsTreeHtml(auth, db, response, comment.id, with_reviews))
	else:
		commentsTree.append(DIV(SPAN(current.T('No user comments yet')), _style="margin-top: 15px"))

 	snippetVars = dict(
	 	isLoggedIn = isLoggedIn,
		scrollToCommentForm = scrollToCommentForm,
		commentForm = commentForm,
		commentsTree = commentsTree
	)
	
	return XML(
		response.render(
			'snippets/comments_tree_and_form.html',
			snippetVars
		)
	)

######################################################################################################################################################################
def getCommentsTreeHtml(auth, db, response, commentId, with_reviews=False): 
	comment = db.t_comments[commentId]
	childrenDiv = []
	children = db(db.t_comments.parent_id==comment.id).select(orderby=db.t_comments.comment_datetime)

	for child in children:
		childrenDiv.append(getCommentsTreeHtml(auth, db, response, child.id, with_reviews))

	snippetVars = dict(
		userLink = common_small_html.mkUser_U(auth, db, comment.user_id, linked=True),
		commentDate = str(comment.comment_datetime),
		commentText = comment.user_comment or '',
		replyToLink = A(
				current.T('Reply...'), 
				_href=URL(c='articles', f='rec', vars=dict(articleId=comment.article_id, comments=True, reviews=with_reviews,replyTo=comment.id)),
				_style="margin: 0"
			) if auth.user else '',
		childrenDiv = childrenDiv
	)
	return XML(
			response.render(
				'snippets/comments_tree.html',
				snippetVars
			)
		)