# -*- coding: utf-8 -*-

import gc
import os
import pytz, datetime
from re import sub, match
from copy import deepcopy
from datetime import datetime, timedelta
from dateutil.relativedelta import *

import io
from PIL import Image

from gluon import current, IS_IN_DB
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail
from sqlhtml import *

myconf = AppConfig(reload=True)


def takePort(p):
	#print 'port="%s"' % p
	if p is None:
		return False
	elif match('^[0-9]+$', p):
		return int(p)
	else:
		return False

statusArticles = dict()
def mkStatusArticles(db):
	statusArticles.clear()
	for sa in db(db.t_status_article).select():
		statusArticles[sa['status']] = sa



# Builds the right-panel for home page
def mkTopPanel(myconf, auth, inSearch=False):
	#if inSearch:
		#panel = [A(current.T('Search recommended articles'), _href='#TOP', _class='btn btn-default')]
	#else:
		#panel = [A(current.T('Search recommended articles'), _href=URL('public', 'recommended_articles'), _class='btn btn-default')]
	panel = []
	if auth.user:
		panel.append(A(current.T("Request a recommendation for your preprint"), 
							_href=URL('user', 'new_submission', user_signature=True), 
							_class="btn btn-success"))
	else:
		#panel.append(A(current.T("Request a recommendation for your preprint"), 
							#_href=URL('default', 'user'),
							#_class="btn btn-success"))
		panel.append(DIV(
						#LABEL(current.T('You have to be logged in before requesting a recommendation: ')),
						A(current.T('Log in'), _href=URL(c='default', f='user', args=['login']), _class="btn btn-info"),
						LABEL(current.T(' or ')),
						A(current.T('Register'), _href=URL(c='default', f='user', args=['register']), _class="btn btn-info"),
						_style='text-align:right;',
					))
	if auth.has_membership('recommender'):
		panel.append(A(current.T("Recommend a postprint"), 
							_href=URL('recommender', 'new_submission', user_signature=True), 
							_class="btn btn-info"))
		panel.append(A(current.T("Consider preprint recommendation requests"), 
							_href=URL('recommender', 'all_awaiting_articles', user_signature=True), 
							_class="btn btn-default"))
	return DIV(panel, _style='margin-top:20px; margin-bottom:20px; text-align:center;')


## Builds the right-panel for home page
#def mkPanel(myconf, auth, inSearch=False):
	#if inSearch:
		#panel = [LI(A(current.T('Search recommended articles'), _href='#TOP', _class='btn btn-default'), _class="list-group-item list-group-item-centered"),]
	#else:
		#panel = [LI(A(current.T('Search recommended articles'), _href=URL('public', 'recommended_articles'), _class='btn btn-default'), _class="list-group-item list-group-item-centered"),]
	#if auth.user_id is not None:
		##panel.append(LI(A(current.T("Request a recommendation"), _href=URL('user', 'my_articles', args=['new', 't_articles'], user_signature=True), _class="btn btn-success"), _class="list-group-item list-group-item-centered"))
		#panel.append(LI(A(current.T("Request a recommendation for your preprint for a recommendation"), 
							#_href=URL('user', 'new_submission', user_signature=True), 
							#_class="btn btn-success"), 
						#_class="list-group-item list-group-item-centered"))
	#else:
		#panel.append(LI(A(current.T("Log in before requesting a recommendation"), _href=URL('default', 'user')), _class="list-group-item"))
	#if auth.has_membership('recommender'):
		#panel.append(LI(A(current.T("Start a recommendation process"), 
							#_href=URL('recommender', 'new_submission', user_signature=True), 
							#_class="btn btn-info"), 
						#_class="list-group-item list-group-item-centered"))
		#panel.append(LI(A(current.T("Template email for authors"), 
							#_href=URL('recommender', 'email_for_author', user_signature=True), 
							#_class="btn btn-info"), 
						#_class="list-group-item list-group-item-centered"))
	#return DIV(UL( panel, _class="list-group"), _class="panel panel-info")




# Transforms a DOI in link
def mkDOI(doi):
	if (doi is not None) and (doi != ''):
		if (match('^http', doi)):
			return A(doi, _href=doi, _class="doi_url", _target="_blank")
		else:
			return A(doi, _href="http://dx.doi.org/"+sub(r'doi: *', '', doi), _class="doi_url", _target="_blank") 
	else:
		return SPAN('', _class="doi_url")




# Builds common search form (fuzzy + thematic fields)
def mkSearchForm(auth, db, myVars, allowBlank=True, withThematics=True):
	if withThematics:
		# number of columns of thematic fields
		nCol = 5
		# count requested thematic fields
		if myVars is None:
			myVars = dict()
		ntf = 0
		for myVar in myVars:
			if (match('^qy_', myVar)):
				ntf += 1
		#if ntf == 0: # if none requested, use user's thematic fields by default
			#if auth.user_id is not None:
				#myProfiles = db(db.auth_user._id == auth.user_id).select()
				#for myProfile in myProfiles:
					#for thema in myProfile.thematics:
						#myVars['qy_'+thema] = 'on'
						#ntf += 1
		# process thematic fields
		tab = []
		r = []
		c = 1
		for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
			f = INPUT(_name='qy_'+thema.keyword, _type='checkbox', value=('qy_'+thema.keyword in myVars) or (ntf == 0), keepvalues=True)
			r.append(TD(f, thema.keyword, _class='pci-thematicFieldsCheck'))
			c += 1
			if (c % nCol) == 0:
				tab.append(TR(deepcopy(r)))
				r = []
				c = 1
		tab.append(deepcopy(r))
		
		themaDiv = DIV(
				BR(),
				LABEL(current.T('in thematic fields:')), 
				DIV(
					TABLE(tab, _class='pci-thematicFieldsTable'),
					SPAN(
						A(SPAN(current.T('Check all thematic fields'), _class='buttontext btn btn-default'), _onclick="jQuery('input[type=checkbox]').each(function(k){if (this.name.match('^qy_')) {jQuery(this).prop('checked', true);} });", _class="pci-flushright"),
						A(SPAN(current.T('Toggle thematic fields'), _class='buttontext btn btn-default'), _onclick="jQuery('input[type=checkbox]').each(function(k){if (this.name.match('^qy_')) {jQuery(this).prop('checked', !jQuery(this).prop('checked'));} });", _class="pci-flushright"),
					),
					DIV(
						INPUT(_type='submit', _value=current.T('Search'), _class='btn btn-warning'), 
						_style='text-align:center; margin-top:8px;', 
					),
					_class="pci-thematicFieldsDiv"),
			)
	else:
		themaDiv = INPUT(_type='submit', _value=current.T('Search'), _class='btn btn-warning searchFormInline')
		
	
	# process searched words
	kwVal = None
	if 'qyKeywords' in myVars:
		kwVal = myVars['qyKeywords']
		if isinstance(kwVal, list):
			kwVal = kwVal[1]

	# build form
	form = FORM(SPAN(current.T('Leave search field blank for no filtering on words'), _style='color:#e0e0e0;')+BR() if allowBlank else '',
				LABEL(current.T('Search for'), _style='margin-right:12px;'),
				INPUT(_name='qyKeywords', value=kwVal, keepvalues=True, _class=('searchField' if withThematics else 'searchFieldInline')), 
				themaDiv,
				_class='' if withThematics else 'form-inline',
				_name='searchForm',
				_action=(URL(c='public', f='recommended_articles', user_signature=True)) if not(withThematics) else '',
			)
	if withThematics:
		return form
	else:
		return DIV(form, _class='searchFormDivInline')






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
	
	#if recomm.recommender_id is not None:
		#theUser = db(db.auth_user.id == recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
		#whoDidIt = [ mkUser_U(auth, db, theUser, linked=True, scheme=scheme, host=host, port=port) ]
		#if row.already_published:
			#contrQy = db(
							#(db.t_press_reviews.recommendation_id==recomm.id) & (db.auth_user.id==db.t_press_reviews.contributor_id)
						#).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, cacheable=True, orderby=db.t_press_reviews.id)
			#n=len(contrQy)
			#ic=0
			#for contr in contrQy:
				#ic += 1
				#if ic == n:
					#whoDidIt.append(SPAN(' & ', mkUser_U(auth, db, contr, linked=True, host=host, scheme=scheme, port=port)))
				#else:
					#whoDidIt.append(SPAN(', ', mkUser_U(auth, db, contr, linked=True, host=host, scheme=scheme, port=port)))
		#else:
			#contrQy = db(
							#(db.t_reviews.recommendation_id==recomm.id) & (db.t_reviews.anonymously==False) & (db.auth_user.id==db.t_reviews.reviewer_id) 
						#).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, cacheable=True, orderby=db.t_reviews.id)
			#n=len(contrQy)
			#ic=0
			#if n>0:
				#whoDidIt.append(SPAN(' based on reviews by '))
			#for contr in contrQy:
				#ic += 1
				#if ic == n and ic>1:
					#whoDidIt.append(SPAN(' & ', mkUser_U(auth, db, contr, linked=True, host=host, scheme=scheme, port=port)))
				#elif ic>1:
					#whoDidIt.append(SPAN(', ', mkUser_U(auth, db, contr, linked=True, host=host, scheme=scheme, port=port)))
				#else:
					#whoDidIt.append(mkUser_U(auth, db, contr, linked=True, host=host, scheme=scheme, port=port))
	#else:
		#whoDidIt = [SPAN(current.T('See recommendation'))]
	
	whoDidIt = mkWhoDidIt4Article(auth, db, row, with_reviewers=True, linked=True, host=False, port=False, scheme=False)
	
	img = []
	if withDate:
		img += [SPAN(mkLastChange(row.last_status_change), _class='pci-lastArticles-date'),BR(),]
	if withImg:
		if (row.uploaded_picture is not None and row.uploaded_picture != ''):
			img += [IMG(_src=URL('default', 'download', scheme=scheme, host=host, port=port, args=row.uploaded_picture), _class='pci-articlePicture')]
	resu.append(TD( img, _style='vertical-align:top; text-align:left;' ))

	shortTxt = recomm.recommendation_comments or ''
	if len(shortTxt)>500:
		shortTxt = shortTxt[0:500] + '...'
	
	if row.authors and len(row.authors)>500:
		authors = row.authors[:500]+'...'
	else:
		authors = row.authors or ''
	resu.append(
				TD(
					SPAN(row.title, _style='font-size:18px;'),
					BR(),
					SPAN(authors),
					BR(),
					mkDOI(row.doi),
					P(),
					DIV(
						I(SPAN('Recommended by '), SPAN(whoDidIt), 
							BR(),
							SPAN((recomm.recommendation_title or 'Read...'), _target='blank', _style="font-size:16px;"),# color:green;"),
						),
						#BR(),
						DIV(WIKI(shortTxt), _class='pci-shortTxt'),
						#BR(),
						A(current.T('More'), _target='blank', 
							_href= URL(c='public', f='rec', vars=dict(id=row.id), scheme=scheme, host=host, port=port),
							_class='btn btn-success pci-smallBtn',
						),
						_style='margin-right:1cm; margin-left:1cm; padding-left:8px; border-left:1px solid #cccccc;',
					),
					_class='pci-lastArticles-cell'
				),
			)
	
	if withScore:
			resu.append(TD(row.score or '', _class='pci-lastArticles-date'))
	return TR(resu, _class='pci-lastArticles-row')





# Builds a html representation of an article
def mkRepresentArticle(auth, db, articleId):
	resu = ''
	if articleId:
		art = db.t_articles[articleId]
		if art is not None:
			submitter = ''
			sub_repr = ''
			if art.user_id is not None:
				submitter = db(db.auth_user.id==art.user_id).select(db.auth_user.first_name, db.auth_user.last_name).last()
				sub_repr = 'by %s %s,' % (submitter.first_name, submitter.last_name)
			resu = DIV(
						SPAN(I(current.T('Submitted')+' %s %s' % (sub_repr, art.upload_timestamp.strftime('%Y-%m-%d %H:%M') if art.upload_timestamp else '')))
						,H4(art.authors)
						,H3(art.title)
						,SPAN(art.article_source)+BR() if art.article_source else ''
						,mkDOI(art.doi)+BR() if art.doi else ''
						,SPAN(I(current.T('Keywords:')+' '))+I(art.keywords or '') if art.keywords else ''
						,BR()+B(current.T('Abstract'))+BR()+DIV(WIKI(art.abstract or ''), _class='pci-bigtext') if art.abstract else ''
						, _class='pci-article-div'
					)
	return resu

# Builds a nice representation of an article WITH recommendations link
def mkArticleCell(auth, db, art):
	anchor = ''
	if art:
		# Recommender name(s)
		recomm = db( (db.t_recommendations.article_id==art.id) ).select(orderby=db.t_recommendations.id).last()
		if recomm is not None and recomm.recommender_id is not None:
			whowhen = [SPAN(current.T('See recommendation by '), mkUser(auth, db, recomm.recommender_id))]
			if art.already_published:
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
					BR(),
					SPAN(art.authors),
					BR(),
					mkDOI(art.doi),
					(BR()+SPAN(art.article_source) if art.article_source else ''),
					A(whowhen, 
								_href=URL(c='public', f='rec', vars=dict(id=art.id)),
								_target='blank',
								_style="color:green;margin-left:12px;",
						),
				)
	return anchor


# Builds a nice representation of an article WITHOUT recommendations link
def mkArticleCellNoRecomm(auth, db, art):
	anchor = ''
	if art:
		anchor = DIV(
					B(art.title),
					BR(),
					SPAN(art.authors),
					BR(),
					mkDOI(art.doi),
					(BR()+SPAN(art.article_source) if art.article_source else ''),
				)
	return anchor




def mkRepresentArticleLight(auth, db, article_id):
	anchor = ''
	art = db.t_articles[article_id]
	if art:
		anchor = DIV(
					B(art.title),
					BR(),
					SPAN(art.authors),
					BR(),
					mkDOI(art.doi),
					(BR()+SPAN(art.article_source) if art.article_source else '')
				)
	return anchor



def mkRepresentRecommendationLight(auth, db, recommId):
	anchor = ''
	recomm = db.t_recommendations[recommId]
	if recomm:
		art = db.t_articles[recomm.article_id]
		if art:
			if art.already_published:
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
			else:
				recommenders = mkUser(auth, db, recomm.recommender_id)
			anchor = DIV(
						B(recomm.recommendation_title), SPAN(current.T(' by ')), recommenders, mkDOI(recomm.recommendation_doi),
						P(),
						SPAN(current.T('A recommendation of ')), I(art.title), SPAN(current.T(' by ')), SPAN(art.authors), 
						(SPAN(current.T(' in '))+SPAN(art.article_source) if art.article_source else ''),
						BR(), 
						mkDOI(art.doi),
					)
	return anchor



#def mkViewArticle4ReviewButton(auth, db, row):
	#anchor = ''
	#recomm = db.t_recommendations[row.recommendation_id]
	#if recomm:
		#art = db.t_articles[recomm.article_id]
		#if art:
			#anchor = DIV(
						#B(art.title),
						#BR(),
						#SPAN(art.authors),
						#BR(),
						#mkDOI(art.doi),
					#)
	#return anchor



## Builds a search button for recommenders matching keywords
#def mkSearchRecommendersManagerButton(auth, db, row):
	##if statusArticles is None or len(statusArticles) == 0:
		##mkStatusArticles(db)
	#anchor = ''
	#if row['status'] == 'Awaiting consideration' or row['status'] == 'Pending':
		#myVars = dict(articleId=row['id'])
		#for thema in row['thematics']:
			#myVars['qy_'+thema] = 'on'
		##NOTE: useful or useless? 
		##myVars['qyKeywords'] = ' '.join(row['thematics'])
		#anchor = A(SPAN('+ '+current.T('Suggest'),BR(),current.T('recommenders'), _class='buttontext btn btn-default'), _href=URL(c='manager', f='search_recommenders', vars=myVars, user_signature=True), _class='button')
	#return anchor



## Builds a search button for recommenders matching keywords
#def mkSearchRecommendersUserButton(auth, db, row):
	##if statusArticles is None or len(statusArticles) == 0:
		##mkStatusArticles(db)
	#anchor = ''
	#if row['status'] == 'Awaiting consideration' or row['status'] == 'Pending':
		#myVars = dict(articleId=row['id'])
		#for thema in row['thematics']:
			#myVars['qy_'+thema] = 'on'
		##NOTE: useful or useless? 
		##myVars['qyKeywords'] = ' '.join(row['thematics'])
		#anchor = A(SPAN('+ '+current.T('Suggest'),BR(),current.T('recommenders'), _class='buttontext btn btn-default'), _href=URL(c='user', f='recommenders', vars=myVars, user_signature=True), _class='button')
	#return anchor



## Builds a search button for reviewers matching keywords
#def mkSearchReviewersButton(auth, db, row):
	##if statusArticles is None or len(statusArticles) == 0:
		##mkStatusArticles(db)
	#anchor = ''
	#article = db.t_articles[row['article_id']]
	#if article and article['status'] == 'Under consideration':
		#myVars = dict(recommId=row['id'])
		#for thema in article['thematics']:
			#myVars['qy_'+thema] = 'on'
		##NOTE: useful or useless? 
		##myVars['qyKeywords'] = ' '.join(article['thematics'])
		#if article['already_published'] and row['auto_nb_agreements']==0:
			#myVars['4press'] = 'on'
			#anchor = A(SPAN('+ '+current.T('Add'),BR(),current.T('contributors'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='search_reviewers', vars=myVars, user_signature=True), _class='button')
		#elif article['already_published'] is False:
			#myVars['4review'] = 'on'
			#anchor = A(SPAN('+ '+current.T('Add'),BR(),current.T('reviewers'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='search_reviewers', vars=myVars, user_signature=True), _class='button')
	#return anchor




# Builds a coloured status label
def mkStatusDiv(auth, db, status):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	status_txt = (current.T(status)).upper()
	color_class = statusArticles[status]['color_class'] or 'default'
	hint = statusArticles[status]['explaination'] or ''
	return DIV(status_txt, _class='pci-status '+color_class, _title=current.T(hint))

def mkStatusBigDiv(auth, db, status):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	status_txt = (current.T(status)).upper()
	color_class = statusArticles[status]['color_class'] or 'default'
	hint = statusArticles[status]['explaination'] or ''
	return DIV(status_txt, _class='pci-status-big '+color_class, _title=current.T(hint))


def mkReviewStateDiv(auth, db, state):
	#state_txt = (current.T(state)).upper()
	state_txt = (state or '').upper()
	if state == 'Pending': color_class = 'warning'
	elif state == 'Under consideration': color_class = 'info'
	else: color_class = 'default'
	return DIV(state_txt, _class='pci-status '+color_class)


def mkContributionStateDiv(auth, db, state):
	#state_txt = (current.T(state)).upper()
	state_txt = (state or '').upper()
	if state == 'Pending': color_class = 'warning'
	elif state == 'Under consideration': color_class = 'info'
	elif state == 'Recommendation agreed': color_class = 'success'
	else: color_class = 'default'
	return DIV(state_txt, _class='pci-status '+color_class)


def mkAnonymousMask(auth, db, anon):
	if anon:
		return DIV(IMG(_src=URL(c='static',f='images/mask.png')), _style='text-align:center;')
	else:
		return ''


def mkJournalImg(auth, db, press):
	if press:
		return DIV(IMG(_src=URL(c='static',f='images/journal.png')), _style='text-align:center;')
	else:
		return ''


# code for a "Back" button
# go to the target instead, if any.
def mkBackButton(text=current.T('Back'), target=None):
	if target:
		return A(SPAN(text, _class='buttontext btn btn-default'), _href=target, _class='button')
	else:
		return A(SPAN(text, _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')

# code for a "Close" button
def mkCloseButton():
	return A(SPAN(current.T('Close'), _class='pci-ArticleTopButton buttontext btn btn-default'), _onclick='window.top.close();', _class='button')



def mkWhoDidIt4Article(auth, db, article, with_reviewers=False, linked=False, host=False, port=False, scheme=False):
	whoDidIt = []
	if article.already_published: #NOTE: POST-PRINT
		mainRecommenders = db(
							(db.t_recommendations.article_id==article.id) & (db.t_recommendations.recommender_id == db.auth_user.id)
						).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
		coRecommenders = db(
							(db.t_recommendations.article_id==article.id) & (db.t_press_reviews.recommendation_id==db.t_recommendations.id) & (db.auth_user.id==db.t_press_reviews.contributor_id)
							).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
		allRecommenders = mainRecommenders | coRecommenders
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
		mainRecommenders = db(
							(db.t_recommendations.article_id==article.id) & (db.t_recommendations.recommender_id == db.auth_user.id)
						).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
		if with_reviewers:
			namedReviewers = db(
							(db.t_recommendations.article_id==article.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) & (db.auth_user.id==db.t_reviews.reviewer_id) & (db.t_reviews.anonymously==False) & (db.t_reviews.review_state=='Terminated')
							).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
			na = db(
							(db.t_recommendations.article_id==article.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) & (db.auth_user.id==db.t_reviews.reviewer_id) & (db.t_reviews.anonymously==True) & (db.t_reviews.review_state=='Terminated')
							).count(distinct=db.auth_user.id)
			na1 = 1 if na>0 else 0
		else:
			namedReviewers = []
			na = 0
		nr = len(mainRecommenders)
		nw = len(namedReviewers)
		ir = 0
		for theUser in mainRecommenders:
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
		#if nw > 0 and na > 0:
			#whoDidIt.append(current.T(' and '))
		if na > 1:
			whoDidIt.append(current.T('%d anonymous reviewers') % (na))
		elif na == 1:
			whoDidIt.append(current.T('%d anonymous reviewer') % (na))
	
	return whoDidIt


def mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=False, as_list=False, as_items=False, linked=False, host=False, port=False, scheme=False):
	whoDidIt = []
	article = db( db.t_articles.id==recomm.article_id ).select(db.t_articles.already_published).last()
	
	if article.already_published: #NOTE: POST-PRINT
		mainRecommenders = db(
							(db.t_recommendations.id==recomm.id) & (db.t_recommendations.recommender_id == db.auth_user.id)
						).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
		coRecommenders = db(
							(db.t_recommendations.id==recomm.id) & (db.t_press_reviews.recommendation_id==db.t_recommendations.id) & (db.auth_user.id==db.t_press_reviews.contributor_id)
							).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
		allRecommenders = mainRecommenders | coRecommenders

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
		mainRecommenders = db(
							(db.t_recommendations.id==recomm.id) & (db.t_recommendations.recommender_id == db.auth_user.id)
						).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
		if with_reviewers:
			namedReviewers = db(
							(db.t_recommendations.id==recomm.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) & (db.auth_user.id==db.t_reviews.reviewer_id) & (db.t_reviews.anonymously==False) & (db.t_reviews.review_state=='Terminated')
							).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
			na = db(
							(db.t_recommendations.id==recomm.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) & (db.t_reviews.anonymously==True) & (db.t_reviews.review_state=='Terminated')
							).count(distinct=db.t_reviews.reviewer_id)
			na1 = (1 if(na>0) else 0)
		else:
			namedReviewers = []
			na = 0
		nr = len(mainRecommenders)
		nw = len(namedReviewers)
		ir = 0
		for theUser in mainRecommenders:
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
		#if nw > 0 and na > 0 and as_items is False:
			#whoDidIt.append(current.T(' and '))
		if not as_list:
			if na > 1:
				whoDidIt.append(current.T('%d anonymous reviewers') % (na))
			elif na == 1:
				whoDidIt.append(current.T('%d anonymous reviewer') % (na))
	
	return whoDidIt



def mkFeaturedRecommendation(auth, db, art, printable=False, with_reviews=False, with_comments=False, fullURL=True):
	if fullURL:
		scheme=myconf.take('alerts.scheme')
		host=myconf.take('alerts.host')
		port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	else:
		scheme=False
		host=False
		port=False
	
	myMeta = dict()
	myContents = DIV(_class=('pci-article-div-printable' if printable else 'pci-article-div'))
	#submitter = db(db.auth_user.id==art.user_id).select(db.auth_user.first_name, db.auth_user.last_name).last()
	###NOTE: article facts
	if (art.uploaded_picture is not None and art.uploaded_picture != ''):
		img = DIV(IMG(_src=URL('default', 'download', args=art.uploaded_picture), _style='max-width:150px; max-height:150px;'), _style='text-align:center;')
	else:
		img = ''
	doi = sub(r'doi: *', '', (art.doi or ''))
	if printable:
		altmetric = XML("<div class='altmetric-embed' data-badge-type='donut' data-badge-details='right' data-hide-no-mentions='true' data-doi='%s'></div>" % doi)
	else:
		altmetric = XML("<div class='altmetric-embed' data-badge-type='donut' data-badge-details='right' data-hide-no-mentions='true' data-doi='%s'></div>" % doi)
	myArticle = DIV(
					DIV(DIV(I(current.T('Recommended article')), _class='pci-ArticleText'), _class='pci-ArticleHeader recommended'+(' printable' if printable else ''))
					,DIV(altmetric, _style='text-align:right;')
					,img
					,H4(art.authors or '')
					,H3(art.title or '')
					,(mkDOI(art.doi)+P()) if (art.doi) else SPAN('')
					,(SPAN(art.article_source)+P() if art.article_source else '')
					,B(current.T('Abstract'))+BR()
					,DIV(WIKI(art.abstract or ''))
					,SPAN(I(current.T('Keywords:')+' '+art.keywords)+BR() if art.keywords else '')
					#,_class=('pci-article-div-printable' if printable else 'pci-article-div')
					,_class='pci-bigtext pci-article-reference'
				)
	
	#WARNING: article enlevé de la recommendation
	#myContents.append(myArticle)
	
	recomGreen=DIV(
				DIV(
					DIV(I(current.T('Recommendation')), _class='pci-ArticleText'),
					_class='pci-ArticleHeader recommended'+ (' printable' if printable else '')
				))
	myContents.append(P())
	myContents.append(recomGreen)
	###NOTE: recommendations counting
	if with_reviews:
		recomms = db( (db.t_recommendations.article_id==art.id) ).select(orderby=~db.t_recommendations.id)
	else:
		recomms = db( (db.t_recommendations.article_id==art.id) & (db.t_recommendations.recommendation_state=='Recommended') ).select(orderby=~db.t_recommendations.id)

	leftShift=0
	for recomm in recomms:
		
		pdfQ = db(db.t_pdf.recommendation_id == recomm.id).select(db.t_pdf.id, db.t_pdf.pdf)
		if len(pdfQ)>0:
			pdf = A(SPAN(current.T('PDF recommendation'), ' ', IMG(_src=URL('static', 'images/application-pdf.png'))), _href=URL('default', 'download', args=pdfQ[0]['pdf']), _class='btn btn-info')
		else:
			pdf = None
		
		whoDidItTxt = mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=True, linked=not(printable), host=host, port=port, scheme=scheme)
		whoDidItCite = mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)
		whoDidIt = mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=False, linked=not(printable), as_items=True, host=host, port=port, scheme=scheme)
		whoDidItMeta = mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=False, linked=False, as_list=True, as_items=False, host=host, port=port, scheme=scheme)

		# METADATA
		desc = 'A recommendation of: '+(art.authors or '')+' '+(art.title or '')+' '+(art.doi or '')
		myMeta['DC.issued'] = recomm.last_change.date()
		myMeta['DC.date'] = recomm.last_change.date()
		myMeta['citation_publication_date'] = recomm.last_change.date()
		myMeta['citation_online_date'] = recomm.last_change.date()
		myMeta['DC.rights'] = '(C) '+myconf.take("app.description")+', '+str(recomm.last_change.date().year)
		myMeta['DC.publisher'] = myconf.take("app.description")
		myMeta['citation_publisher'] = myconf.take("app.description")
		myMeta['DC.relation.ispartof'] = myconf.take("app.description")
		myMeta['citation_journal_title'] = myconf.take("app.description")
		myMeta['citation_journal_abbrev'] = myconf.take("app.name")
		myMeta['citation_issn'] = myconf.take("app.issn")
		myMeta['DC.language'] = 'en'
		myMeta['DC.title'] = recomm.recommendation_title
		myMeta['og:title'] = recomm.recommendation_title
		myMeta['description'] = desc
		myMeta['DC.description'] = desc
		myMeta['citation_abstract'] = desc
		if recomm.recommendation_doi:
			myMeta['citation_doi'] = sub(r'doi: *', '', recomm.recommendation_doi) # for altmetrics
			myMeta['DC.identifier'] = myMeta['citation_doi']
		#for recommenderNames in whoDidItMeta:
			#myMeta['DC.creator'] = recommenderNames # for altmetrics
		if len(whoDidItMeta)>0:
			myMeta['DC.creator'] = ' ; '.join(whoDidItMeta) # syntax follows: http://dublincore.org/documents/2000/07/16/usageguide/#usinghtml
			myMeta['citation_author'] = ' ; '.join(whoDidItMeta) # syntax follows: http://dublincore.org/documents/2000/07/16/usageguide/#usinghtml
		
		
		if recomm.recommendation_doi:
			citeNumSearch = re.search('([0-9]+$)', recomm.recommendation_doi, re.IGNORECASE)
			if citeNumSearch:
				citeNum = citeNumSearch.group(1)
				myMeta['citation_firstpage'] = citeNum
			else:
				citeNum = recomm.recommendation_doi
			citeRef = mkDOI(recomm.recommendation_doi)
			if printable:
				recomm_altmetric = XML("<div class='altmetric-embed' data-badge-type='donut' data-badge-details='right' data-hide-no-mentions='true' data-doi='%s'></div>" % sub(r'doi: *', '', recomm.recommendation_doi))
			else:
				recomm_altmetric = XML("<div class='altmetric-embed' data-badge-type='donut' data-badge-details='right' data-hide-no-mentions='true' data-doi='%s'></div>" % sub(r'doi: *', '', recomm.recommendation_doi))
		else:
			citeUrl = URL(c='public', f='rec', vars=dict(id=art.id), host=host, scheme=scheme, port=port)
			citeRef = A(citeUrl, _href=citeUrl)+SPAN(' accessed ', datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))
			citeNum = ''
			recomm_altmetric = ''
		if recomm.recommendation_state == 'Recommended':
			cite = DIV(
						SPAN(B('Cite as:'), 
						BR(), SPAN(whoDidItCite), ' ', recomm.last_change.strftime('(%Y)'), ' ', recomm.recommendation_title, '. ', I(myconf.take('app.description')+', '+citeNum+'. '), 
						citeRef, 
					), _class='pci-citation')
		else:
			cite = ''
			
		###NOTE: POST-PRINT ARTICLE
		if art.already_published:
			myContents.append(
				DIV(recomm_altmetric
					,cite
					,H2(recomm.recommendation_title if ((recomm.recommendation_title or '') != '') else current.T('Recommendation'))
					,H4(current.T(' by '), UL(whoDidIt))
					,I(recomm.last_change.strftime('%Y-%m-%d'))+BR() if recomm.last_change else ''
					,SPAN(SPAN(current.T('Recommendation:')+' '), mkDOI(recomm.recommendation_doi), BR()) if ((recomm.recommendation_doi or '')!='') else ''
					,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext')
					, _class='pci-recommendation-div'
				)
			)
		
		
		###NOTE: PRE-PRINT ARTICLE
		else: 
			myReviews = ''
			myReviews = []
			# Check for reviews
			reviews = db( (db.t_reviews.recommendation_id==recomm.id) & (db.t_reviews.review_state=='Terminated') ).select(orderby=db.t_reviews.id)
			for review in reviews:
				if with_reviews:
					# display the review
					if review.anonymously:
						myReviews.append(
							H4(current.T('Reviewed by')+' '+current.T('anonymous reviewer')+(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else ''))
						)
					else:
						myReviews.append(
							H4(current.T('Reviewed by'),' ',mkUser(auth, db, review.reviewer_id, linked=not(printable)),(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else ''))
						)
					myReviews.append(BR())
					myReviews.append(DIV(WIKI(review.review or ''), _class='pci-bigtext margin'))
			if recomm.reply:
				reply = DIV(
						H4(B(current.T('Author\'s reply:'))),
						DIV(WIKI(recomm.reply), _class='pci-bigtext'),
						_style='margin-top:32px;',
					)
			else:
				reply = ''
			myContents.append( DIV(recomm_altmetric
						,cite
						,H2(recomm.recommendation_title if ((recomm.recommendation_title or '') != '') else T('Recommendation'))
						,H4(current.T(' by '), UL(whoDidIt)) #mkUserWithAffil(auth, db, recomm.recommender_id, linked=not(printable)))
						,I(recomm.last_change.strftime('%Y-%m-%d'))+BR() if recomm.last_change else ''
						,SPAN(SPAN(current.T('Recommendation:')+' '), mkDOI(recomm.recommendation_doi), BR()) if ((recomm.recommendation_doi or '')!='') else ''
						,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext')
						,DIV(myReviews, _class='pci-reviews') if len(myReviews) > 0 else ''
						,reply
						, _class='pci-recommendation-div'
						, _style='margin-left:%spx' % (leftShift)
						)
					)
			leftShift += 50
	
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
			myContents.append(DIV(A(SPAN(current.T('New comment'), _class='buttontext btn btn-default'), 
									_href=URL(c='user', f='new_comment', vars=dict(articleId=art.id), user_signature=True)), 
								_class='pci-EditButtons'))
	
	nbRecomms = db( (db.t_recommendations.article_id==art.id) ).count()
	nbReviews = db( (db.t_recommendations.article_id==art.id) & (db.t_reviews.recommendation_id==db.t_recommendations.id) ).count()
	return dict(myContents=myContents, pdf=pdf, nbReviews=(nbReviews+(nbRecomms-1)), myMeta=myMeta)


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


# The most important function of the site !!
# Be *VERY* careful with rights management
def mkFeaturedArticle(auth, db, art, printable=False, with_comments=False, quiet=True, scheme=False, host=False, port=False):
	submitter = db(db.auth_user.id==art.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
	allowOpinion = None
	###NOTE: article facts
	if (art.uploaded_picture is not None and art.uploaded_picture != ''):
		img = DIV(IMG(_src=URL('default', 'download', args=art.uploaded_picture, scheme=scheme, host=host, port=port), _style='max-width:150px; max-height:150px;'))
	else:
		img = ''
	myContents = DIV(
					DIV(XML("<div class='altmetric-embed' data-badge-type='donut' data-doi='%s'></div>" % sub(r'doi: *', '', (art.doi or ''))), _style='text-align:right;'),
					img,
					SPAN(I(current.T('Submitted by')+' '+(submitter.first_name or '')+' '+(submitter.last_name or '')+' '+(art.upload_timestamp.strftime('%Y-%m-%d %H:%M') if art.upload_timestamp else '')) if submitter else '')
					,H4(art.authors or '')
					,H3(art.title or '')
					,(mkDOI(art.doi)+BR()) if (art.doi) else SPAN('')
					,(SPAN(art.article_source)+BR() if art.article_source else '')
					,SPAN(I(current.T('Keywords:')+' '+art.keywords)+BR() if art.keywords else '')
					,B(current.T('Abstract'))+BR()
					,DIV(WIKI(art.abstract or ''), _class='pci-bigtext')
					, _class=('pci-article-div-printable' if printable else 'pci-article-div')
				)
	if ((art.user_id == auth.user_id) and (art.status in ('Pending', 'Awaiting revision'))) and not(printable) and not (quiet):
		# author's button allowing article edition
		myContents.append(DIV(A(SPAN(current.T('Edit article'), _class='buttontext btn btn-default'), 
								_href=URL(c='user', f='edit_my_article', vars=dict(articleId=art.id), user_signature=True)), 
							_class='pci-EditButtons'))
	if auth.has_membership(role='manager') and not(printable) and not (quiet):
		# manager's button allowing article edition
		myContents.append(DIV(A(SPAN(current.T('Manage this request'), _class='buttontext btn btn-info'), 
								_href=URL(c='manager', f='edit_article', vars=dict(articleId=art.id), user_signature=True)), 
							_class='pci-EditButtons'))

	###NOTE: recommendations counting
	recomms = db(db.t_recommendations.article_id == art.id).select(orderby=db.t_recommendations.id)
	nbRecomms = len(recomms)
	if nbRecomms > 0 and auth.has_membership(role='manager') and not(printable) and not (quiet):
		# manager's button allowing recommendations management
		myContents.append(DIV(A(SPAN(current.T('Manage recommendations'), _class='buttontext btn btn-info'), _href=URL(c='manager', f='manage_recommendations', vars=dict(articleId=art.id), user_signature=True)), _class='pci-EditButtons'))
	if len(recomms)==0 and auth.has_membership(role='recommender') and art.status=='Awaiting consideration' and not(printable) and not (quiet):
		# suggested or any recommender's button for recommendation consideration
		btsAccDec = [A(SPAN(current.T('I wish to consider this preprint for recommendation'), _class='buttontext btn btn-success'), 
								_href=URL(c='recommender', f='accept_new_article_to_recommend', vars=dict(articleId=art.id), user_signature=True),
								_class='button'),]
		amISugg = db( (db.t_suggested_recommenders.article_id==art.id) & (db.t_suggested_recommenders.suggested_recommender_id==auth.user_id) ).count()
		if amISugg > 0:
			# suggested recommender's button for declining recommendation
			btsAccDec.append(A(SPAN(current.T('No, thanks, I decline this suggestion'), _class='buttontext btn btn-warning'), 
								_href=URL(c='recommender', f='decline_new_article_to_recommend', vars=dict(articleId=art.id), user_signature=True),
								_class='button'),
							)
		myContents.append( DIV(btsAccDec, _class='pci-opinionform') )
	
	###NOTE: here start recommendations display
	iRecomm = 0
	for recomm in recomms:
		iRecomm += 1
		recommender = db(db.auth_user.id==recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
		
		###NOTE: POST-PRINT ARTICLE
		if art.already_published:
			contributors = []
			contrQy = db( (db.t_press_reviews.recommendation_id==recomm.id) ).select(orderby=db.t_press_reviews.id)
			for contr in contrQy:
				contributors.append(contr.contributor_id)
			#whoDidIt = [(recommender.first_name or '')+' '+(recommender.last_name or '')]
			#if len(contributors) > 0:
				#for ic in range(0, len(contributors)):
					#if ic == len(contributors)-1:
						#whoDidIt.append(SPAN(' & ', mkUser(auth, db, contributors[ic])))
					#else:
						#whoDidIt.append(SPAN(', ', mkUser(auth, db, contributors[ic])))
			whoDidIt = mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=False, linked=not(printable), host=host, port=port, scheme=scheme)
			
			myContents.append(
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
			if not(recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == 'Under consideration') and not(printable) and not (quiet):
				# recommender's button allowing recommendation edition
				myContents.append(DIV(A(SPAN(current.T('Write or edit your recommendation'), _class='buttontext btn btn-default'), 
											_href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recomm.id), user_signature=True)), 
										_class='pci-EditButtons'))
				
				# recommender's button allowing recommendation submission, provided there are co-recommenders
				if len(contributors)>0:
					if len(recomm.recommendation_comments)>50:
						myContents.append(DIV(
									A(SPAN(current.T('Terminate this collective recommendation and send it to managing board'), _class='buttontext btn btn-success'), 
										_href=URL(c='recommender', f='recommend_article', vars=dict(recommId=recomm.id), user_signature=True), 
										_title=current.T('Click here to terminate the recommendation of this article and send it to the managing board')),
								_class='pci-EditButtons-centered'))
				else:
					# otherwise button for adding co-recommender(s)
					myContents.append(DIV(
									A(SPAN(current.T('You have to add at least one contributor in order to collectively validate this recommendation'), _class='buttontext btn btn-info'), 
										_href=URL(c='recommender', f='add_contributor', vars=dict(recommId=recomm.id), user_signature=True), 
										_title=current.T('Click here to add contributors of this article')),
								_class='pci-EditButtons-centered'))
				
				# recommender's button allowing cancellation
				myContents.append(DIV(A(SPAN(current.T('Cancel this postprint recommendation'), _class='buttontext btn btn-warning'), 
												_href=URL(c='recommender', f='do_cancel_press_review', vars=dict(recommId=recomm.id), user_signature=True), 
												_title=current.T('Click here in order to cancel this recommendation')), 
										_class='pci-EditButtons-centered'))
				

		
		
		else: ###NOTE: PRE-PRINT ARTICLE
			# During recommendation, no one is not allowed to see last (unclosed) recommendation 
			hideOngoingRecomm = (art.status=='Under consideration') and (iRecomm==nbRecomms)
			#  ... unless he/she is THE recommender
			if auth.has_membership(role='recommender') and (recomm.recommender_id==auth.user_id):
				hideOngoingRecomm = False
			# or a manager
			if auth.has_membership(role='manager'):
				hideOngoingRecomm = False
			
			# Check for reviews
			existOngoingReview = False
			myReviews = []
			reviews = db( (db.t_reviews.recommendation_id==recomm.id) & (db.t_reviews.review_state != 'Declined') ).select(orderby=db.t_reviews.id)
			for review in reviews:
				if review.review_state == 'Under consideration': 
					existOngoingReview = True
				
				# No one is allowd to see ongoing reviews
				hideOngoingReview = True
				if (review.reviewer_id == auth.user_id):
					# ...  except the reviewer himself ...
					hideOngoingReview = False
				if auth.has_membership(role='recommender') and (recomm.recommender_id==auth.user_id):
					# ... or he/she is THE recommender ...
					hideOngoingReview = False
				if auth.has_membership(role='manager'):
					# ... or a manager
					hideOngoingReview = False
				
				if not(hideOngoingReview):
					if (review.reviewer_id==auth.user_id) and (review.reviewer_id != recomm.recommender_id) and (art.status=='Under consideration') and (review.review_state=='Pending') and not(printable) and not(quiet):
						# reviewer's buttons in order to accept/decline pending review
						myReviews.append(DIV(
										A(SPAN(current.T('Yes, I agree to review this preprint'), _class='buttontext btn btn-success'), 
											_href=URL(c='user', f='accept_new_review',  vars=dict(reviewId=review.id), user_signature=True), _class='button'),
										A(SPAN(current.T('No thanks, I\'d rather not'), _class='buttontext btn btn-warning'), 
											_href=URL(c='user', f='decline_new_review', vars=dict(reviewId=review.id), user_signature=True), _class='button'),
										_class='pci-opinionform'
									))
					elif (review.review_state != 'Pending'): # review accepted or terminated
						# display the review
						if review.anonymously:
							myReviews.append(
								SPAN(I(current.T('Reviewed by')+' '+current.T('anonymous reviewer')+(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
							)
						else:
							reviewer = db(db.auth_user.id==review.reviewer_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
							myReviews.append(
								SPAN(I(current.T('Reviewed by')+' '+(reviewer.first_name or '')+' '+(reviewer.last_name or '')+(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
							)
						myReviews.append(BR())
						myReviews.append(DIV(WIKI(review.review or ''), _class='pci-bigtext margin'))
						# buttons allowing to edit and validate the review
						if (review.reviewer_id==auth.user_id) and (review.review_state == 'Under consideration') and (art.status == 'Under consideration') and not(printable) and not(quiet):
							# reviewer's buttons in order to edit/complete pending review
							myReviews.append(DIV(
												A(SPAN(current.T('Write or edit your review'), _class='buttontext btn btn-default'), _href=URL(c='user', f='edit_review', vars=dict(reviewId=review.id), user_signature=True)), 
												#A(SPAN(current.T('Review completed'), _class='buttontext btn btn-success'+(' disabled' if (review.review or '')=='' else '')), _href=URL(c='user', f='review_completed', vars=dict(reviewId=review.id), user_signature=True)), 
												_class='pci-EditButtons')
											)
			
			myContents.append(HR())
			if recomm.recommendation_state == 'Recommended':
				tit2 = current.T('Recommendation & reviews')
			else:
				tit2 = current.T('Decision & reviews')
				
			myContents.append( DIV(''
						,B(SPAN(recomm.recommendation_title))
						,BR()
						,SPAN(I(current.T('by ')+' '+(recommender.first_name or '')+' '+(recommender.last_name or '')+(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
						,BR()
						,SPAN(current.T('Manuscript:')+' ', mkDOI(recomm.doi)+BR()) if (recomm.doi) else SPAN('')
						,B(tit2)+BR()
						,(DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext margin') if (not(hideOngoingRecomm)) else '')
						,DIV(myReviews, _class='pci-bigtext margin') if len(myReviews) > 0 else ''
						, _class='pci-recommendation-div'
					)
				)
			
			if not(recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == 'Under consideration') and not(printable) and not (quiet):
				# recommender's button for recommendation edition
				myContents.append(DIV(A(SPAN(current.T('Write or edit your recommendation'), _class='buttontext btn btn-default'), 
										_href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recomm.id), user_signature=True)), 
									_class='pci-EditButtons'))

				# final opinion allowed if comments filled and no ongoing review
				if (len(recomm.recommendation_comments or '')>50) and not(existOngoingReview):# and len(reviews)>=2 :
					allowOpinion = recomm.id
				else:
					allowOpinion = -1
				
			
			if (recomm.reply is not None) and (len(recomm.reply) > 0):
				myContents.append(B(current.T('Author\'s Reply:'))+BR()+DIV(WIKI(recomm.reply or ''), _class='pci-bigtext'))
			
			if (art.user_id==auth.user_id or auth.has_membership(role='manager')) and (art.status=='Awaiting revision') and not(recomm.is_closed) and not(printable) and not (quiet):
				myContents.append(DIV(A(SPAN(current.T('Edit your reply to recommender'), 
											_class='buttontext btn btn-info'), 
											_href=URL(c='user', f='edit_reply', vars=dict(recommId=recomm.id), user_signature=True)),
										_class='pci-EditButtons'))
			
			
	myContents.append(HR())
	if (art.user_id==auth.user_id) and (art.status=='Awaiting revision') and not(printable) and not (quiet):
		# author's button enabling resubmission
		myContents.append(DIV(A(SPAN(current.T('Revision terminated: submit new version and close revision process'), _class='buttontext btn btn-success'), 
										_href=URL(c='user', f='article_revised', vars=dict(articleId=art.id), user_signature=True), 
										_title=current.T('Click here when the revision is terminated in order to submit the new version')), 
								_class='pci-EditButtons-centered'))
	
	if (art.user_id==auth.user_id) and not(art.already_published) and (art.status not in ('Cancelled', 'Rejected', 'Pre-recommended', 'Recommended')) and not(printable) and not (quiet):
		myContents.append(DIV(A(SPAN(current.T('I wish to cancel this recommendation request'), _class='buttontext btn btn-warning'), 
										_href=URL(c='user', f='do_cancel_article', vars=dict(articleId=art.id), user_signature=True), 
										_title=current.T('Click here in order to cancel this recommendation request')), 
								_class='pci-EditButtons-centered')) # author's button allowing cancellation
	
	if allowOpinion:
		if allowOpinion > 0:
			myContents.append( FORM(
				DIV(
					SPAN(INPUT(_name='recommender_opinion', _type='radio', _value='do_recommend'), current.T('I recommend this preprint'), _class='pci-radio pci-recommend btn-success'),
					SPAN(INPUT(_name='recommender_opinion', _type='radio', _value='do_revise'), current.T('This preprint worth a revision'), _class='pci-radio pci-review btn-default'),
					SPAN(INPUT(_name='recommender_opinion', _type='radio', _value='do_reject'), current.T('I reject this preprint'), _class='pci-radio pci-reject btn-warning'),
					_style="height:48px;"
				),
				INPUT(_value=current.T('submit'), _type='submit', _class='btn btn-info'),
				_class='pci-opinionform', keepvalues=True,
				_action=URL(c='recommender', f='process_opinion', vars=dict(recommId=allowOpinion), user_signature=True),
				_name='opinionForm'
			))
		else: # -1
			myContents.append(
				LABEL(current.T('All reviewers must have completed their reviews before you can take a decision (I recommend this preprint, This preprint worth a revision or I reject this preprint) on this preprint.')), 
			)
	if auth.has_membership(role='manager') and art.status == 'Pending' and not(printable) and not (quiet):
		myContents.append(DIV(	A(SPAN(current.T('Validate this request'), _class='buttontext btn btn-success'), 
										_href=URL(c='manager', f='do_validate_article', vars=dict(articleId=art.id), user_signature=True), 
										_title=current.T('Click here to validate this request and start recommendation process')),
								A(SPAN(current.T('Cancel this request'), _class='buttontext btn btn-warning'), 
										_href=URL(c='manager', f='do_cancel_article', vars=dict(articleId=art.id), user_signature=True), 
										_title=current.T('Click here in order to cancel this request')),
								_class='pci-EditButtons-centered'))
	if auth.has_membership(role='manager') and art.status == 'Pre-recommended' and not(printable) and not (quiet):
		myContents.append(DIV(	A(SPAN(current.T('Validate the recommendation of this article'), _class='buttontext btn btn-success'), 
										_href=URL(c='manager', f='do_recommend_article', vars=dict(articleId=art.id), user_signature=True), 
										_title=current.T('Click here to validate recommendation of this article')),
								_class='pci-EditButtons-centered'))
	return myContents



def mkLastRecommendation(auth, db, articleId):
	lastRecomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
	if lastRecomm:
		return lastRecomm.recommendation_title or ''
	else:
		return ''


def mkSuggestUserArticleToButton(auth, db, row, articleId):
	anchor = A(SPAN(current.T('Suggest as recommender'), _class='buttontext btn btn-default'), _href=URL(c='user', f='suggest_article_to', vars=dict(articleId=articleId, recommenderId=row['id']), user_signature=True), _class='button')
	return anchor



def mkSuggestReviewToButton(auth, db, row, recommId, myGoal):
	if myGoal == '4review':
		anchor = A(SPAN(current.T('Add'), _class='buttontext btn btn-default'), 
				_href=URL(c='recommender', f='suggest_review_to', vars=dict(recommId=recommId, reviewerId=row['id']), user_signature=True),
				_class='button')
	elif myGoal == '4press':
		anchor = A(SPAN(current.T('Suggest'), _class='buttontext btn btn-default'), 
				_href=URL(c='recommender', f='suggest_collaboration_to', vars=dict(recommId=recommId, reviewerId=row['id']), user_signature=True),
				_class='button')
	else:
		anchor = ''
	return anchor



def mkSuggestedRecommendersButton(auth, db, row):
	if row.status == 'Pending' or row.status == 'Awaiting consideration':
		return A(XML((db.v_suggested_recommenders[row.id]).suggested_recommenders.replace(', ', '<br>')), _href=URL(c='manager', f='suggested_recommenders', vars=dict(articleId=row.id)))
	else:
		return SPAN((db.v_article_recommender[row.id]).recommender)






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
		butts.append( A('['+current.T('Solicit a reviewer')+'] ', _href=URL(c='recommender', f='reviewers', vars=myVars, user_signature=True)) )
	return butts


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

def mkClosedRev(auth, db, row):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db( (db.t_reviews.recommendation_id == row.id) & (db.t_reviews.review_state == "Terminated") ).select()
	for rev in revs:
		if rev.reviewer_id:
			hrevs.append(LI(mkUserWithMail(auth, db, rev.reviewer_id)))
		else:
			hrevs.append(LI(I(current.T('not registered'))))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	return butts





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



def mkSollicitedPress(auth, db, row):
	butts = []
	hrevs = []
	#exclude = [str(auth.user_id)]
	art = db.t_articles[row.article_id]
	revs = db(db.t_press_reviews.recommendation_id == row.id).select()
	for rev in revs:
		if rev.contributor_id:
			hrevs.append(LI(mkUserWithMail(auth, db, rev.contributor_id)))
			#exclude.append(str(rev.contributor_id))
		else:
			hrevs.append(LI(I(current.T('not registered'))))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	if len(hrevs)>0:
		txt = '['+current.T('ADD / DELETE')+'] '
	else:
		txt = '['+current.T('ADD')+'] '
	if art.status == 'Under consideration':
		myVars = dict(recommId=row['id'])
		#if len(exclude)>0:
			#myVars['exclude'] = ','.join(exclude)
		butts.append( A(txt, _href=URL(c='recommender', f='add_contributor', vars=myVars, user_signature=True)) )
		#for thema in art['thematics']:
			#myVars['qy_'+thema] = 'on'
		#butts.append( A('['+current.T('+ADD')+'] ', _href=URL(c='recommender', f='search_reviewers', vars=myVars, user_signature=True)) )
	return butts


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



def mkRecommendation4ReviewFormat(auth, db, row):
	recomm = db(db.t_recommendations.id==row.recommendation_id).select(db.t_recommendations.id, db.t_recommendations.recommender_id).last()
	anchor = SPAN(mkUserWithMail(auth, db, recomm.recommender_id))
	return anchor


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


def mkUser(auth, db, userId, linked=False, scheme=False, host=False, port=False):
	if userId is not None:
		theUser = db(db.auth_user.id==userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
		return mkUser_U(auth, db, theUser, linked=linked, scheme=scheme, host=host, port=port)
	else:
		return ''

def mkUserId(auth, db, userId, linked=False, scheme=False, host=False, port=False):
	resu = SPAN('')
	if userId is not None:
		if linked:
			resu = A(str(userId), _href=URL(c='public', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=userId)))
		else:
			resu = SPAN(str(userId))
	return resu

def mkUser_U(auth, db, theUser, linked=False, scheme=False, host=False, port=False):
	if theUser:
		if linked:
			resu = A('%s %s' % (theUser.first_name, theUser.last_name), _href=URL(c='public', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=theUser.id)))
		else:
			resu = SPAN('%s %s' % (theUser.first_name, theUser.last_name))
	else:
		resu = SPAN('?')
	return resu


def mkUserWithAffil_U(auth, db, theUser, linked=False, scheme=False, host=False, port=False):
	if theUser:
		if linked:
			resu = SPAN(A('%s %s' % (theUser.first_name, theUser.last_name), _href=URL(c='public', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=theUser.id))), I(' -- %s, %s -- %s, %s' % (theUser.laboratory, theUser.institution, theUser.city, theUser.country)))
		else:
			resu = SPAN(SPAN('%s %s' % (theUser.first_name, theUser.last_name)), I(' -- %s, %s -- %s, %s' % (theUser.laboratory, theUser.institution, theUser.city, theUser.country)))
	else:
		resu = SPAN('?')
	return resu

def mkUserWithAffil(auth, db, userId, linked=False, scheme=False, host=False, port=False):
	resu = SPAN('')
	if userId is not None:
		theUser = db(db.auth_user.id==userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.laboratory, db.auth_user.institution, db.auth_user.city, db.auth_user.country, db.auth_user.email).last()
		mkUserWithAffil_U(auth, db, theUser, linked=linked, scheme=scheme, host=host, port=port)
	return resu


def mkUserWithMail(auth, db, userId, linked=False, scheme=False, host=False, port=False):
	resu = SPAN('')
	if userId is not None:
		theUser = db(db.auth_user.id==userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
		if theUser:
			if linked:
				resu = SPAN(A('%s %s' % (theUser.first_name, theUser.last_name), _href=URL(c='public', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=userId))), A(' [%s]' % theUser.email, _href='mailto:%s' % theUser.email))
			else:
				resu = SPAN(SPAN('%s %s' % (theUser.first_name, theUser.last_name)), A(' [%s]' % theUser.email, _href='mailto:%s' % theUser.email))
		else:
			resu = SPAN('?')
	return resu



def mkLastChange(t):
	if t:
		d = datetime.datetime.now() - t
		if d.days==0:
			return SPAN(current.T('Today'))
		elif d.days==1:
			return SPAN(current.T('Yesterday'))
		else:
			return SPAN(current.T('%s days ago') % d.days)
	else:
		return ''


def mkElapsed(t):
	if t:
		d = datetime.datetime.now() - t
		if d.days<2:
			return SPAN(current.T('%s day') % d.days)
		else:
			return SPAN(current.T('%s days') % d.days)
	else:
		return ''


def mkDuration(t0, t1):
	if t0 and t1:
		d = t1 - t0
		if d.days<2:
			return SPAN(current.T('%s day') % d.days)
		else:
			return SPAN(current.T('%s days') % d.days)
	else:
		return ''




def mkUserRow(auth, db, userRow, withPicture=False, withMail=False, withRoles=False):
	resu = []
	if withPicture:
		if (userRow.uploaded_picture is not None and userRow.uploaded_picture != ''):
			img = IMG(_src=URL('default', 'download', args=userRow.uploaded_picture), _class='pci-userPicture', _style='float:left;')
		else:
			img = IMG(_src=URL(c='static',f='images/default_user.png'), _class='pci-userPicture', _style='float:left;')
		resu.append(TD(img))
	name = ''
	if (userRow.first_name or '') != '':
		name += userRow.first_name
	if (userRow.last_name or '') != '':
		if name != '': name += ' '
		name += userRow.last_name.upper()
	resu.append(TD(A(name, _href=URL(c='public', f='viewUserCard', vars=dict(userId=userRow.id)))))
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




def mkUserCard(auth, db, userId, withMail=False):
	user  = db.auth_user[userId]
	name  = LI(B( (user.last_name or '').upper(), ' ', (user.first_name or '') ))
	nameTitle  = (user.last_name or '').upper(), ' ', (user.first_name or '')
	addr  = LI(I( (user.laboratory or ''), ', ', (user.institution or ''), ', ', (user.city or ''), ', ', (user.country or '') ))
	thema = LI(', '.join(user.thematics))
	mail  = LI(A(' [%s]' % user.email, _href='mailto:%s' % user.email) if withMail else '')
	if (user.uploaded_picture is not None and user.uploaded_picture != ''):
		img = IMG(_src=URL('default', 'download', args=user.uploaded_picture), _class='pci-userPicture', _style='float:left;')
	else:
		img = IMG(_src=URL(c='static',f='images/default_user.png'), _class='pci-userPicture', _style='float:left;')
	if (user.cv or '') != '':
		cv = DIV(WIKI(user.cv or ''), _class='pci-bigtext margin', _style='border: 1px solid #f0f0f0;')
	else:
		cv = ''
	rolesQy = db( (db.auth_membership.user_id==userId) & (db.auth_membership.group_id==db.auth_group.id) ).select(db.auth_group.role)
	rolesList = []
	for roleRow in rolesQy:
		rolesList.append(roleRow.role)
	roles = LI(B(', '.join(rolesList)))
	# recommendations
	recomms = []
	recommsQy = db( 
				(
					(db.t_recommendations.recommender_id == userId) | ( (db.t_recommendations.id == db.t_press_reviews.recommendation_id) & (db.t_press_reviews.contributor_id == userId) )
				)
				& (db.t_recommendations.recommendation_state == 'Recommended')
				& (db.t_recommendations.article_id == db.t_articles.id)
				& (db.t_articles.status == 'Recommended')
			).select(db.t_articles.ALL, distinct=True, orderby=~db.t_articles.last_status_change)
	nbRecomms = len(recommsQy)
	for row in recommsQy:
		recomms.append(mkRecommArticleRow(auth, db, row, withImg=True, withScore=False, withDate=True, fullURL=False))
	# reviews
	reviews = []
	reviewsQy = db(
				(db.t_reviews.reviewer_id == userId)
				& ~(db.t_reviews.anonymously == True)
				& (db.t_reviews.recommendation_id == db.t_recommendations.id)
				#& (db.t_recommendations.recommendation_state == 'Recommended')
				& (db.t_recommendations.article_id == db.t_articles.id)
				& (db.t_articles.status == 'Recommended')
			).select(db.t_articles.ALL, distinct=True, orderby=~db.t_articles.last_status_change)
	nbReviews = len(reviewsQy)
	for row in reviewsQy:
		reviews.append(mkRecommArticleRow(auth, db, row, withImg=True, withScore=False, withDate=True, fullURL=False))
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
				TABLE(recomms, _class='pci-lastArticles-table'), 
				H2(current.T('%s %%{review}', symbols=nbReviews)),
				TABLE(reviews,_class='pci-lastArticles-table'), 
			),
			#_style='margin-top:20px; margin-left:auto; margin-right:auto; max-width:60%;',
			)
	return resu



def do_suggest_article_to(auth, db, articleId, recommenderId):
	db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)




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



def makeArticleThumbnail(auth, db, articleId, size=(150,150)):
	art = db(db.t_articles.id==articleId).select().last()
	if art.picture_data:
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


def getRecommender(auth, db, row):
	recomm = db( db.t_recommendations.article_id == row.id ).select(db.t_recommendations.recommender_id, orderby=db.t_recommendations.id).last()
	if recomm and recomm.recommender_id:
		return mkUser(auth, db, recomm.recommender_id)
	else:
		return ''


