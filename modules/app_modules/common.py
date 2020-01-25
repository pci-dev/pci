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

import common_html_snippets

myconf = AppConfig(reload=True)
######################################################################################################################################################################
# End New common modules

######################################################################################################################################################################
def takePort(p):
	#print 'port="%s"' % p
	if p is None:
		return False
	elif match('^[0-9]+$', p):
		return int(p)
	else:
		return False


######################################################################################################################################################################
statusArticles = dict()
def mkStatusArticles(db):
	statusArticles.clear()
	for sa in db(db.t_status_article).select():
		statusArticles[sa['status']] = sa



######################################################################################################################################################################
# Builds the right-panel for home page
def mkTopPanel(myconf, auth, inSearch=False):
	panel = []
	if auth.user:
		panel.append(A(current.T("Submit a preprint"), 
							_href=URL('user', 'new_submission', user_signature=True), 
							_class="btn btn-success pci-public"))
	else:
		panel.append(DIV(
						A(current.T("Submit a preprint"), 
							_href=URL('user', 'new_submission', user_signature=True), 
							_class="btn btn-success"),
						A(current.T('Log in'), _href=URL(c='default', f='user', args=['login']), _class="btn btn-info"),
						LABEL(current.T(' or ')),
						A(current.T('Register'), _href=URL(c='default', f='user', args=['register']), _class="btn btn-info"),
						#A(current.T('Lost password?'), _href=URL(c='default', f='user', args=['request_reset_password'], vars=dict(_next="/pcidev/default/index")), _class="pci-lostPassword"),
						
					))
	if auth.has_membership('recommender'):
		panel.append(A(current.T("Recommend a postprint"), 
							_href=URL('recommender', 'new_submission', user_signature=True), 
							_class="btn btn-info pci-recommender"))
		panel.append(A(current.T("Submitted preprints requiring a recommender"), 
							_href=URL('recommender', 'all_awaiting_articles', user_signature=True), 
							_class="btn btn-default pci-recommender"))
	return DIV(panel, _style='margin-top:20px; margin-bottom:20px; text-align:center;')



######################################################################################################################################################################
# Transforms a DOI in link
# After CrossRef syntax must be: https://doi.org/xxxx.xx/xxx.xx
def mkDOI(doi):
	if (doi is not None) and (doi != ''):
		if (match('^http', doi)):
			return A(doi, _href=doi, _class="doi_url", _target="_blank")
		else:
			return A(doi, _href="https://doi.org/"+sub(r'doi: *', '', doi), _class="doi_url", _target="_blank") 
	else:
		return SPAN('', _class="doi_url")

def mkSimpleDOI(doi):
	if (doi is not None) and (doi != ''):
		if (match('^http', doi)):
			return A(doi, _href=doi)
		else:
			return A(doi, _href="https://doi.org/"+sub(r'doi: *', '', doi)) 
	else:
		return ''

def mkLinkDOI(doi):
	if (doi is not None) and (doi != ''):
		if (match('^http', doi)):
			return doi
		else:
			return "https://doi.org/"+sub(r'doi: *', '', doi)
	else:
		return ''


######################################################################################################################################################################
def mkRecommArticleRow(auth, db, row, withImg=True, withScore=False, withDate=False, fullURL=False):
	if fullURL:
		scheme=myconf.take('alerts.scheme')
		host=myconf.take('alerts.host')
		port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	else:
		scheme=False
		host=False
		port=False
	resu = []
	# Recommender name(s)
	recomm = db( (db.t_recommendations.article_id==row.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=db.t_recommendations.id).last()
	if recomm is None: 
		return None
	
	whoDidIt = getRecommAndReviewAuthors(auth, db, row, with_reviewers=True, linked=True, host=host, port=port, scheme=scheme)
	
	img = []
	if withDate:
		img += [DIV(SPAN(mkLastChange(row.last_status_change), _class='pci-lastArticles-date'), _class='pci-lastArticles-date-div')]
	if withImg:
		if (row.uploaded_picture is not None and row.uploaded_picture != ''):
			img += [
				IMG(
					_alt='article picture', 
					_src=URL('default', 'download', scheme=scheme, host=host, port=port, args=row.uploaded_picture),
					_class='pci-articlePicture'
				)
			]
	#if row.already_published is False:
		#img += [DIV(SPAN(current.T('PREPRINT'), _class='pci-preprintTagText'), _class='pci-preprintTag')]
	resu.append(
			TD( img, 
				_class='pci-lastArticles-leftcell',
				_onclick="window.open('%s')" % URL(c='articles', f='rec', vars=dict(id=row.id, reviews=True), scheme=scheme, host=host, port=port),
			))

	shortTxt = recomm.recommendation_comments or ''
	if len(shortTxt)>500:
		shortTxt = shortTxt[0:500] + '...'
	
	if row.authors and len(row.authors)>500:
		authors = row.authors[:500]+'...'
	else:
		authors = row.authors or ''
	resu.append(
				TD(
					SPAN(row.title, _style='font-weight: bold; font-size:18px;'), BR(),
					SPAN(authors), BR(),
					mkDOI(row.doi), P(),
					DIV(
						I(SPAN('Recommended by '), SPAN(whoDidIt), BR(),
							SPAN((recomm.recommendation_title or 'Read...'), _target='blank', _style="font-size:16px;"),# color:green;"),
						),
						DIV(WIKI(shortTxt), _class='pci-shortTxt'),
						A(current.T('More'), _target='blank', 
							_href=URL(c='articles', f='rec', vars=dict(id=row.id, reviews=True), scheme=scheme, host=host, port=port),
							_class='btn btn-success pci-public pci-smallBtn',
						),
						_style='margin-right: 10px; margin-left: 0px; padding-left:10px; border-left:1px solid #cccccc;',
					),
					_class='pci-lastArticles-cell',
				),
			)
	
	if withScore:
			resu.append(TD(row.score or '', _class='pci-lastArticles-date'))
	return TR(resu, _class='pci-lastArticles-row')





######################################################################################################################################################################
# Builds a html representation of an article
def mkRepresentArticle(auth, db, articleId):
	resu = ''
	if articleId:
		art = db.t_articles[articleId]
		if art is not None:
			submitter = ''
			sub_repr = ''
			if art.user_id is not None and art.anonymous_submission is False:
				submitter = db(db.auth_user.id==art.user_id).select(db.auth_user.first_name, db.auth_user.last_name).last()
				sub_repr = 'by %s %s,' % (submitter.first_name, submitter.last_name)
			resu = DIV(
				SPAN(I(current.T('Submitted')+' %s %s' % (sub_repr, art.upload_timestamp.strftime('%Y-%m-%d %H:%M') if art.upload_timestamp else '')))
				,H4(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors))
				,H3(art.title)
				,BR()+SPAN(art.article_source) if art.article_source else ''
				,BR()+mkDOI(art.doi) if art.doi else ''
				,SPAN(' '+current.T('version')+' '+art.ms_version) if art.ms_version else ''
				,BR()
				,SPAN(I(current.T('Keywords:')+' '))+I(art.keywords or '') if art.keywords else ''
				,BR()+B(current.T('Abstract'))+BR()+DIV(WIKI(art.abstract or ''), _class='pci-bigtext') if art.abstract else ''
				, _class='pci-article-div'
			)
	return resu


######################################################################################################################################################################
# Builds a nice representation of an article WITH recommendations link
def mkArticleCell(auth, db, art):
	anchor = ''
	if art:
		# Recommender name(s)
		recomm = db( (db.t_recommendations.article_id==art.id) ).select(orderby=db.t_recommendations.id).last()
		if recomm is not None and recomm.recommender_id is not None:
			whowhen = [SPAN(current.T('See recommendation by '), mkUser(auth, db, recomm.recommender_id))]
			contrQy = db( (db.t_press_reviews.recommendation_id==recomm.id) ).select(orderby=db.t_press_reviews.id)
			if len(contrQy) > 0:
				whowhen.append(SPAN(current.T(' with ')))
			for ic in range(0, len(contrQy)):
				whowhen.append(mkUser(auth, db, contrQy[ic].contributor_id))
				if ic < len(contrQy)-1:
					whowhen.append(', ')
		else:
			whowhen = [SPAN(current.T('See recommendation'))]
		anchor = DIV(
					B(art.title),
					DIV(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
					mkDOI(art.doi),
					SPAN(' '+current.T('version')+' '+art.ms_version) if art.ms_version else '',
					(BR()+SPAN(art.article_source) if art.article_source else ''),
					A(whowhen, 
								_href=URL(c='articles', f='rec', vars=dict(id=art.id)),
								_target='blank',
								_style="color:green;margin-left:12px;",
						),
				)
	return anchor


######################################################################################################################################################################
# Builds a nice representation of an article WITHOUT recommendations link
def mkArticleCellNoRecomm(auth, db, art0):
	anchor = ''
	if art0:
		if ('t_articles' in art0):
			art = art0.t_articles
		else:
			art = art0
		anchor = DIV(
					B(art.title),
					DIV(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
					mkDOI(art.doi),
					SPAN(' '+current.T('version')+' '+art.ms_version) if art.ms_version else '',
					(BR()+SPAN(art.article_source) if art.article_source else ''),
				)
	return anchor



######################################################################################################################################################################
def mkRepresentArticleLight(auth, db, article_id):
	anchor = ''
	art = db.t_articles[article_id]
	if art:
		anchor = DIV(
					B(art.title),
					DIV(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
					mkDOI(art.doi),
					SPAN(' '+current.T('version')+' '+art.ms_version) if art.ms_version else '',
					(BR()+SPAN(art.article_source) if art.article_source else ''),
				)
	return anchor


######################################################################################################################################################################
def mkRepresentRecommendationLight(auth, db, recommId):
	anchor = ''
	recomm = db.t_recommendations[recommId]
	if recomm:
		art = db.t_articles[recomm.article_id]
		if art:
			#if art.already_published:
			recommenders = [mkUser(auth, db, recomm.recommender_id)]
			contribsQy = db( db.t_press_reviews.recommendation_id == recommId ).select()
			n = len(contribsQy)
			i = 0
			for contrib in contribsQy:
				i += 1
				if (i < n):
					recommenders += ', '
				else:
					recommenders += ' and '
				recommenders += mkUser(auth, db, contrib.contributor_id)
			recommenders = SPAN(recommenders)
			#else:
				#recommenders = mkUser(auth, db, recomm.recommender_id)
			anchor = DIV(
						B(recomm.recommendation_title), SPAN(current.T(' by ')), recommenders, mkDOI(recomm.recommendation_doi),
						P(),
						SPAN(current.T('A recommendation of ')), 
						I(art.title), SPAN(current.T(' by ')), SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)), 
						(SPAN(current.T(' in '))+SPAN(art.article_source) if art.article_source else ''),
						BR(), 
						mkDOI(art.doi),
						(SPAN(current.T(' version ') + art.ms_version) if art.ms_version else ''),
					)
	return anchor



######################################################################################################################################################################
def mkTFDict(tfArray):
	resu = dict()
	for tf in tfArray:
		resu['qy_'+tf] = 'on'
	return resu

######################################################################################################################################################################
# Builds a coloured status label
def mkStatusDiv(auth, db, status):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	status_txt = (current.T(status)).upper()
	color_class = statusArticles[status]['color_class'] or 'default'
	hint = statusArticles[status]['explaination'] or ''
	return DIV(status_txt, _class='pci-status '+color_class, _title=current.T(hint))

######################################################################################################################################################################
# Builds a coloured status label with pre-decision concealed
def mkStatusDivUser(auth, db, status):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	if status.startswith('Pre-'):
		status2 = 'Under consideration'
	else:
		status2 = status
	status_txt = (current.T(status2)).upper()
	color_class = statusArticles[status2]['color_class'] or 'default'
	hint = statusArticles[status2]['explaination'] or ''
	return DIV(status_txt, _class='pci-status '+color_class, _title=current.T(hint))

######################################################################################################################################################################
def mkStatusBigDiv(auth, db, status):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	status_txt = (current.T(status)).upper()
	color_class = statusArticles[status]['color_class'] or 'default'
	hint = statusArticles[status]['explaination'] or ''
	return DIV(status_txt, _class='pci-status-big '+color_class, _title=current.T(hint))

######################################################################################################################################################################
def mkStatusBigDivUser(auth, db, status):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	if status.startswith('Pre-'):
		status2 = 'Under consideration'
	else:
		status2 = status
	status_txt = (current.T(status2)).upper()
	color_class = statusArticles[status2]['color_class'] or 'default'
	hint = statusArticles[status2]['explaination'] or ''
	return DIV(status_txt, _class='pci-status-big '+color_class, _title=current.T(hint))

######################################################################################################################################################################
def mkReviewStateDiv(auth, db, state):
	#state_txt = (current.T(state)).upper()
	state_txt = (state or '').upper()
	if state == 'Pending': color_class = 'warning'
	elif state == 'Under consideration': color_class = 'info'
	elif state == 'Completed': color_class = 'success'
	else: color_class = 'default'
	return DIV(state_txt, _class='pci-status '+color_class)

######################################################################################################################################################################
def mkContributionStateDiv(auth, db, state):
	#state_txt = (current.T(state)).upper()
	state_txt = (state or '').upper()
	if state == 'Pending': color_class = 'warning'
	elif state == 'Under consideration': color_class = 'info'
	elif state == 'Recommendation agreed': color_class = 'success'
	else: color_class = 'default'
	return DIV(state_txt, _class='pci-status '+color_class)


######################################################################################################################################################################
def mkAnonymousMask(auth, db, anon):
	if anon is True:
		return DIV(IMG(_alt='anonymous', _src=URL(c='static',f='images/mask.png')), _style='text-align:center;')
	else:
		return ''


######################################################################################################################################################################
def mkAnonymousArticleField(auth, db, anon, value):
	if anon is True:
		return IMG(_alt='anonymous', _src=URL(c='static',f='images/mask.png'))
	else:
		return value


######################################################################################################################################################################
def mkJournalImg(auth, db, press):
	if press is True:
		return DIV(IMG(_alt='published', _src=URL(c='static',f='images/journal.png')), _style='text-align:center;')
	else:
		return ''


######################################################################################################################################################################
# code for a "Back" button
# go to the target instead, if any.
def mkBackButton(text=current.T('Back'), target=None):
	if target:
		return A(SPAN(text, _class='buttontext btn btn-default pci-public'), _href=target, _class='button')
	else:
		return A(SPAN(text, _class='buttontext btn btn-default pci-public'), _onclick='window.history.back();', _class='button')

######################################################################################################################################################################
# code for a "Close" button
def mkCloseButton():
	return A(SPAN(current.T('Close'), _class='pci-ArticleTopButton buttontext btn btn-default pci-public'), _onclick='window.close(); window.top.close();', _class='button')


######################################################################################################################################################################
# builds names list (recommender, co-recommenders, reviewers)
def getRecommAndReviewAuthors(auth, db, article, with_reviewers=False, linked=False, host=False, port=False, scheme=False):
	whoDidIt = []
	mainRecommenders = db(
			(db.t_recommendations.article_id==article.id) & (db.t_recommendations.recommender_id == db.auth_user.id) & (db.t_recommendations.recommendation_state == 'Recommended')
		).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
	coRecommenders = db(
			(db.t_recommendations.article_id==article.id) & (db.t_recommendations.recommendation_state == 'Recommended') & (db.t_press_reviews.recommendation_id==db.t_recommendations.id) & (db.auth_user.id==db.t_press_reviews.contributor_id)
		).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
	allRecommenders = mainRecommenders | coRecommenders
	if article.already_published: #NOTE: POST-PRINT
		nr = len(allRecommenders)
		ir=0
		for theUser in allRecommenders:
			ir += 1
			whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme))
			if ir == nr-1 and ir>=1:
				whoDidIt.append(current.T(' and '))
			elif ir < nr:
				whoDidIt.append(', ')
	else: #NOTE: PRE-PRINT
		if with_reviewers:
			namedReviewers = db(
							(db.t_recommendations.article_id==article.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) & 
							(db.auth_user.id==db.t_reviews.reviewer_id) & (db.t_reviews.anonymously==False) & (db.t_reviews.review_state=='Completed')
							).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
			na = db(
							(db.t_recommendations.article_id==article.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) & 
							(db.auth_user.id==db.t_reviews.reviewer_id) & (db.t_reviews.anonymously==True) & (db.t_reviews.review_state=='Completed')
							).count(distinct=db.auth_user.id)
			na1 = 1 if na>0 else 0
		else:
			namedReviewers = []
			na = 0
		nr = len(allRecommenders)
		nw = len(namedReviewers)
		ir = 0
		for theUser in allRecommenders:
			ir += 1
			whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme))
			if ir == nr-1 and ir >= 1:
				whoDidIt.append(current.T(' and '))
			elif ir < nr:
				whoDidIt.append(', ')
		if nr > 0: 
			if nw+na > 0:
				whoDidIt.append(current.T(' based on reviews by '))
			elif nw+na == 1:
				whoDidIt.append(current.T(' based on review by '))
		iw = 0
		for theUser in namedReviewers:
			iw += 1
			whoDidIt.append(mkUser_U(auth, db, theUser, linked=False, host=host, port=port, scheme=scheme))
			if iw == nw+na1-1 and iw >= 1:
				whoDidIt.append(current.T(' and '))
			elif iw < nw+na1:
				whoDidIt.append(', ')
		if na > 1:
			whoDidIt.append(current.T('%d anonymous reviewers') % (na))
		elif na == 1:
			whoDidIt.append(current.T('%d anonymous reviewer') % (na))
	
	return whoDidIt

######################################################################################################################################################################
def mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=False, as_list=False, as_items=False, linked=False, host=False, port=False, scheme=False):
	whoDidIt = []
	if recomm is None or (not hasattr(recomm, 'article_id')) or recomm.article_id is None:
		return whoDidIt
	else:
		article = db( db.t_articles.id==recomm.article_id ).select(db.t_articles.already_published).last()
		
		mainRecommenders = db(
							(db.t_recommendations.id==recomm.id) & (db.t_recommendations.recommender_id == db.auth_user.id)
						).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
		coRecommenders = db(
							(db.t_recommendations.id==recomm.id) & (db.t_press_reviews.recommendation_id==db.t_recommendations.id) & (db.auth_user.id==db.t_press_reviews.contributor_id)
							).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
		allRecommenders = mainRecommenders | coRecommenders

		if article.already_published: #NOTE: POST-PRINT
			nr = len(allRecommenders)
			ir=0
			for theUser in allRecommenders:
				ir += 1
				if as_items:
					whoDidIt.append(LI(mkUserWithAffil_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme)))
				elif as_list:
					whoDidIt.append('%s %s' % (theUser.first_name, theUser.last_name))
				else:
					whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme))
					if ir == nr-1 and ir>=1:
						whoDidIt.append(current.T(' and '))
					elif ir < nr:
						whoDidIt.append(', ')
		
		else: #NOTE: PRE-PRINT
			if with_reviewers:
				namedReviewers = db(
								(db.t_recommendations.article_id==recomm.article_id) 
								& (db.t_reviews.recommendation_id==db.t_recommendations.id) 
								& (db.auth_user.id==db.t_reviews.reviewer_id) 
								& (db.t_reviews.anonymously==False) 
								& (db.t_reviews.review_state=='Completed')
								).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
				na = db(
								(db.t_recommendations.article_id==recomm.article_id) 
								& (db.t_reviews.recommendation_id==db.t_recommendations.id) 
								& (db.t_reviews.anonymously==True) 
								& (db.t_reviews.review_state=='Completed')
								).count(distinct=db.t_reviews.reviewer_id)
				na1 = (1 if(na>0) else 0)
			else:
				namedReviewers = []
				na = 0
			nr = len(allRecommenders)
			nw = len(namedReviewers)
			ir = 0
			for theUser in allRecommenders:
				ir += 1
				if as_items:
					whoDidIt.append(LI(mkUserWithAffil_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme)))
				elif as_list:
					whoDidIt.append('%s %s' % (theUser.first_name, theUser.last_name))
				else:
					whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme))
					if ir == nr-1 and ir >= 1:
						whoDidIt.append(current.T(' and '))
					elif ir < nr:
						whoDidIt.append(', ')
			if nr > 0 and as_items is False: 
				if nw+na > 0:
					whoDidIt.append(current.T(' based on reviews by '))
				elif nw+na == 1:
					whoDidIt.append(current.T(' based on review by '))
			iw = 0
			for theUser in namedReviewers:
				iw += 1
				if as_list:
					whoDidIt.append('%s %s' % (theUser.first_name, theUser.last_name))
				else:
					whoDidIt.append(mkUser_U(auth, db, theUser, linked=False, host=host, port=port, scheme=scheme))
					if as_items is False:
						if iw == nw+na1-1 and iw >= 1:
							whoDidIt.append(current.T(' and '))
						elif iw < nw+na1:
							whoDidIt.append(', ')
		
			if not as_list:
				if na > 1:
					whoDidIt.append(current.T('%d anonymous reviewers') % (na))
				elif na == 1:
					whoDidIt.append(current.T('%d anonymous reviewer') % (na))
		
	return whoDidIt

# (gab) TOO BIG FUNCTION (need) 
######################################################################################################################################################################
def mkFeaturedRecommendation(auth, db, art, printable=False, with_reviews=False, with_comments=False, fullURL=True):
	if fullURL:
		scheme=myconf.take('alerts.scheme')
		host=myconf.take('alerts.host')
		port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	else:
		scheme=False
		host=False
		port=False
	
	myContents = DIV(_class=('pci-article-div-printable' if printable else 'pci-article-div'))
	## NOTE: article facts
	if (art.uploaded_picture is not None and art.uploaded_picture != ''):
		img = DIV(IMG(_alt='picture', _src=URL('default', 'download', args=art.uploaded_picture), _style='max-width:150px; max-height:150px;'), _style='text-align:center;')
	else:
		img = ''
	doi = sub(r'doi: *', '', (art.doi or ''))
	if printable:
		altmetric = XML("<div class='altmetric-embed' data-badge-type='donut' data-badge-details='right' data-hide-no-mentions='true' data-doi='%s'></div>" % doi)
	else:
		altmetric = XML("<div class='altmetric-embed' data-badge-type='donut' data-badge-details='right' data-hide-no-mentions='true' data-doi='%s'></div>" % doi)
	myArticle = DIV(
					SPAN((art.authors or '')+'. ', _class='pci-recomOfAuthors')
					,SPAN((art.title or '')+' ', _class='pci-recomOfTitle')
					,(SPAN((art.article_source+'. '), _class='pci-recomOfSource') if art.article_source else ' ')
					,(mkDOI(art.doi)) if (art.doi) else SPAN('')
					,SPAN(' '+current.T('version')+' '+art.ms_version) if art.ms_version else ''
					,DIV(altmetric, _style='margin-top:12px;')
					,_class='pci-recommOfArticle'
				)
	#myArticle = IFRAME( _src=mkLinkDOI(art.doi), _class='pci-recommOfArticle')
	
	recomGreen=DIV(
		DIV(
			DIV(I(current.T('Recommendation')), _class='pci-ArticleText'),
			_class='pci-ArticleHeader recommended'+ (' printable' if printable else '')
		))
	myContents.append(P())
	myContents.append(recomGreen)
	
	# Last recommendation
	lastRecomm = db( (db.t_recommendations.article_id==art.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=~db.t_recommendations.id).last()

	# PDF (if any)
	pdfQ = db(db.t_pdf.recommendation_id == lastRecomm.id).select(db.t_pdf.id, db.t_pdf.pdf)
	if len(pdfQ) > 0:
		pdfLink = URL('articles', 'rec', vars=dict(articleId=art.id, asPDF=True), host=host, scheme=scheme, port=port)
		pdf = A(SPAN(current.T('PDF recommendation'), ' ', IMG(_alt='pdf', _src=URL('static', 'images/application-pdf.png'))), _href=pdfLink, _class='btn btn-info pci-public')
	else:
		pdfLink = None
		pdf = None

	# METADATA
	desc = 'A recommendation of: '+(art.authors or '')+' '+(art.title or '')+' '+(art.doi or '')
	whoDidItMeta = mkWhoDidIt4Recomm(auth, db, lastRecomm, with_reviewers=False, linked=False, as_list=True, as_items=False)
	citeNum = ''
	citeRef = None
	recomm_altmetric = ''
	if lastRecomm.recommendation_doi:
		citeNumSearch = re.search('([0-9]+$)', lastRecomm.recommendation_doi, re.IGNORECASE)
		if citeNumSearch:
			citeNum = citeNumSearch.group(1)
		citeRef = mkDOI(lastRecomm.recommendation_doi)
		if printable:
			recomm_altmetric = XML("<div class='altmetric-embed' data-badge-type='donut' data-badge-details='right' data-hide-no-mentions='true' data-doi='%s'></div>" % sub(r'doi: *', '', lastRecomm.recommendation_doi))
		else:
			recomm_altmetric = XML("<div class='altmetric-embed' data-badge-type='donut' data-badge-details='right' data-hide-no-mentions='true' data-doi='%s'></div>" % sub(r'doi: *', '', lastRecomm.recommendation_doi))
	if citeRef:
		citeUrl = citeRef
	else:
		citeUrl = URL(c='articles', f='rec', vars=dict(id=art.id), host=host, scheme=scheme, port=port)
		citeRef = A(citeUrl, _href=citeUrl) # + SPAN(' accessed ', datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))

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
	
	
	whoDidItCite = mkWhoDidIt4Recomm(auth, db, lastRecomm, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)
	cite = DIV(
				SPAN(B('Cite this recommendation as:'), 
				BR(), SPAN(whoDidItCite), ' ', lastRecomm.last_change.strftime('(%Y)'), ' ', lastRecomm.recommendation_title, '. ', I(myconf.take('app.description')+', '+(citeNum or '')+'. '), 
				citeRef, 
			), _class='pci-citation')

	
	
	## NOTE: recommendations counting
	if with_reviews:
		recomms = db( (db.t_recommendations.article_id==art.id) ).select(orderby=~db.t_recommendations.id)
	else:
		recomms = db( (db.t_recommendations.article_id==art.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=~db.t_recommendations.id)

	recommRound = len(recomms)
	leftShift=0
	headerDone = False
	
	for recomm in recomms:
		
		whoDidIt = mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=True, linked=not(printable), as_items=False, host=host, port=port, scheme=scheme)
			
		## NOTE: POST-PRINT ARTICLE
		if art.already_published and not(headerDone):
			myContents.append(
				DIV(recomm_altmetric
					,H2(recomm.recommendation_title if ((recomm.recommendation_title or '') != '') else current.T('Recommendation'))
					,H4(SPAN(whoDidIt))
					#,I(recomm.last_change.strftime('%Y-%m-%d'))+BR() if recomm.last_change else ''
					,SPAN('A recommendation of:', _class='pci-recommOf')
					,DIV(myArticle, _class='pci-recommOfDiv')
					,DIV( 
							I(recomm.last_change.strftime('Recommended: %d %B %Y')) if recomm.last_change else ''
					)
					,cite
					,HR()
					,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext')
					, _class='pci-recommendation-div'
				)
			)
			headerDone = True
		## NOTE: PRE-PRINT ARTICLE
		else: 
			myReviews = ''
			myReviews = []
			# Check for reviews
			reviews = db( (db.t_reviews.recommendation_id==recomm.id) & (db.t_reviews.review_state=='Completed') ).select(orderby=db.t_reviews.id)
			for review in reviews:
				if with_reviews:
					# display the review
					if review.anonymously:
						myReviews.append(
							H4(current.T('Reviewed by')+' '+current.T('anonymous reviewer')+(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else ''))
						)
					else:
						myReviews.append(
							H4(current.T('Reviewed by'),' ',mkUser(auth, db, review.reviewer_id, linked=not(printable)),(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else ''))
						)
					myReviews.append(BR())
					if len(review.review or '')>2:
						myReviews.append(DIV(WIKI(review.review), _class='pci-bigtext margin'))
						if review.review_pdf:
							myReviews.append(DIV(A(current.T('Download the review (PDF file)'), _href=URL('default', 'download', args=review.review_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'))
					elif review.review_pdf:
						myReviews.append(DIV(A(current.T('Download the review (PDF file)'), _href=URL('default', 'download', args=review.review_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'))
					else:
						pass
						
			if recomm.reply:
				if recomm.reply_pdf:
					reply = DIV(
							H4(B(current.T('Author\'s reply:'))),
							DIV(WIKI(recomm.reply), _class='pci-bigtext'),
							DIV(A(current.T('Download author\'s reply (PDF file)'), _href=URL('default', 'download', args=recomm.reply_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'),
							_style='margin-top:32px;',
						)
				else:
					reply = DIV(
							H4(B(current.T('Author\'s reply:'))),
							DIV(WIKI(recomm.reply), _class='pci-bigtext'),
							_style='margin-top:32px;',
						)
			elif recomm.reply_pdf:
				reply = DIV(
						H4(B(current.T('Author\'s reply:'))),
						DIV(A(current.T('Download author\'s reply (PDF file)'), _href=URL('default', 'download', args=recomm.reply_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'),
						_style='margin-top:32px;',
					)
			else:
				reply = ''
			if not(headerDone):
				myContents.append( DIV(recomm_altmetric
						,H2(recomm.recommendation_title if ((recomm.recommendation_title or '') != '') else T('Recommendation'))
						,H4(SPAN(whoDidIt)) #mkUserWithAffil(auth, db, recomm.recommender_id, linked=not(printable)))
						,SPAN('A recommendation of:', _class='pci-recommOf')
						,DIV(
							#SPAN('References', _class='pci-recommOf'), BR(), 
							myArticle, _class='pci-recommOfDiv')
						,DIV( 
							  I(art.upload_timestamp.strftime('Submitted: %d %B %Y')) if art.upload_timestamp else ''
							 ,', '
							 ,I(recomm.last_change.strftime('Recommended: %d %B %Y')) if recomm.last_change else ''
						)
						,cite
						,HR()
						,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext')
						,DIV(myReviews, _class='pci-reviews') if len(myReviews) > 0 else ''
						,reply
						, _class='pci-recommendation-div'
						, _style='margin-left:%spx' % (leftShift)
						)
					)
				headerDone = True
			else:
				myContents.append( DIV( HR()
						#H2(recomm.recommendation_title if ((recomm.recommendation_title or '') != '') else T('Recommendation'))
						#,H4(current.T(' by '), UL(whoDidIt)) #mkUserWithAffil(auth, db, recomm.recommender_id, linked=not(printable)))
						,H3('Revision round #%s' % recommRound)
						,SPAN(I(recomm.last_change.strftime('%Y-%m-%d')+' ')) if recomm.last_change else ''
						#,SPAN(SPAN(current.T('Recommendation:')+' '), mkDOI(recomm.recommendation_doi), BR()) if ((recomm.recommendation_doi or '')!='') else ''
						#,DIV(SPAN('A recommendation of:', _class='pci-recommOf'), myArticle, _class='pci-recommOfDiv')
						,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext')
						,DIV(I(current.T('Preprint DOI:')+' '), mkDOI(recomm.doi), BR()) if ((recomm.doi or '')!='') else ''
						,DIV(myReviews, _class='pci-reviews') if len(myReviews) > 0 else ''
						,reply
						, _class='pci-recommendation-div'
						, _style='margin-left:%spx' % (leftShift)
						)
					)
				headerDone = True
			leftShift += 16
		recommRound -= 1
	
	if with_comments:
		# comments
		commentsQy = db( (db.t_comments.article_id == art.id) & (db.t_comments.parent_id==None) ).select(orderby=db.t_comments.comment_datetime)
		if len(commentsQy) > 0:
			myContents.append(H2(current.T('User comments')))
			for comment in commentsQy:
				myContents.append(mkCommentsTree(auth, db, comment.id))
		else:
			myContents.append(SPAN(current.T('No user comments yet')))
		
		# add comment button
		if auth.user and not(printable):
			myContents.append(DIV(A(SPAN(current.T('Write a comment'), _class='buttontext btn btn-default pci-public'), 
									_href=URL(c='user', f='new_comment', vars=dict(articleId=art.id), user_signature=True)), 
								_class='pci-EditButtons'))
	
	nbRecomms = db( (db.t_recommendations.article_id==art.id) ).count()
	nbReviews = db( (db.t_recommendations.article_id==art.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) ).count()
	return dict(myContents=myContents, pdf=pdf, nbReviews=(nbReviews+(nbRecomms-1)), myMeta=myMeta)



######################################################################################################################################################################
def mkCommentsTree(auth, db, commentId):
	comment = db.t_comments[commentId]
	childrenDiv = []
	children = db(db.t_comments.parent_id==comment.id).select(orderby=db.t_comments.comment_datetime)
	for child in children:
		childrenDiv.append(mkCommentsTree(auth, db, child.id))
	return DIV(
		SPAN(current.T('Comment by')+' ', mkUser(auth, db,comment.user_id), ', '+str(comment.comment_datetime), _class='pci-commentHeader'),
		DIV(WIKI(comment.user_comment or ''), _class='pci-bigtext'),
		A(current.T('Reply...'), _href=URL(c='user', f='new_comment', vars=dict(articleId=comment.article_id, parentId=comment.id)), _class='pci-commentReplyLink') if auth.user else '',
		DIV(childrenDiv) if len(childrenDiv)>0 else '',
		_class='pci-comment',
	)


######################################################################################################################################################################
##WARNING The most sensitive function of the whole website!!
##WARNING Be *VERY* careful with rights management
def mkFeaturedArticle(auth, db, art, printable=False, with_comments=False, quiet=True, scheme=False, host=False, port=False):
	class FakeSubmitter(object):
		id = None
		first_name = ''
		last_name = '[undisclosed]'
	submitter = FakeSubmitter()
	hideSubmitter = True
	qyIsRecommender = db( (db.t_recommendations.article_id==art.id) & (db.t_recommendations.recommender_id==auth.user_id) ).count()
	qyIsCoRecommender = db( (db.t_recommendations.article_id==art.id) & (db.t_press_reviews.recommendation_id==db.t_recommendations.id) & (db.t_press_reviews.contributor_id==auth.user_id) ).count()
	if ( (art.anonymous_submission is False) or (qyIsRecommender > 0) or (qyIsCoRecommender > 0) or (auth.has_membership(role='manager')) ):
		submitter = db(db.auth_user.id==art.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
		if submitter is None:
			submitter = FakeSubmitter()
		hideSubmitter = False
	allowOpinion = None
	###NOTE: article facts
	if (art.uploaded_picture is not None and art.uploaded_picture != ''):
		img = DIV(IMG(_alt='article picture', _src=URL('default', 'download', args=art.uploaded_picture, scheme=scheme, host=host, port=port), _style='max-width:150px; max-height:150px;'))
	else:
		img = ''
	myArticle = DIV(
		DIV(XML("<div class='altmetric-embed' data-badge-type='donut' data-doi='%s'></div>" % sub(r'doi: *', '', (art.doi or ''))), _style='text-align:right;')
		# NOTE: publishing tools not ready yet...
		#,DIV(
			 #A(current.T('Publishing tools'), _href=URL(c='admin', f='rec_as_latex', vars=dict(articleId=art.id)), _class='btn btn-info')
			#,A(current.T('PDF Front page'), _href=URL(c='admin', f='fp_as_pdf', vars=dict(articleId=art.id)), _class='btn btn-info')
			#,A(current.T('PDF Recommendation'), _href=URL(c='admin', f='rec_as_pdf', vars=dict(articleId=art.id)), _class='btn btn-info')
			#,A(current.T('Complete PDF Recommendation'), _href=URL(c='admin', f='rec_as_pdf', vars=dict(articleId=art.id, withHistory=1)), _class='btn btn-info')
			#,_style='text-align:right; margin-top:12px; margin-bottom:8px;'
		#) if ((auth.has_membership(role='administrator') or auth.has_membership(role='developper'))) else ''
		,img
		,H3(art.title or '')
		,H4(mkAnonymousArticleField(auth, db, hideSubmitter, (art.authors or '')))
		,mkDOI(art.doi) if (art.doi) else SPAN('')
		,SPAN(' '+current.T('version')+' '+art.ms_version) if art.ms_version else ''
		,BR()
		,DIV(
				I(current.T('Submitted by ')),
				I(mkAnonymousArticleField(auth, db, hideSubmitter, (submitter.first_name or '')+' '+(submitter.last_name or ''))),
				I(art.upload_timestamp.strftime(' %Y-%m-%d %H:%M') if art.upload_timestamp else '')
		) if (art.already_published is False) else ''
		,(B('Parallel submission') if art.parallel_submission else '')
		,(SPAN(art.article_source)+BR() if art.article_source else '')
	)
	# Allow to display cover letter if role is manager or above
	if not(printable) and not(quiet) :
		if len(art.cover_letter or '')>2:
			myArticle.append(DIV(A(current.T('Show / Hide Cover letter'), 
							_onclick="""jQuery(function(){ if ($.cookie('PCiHideCoverLetter') == 'On') {
													$('DIV.pci-onoffCoverLetter').show(); 
													$.cookie('PCiHideCoverLetter', 'Off', {expires:365, path:'/'});
												} else {
													$('DIV.pci-onoffCoverLetter').hide(); 
													$.cookie('PCiHideCoverLetter', 'On', {expires:365, path:'/'});
												}
										})""", _class='btn btn-default'), _class='pci-EditButtons'))
			myArticle.append(SCRIPT("$.cookie('PCiHideCoverLetter', 'On', {expires:365, path:'/'});"))
			myArticle.append(DIV(B(current.T('Cover letter')), 
								BR(), 
								WIKI((art.cover_letter or '')), 
					_class='pci-bigtext pci-onoffCoverLetter'))
		else:
			myArticle.append(DIV(A(current.T('No Cover letter'), _class='btn btn-default disabled'), _class='pci-EditButtons'))
	if not(printable) and not (quiet):
		myArticle.append(DIV(A(current.T('Show / Hide Abstract'), 
						_onclick="""jQuery(function(){ if ($.cookie('PCiHideAbstract') == 'On') {
												$('DIV.pci-onoffAbstract').show(); 
												$.cookie('PCiHideAbstract', 'Off', {expires:365, path:'/'});
											} else {
												$('DIV.pci-onoffAbstract').hide(); 
												$.cookie('PCiHideAbstract', 'On', {expires:365, path:'/'});
											}
									})""", _class='btn btn-default pci-public'), _class='pci-EditButtons'))
		myArticle.append(SCRIPT("$.cookie('PCiHideAbstract', 'On', {expires:365, path:'/'});"))
		myArticle.append(DIV(B(current.T('Abstract')), 
							BR(), 
							WIKI((art.abstract or '')), 
							SPAN(I(current.T('Keywords:')+' '+art.keywords)+BR() if art.keywords else ''),
				_class='pci-bigtext pci-onoffAbstract'))
	else:
		myArticle.append(
			DIV(B(current.T('Abstract')), 
							BR(), 
							WIKI((art.abstract or '')), 
							SPAN(I(current.T('Keywords:')+' '+art.keywords)+BR() if art.keywords else ''),
				_class='pci-bigtext')
			)
	if ((art.user_id == auth.user_id) and (art.status in ('Pending', 'Awaiting revision'))) and not(printable) and not (quiet):
		# author's button allowing article edition
		myArticle.append(DIV(A(SPAN(current.T('Edit article'), _class='buttontext btn btn-info pci-submitter'), 
								_href=URL(c='user', f='edit_my_article', vars=dict(articleId=art.id), user_signature=True)), 
							_class='pci-EditButtons'))
	if auth.has_membership(role='manager') and not(art.user_id==auth.user_id) and not(printable) and not (quiet):
		# manager's button allowing article edition
		myArticle.append(DIV(A(SPAN(current.T('Manage this request'), _class='buttontext btn btn-info pci-manager'), 
								_href=URL(c='manager', f='edit_article', vars=dict(articleId=art.id), user_signature=True)), 
							_class='pci-EditButtons'))
	myContents = DIV(myArticle, _class=('pci-article-div-printable' if printable else 'pci-article-div'))
	
	###NOTE: recommendations counting
	recomms = db(db.t_recommendations.article_id == art.id).select(orderby=~db.t_recommendations.id)
	nbRecomms = len(recomms)
	myButtons = DIV()
	if nbRecomms > 0 and auth.has_membership(role='manager') and not(art.user_id==auth.user_id) and not(printable) and not (quiet):
		# manager's button allowing recommendations management
		myButtons.append(DIV(A(SPAN(current.T('Manage recommendations'), _class='buttontext btn btn-info pci-manager'), _href=URL(c='manager', f='manage_recommendations', vars=dict(articleId=art.id), user_signature=True)), _class='pci-EditButtons'))
	if len(recomms)==0 and auth.has_membership(role='recommender') and not(art.user_id==auth.user_id) and art.status=='Awaiting consideration' and not(printable) and not(quiet):
		# suggested or any recommender's button for recommendation consideration
		btsAccDec = [A(SPAN(current.T('Click here before starting the evaluation process'), _class='buttontext btn btn-success pci-recommender'), 
								_href=URL(c='recommender', f='accept_new_article_to_recommend', vars=dict(articleId=art.id), user_signature=True),
								_class='button'),]
		amISugg = db( (db.t_suggested_recommenders.article_id==art.id) & (db.t_suggested_recommenders.suggested_recommender_id==auth.user_id) ).count()
		if amISugg > 0:
			# suggested recommender's button for declining recommendation
			btsAccDec.append(A(SPAN(current.T('No, thanks, I decline this suggestion'), _class='buttontext btn btn-warning pci-recommender'), 
								_href=URL(c='recommender_actions', f='decline_new_article_to_recommend', vars=dict(articleId=art.id), user_signature=True),
								_class='button'),
							)
		myButtons.append( DIV(btsAccDec, _class='pci-opinionform') )
	
	if (art.user_id==auth.user_id) and not(art.already_published) and (art.status not in ('Cancelled', 'Rejected', 'Pre-recommended', 'Recommended')) and not(printable) and not (quiet):
		myButtons.append(DIV(A(SPAN(current.T('I wish to cancel my submission'), _class='buttontext btn btn-warning pci-submitter'), 
										_href=URL(c='user_actions', f='do_cancel_article', vars=dict(articleId=art.id), user_signature=True), 
										_title=current.T('Click here in order to cancel this submission')), 
								_class='pci-EditButtons')) # author's button allowing cancellation
	myContents.append(myButtons)
	
	###NOTE: here start recommendations display
	iRecomm = 0
	roundNb = nbRecomms+1
	reply_filled = False
	myRound = None
	for recomm in recomms:
		iRecomm += 1
		roundNb -= 1
		nbCompleted = 0
		nbOnGoing = 0
		myRound = DIV()
		recommender = db(db.auth_user.id==recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
		whoDidIt = mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=False, linked=not(printable), host=host, port=port, scheme=scheme)
		
		###NOTE: POST-PRINT ARTICLE
		if art.already_published:
			contributors = []
			contrQy = db( (db.t_press_reviews.recommendation_id==recomm.id) ).select(orderby=db.t_press_reviews.id)
			for contr in contrQy:
				contributors.append(contr.contributor_id)
			
			myRound.append(
				DIV( HR()
					,B(SPAN(recomm.recommendation_title))+BR() if (recomm.recommendation_title or '') != '' else ''
					,B(current.T('Recommendation by '), SPAN(whoDidIt))+BR()
					,SPAN(current.T('Recommendation:')+' '), mkDOI(recomm.recommendation_doi), BR()
					,SPAN(current.T('Manuscript:')+' ', mkDOI(recomm.doi)+BR()) if (recomm.doi != art.doi) else SPAN('')
					,I(recomm.last_change.strftime('%Y-%m-%d')) if recomm.last_change else ''
					,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext margin')
					, _class='pci-recommendation-div'
				)
			)
			if (recomm.recommender_id == auth.user_id) and (art.status == 'Under consideration') and not(recomm.is_closed) and not(printable) and not (quiet):
				# recommender's button allowing recommendation edition
				myRound.append(DIV(A(SPAN(current.T('Write or edit your decision / recommendation'), _class='buttontext btn btn-default pci-recommender'), 
											_href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recomm.id), user_signature=True)), 
										_class='pci-EditButtons'))
				# recommender's button allowing recommendation submission, provided there are co-recommenders
				if len(contributors) >= minimal_number_of_corecommenders:
					if len(recomm.recommendation_comments)>50:
						myRound.append(DIV(
									A(SPAN(current.T('Send your recommendation to the managing board for validation'), _class='buttontext btn btn-success pci-recommender'), 
										_href=URL(c='recommender_actions', f='recommend_article', vars=dict(recommId=recomm.id), user_signature=True), 
										#_title=current.T('Click here to close the recommendation process of this article and send it to the managing board')
									),
								_class='pci-EditButtons-centered'))
					else:
						myRound.append(DIV(SPAN(I(current.T('Recommendation text too short for allowing submission'), _class='buttontext btn btn-success pci-recommender disabled')), _class='pci-EditButtons-centered'))
				else:
					# otherwise button for adding co-recommender(s)
					myRound.append(DIV(
									A(SPAN(current.T('You have to add at least one contributor in order to collectively validate this recommendation'), _class='buttontext btn btn-info pci-recommender'), 
										_href=URL(c='recommender', f='add_contributor', vars=dict(recommId=recomm.id), user_signature=True), 
										_title=current.T('Click here to add contributors of this article')),
								_class='pci-EditButtons-centered'))
				
				# recommender's button allowing cancellation
				myContents.append(DIV(A(SPAN(current.T('Cancel this postprint recommendation'), _class='buttontext btn btn-warning pci-recommender'), 
												_href=URL(c='recommender_actions', f='do_cancel_press_review', vars=dict(recommId=recomm.id), user_signature=True), 
												_title=current.T('Click here in order to cancel this recommendation')), 
										_class='pci-EditButtons-centered'))
				

		
		
		else: ###NOTE: PRE-PRINT ARTICLE
			# Am I a co-recommender?
			amICoRecommender = (db((db.t_press_reviews.recommendation_id==recomm.id) & (db.t_press_reviews.contributor_id==auth.user_id)).count() > 0)
			# Am I a reviewer?
			amIReviewer = (db((db.t_recommendations.article_id==art.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) & (db.t_reviews.reviewer_id==auth.user_id)).count() > 0)
			# During recommendation, no one is not allowed to see last (unclosed) recommendation 
			hideOngoingRecomm = ((art.status=='Under consideration') or (art.status.startswith('Pre-'))) and not(recomm.is_closed) #(iRecomm==1)
			#  ... unless he/she is THE recommender
			if auth.has_membership(role='recommender') and (recomm.recommender_id==auth.user_id or amICoRecommender):
				hideOngoingRecomm = False
			# or a manager, provided he/she is reviewer
			if auth.has_membership(role='manager') and (art.user_id != auth.user_id) and (amIReviewer is False):
				hideOngoingRecomm = False
			
			if (((recomm.reply is not None) and (len(recomm.reply) > 0)) or recomm.reply_pdf is not None):
				myRound.append(HR())
				myRound.append(DIV(B(current.T('Author\'s Reply:'))))
			if ((recomm.reply is not None) and (len(recomm.reply) > 0)):
				myRound.append(DIV(WIKI(recomm.reply or ''), _class='pci-bigtext margin'))
			if recomm.reply_pdf:
				myRound.append(A(current.T('Download author\'s reply (PDF file)'), _href=URL('default', 'download', args=recomm.reply_pdf, scheme=scheme, host=host, port=port), _style='margin-bottom: 64px;'))
				if recomm.track_change:
					myRound.append(BR()) # newline if both links for visibility
			if recomm.track_change:
				myRound.append(A(current.T('Download tracked changes file'), _href=URL('default', 'download', args=recomm.track_change, scheme=scheme, host=host, port=port), _style='margin-bottom: 64px;'))
			if (recomm.reply_pdf or len(recomm.reply or '')>5):
				reply_filled = True
			
			# Check for reviews
			existOngoingReview = False
			myReviews = DIV()
			reviews = db( (db.t_reviews.recommendation_id==recomm.id) & (db.t_reviews.review_state != 'Declined') & (db.t_reviews.review_state != 'Cancelled') ).select(orderby=db.t_reviews.id)
			for review in reviews:
				if review.review_state == 'Under consideration': 
					existOngoingReview = True
				if (review.review_state == 'Completed'): nbCompleted += 1
				if (review.review_state == 'Under consideration'): nbOnGoing += 1
			# If the recommender is also a reviewer, did he/she already completed his/her review?
			recommReviewFilledOrNull = False # Let's say no by default
			# Get reviews states for this case
			recommenderOwnReviewStates = db( (db.t_reviews.recommendation_id==recomm.id) & (db.t_reviews.reviewer_id==recomm.recommender_id) ).select(db.t_reviews.review_state)
			if (len(recommenderOwnReviewStates) == 0): 
				# The recommender is not also a reviewer
				recommReviewFilledOrNull = True # He/she is allowed to see other's reviews
			else:
				# The recommender is also a reviewer
				for recommenderOwnReviewState in recommenderOwnReviewStates:
					if (recommenderOwnReviewState.review_state == 'Completed'):
						recommReviewFilledOrNull = True # Yes, his/her review is completed
			
			for review in reviews:
				# No one is allowd to see ongoing reviews ...
				hideOngoingReview = True
				# ... but:
				# ... the author for a closed decision/recommendation ...
				if (art.user_id == auth.user_id) and (recomm.is_closed or art.status=='Awaiting revision'): 
					hideOngoingReview = False
				# ...  the reviewer himself once accepted ...
				if (review.reviewer_id == auth.user_id) and (review.review_state in ('Under consideration', 'Completed')): 
					hideOngoingReview = False
				# ...  a reviewer himself once the decision made up ...
				if (amIReviewer) and (recomm.recommendation_state in ('Recommended', 'Rejected', 'Revision')) and recomm.is_closed and (art.status in ('Under consideration', 'Recommended', 'Rejected', 'Awaiting revision')): 
					hideOngoingReview = False
				# ... or he/she is THE recommender and he/she already filled his/her own review ...
				if auth.has_membership(role='recommender') and (recomm.recommender_id==auth.user_id) and recommReviewFilledOrNull: 
					hideOngoingReview = False
				# ... or he/she is A CO-recommender and he/she already filled his/her own review ...
				if auth.has_membership(role='recommender') and amICoRecommender and recommReviewFilledOrNull: 
					hideOngoingReview = False
				# ... or a manager, unless submitter or reviewer
				if auth.has_membership(role='manager') and not(art.user_id==auth.user_id) and not amIReviewer: 
					hideOngoingReview = False
				#print "hideOngoingReview=%s" % (hideOngoingReview)
				
				if (review.reviewer_id == auth.user_id) and (review.reviewer_id != recomm.recommender_id) and (art.status=='Under consideration') and not(printable) and not(quiet):
					if (review.review_state=='Pending'):
						# reviewer's buttons in order to accept/decline pending review
						myReviews.append(DIV(
										A(SPAN(current.T('Yes, I agree to review this preprint'), _class='buttontext btn btn-success pci-reviewer'), 
											_href=URL(c='user', f='accept_new_review',  vars=dict(reviewId=review.id), user_signature=True), _class='button'),
										A(SPAN(current.T('No thanks, I\'d rather not'), _class='buttontext btn btn-warning pci-reviewer'), 
											_href=URL(c='user_actions', f='decline_new_review', vars=dict(reviewId=review.id), user_signature=True), _class='button'),
										_class='pci-opinionform'
									))
				elif (review.review_state=='Pending'):
					hideOngoingReview = True
				
				if (review.reviewer_id==auth.user_id) and (review.review_state == 'Under consideration') and (art.status == 'Under consideration') and not(printable) and not(quiet):
					# reviewer's buttons in order to edit/complete pending review
					myReviews.append(DIV(A(SPAN(current.T('Write, edit or upload your review'), _class='buttontext btn btn-default pci-reviewer'), _href=URL(c='user', f='edit_review', vars=dict(reviewId=review.id), user_signature=True)), _class='pci-EditButtons'))
				
				if not(hideOngoingReview):
					# display the review
					#myReviews.append(HR())
					# buttons allowing to edit and validate the review
					if review.anonymously:
						myReviews.append(
							SPAN(I(current.T('Reviewed by')+' '+current.T('anonymous reviewer')+(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else '')))
						)
					else:
						reviewer = db(db.auth_user.id==review.reviewer_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
						if reviewer is not None:
							myReviews.append(
								SPAN(I(current.T('Reviewed by')+' '+(reviewer.first_name or '')+' '+(reviewer.last_name or '')+(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else '')))
							)
					myReviews.append(BR())
					if len(review.review or '')>2:
						myReviews.append(DIV(WIKI(review.review), _class='pci-bigtext margin'))
						if review.review_pdf:
							myReviews.append(DIV(A(current.T('Download the review (PDF file)'), _href=URL('default', 'download', args=review.review_pdf, scheme=scheme, host=host, port=port), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'))
					elif review.review_pdf:
						myReviews.append(DIV(A(current.T('Download the review (PDF file)'), _href=URL('default', 'download', args=review.review_pdf, scheme=scheme, host=host, port=port), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'))
			
			myRound.append(HR())
			if recomm.recommendation_state == 'Recommended':
				if recomm.recommender_id == auth.user_id:
					tit2 = current.T('Your recommendation')
				else:
					tit2 = current.T('Recommendation')
			else:
				if recomm.recommender_id == auth.user_id:
					tit2 = current.T('Your decision')
				elif recomm.is_closed:
					tit2 = current.T('Decision')
				else:
					tit2 = ''
			
			if not(recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == 'Under consideration') and not(printable) and not (quiet):
				# recommender's button for recommendation edition
				#myRound.append(DIV(A(SPAN(current.T('Write or edit your decision / recommendation'), _class='buttontext btn btn-default pci-recommender'), _href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recomm.id), user_signature=True)), _class='pci-EditButtons'))
				if ( (nbCompleted >= 2 and nbOnGoing == 0) or roundNb > 1 ):
					myRound.append(DIV(A(SPAN(current.T('Write or edit your decision / recommendation'), _class='btn btn-default pci-recommender'), 
											_href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recomm.id)))))
				else:
					myRound.append(DIV(A(SPAN(current.T('Write your decision / recommendation'), 
								_title=current.T('Write your decision or recommendation once all reviews are completed. At least two reviews are required.'),
								_style='white-space:normal;', _class='btn btn-default pci-recommender disabled'), _style='width:300px;')))
				

				# final opinion allowed if comments filled and no ongoing review
				if (len(recomm.recommendation_comments or '')>5) and not(existOngoingReview):# and len(reviews)>=2 :
					allowOpinion = recomm.id
				else:
					allowOpinion = -1
				
			#if (art.user_id==auth.user_id or auth.has_membership(role='manager')) and (art.status=='Awaiting revision') and not(recomm.is_closed) and not(printable) and not (quiet):
			if (art.user_id==auth.user_id) and (art.status=='Awaiting revision') and not(printable) and not (quiet) and (iRecomm==1):
				myRound.append(DIV(A(SPAN(current.T('Write, edit or upload your reply to the recommender'), 
											_class='buttontext btn btn-info pci-submitter'), 
											_href=URL(c='user', f='edit_reply', vars=dict(recommId=recomm.id), user_signature=True)),
										_class='pci-EditButtons'))
			
			truc = DIV( H3(tit2)
				#,SPAN(I(current.T('by ')+' '+(recommender.first_name if recommender else None or '')+' '+(recommender.last_name if recommender else None or '')+(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
				,I(SPAN(current.T('by ')), SPAN(whoDidIt), SPAN(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else ''))
				,BR()
				,SPAN(current.T('Manuscript:')+' ', mkDOI(recomm.doi)) if (recomm.doi) else SPAN('')
				,SPAN(' '+current.T('version')+' ', recomm.ms_version) if (recomm.ms_version) else SPAN('')
				,BR()
				,H4(recomm.recommendation_title or '') if (hideOngoingRecomm is False) else ''
				,BR()
				,(DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext margin') if (hideOngoingRecomm is False) else '')
				,_class='pci-recommendation-div'
			)
			if (hideOngoingRecomm is False and recomm.recommender_file) :
				truc.append(A(current.T('Download recommender\'s annotations (PDF)'), _href=URL('default', 'download', args=recomm.recommender_file, scheme=scheme, host=host, port=port), _style='margin-bottom: 64px;'))
			
			if not(recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == 'Under consideration'):
				truc.append(DIV(A(SPAN(current.T('Invite a reviewer'), _class='btn btn-default pci-recommender'), _href=URL(c='recommender', f='reviewers', vars=dict(recommId=recomm.id)))))
			truc.append(H3(current.T('Reviews'))+DIV(myReviews, _class='pci-bigtext margin') if len(myReviews) > 0 else '')
			myRound.append(truc)
			
		myContents.append( H2(current.T('Round #%s') % (roundNb)) )
		if myRound and (recomm.is_closed or art.status == 'Awaiting revision' or art.user_id != auth.user_id):
			myContents.append(myRound)
	
	if auth.has_membership(role='manager') and not(art.user_id==auth.user_id) and not(printable) and not (quiet):
		if art.status == 'Pending':
			myContents.append(DIV(	A(SPAN(current.T('Validate this submission'), _class='buttontext btn btn-success pci-manager'), 
											_href=URL(c='manager_actions', f='do_validate_article', vars=dict(articleId=art.id), user_signature=True), 
											_title=current.T('Click here to validate this request and start recommendation process')),
									_class='pci-EditButtons-centered'))
		elif art.status == 'Pre-recommended':
			myContents.append(DIV(	A(SPAN(current.T('Validate this recommendation'), _class='buttontext btn btn-info pci-manager'), 
										_href=URL(c='manager_actions', f='do_recommend_article', vars=dict(articleId=art.id), user_signature=True), 
										_title=current.T('Click here to validate recommendation of this article')),
								_class='pci-EditButtons-centered'))
		elif art.status == 'Pre-revision':
			myContents.append(DIV(	A(SPAN(current.T('Validate this decision'), _class='buttontext btn btn-info pci-manager'), 
										_href=URL(c='manager_actions', f='do_revise_article', vars=dict(articleId=art.id), user_signature=True), 
										_title=current.T('Click here to validate revision of this article')),
								_class='pci-EditButtons-centered'))
		elif art.status == 'Pre-rejected':
			myContents.append(DIV(	A(SPAN(current.T('Validate this rejection'), _class='buttontext btn btn-info pci-manager'), 
										_href=URL(c='manager_actions', f='do_reject_article', vars=dict(articleId=art.id), user_signature=True), 
										_title=current.T('Click here to validate the rejection of this article')),
								_class='pci-EditButtons-centered'))
	return myContents


######################################################################################################################################################################
def mkLastRecommendation(auth, db, articleId):
	lastRecomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
	if lastRecomm:
		return DIV(lastRecomm.recommendation_title or '', _class='pci-w200Cell')
	else:
		return ''

######################################################################################################################################################################
def mkSuggestUserArticleToButton(auth, db, row, articleId, excludeList, vars):
	vars['recommenderId'] = row['id']
	anchor = A(SPAN(current.T('Suggest as recommender'), _class='buttontext btn btn-default pci-submitter')
									, _href=URL(c='user_actions', f='suggest_article_to'
										#, vars=dict(articleId=articleId, recommenderId=row['id'], exclude=excludeList)
										, vars=vars
										, user_signature=True)
										, _class='button')
	return anchor


######################################################################################################################################################################
def mkSuggestReviewToButton(auth, db, row, recommId, myGoal):
	if myGoal == '4review':
		anchor = A(SPAN(current.T('Add'), _class='buttontext btn btn-default pci-recommender'), 
				_href=URL(c='recommender_actions', f='suggest_review_to', vars=dict(recommId=recommId, reviewerId=row['id']), user_signature=True),
				_class='button')
	elif myGoal == '4press':
		anchor = A(SPAN(current.T('Suggest'), _class='buttontext btn btn-default pci-recommender'), 
				_href=URL(c='recommender_actions', f='suggest_collaboration_to', vars=dict(recommId=recommId, reviewerId=row['id']), user_signature=True),
				_class='button')
	else:
		anchor = ''
	return anchor


######################################################################################################################################################################
def mkSuggestedRecommendersButton(auth, db, row):
	if row.status == 'Pending' or row.status == 'Awaiting consideration':
		return A(XML((db.v_suggested_recommenders[row.id]).suggested_recommenders.replace(', ', '<br>')), _href=URL(c='manager', f='suggested_recommenders', vars=dict(articleId=row.id)))
	else:
		return SPAN((db.v_article_recommender[row.id]).recommender)





######################################################################################################################################################################
def mkSollicitedRev(auth, db, row):
	butts = []
	hrevs = []
	#exclude = [str(auth.user_id)]
	exclude = []
	art = db.t_articles[row.article_id]
	revs = db(db.t_reviews.recommendation_id == row.id).select()
	for rev in revs:
		if rev.reviewer_id:
			hrevs.append(LI(mkUserWithMail(auth, db, rev.reviewer_id)))
			exclude.append(str(rev.reviewer_id))
		else:
			hrevs.append(LI(I(current.T('not registered'))))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	if art.status == 'Under consideration' and not(row.is_closed):
		myVars = dict(recommId=row['id'])
		if len(exclude)>0:
			myVars['exclude'] = ','.join(exclude)
			butts.append( A('['+current.T('MANAGE')+'] ', _href=URL(c='recommender', f='reviews', vars=myVars, user_signature=True)) )
		for thema in art['thematics']:
			myVars['qy_'+thema] = 'on'
		butts.append( A('['+current.T('Invite a reviewer')+'] ', _href=URL(c='recommender', f='reviewers', vars=myVars, user_signature=True)) )
	return butts

######################################################################################################################################################################
def mkDeclinedRev(auth, db, row):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db( (db.t_reviews.recommendation_id == row.id) & (db.t_reviews.review_state == "Declined") ).select()
	for rev in revs:
		if rev.reviewer_id:
			hrevs.append(LI(mkUserWithMail(auth, db, rev.reviewer_id)))
		else:
			hrevs.append(LI(I(current.T('not registered'))))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	return butts

######################################################################################################################################################################
def mkOngoingRev(auth, db, row):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db( (db.t_reviews.recommendation_id == row.id) & (db.t_reviews.review_state == "Under consideration") ).select()
	for rev in revs:
		if rev.reviewer_id:
			hrevs.append(LI(mkUserWithMail(auth, db, rev.reviewer_id)))
		else:
			hrevs.append(LI(I(current.T('not registered'))))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	return butts

######################################################################################################################################################################
def mkClosedRev(auth, db, row):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db( (db.t_reviews.recommendation_id == row.id) & (db.t_reviews.review_state == "Completed") ).select()
	for rev in revs:
		if rev.reviewer_id:
			hrevs.append(LI(mkUserWithMail(auth, db, rev.reviewer_id)))
		else:
			hrevs.append(LI(I(current.T('not registered'))))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	return butts




######################################################################################################################################################################
def mkOtherContributors(auth, db, row):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db(db.t_press_reviews.recommendation_id == row.id).select()
	for rev in revs:
		if rev.contributor_id:
			if rev.contributor_id != auth.user_id:
				hrevs.append(LI(mkUserWithMail(auth, db, rev.contributor_id)))
		else:
			hrevs.append(LI(I(current.T('not registered'))))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	return butts



######################################################################################################################################################################
def mkCoRecommenders(auth, db, row, goBack=URL()):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db(db.t_press_reviews.recommendation_id == row.id).select()
	for rev in revs:
		if rev.contributor_id:
			hrevs.append(LI(mkUserWithMail(auth, db, rev.contributor_id)))
		else:
			hrevs.append(LI(I(current.T('not registered'))))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	if len(hrevs)>0:
		txt = current.T('ADD / DELETE')
	else:
		txt = current.T('ADD')
	if art.status == 'Under consideration':
		myVars = dict(recommId=row['id'], goBack=goBack)
		butts.append( A(txt, _class='btn btn-default pci-smallBtn pci-recommender', _href=URL(c='recommender', f='add_contributor', vars=myVars, user_signature=True)) )
	return DIV(butts, _class='pci-w200Cell')


######################################################################################################################################################################
def mkRecommendationFormat2(auth, db, row):
	recommender = db(db.auth_user.id==row.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
	if recommender:
		recommFmt = SPAN('%s %s' % (recommender.first_name, recommender.last_name))
	else:
		recommFmt = ''
	art = db.t_articles[row.article_id]
	artRep = mkRepresentArticleLight(auth, db, art.id)
	anchor = DIV(
		artRep,BR(),
		row.recommendation_title,BR(),
		B(current.T('Recommender:')+' '), recommFmt,BR(),
		mkDOI(row.doi),
		_class='pci-RecommendationFormat2'
	)
	return anchor

######################################################################################################################################################################
def mkRecommendationFormat(auth, db, row):
	recommender = db(db.auth_user.id==row.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
	if recommender:
		recommFmt = SPAN('%s %s' % (recommender.first_name, recommender.last_name))
	else:
		recommFmt = ''
	art = db.t_articles[row.article_id]
	anchor = SPAN(  row.recommendation_title,
					BR(),
					B(current.T('Recommender:')+' '), recommFmt,
					BR(),
					mkDOI(row.doi),
				)
	return anchor



######################################################################################################################################################################
def mkRecommendation4ReviewFormat(auth, db, row):
	recomm = db(db.t_recommendations.id==row.recommendation_id).select(db.t_recommendations.id, db.t_recommendations.recommender_id).last()
	anchor = SPAN(mkUserWithMail(auth, db, recomm.recommender_id))
	return anchor


######################################################################################################################################################################
def mkRecommendation4PressReviewFormat(auth, db, row):
	recomm = db.t_recommendations[row.recommendation_id]
	anchor = DIV(  SPAN(mkUserWithMail(auth, db, recomm.recommender_id)),
					BR(),
					mkDOI(recomm.doi),
					BR(),
					I(current.T('Started %s days ago') % relativedelta(datetime.datetime.now(), recomm.recommendation_timestamp).days),
					BR(),
					WIKI(recomm.recommendation_comments or ''),
				)
	return anchor


######################################################################################################################################################################
def mkUser(auth, db, userId, linked=False, scheme=False, host=False, port=False):
	if userId is not None:
		theUser = db(db.auth_user.id==userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
		return mkUser_U(auth, db, theUser, linked=linked, scheme=scheme, host=host, port=port)
	else:
		return SPAN('')

######################################################################################################################################################################
def mkUserId(auth, db, userId, linked=False, scheme=False, host=False, port=False):
	resu = SPAN('')
	if userId is not None:
		if linked:
			resu = A(str(userId), _href=URL(c='user', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=userId)))
		else:
			resu = SPAN(str(userId))
	return resu

######################################################################################################################################################################
def mkUser_U(auth, db, theUser, linked=False, scheme=False, host=False, port=False):
	if theUser:
		if linked:
			resu = A('%s %s' % (theUser.first_name, theUser.last_name), _href=URL(c='user', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=theUser.id)))
		else:
			resu = SPAN('%s %s' % (theUser.first_name, theUser.last_name))
	else:
		resu = SPAN('?')
	return resu


######################################################################################################################################################################
def mkUserWithAffil_U(auth, db, theUser, linked=False, scheme=False, host=False, port=False):
	if theUser:
		if linked:
			resu = SPAN(A('%s %s' % (theUser.first_name, theUser.last_name), _href=URL(c='user', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=theUser.id))), I(' -- %s, %s -- %s, %s' % (theUser.laboratory, theUser.institution, theUser.city, theUser.country)))
		else:
			resu = SPAN(SPAN('%s %s' % (theUser.first_name, theUser.last_name)), I(' -- %s, %s -- %s, %s' % (theUser.laboratory, theUser.institution, theUser.city, theUser.country)))
	else:
		resu = SPAN('?')
	return resu

######################################################################################################################################################################
def mkUserWithAffil(auth, db, userId, linked=False, scheme=False, host=False, port=False):
	resu = SPAN('')
	if userId is not None:
		theUser = db(db.auth_user.id==userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.laboratory, db.auth_user.institution, db.auth_user.city, db.auth_user.country, db.auth_user.email).last()
		mkUserWithAffil_U(auth, db, theUser, linked=linked, scheme=scheme, host=host, port=port)
	return resu


######################################################################################################################################################################
def mkUserWithMail(auth, db, userId, linked=False, scheme=False, host=False, port=False):
	resu = SPAN('')
	if userId is not None:
		theUser = db(db.auth_user.id==userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
		if theUser:
			if linked:
				resu = SPAN(A('%s %s' % (theUser.first_name, theUser.last_name), _href=URL(c='user', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=userId))), A(' [%s]' % theUser.email, _href='mailto:%s' % theUser.email))
			else:
				resu = SPAN(SPAN('%s %s' % (theUser.first_name, theUser.last_name)), A(' [%s]' % theUser.email, _href='mailto:%s' % theUser.email))
		else:
			resu = SPAN('?')
	return resu



######################################################################################################################################################################
def mkLastChange(t):
	if t:
		d = datetime.datetime.now() - t
		if d.days==0:
			return SPAN(current.T('Today'))
		elif d.days==1:
			return SPAN(current.T('Yesterday'))
		else:
			tdt = t.strftime('%Y-%m-%d ')
			return SPAN(tdt)
	else:
		return ''


######################################################################################################################################################################
def mkElapsedDays(t):
	if t:
		tdt = SPAN(t.strftime('%Y-%m-%d'), _style="font-size:7pt;")
		d = datetime.datetime.now() - t
		if d.days==0:
			#return SPAN(current.T('Today'), BR(), tdt)
			return SPAN(current.T('Today'))
		elif d.days==1:
			#return SPAN(current.T('Yesterday'), BR(), tdt)
			return SPAN(current.T('Yesterday'))
		else:
			#return SPAN(current.T('%s days ago') % (d.days), BR(), tdt)
			return SPAN(current.T('%s days ago') % (d.days))
	else:
		return ''


######################################################################################################################################################################
def mkElapsed(t):
	if t:
		d = datetime.datetime.now() - t
		if d.days<2:
			return SPAN(current.T('%s day') % d.days)
		else:
			return SPAN(current.T('%s days') % d.days)
	else:
		return ''


######################################################################################################################################################################
def mkDuration(t0, t1):
	if t0 and t1:
		d = t1 - t0
		if d.days<2:
			return SPAN(current.T('%s day') % d.days)
		else:
			return SPAN(current.T('%s days') % d.days)
	else:
		return ''




######################################################################################################################################################################
def mkUserRow(auth, db, userRow, withPicture=False, withMail=False, withRoles=False):
	resu = []
	if withPicture:
		if (userRow.uploaded_picture is not None and userRow.uploaded_picture != ''):
			img = IMG(_alt='avatar', _src=URL('default', 'download', args=userRow.uploaded_picture), _class='pci-userPicture', _style='float:left;')
		else:
			img = IMG(_alt='avatar', _src=URL(c='static',f='images/default_user.png'), _class='pci-userPicture', _style='float:left;')
		resu.append(TD(img))
	name = ''
	if (userRow.first_name or '') != '':
		name += userRow.first_name
	if (userRow.last_name or '') != '':
		if name != '': name += ' '
		name += userRow.last_name.upper()
	resu.append(TD(A(name, _target='blank', _href=URL(c='user', f='viewUserCard', vars=dict(userId=userRow.id)))))
	affil = ''
	if (userRow.laboratory or '') != '':
		affil += userRow.laboratory
	if (userRow.institution or '') != '':
		if affil != '': affil += ', '
		affil += userRow.institution
	if (userRow.city or '') != '':
		if affil != '': affil += ', '
		affil += userRow.city
	if (userRow.country or '') != '':
		if affil != '': affil += ', '
		affil += userRow.country
	resu.append(TD(I(affil)))
	if withMail:
		resu.append(TD(A(' [%s]' % userRow.email, _href='mailto:%s' % userRow.email) if withMail else TD('')))
	if withRoles:
		rolesQy = db( (db.auth_membership.user_id==userRow.id) & (db.auth_membership.group_id==db.auth_group.id) ).select(db.auth_group.role, orderby=db.auth_group.role)
		rolesList = []
		for roleRow in rolesQy:
			rolesList.append(roleRow.role)
		roles = ', '.join(rolesList)
		resu.append(TD(B(roles)))
	return TR(resu, _class='pci-UsersTable-row')




######################################################################################################################################################################
def mkUserCard(auth, db, response, userId, withMail=False):
	user  = db.auth_user[userId]
	if user:
		name  = LI(B( (user.last_name or '').upper(), ' ', (user.first_name or '') ))
		nameTitle  = (user.last_name or '').upper(), ' ', (user.first_name or '')
		addr  = LI(I( (user.laboratory or ''), ', ', (user.institution or ''), ', ', (user.city or ''), ', ', (user.country or '') ))
		thema = LI(', '.join(user.thematics))
		mail  = LI(A(' [%s]' % user.email, _href='mailto:%s' % user.email) if withMail else '')
		if (user.uploaded_picture is not None and user.uploaded_picture != ''):
			img = IMG(_alt='avatar', _src=URL('default', 'download', args=user.uploaded_picture), _class='pci-userPicture', _style='float:left;')
		else:
			img = IMG(_alt='avatar', _src=URL(c='static',f='images/default_user.png'), _class='pci-userPicture', _style='float:left;')
		if (user.cv or '') != '':
			cv = DIV(WIKI(user.cv or ''), _class='pci-bigtext margin', _style='border: 1px solid #f0f0f0;')
		else:
			cv = ''
		rolesQy = db( (db.auth_membership.user_id==userId) & (db.auth_membership.group_id==db.auth_group.id) ).select(db.auth_group.role)
		rolesList = []
		for roleRow in rolesQy:
			rolesList.append(roleRow.role)
		roles = LI(B(', '.join(rolesList)))
		# recommendations ## Patch SP 2020-01-06
		recommsQy0sql = """
			SELECT t_articles.id
			FROM t_articles
			JOIN t_recommendations ON (
				t_recommendations.article_id = t_articles.id
				AND t_recommendations.recommendation_state = 'Recommended'
				AND t_recommendations.id IN (
					SELECT DISTINCT recommendation_id FROM t_press_reviews WHERE t_press_reviews.contributor_id = %(userId)s
					UNION
					SELECT id FROM t_recommendations WHERE recommender_id = %(userId)s
				)
			)
			WHERE t_articles.status = 'Recommended'
			ORDER BY t_articles.last_status_change DESC
		""" % locals()
		recommsQy0 = []
		for t in db.executesql(recommsQy0sql):
			recommsQy0.append(t[0])
		#recommsQy = db( 
					#(
						#(db.t_recommendations.recommender_id == userId) | ( (db.t_recommendations.id == db.t_press_reviews.recommendation_id) & (db.t_press_reviews.contributor_id == userId) )
					#)
					#& (db.t_recommendations.recommendation_state == 'Recommended')
					#& (db.t_recommendations.article_id == db.t_articles.id)
					#& (db.t_articles.status == 'Recommended')
				#).select(db.t_articles.ALL, distinct=True, orderby=~db.t_articles.last_status_change)
		recommsQy = db(db.t_articles.id.belongs(recommsQy0) ).select(db.t_articles.ALL, distinct=True, orderby=~db.t_articles.last_status_change)
		nbRecomms = len(recommsQy)
		recomms = []
		for row in recommsQy:
			recomms.append(
				common_html_snippets.getRecommArticleRowCard(auth, db, response, row, withImg=True, withScore=False, withDate=True, fullURL=False)
			)
		# reviews
		reviews = []
		reviewsQy = db(
					(db.t_reviews.reviewer_id == userId)
					& ~(db.t_reviews.anonymously == True)
					& (db.t_reviews.review_state == 'Completed')
					& (db.t_reviews.recommendation_id == db.t_recommendations.id)
					#& (db.t_recommendations.recommendation_state == 'Recommended')
					& (db.t_recommendations.article_id == db.t_articles.id)
					& (db.t_articles.status == 'Recommended')
				).select(db.t_articles.ALL, distinct=True, orderby=~db.t_articles.last_status_change)
		nbReviews = len(reviewsQy)
		for row in reviewsQy:
			reviews.append(
				common_html_snippets.getRecommArticleRowCard(auth, db, response, row, withImg=True, withScore=False, withDate=True, fullURL=False)
			)
			
		resu = DIV(
				H2(nameTitle),
				DIV(
					img,
					DIV(
						UL(addr, mail, thema, roles) if withMail else UL(addr, thema, roles), 
						_style='margin-left:120px; margin-bottom:24px; min-height:120px;'),
				),
				cv,
				DIV(
					H2(current.T('%s %%{recommendation}', symbols=nbRecomms)),
					DIV(
						recomms, 
						_class='pci2-articles-list'
					),
					H2(current.T('%s %%{review}', symbols=nbReviews)),
					DIV(
						reviews, 
						_class='pci2-articles-list'
					),
				),
					_class='pci2-flex-column pci2-flex-center'
				
			)
	else:
		resu = B(current.T('Unavailable'))
	return resu



######################################################################################################################################################################
def do_suggest_article_to(auth, db, articleId, recommenderId):
	db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)




######################################################################################################################################################################
def makeUserThumbnail(auth, db, userId, size=(150,150)):
	user = db(db.auth_user.id==userId).select().last()
	if user.picture_data:
		try:
			im = Image.open(io.BytesIO(user.picture_data))
			width, height = im.size
			if width>200 or height>200:
				im.thumbnail(size,Image.ANTIALIAS)
				imgByteArr = io.BytesIO()
				im.save(imgByteArr, format='PNG')
				imgByteArr = imgByteArr.getvalue() 
				user.update_record(picture_data=imgByteArr)
		except:
			pass
	return



######################################################################################################################################################################
def makeArticleThumbnail(auth, db, articleId, size=(150,150)):
	art = db(db.t_articles.id==articleId).select().last()
	if art and art.picture_data:
		try:
			im = Image.open(io.BytesIO(art.picture_data))
			width, height = im.size
			if width>200 or height>200:
				im.thumbnail(size,Image.ANTIALIAS)
				imgByteArr = io.BytesIO()
				im.save(imgByteArr, format='PNG')
				imgByteArr = imgByteArr.getvalue() 
				art.update_record(picture_data=imgByteArr)
		except:
			pass
	return


######################################################################################################################################################################
def makeResourceThumbnail(auth, db, resourceId, size=(150,150)):
	rec = db(db.t_resources.id==resourceId).select().last()
	if rec and rec.resource_logo_data:
		try:
			im = Image.open(io.BytesIO(rec.resource_logo_data))
			width, height = im.size
			if width>200 or height>200:
				im.thumbnail(size,Image.ANTIALIAS)
				imgByteArr = io.BytesIO()
				im.save(imgByteArr, format='PNG')
				imgByteArr = imgByteArr.getvalue() 
				rec.update_record(resource_logo_data=imgByteArr)
		except:
			pass
	return


######################################################################################################################################################################
def getRecommender(auth, db, row):
	recomm = db( db.t_recommendations.article_id == row["t_articles.id"] ).select(db.t_recommendations.id, db.t_recommendations.recommender_id, orderby=db.t_recommendations.id).last()
	if recomm and recomm.recommender_id:
		#return mkUser(auth, db, recomm.recommender_id)
		resu = SPAN(mkUser(auth, db, recomm.recommender_id))
		corecommenders = db(db.t_press_reviews.recommendation_id==recomm.id).select(db.t_press_reviews.contributor_id)
		if len(corecommenders) > 0:
			resu.append(BR())
			resu.append(B(current.T('Co-recommenders:')))
			resu.append(BR())
			for corecommender in corecommenders:
				resu.append(SPAN(mkUser(auth, db, corecommender.contributor_id))+BR())
		return(DIV(resu, _class='pci-w200Cell'))
	else:
		return ''


######################################################################################################################################################################
def mkReviewsSubTable(auth, db, recomm):
	art = db.t_articles[recomm.article_id]
	recomm_round = db( (db.t_recommendations.article_id == recomm.article_id) & (db.t_recommendations.id <= recomm.id) ).count()
	reviews = db(db.t_reviews.recommendation_id == recomm.id).select(
					  db.t_reviews.reviewer_id
					, db.t_reviews.review_state
					, db.t_reviews.acceptation_timestamp
					, db.t_reviews.last_change
					, db.t_reviews._id
					, orderby=~db.t_reviews.last_change)
	nbUnfinishedReviews = db( (db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state.belongs('Pending', 'Under consideration')) ).count()
	isRecommenderAlsoReviewer = db( (db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.reviewer_id == recomm.recommender_id) ).count()
	allowed_to_see_reviews = True
	if (nbUnfinishedReviews > 0) and (isRecommenderAlsoReviewer == 1):
		allowed_to_see_reviews = False
	if len(reviews) > 0:
		resu = TABLE(TR(TH('Reviewer'), TH('Status'), 
						TH('Last change'), TH(''), TH('Actions')), _class='table')
	else:
		resu = TABLE()
	nbCompleted = 0
	nbOnGoing = 0
	for myRev in reviews:
		myRow = TR(
				TD(mkUserWithMail(auth, db, myRev.reviewer_id)),
				TD(mkReviewStateDiv(auth, db, myRev.review_state)),
				TD(mkElapsedDays(myRev.last_change)),
			)
		myRow.append(TD(A(current.T('See emails'), _class='btn btn-default pci-smallBtn pci-recommender', _target="blank", _href=URL(c='recommender', f='review_emails', vars=dict(reviewId=myRev.id)))))
		lastCol = TD()
		if (allowed_to_see_reviews and myRev.review_state == 'Completed') :
			lastCol.append(SPAN(A(current.T('See review'), _class='btn btn-default', _target="blank", _href=URL(c='recommender', f='one_review', vars=dict(reviewId=myRev.id)))))
		if (art.status == 'Under consideration' and not(recomm.is_closed)):
			if ((myRev.reviewer_id == auth.user_id) and (myRev.review_state == 'Under consideration')) :
				lastCol.append(SPAN(A(current.T('Write, edit or upload your review'), _class='btn btn-default pci-reviewer', _href=URL(c='user', f='edit_review', vars=dict(reviewId=myRev.id)))))
			if ((myRev.reviewer_id != auth.user_id) and ((myRev.review_state or 'Pending') in ('Pending', 'Under consideration'))) :
				if myRev.review_state == 'Under consideration':
					btn_txt = current.T('Send an overdue message')
				else:
					btn_txt = current.T('Send a reminder')
				lastCol.append(SPAN(A(btn_txt, _class='btn btn-info pci-recommender', _href=URL(c='recommender', f='send_review_reminder', vars=dict(reviewId=myRev.id)))))
			if ((myRev.reviewer_id != auth.user_id) and ((myRev.review_state or 'Pending') == 'Pending')) :
				lastCol.append(SPAN(A(current.T('Send a cancellation notification'), _class='btn btn-warning pci-recommender', _href=URL(c='recommender', f='send_review_cancellation', vars=dict(reviewId=myRev.id)))))
		myRow.append(lastCol)
		resu.append(myRow)
		if (myRev.review_state == 'Completed'): nbCompleted += 1
		if (myRev.review_state == 'Under consideration'): nbOnGoing += 1
	myVars = dict(recommId=recomm['id'])
	if not(recomm.is_closed) and ((recomm.recommender_id == auth.user_id) or auth.has_membership(role='manager') or auth.has_membership(role='administrator')) and (art.status == 'Under consideration'):
		buts = TR()
		buts.append(TD(A(SPAN(current.T('Invite a reviewer'), _class='btn btn-default pci-recommender'), _href=URL(c='recommender', f='reviewers', vars=myVars))))
		buts.append(TD())
		buts.append(TD())
		buts.append(TD())
		if ( (nbCompleted >= 2 and nbOnGoing == 0) or recomm_round > 1 ):
			buts.append(TD(A(SPAN(current.T('Write or edit your decision / recommendation'), _class='btn btn-success pci-recommender'), 
									_href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recomm.id)))))
		else:
			buts.append(TD(A(SPAN(current.T('Write your decision / recommendation'), # once two or more reviews are completed'), 
						 _title=current.T('Write your decision or recommendation once all reviews are completed. At least two reviews are required.'),
						 _style='white-space:normal;', _class='btn btn-default pci-recommender disabled'), _style='width:300px;')))
		resu.append(buts)
	return DIV(H3('Round #%s'%recomm_round), resu, _class="pci-reviewers-table-div")


######################################################################################################################################################################
def mkRecommArticleRss(auth, db, row):
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	recomm = db( (db.t_recommendations.article_id==row.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=db.t_recommendations.id).last()
	if recomm is None: 
		return None
	if (row.uploaded_picture is not None and row.uploaded_picture != ''):
		img = IMG(_alt='article picture', _src=URL('default', 'download', scheme=scheme, host=host, port=port, args=row.uploaded_picture), _style='padding:8px;')
	else: img = None
	link = URL(c='articles', f='rec', vars=dict(id=row.id), scheme=scheme, host=host, port=port)
	whoDidIt = getRecommAndReviewAuthors(auth, db, row, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)
	desc = DIV()
	article = DIV(CENTER( I(row.title), BR(), SPAN(row.authors), BR(), mkDOI(row.doi) ), _style='border:2px solid #cccccc; margin-bottom:8px; font-size:larger;')
	desc.append(article)
	if img: 
			desc.append(CENTER(img)) 
	desc.append(BR())

	what = SPAN()
	#if (row.already_published):
		#what.append(B(u'Article '))
	#else:
		#what.append(B(u'Preprint '))
	what.append(CAT(SPAN(u'Recommended by '), SPAN(whoDidIt)))
	what.append(' ')
	what.append(A(current.T('view'), _href=link))
	desc.append(what)
	
	desc.append(DIV(WIKI(recomm.recommendation_comments or u''), _style='font-size:smaller;'))
	desc.append(HR())
	
	xdesc = desc.xml()
	title = recomm.recommendation_title or u'(no title)'
	
	local = pytz.timezone ("Europe/Paris")
	local_dt = local.localize(row.last_status_change, is_dst=None)
	created_on = local_dt.astimezone (pytz.utc)
	
	return dict(
		guid = link,
		title = title.decode('utf-8'),
		link = link,
		description = xdesc.decode('utf-8'),
		created_on = created_on,
	 )


def mkReviewersString(auth, db, articleId):
	reviewers = []
	reviewsQy = db( (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == articleId) & (db.t_reviews.anonymously == False) & (db.t_reviews.review_state=='Completed') ).select(db.t_reviews.reviewer_id, distinct=True)
	if reviewsQy is not None:
		nR = len(reviewsQy)
		i = 0
		for rw in reviewsQy:
			if rw.reviewer_id:
				i += 1
				if (i > 1):
					if (i < nR):
						reviewers += ', '
					else:
						reviewers += ' and '
				reviewers += mkUser(auth, db, rw.reviewer_id).flatten()
	reviewsQyAnon = db( (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == articleId) & (db.t_reviews.anonymously == True) & (db.t_reviews.review_state=='Completed') ).select(db.t_reviews.reviewer_id, distinct=True)
	if reviewsQyAnon is not None:
		nRA = len(reviewsQyAnon)
		if nRA > 0:
			if len(reviewers) > 0:
				reviewers += ' and '
			if nRA > 1:
				reviewers += '%s anonymous reviewers' % nRA
			else:
				reviewers += 'one anonymous reviewer'
	reviewersStr = ''.join(reviewers)
	return(reviewersStr)

def mkRecommendersList(auth, db, recomm):
	recommenders = [mkUser(auth, db, recomm.recommender_id).flatten()]
	contribsQy = db( db.t_press_reviews.recommendation_id == recomm.id ).select()
	for contrib in contribsQy:
		recommenders.append(mkUser(auth, db, contrib.contributor_id).flatten())
	return(recommenders)

def mkRecommendersString(auth, db, recomm):
	recommenders = [mkUser(auth, db, recomm.recommender_id).flatten()]
	contribsQy = db( db.t_press_reviews.recommendation_id == recomm.id ).select()
	n = len(contribsQy)
	i = 0
	for contrib in contribsQy:
		i += 1
		if (i < n):
			recommenders += ', '
		else:
			recommenders += ' and '
		recommenders += mkUser(auth, db, contrib.contributor_id).flatten()
	recommendersStr = ''.join(recommenders)
	return(recommendersStr)

def mkRecommendersAffiliations(auth, db, recomm):
	affiliations = []
	theUser = db.auth_user[recomm.recommender_id]
	if theUser:
		affiliations.append(('%s, %s -- %s, %s' % (theUser.laboratory, theUser.institution, theUser.city, theUser.country)))
	contribsQy = db( db.t_press_reviews.recommendation_id == recomm.id ).select()
	for contrib in contribsQy:
		theUser = db.auth_user[contrib.contributor_id]
		if theUser:
			affiliations.append(('%s, %s -- %s, %s' % (theUser.laboratory, theUser.institution, theUser.city, theUser.country)))
	return(affiliations)

	recommendersStr = mkRecommendersString(auth, db,recomm)
	#reviewers = []
	reviewsQy = db( (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == articleId) & (db.t_reviews.anonymously == False) & (db.t_reviews.review_state=='Completed') ).select(db.t_reviews.reviewer_id, distinct=True)
	#if reviewsQy is not None:
		#nR = len(reviewsQy)
		#i = 0
		#for rw in reviewsQy:
			#if rw.reviewer_id:
				#i += 1
				#if (i > 1):
					#if (i < nR):
						#reviewers += ', '
					#else:
						#reviewers += ' and '
				#reviewers += mkUser(auth, db, rw.reviewer_id).flatten()
	reviewsQyAnon = db( (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == articleId) & (db.t_reviews.anonymously == True) & (db.t_reviews.review_state=='Completed') ).select(db.t_reviews.reviewer_id, distinct=True)
	#if reviewsQyAnon is not None:
		#nRA = len(reviewsQyAnon)
		#if nRA > 0:
			#if len(reviewers) > 0:
				#reviewers += ' and '
			#if nRA > 1:
				#reviewers += '%s anonymous reviewers' % nRA
			#else:
				#reviewers += 'one anonymous reviewer'
	#reviewersStr = ''.join(reviewers)
	return(reviewersStr)

######################################################################################################################################################################
def mkRecommArticleRss4bioRxiv(auth, db, row):
	## Template:
	#<link providerId="PCI">
	#<resource>
		#<title>Version 3 of this preprint has been peer-reviewed and recommended by Peer Community in Evolutionary Biology</title>
		#<url>https://dx.doi.org/10.24072/pci.evolbiol.100055</url>
		#<editor>Charles Baer</editor>
		#<date>2018-08-08</date>
		#<reviewers>anonymous and anonymous</reviewers>
		#<logo>https://peercommunityindotorg.files.wordpress.com/2018/09/small_logo_pour_pdf.png</logo>
	#</resource>
	#<doi>10.1101/273367</doi> 
	#</link>
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	recomm = db( (db.t_recommendations.article_id==row.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=db.t_recommendations.id).last()
	if recomm is None: 
		return None
	version = recomm.ms_version or ''
	pci = myconf.take('app.description')
	title = 'Version %(version)s of this preprint has been peer-reviewed and recommended by %(pci)s' % locals()
	url = URL(c='articles', f='rec', vars=dict(id=row.id), scheme=scheme, host=host, port=port)
	#recommenders = [mkUser(auth, db, recomm.recommender_id).flatten()]
	#contribsQy = db( db.t_press_reviews.recommendation_id == recomm.id ).select()
	#n = len(contribsQy)
	#i = 0
	#for contrib in contribsQy:
		#i += 1
		#if (i < n):
			#recommenders += ', '
		#else:
			#recommenders += ' and '
		#recommenders += mkUser(auth, db, contrib.contributor_id).flatten()
	#recommendersStr = ''.join(recommenders)
	recommendersStr = mkRecommendersString(auth, db,recomm)
	
	#reviewers = []
	#reviewsQy = db( (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == row.id) & (db.t_reviews.anonymously == False) & (db.t_reviews.review_state=='Completed') ).select(db.t_reviews.reviewer_id, distinct=True)
	#if reviewsQy is not None:
		#nR = len(reviewsQy)
		#i = 0
		#for rw in reviewsQy:
			#if rw.reviewer_id:
				#i += 1
				#if (i > 1):
					#if (i < nR):
						#reviewers += ', '
					#else:
						#reviewers += ' and '
				#reviewers += mkUser(auth, db, rw.reviewer_id).flatten()
	#reviewsQyAnon = db( (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_recommendations.article_id == row.id) & (db.t_reviews.anonymously == True) & (db.t_reviews.review_state=='Completed') ).select(db.t_reviews.reviewer_id, distinct=True)
	#if reviewsQyAnon is not None:
		#nRA = len(reviewsQyAnon)
		#if nRA > 0:
			#if len(reviewers) > 0:
				#reviewers += ' and '
			#if nRA > 1:
				#reviewers += '%s anonymous reviewers' % nRA
			#else:
				#reviewers += 'one anonymous reviewer'
	#reviewersStr = ''.join(reviewers)
	reviewersStr = mkReviewersString(auth, db, row.id)
	
	local = pytz.timezone ("Europe/Paris")
	local_dt = local.localize(row.last_status_change, is_dst=None)
	created_on = local_dt.astimezone (pytz.utc)
	
	return dict(
		title = title.decode('utf-8'),
		url = url,
		recommender = recommendersStr.decode('utf-8'),
		reviewers = reviewersStr.decode('utf-8'),
		date = created_on.strftime('%Y-%m-%d'),
		logo = XML(URL(c='static', f='images/small-background.png', scheme=scheme, host=host, port=port)),
		doi = row.doi,
	 )


######################################################################################################################################################################
def mkRecommCitation(auth, db, myRecomm):
	#scheme=myconf.take('alerts.scheme')
	#host=myconf.take('alerts.host')
	#port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	citeNum = ''
	doi = ''
	if myRecomm is None or not hasattr(myRecomm, 'recommendation_doi'):
		return SPAN('?')
	whoDidItCite = mkWhoDidIt4Recomm(auth, db, myRecomm, with_reviewers=False, linked=False)
	if myRecomm.recommendation_doi:
		citeNumSearch = re.search('([0-9]+$)', myRecomm.recommendation_doi, re.IGNORECASE)
		if citeNumSearch:
			citeNum = ', '+citeNumSearch.group(1)
		doi = SPAN('DOI: ', mkDOI(myRecomm.recommendation_doi))
	citeRecomm = SPAN(
		SPAN(whoDidItCite), ' ', 
		myRecomm.last_change.strftime('(%Y)'), ' ', 
		myRecomm.recommendation_title, '. ', 
		I(applongname)+citeNum, SPAN(' '), 
		doi
	)
	return citeRecomm



######################################################################################################################################################################
def mkArticleCitation(auth, db, myRecomm):
	
	#scheme=myconf.take('alerts.scheme')
	#host=myconf.take('alerts.host')
	#port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	
	if myRecomm is None or not hasattr(myRecomm, 'article_id'):
		return SPAN('?')
	else:
		art = db( (db.t_articles.id == myRecomm.article_id) ).select().last()
		artSrc = art.article_source or ''
		version = myRecomm.ms_version or ''
		citeArticle = SPAN(
			SPAN(art.authors), ' ', 
			art.title, '. ', 
			SPAN(art.last_status_change.strftime('%Y, ')), 
			artSrc, '. ', 
			I('Version ', version, ' peer-reviewed and recommended by ', applongname, '.'), 
			' DOI: ', mkDOI(art.doi)
		)
		return citeArticle


######################################################################################################################################################################
# Tracking of submissions / reviews for CNeuro
def mkTrackRow(auth, db, myArticle):
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	trackR = track = None
	nbReviews = db( (db.t_recommendations.article_id == myArticle.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_reviews.review_state.belongs('Under consideration', 'Completed')) ).count(distinct=db.t_reviews.id)
	if nbReviews > 0 :
		track = DIV(_class='pci-trackItem')
		lastRecomm = db( (db.t_recommendations.article_id == myArticle.id) ).select(orderby=db.t_recommendations.id).last()
		link = mkDOI(myArticle.doi)
		firstDate = myArticle.upload_timestamp.strftime('%Y-%m-%d')
		lastDate = myArticle.last_status_change.strftime('%Y-%m-%d')
		title = myArticle.title
		if (myArticle.anonymous_submission):
			authors = '[anonymous submission]'
		else:
			authors = myArticle.authors
		
		# pci-status
		if myArticle.status == 'Recommended':
			#txt = DIV(SPAN(current.T(' is')), SPAN(current.T('RECOMMENDED'), _class='pci-trackStatus success'), SPAN(SPAN('(', firstDate, ' ➜ ', lastDate, ')'), '. ', A('See recommendations and reviews', _href=URL('articles', 'rec', scheme=scheme, host=host, port=port, vars=dict(id=myArticle.id)), _class='btn btn-success')))
			txt = DIV(
					SPAN(current.T(' was')), 
					SPAN(current.T('UNDER REVIEW'), _class='pci-trackStatus default'),
					SPAN(SPAN('(', firstDate, ' ➜ ', lastDate, ')'),
					'. ', 
					A('See recommendation and reviews', _href=
						URL('articles', 'rec', scheme=scheme, host=host, port=port, vars=dict(id=myArticle.id)), _class='btn btn-success'))
					)
			
		#elif myArticle.status == 'Rejected':
			#txt = DIV(SPAN(current.T(' was')), SPAN(current.T('UNDER REVIEW'), _class='pci-trackStatus pci-status default'), SPAN('(', firstDate, ' ➜ ', lastDate, ')'))
			
		elif myArticle.status == 'Cancelled':
			txt = DIV(SPAN(current.T(' was')), SPAN(current.T('UNDER REVIEW'), _class='pci-trackStatus default'), SPAN('(', firstDate, ' ➜ ', lastDate, '). '), A('See reviews', _href=URL('public', 'pubReviews', scheme=scheme, host=host, port=port, vars=dict(id=myArticle.id)), _class='btn btn-default'))
			
		elif myArticle.status == 'Under consideration' or myArticle.status == 'Pre-recommended' or myArticle.status == 'Pre-rejected' or myArticle.status == 'Pre-revision':
			txt = DIV(SPAN(current.T(' is')), SPAN(current.T('UNDER REVIEW'), _class='pci-trackStatus info'), SPAN('(', current.T('Submitted on'), ' ', firstDate, ')'))
			
		elif myArticle.status == 'Awaiting revision' :
			txt = DIV(SPAN(current.T(' was')), SPAN(current.T('UNDER REVIEW'), _class='pci-trackStatus default'), SPAN('(', current.T('Submitted on'), ' ', firstDate, ')'))

		else:
			return(None)
		track.append(DIV(B(title, _style="font-size:14px")))
		track.append(DIV(SPAN(authors)))
		track.append(DIV(link))
		track.append(txt)
	
		trackR = [TD(IMG(_src=URL(c='static', f='images/small-background.png', scheme=scheme, host=host, port=port), _class='pci-trackImg')), TD(track)]
	return(trackR)


######################################################################################################################################################################
# Show reviews of cancelled articles for CNeuro
def reviewsOfCancelled(auth, db, art):
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname=myconf.take('app.longname')
	track = None
	printable = False
	with_reviews = True
	nbReviews = db( (db.t_recommendations.article_id == art.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_reviews.review_state.belongs('Under consideration', 'Completed')) ).count(distinct=db.t_reviews.id)
	if art.status=='Cancelled' and nbReviews > 0 :
		
		myArticle = DIV(DIV(H1(current.T('Submitted article:')))
			,SPAN((art.authors or '')+'. ', _class='pci-recomOfAuthors')
			,SPAN((art.title or '')+' ', _class='pci-recomOfTitle')
			,(SPAN((art.article_source+'. '), _class='pci-recomOfSource') if art.article_source else ' ')
			,(mkDOI(art.doi)) if (art.doi) else SPAN('')
			,SPAN(' '+current.T('version')+' '+art.ms_version) if art.ms_version else ''
			,_class='pci-recommOfArticle'
		)
		myContents = DIV(myArticle, _class=('pci-article-div-printable' if printable else 'pci-article-div'))
		recomms = db( (db.t_recommendations.article_id==art.id) ).select(orderby=~db.t_recommendations.id)
		recommRound = len(recomms)
		headerDone = False
		
		for recomm in recomms:
			
			whoDidIt = mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=True, linked=not(printable), as_items=False, host=host, port=port, scheme=scheme)
			
			myReviews = ''
			myReviews = []
			headerDone = False
			# Check for reviews
			reviews = db( (db.t_reviews.recommendation_id==recomm.id) & (db.t_reviews.review_state=='Completed') ).select(orderby=db.t_reviews.id)
			for review in reviews:
				if with_reviews:
					# display the review
					if review.anonymously:
						myReviews.append(
							H4(current.T('Reviewed by')+' '+current.T('anonymous reviewer')+(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else ''))
						)
					else:
						myReviews.append(
							H4(current.T('Reviewed by'),' ',mkUser(auth, db, review.reviewer_id, linked=not(printable)),(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else ''))
						)
					myReviews.append(BR())
					if len(review.review or '')>2:
						myReviews.append(DIV(WIKI(review.review), _class='pci-bigtext margin'))
						if review.review_pdf:
							myReviews.append(DIV(A(current.T('Download the review (PDF file)'), _href=URL('default', 'download', args=review.review_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'))
					elif review.review_pdf:
						myReviews.append(DIV(A(current.T('Download the review (PDF file)'), _href=URL('default', 'download', args=review.review_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'))
					else:
						pass
						
			if recomm.reply:
				if recomm.reply_pdf:
					reply = DIV(
							H4(B(current.T('Author\'s reply:'))),
							DIV(WIKI(recomm.reply), _class='pci-bigtext'),
							DIV(A(current.T('Download author\'s reply (PDF file)'), _href=URL('default', 'download', args=recomm.reply_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'),
							_style='margin-top:32px;',
						)
				else:
					reply = DIV(
							H4(B(current.T('Author\'s reply:'))),
							DIV(WIKI(recomm.reply), _class='pci-bigtext'),
							_style='margin-top:32px;',
						)
			elif recomm.reply_pdf:
				reply = DIV(
						H4(B(current.T('Author\'s reply:'))),
						DIV(A(current.T('Download author\'s reply (PDF file)'), _href=URL('default', 'download', args=recomm.reply_pdf), _style='margin-bottom: 64px;'), _class='pci-bigtext margin'),
						_style='margin-top:32px;',
					)
			else:
				reply = ''
			myContents.append( DIV( HR()
					,H3('Revision round #%s' % recommRound)
					,SPAN(I(recomm.last_change.strftime('%Y-%m-%d')+' ')) if recomm.last_change else ''
					,H2(recomm.recommendation_title if ((recomm.recommendation_title or '') != '') else T('Decision'))
					,H4(current.T(' by '), SPAN(whoDidIt)) #mkUserWithAffil(auth, db, recomm.recommender_id, linked=not(printable)))
					#,SPAN(SPAN(current.T('Recommendation:')+' '), mkDOI(recomm.recommendation_doi), BR()) if ((recomm.recommendation_doi or '')!='') else ''
					#,DIV(SPAN('A recommendation of:', _class='pci-recommOf'), myArticle, _class='pci-recommOfDiv')
					,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext')
					,DIV(I(current.T('Preprint DOI:')+' '), mkDOI(recomm.doi), BR()) if ((recomm.doi or '')!='') else ''
					,DIV(myReviews, _class='pci-reviews') if len(myReviews) > 0 else ''
					,reply
					, _class='pci-recommendation-div'
					#, _style='margin-left:%spx' % (leftShift)
					)
				)
			recommRound -= 1
	
	#nbRecomms = db( (db.t_recommendations.article_id==art.id) ).count()
	#nbReviews = db( (db.t_recommendations.article_id==art.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) ).count()
	return(myContents)

######################################################################################################################################################################
def mkViewEditRecommendationsRecommenderButton(auth, db, row):
	return A(SPAN(current.T('Check & Edit'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='recommender', f='recommendations', vars=dict(articleId=row.article_id)), _class='button', _title=current.T('View and/or edit article'))

######################################################################################################################################################################
def mkViewEditRecommendationsManagerButton(auth, db, row):
	return A(SPAN(current.T('Check & Edit'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='manager', f='recommendations', vars=dict(articleId=row.article_id)), _class='button', _title=current.T('View and/or edit article'))

#A(SPAN(current.T('Check & Edit')), 
#_href=URL(c='manager', f='recommendations', vars=dict(articleId=row.id), user_signature=True), 
#_target="_blank", 
#_class='buttontext btn btn-default pci-button pci-manager', 
#_title=current.T('View and/or edit review')
#)
