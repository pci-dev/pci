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

statusArticles = dict()
def mkStatusArticles(db):
	statusArticles.clear()
	for sa in db(db.t_status_article).select():
		statusArticles[sa['status']] = sa



# Builds the right-panel for home page
def mkPanel(myconf, auth):
	panel = [
				LI(A(current.T("About")+" "+myconf.take('app.name'), _href=URL('about', 'about')), _class="list-group-item"),
				LI(A('PCi '+current.T("FAQ"), _href='https://peercommunityin.org/faq/'), _class="list-group-item"),
			]
	if auth.user_id is not None:
		panel.append(LI(A(current.T("Request a recommendation"), _href=URL('user', 'my_articles', args=['new', 't_articles'], user_signature=True)), _class="list-group-item"))
	else:
		panel.append(LI(A(current.T("Log in before requesting a recommendation"), _href=URL('default', 'user')), _class="list-group-item"))
	if auth.has_membership('recommender'):
		panel.append(LI(A(current.T("Initiate a recommendation"), _href=URL('recommender', 'direct_submission', args=['new', 't_articles'], user_signature=True)), _class="list-group-item"))
	return DIV(UL( panel, _class="list-group"), _class="panel panel-info")



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
def mkSearchForm(auth, db, myVars):
	# number of columns of thematic fields
	nCol = 5
	# count requested thematic fields
	if myVars is None:
		myVars = dict()
	ntf = 0
	for myVar in myVars:
		if (match('^qy_', myVar)):
		  ntf += 1
	if ntf == 0: 
		# if none requested, use user's thematic fields by default
		if auth.user_id is not None:
			myProfiles = db(db.auth_user._id == auth.user_id).select()
			for myProfile in myProfiles:
				for thema in myProfile.thematics:
					myVars['qy_'+thema] = 'on'
					ntf += 1
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
	
	# process searched words
	kwVal = None
	if 'qyKeywords' in myVars:
		kwVal = myVars['qyKeywords']
		if isinstance(kwVal, list):
			kwVal = kwVal[1]

	# build form
	form = FORM(
				LABEL(current.T('Search for')),INPUT(_name='qyKeywords', keepvalues=True, _class='searchField', value=kwVal), 
				INPUT(_type='submit', _value=current.T('Search')),
				BR(),
				LABEL(current.T('in thematic fields:')), 
				DIV(
					TABLE(tab, _class='pci-thematicFieldsTable'),
					SPAN(
						A(SPAN(current.T('Check all thematic fields'), _class='buttontext btn btn-default'), _onclick="jQuery('input[type=checkbox]').each(function(k){if (this.name.match('^qy_')) {jQuery(this).prop('checked', true);} });", _class="pci-flushright"),
						A(SPAN(current.T('Toggle thematic fields'), _class='buttontext btn btn-default'), _onclick="jQuery('input[type=checkbox]').each(function(k){if (this.name.match('^qy_')) {jQuery(this).prop('checked', !jQuery(this).prop('checked'));} });", _class="pci-flushright"),
					),
					_class="pci-thematicFieldsDiv"),
				_class='searchForm',
				_name='searchForm',
			)
	return form



# Builds a html representation of an article
def mkRepresentArticle(auth, db, articleId):
	resu = ''
	if articleId:
		art = db.t_articles[articleId]
		if art is not None:
			submitter = ''
			sub_repr = ''
			if art.user_id is not None:
				submitter = db.auth_user[art.user_id]
				sub_repr = '%s %s' % (submitter.first_name, submitter.last_name)
			resu = DIV(
						SPAN(I(current.T('Submitted by')+' %s, %s' % (sub_repr, art.upload_timestamp.strftime('%Y-%m-%d %H:%M') if art.upload_timestamp else '')))
						,H4(art.authors)
						,H3(art.title)
						,SPAN(art.article_source)+BR() if art.article_source else ''
						,mkDOI(art.doi)+BR() if art.doi else ''
						,SPAN(I(current.T('Keywords:')+' '))+I(art.keywords or '') if art.keywords else ''
						,BR()+B(current.T('Abstract'))+BR()+DIV(WIKI(art.abstract or ''), _class='pci-bigtext') if art.abstract else ''
						, _class='pci-article-div'
					)
	return resu

# Builds a nice representation of an article
def mkArticleCell(auth, db, art):
	anchor = ''
	if art:
		anchor = DIV(
					B(art.title),
					BR(),
					SPAN(art.authors),
					BR(),
					mkDOI(art.doi),
					#BR(),
					#SPAN(I(current.T('Keywords:')+' '))+I(art.keywords or ''),
					(BR()+SPAN(art.article_source) if art.article_source else '')
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



def mkViewArticle4ReviewButton(auth, db, row):
	anchor = ''
	recomm = db.t_recommendations[row.recommendation_id]
	if recomm:
		art = db.t_articles[recomm.article_id]
		if art:
			anchor = DIV(
						#A(art.title, _href=URL(c='default', f='under_review_one_article', args=[recomm.article_id], user_signature=True)),
						B(art.title),
						BR(),
						#B(current.T('Authors:')+' '), 
						SPAN(art.authors),
						BR(),
						#B(current.T('Submitted on:')+' '), SPAN(art.upload_timestamp),
						mkDOI(art.doi),
					)
	return anchor



# Builds a search button for recommenders matching keywords
def mkSearchRecommendersButton(auth, db, row):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	anchor = ''
	if row['status'] == 'Awaiting consideration' or row['status'] == 'Pending':
		myVars = dict(articleId=row['id'])
		for thema in row['thematics']:
			myVars['qy_'+thema] = 'on'
		myVars['qyKeywords'] = ' '.join(row['thematics'])
		anchor = A(SPAN('+ '+current.T('Suggest'),BR(),current.T('recommenders'), _class='buttontext btn btn-default'), _href=URL(c='manage', f='search_recommenders', vars=myVars, user_signature=True), _class='button')
	return anchor



# Builds a search button for recommenders matching keywords
def mkSearchRecommendersUserButton(auth, db, row):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	anchor = ''
	if row['status'] == 'Awaiting consideration' or row['status'] == 'Pending':
		myVars = dict(articleId=row['id'])
		for thema in row['thematics']:
			myVars['qy_'+thema] = 'on'
		myVars['qyKeywords'] = ' '.join(row['thematics'])
		anchor = A(SPAN('+ '+current.T('Suggest'),BR(),current.T('recommenders'), _class='buttontext btn btn-default'), _href=URL(c='user', f='search_recommenders', vars=myVars, user_signature=True), _class='button')
	return anchor



# Builds a search button for reviewers matching keywords
def mkSearchReviewersButton(auth, db, row):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	anchor = ''
	article = db.t_articles[row['article_id']]
	if article and article['status'] == 'Under consideration':
		myVars = dict(recommendationId=row['id'])
		for thema in article['thematics']:
			myVars['qy_'+thema] = 'on'
		myVars['qyKeywords'] = ' '.join(article['thematics'])
		if row['is_press_review'] and row['auto_nb_agreements']==0:
			myVars['4press'] = 'on'
			anchor = A(SPAN('+ '+current.T('Add'),BR(),current.T('contributors'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='search_reviewers', vars=myVars, user_signature=True), _class='button')
		elif row['is_press_review'] is False:
			myVars['4review'] = 'on'
			anchor = A(SPAN('+ '+current.T('Add'),BR(),current.T('reviewers'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='search_reviewers', vars=myVars, user_signature=True), _class='button')
	return anchor



# Builds an article status button from a recommendation row
def mkRecommStatusButton(auth, db, row):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	anchor = ''
	status = ''
	status_txt = ''
	color_class = 'btn-default'
	hint = ''
	article = db.t_articles[row.article_id]
	if article:
		status = article['status']
		if status:
			status_txt = current.T(status)
			if (row.is_closed and not(row.is_press_review)):
				color_class = 'btn-default'
			else:
				color_class = statusArticles[status]['color_class'] or 'btn-default'
			hint = statusArticles[status]['explaination'] or ''
	anchor = A(SPAN(status_txt, _class='buttontext btn pci-button '+color_class), _href=URL(c='default', f='under_consideration_one_article', args=[row.article_id], user_signature=True), _class='button', _title=current.T(hint))
	return anchor



# Builds an article status button from a recommendation row
def mkReviewerArticleStatusButton(auth, db, row):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	anchor = ''
	status = ''
	status_txt = ''
	color_class = 'btn-default'
	hint = ''
	article = db.t_articles[row.article_id]
	if article:
		status = article['status']
		if status:
			status_txt = current.T(status)
			if (row.is_closed and not(row.is_press_review)):
				color_class = 'btn-default'
			else:
				color_class = statusArticles[status]['color_class'] or 'btn-default'
			hint = statusArticles[status]['explaination'] or ''
	anchor = A(SPAN(status_txt, _class='buttontext btn pci-button '+color_class), _href=URL(c='default', f='under_consideration_one_article', args=[article.id], user_signature=True), _class='button', _title=current.T(hint))
	return anchor



# Builds a status button which allow to open recommendations only when recommended and recommendations exists
def mkStatusButton(auth, db, row):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	anchor = ''
	articleId = row['id']
	status_txt = '%s (n=%s)' % (current.T(row['status']).replace('-', '- '), row['auto_nb_recommendations'])
	color_class = statusArticles[row['status']]['color_class'] or 'btn-default'
	hint = statusArticles[row['status']]['explaination'] or ''
	if (row['auto_nb_recommendations'] > 0):
		anchor = A(SPAN(status_txt, _class='buttontext btn pci-button '+color_class), _target="_blank", _href=URL(c='public', f='recommendations', vars=dict(articleId=articleId), user_signature=True), _class='button', _title=current.T(hint))
	else:
		anchor = SPAN(status_txt, _class='buttontext btn fake-btn pci-button '+color_class, _title=current.T(hint))
	return anchor



# Builds a status button which allow to open recommendations only when submitter is user
def mkUserStatusButton(auth, db, row):
	if row is None:
		return ''
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	anchor = ''
	articleId = row['id']
	status_txt = '%s (n=%s)' % (current.T(row['status']).replace('-', '- '), row['auto_nb_recommendations'])
	color_class = statusArticles[row['status']]['color_class'] or 'btn-default'
	hint = statusArticles[row['status']]['explaination'] or ''
	if (row['auto_nb_recommendations'] > 0):
		anchor = A(SPAN(status_txt, _class='buttontext btn pci-button '+color_class), _target="_blank", _href=URL(c='user', f='recommendations', vars=dict(articleId=articleId), user_signature=True), _class='button', _title=current.T(hint))
	else:
		anchor = SPAN(status_txt, _class='buttontext btn fake-btn pci-button '+color_class, _title=current.T(hint))
	return anchor



# Builds a status button which allow to open recommendations only when submitter is user
def mkRecommenderStatusButton(auth, db, row):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	anchor = ''
	articleId = row['id']
	status_txt = '%s (n=%s)' % (current.T(row['status']).replace('-', '- '), row['auto_nb_recommendations'])
	color_class = statusArticles[row['status']]['color_class'] or 'btn-default'
	hint = statusArticles[row['status']]['explaination'] or ''
	if (row['auto_nb_recommendations'] > 0):
		anchor = A(SPAN(status_txt, _class='buttontext btn pci-button '+color_class), _target="_blank", _href=URL(c='recommender', f='recommendations', vars=dict(articleId=articleId), user_signature=True), _class='button', _title=current.T(hint))
	else:
		anchor = SPAN(status_txt, _class='buttontext btn fake-btn pci-button '+color_class, _title=current.T(hint))
	return anchor



# Builds a status button always clickable, with number of recommendations
def mkManagerStatusButton(auth, db, row):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	anchor = ''
	articleId = row['id']
	status_txt = '%s (n=%s)' % (current.T(row['status']).replace('-', '- '), row['auto_nb_recommendations'])
	color_class = statusArticles[row['status']]['color_class'] or 'btn-default'
	hint = statusArticles[row['status']]['explaination'] or ''
	anchor = A(SPAN(status_txt, _class='buttontext btn pci-button '+color_class), _href=URL(c='manage', f='manage_recommendations', vars=dict(article=articleId), user_signature=True), _class='button', _title=current.T(hint))
	return anchor



def mkViewArticle4Recommendation(auth, db, row):
	if 't_recommendations' in row:
		recomm = row.t_recommendations
	else:
		recomm = row
	anchor = ''
	art = db.t_articles[recomm.article_id]
	if art:
		anchor = DIV(
					A(art.title, _href=URL(c='default', f='under_consideration_one_article', args=[recomm.article_id], user_signature=True)),
						BR(),
						B(art.authors),
						BR(),
						mkDOI(art.doi),
				)
	return anchor



def mkBackButton(target=None):
	if target:
		return A(SPAN(current.T('Back'), _class='buttontext btn btn-default'), _href=target, _class='button')
	else:
		return A(SPAN(current.T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')




def mkRecommendedArticle(auth, db, art, printable, with_comments=False):
	submitter = db.auth_user[art.user_id]
	myContents = DIV(
					SPAN(I(current.T('Submitted by %s %s, %s') % (submitter.first_name, submitter.last_name, art.upload_timestamp.strftime('%Y-%m-%d %H:%M') if art.upload_timestamp else '')) if submitter else '')
					,H4(art.authors)
					,H3(art.title)
					,(mkDOI(art.doi)+BR()) if (art.doi) else SPAN('')
					,SPAN(art.article_source if art.article_source else '')
					,SPAN(I(current.T('Keywords:')+' '+art.keywords)+BR() if art.keywords else '')
					,B(current.T('Abstract'))+BR()
					,DIV(WIKI(art.abstract or ''), _class='pci-bigtext')
					, _class=('pci-article-div-printable' if printable else 'pci-article-div')
				)
	recomms = db(db.t_recommendations.article_id == art.id).select(orderby=db.t_recommendations.last_change)
	for recomm in recomms:
		recommender = db.auth_user[recomm.recommender_id]
		if recomm.is_press_review:
			contributors = db.v_recommendation_contributors[recomm.id]
			myContents.append(
				DIV( HR()
					,SPAN(I('%s %s %s, %s with %s' % current.T('Recommendation by'), recommender.first_name, recommender.last_name, (recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else ''), contributors))
					,BR()
					,SPAN(current.T('Manuscript doi:')+' ', mkDOI(recomm.doi)+BR()) if (recomm.doi) else SPAN('')
					,B(current.T('Recommendation'))+BR()
					,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext margin')
					, _class='pci-recommendation-div'
				)
			)
		else:
			myReviews = []
			reviews = db(db.t_reviews.recommendation_id == recomm.id).select(orderby=db.t_reviews.last_change)
			for review in reviews:
				if review.anonymously:
					myReviews.append(
						SPAN(I('%s %s, %s' % (current.T('Reviewed by'), current.T('anonymous reviewer'), recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
					)
				else:
					reviewer = db.auth_user[recomm.recommender_id]
					myReviews.append(
						SPAN(I('%s %s %s, %s' % (current.T('Reviewed by'), reviewer.first_name, reviewer.last_name, recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
					)
				myReviews.append(BR())
				myReviews.append(DIV(WIKI(review.review or ''), _class='pci-bigtext margin'))
			myContents.append(
				DIV( HR()
					,SPAN(I('%s %s %s, %s' % (current.T('Recommendation by'), recommender.first_name, recommender.last_name, (recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else ''))))
					,BR()
					,SPAN(current.T('Manuscript doi:')+' ', mkDOI(recomm.doi)+BR()) if (recomm.doi) else SPAN('')
					,B(current.T('Recommendation & Reviews'))+BR()
					,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext margin')
					,DIV(myReviews, _class='pci-bigtext margin') if len(myReviews)>0 else ''
					, _class='pci-recommendation-div'
				)
			)
			if recomm.reply is not None and len(recomm.reply) > 0:
				myContents.append(B(current.T('Reply:'))+BR()+DIV(WIKI(recomm.reply or ''), _class='pci-bigtext'))
	if with_comments:
		#TODO: Add comments (optionnal)
		pass
	return myContents




def mkSuggestArticleToButton(auth, db, row, articleId):
	anchor = A(SPAN(current.T('Suggest'), _class='buttontext btn btn-default'), _href=URL(c='manage', f='suggest_article_to', vars=dict(articleId=articleId, recommenderId=row['id']), user_signature=True), _class='button')
	return anchor

def mkSuggestUserArticleToButton(auth, db, row, articleId):
	anchor = A(SPAN(current.T('Suggest'), _class='buttontext btn btn-default'), _href=URL(c='user', f='suggest_article_to', vars=dict(articleId=articleId, recommenderId=row['id']), user_signature=True), _class='button')
	return anchor

def mkSuggestReviewToButton(auth, db, row, recommendationId, myGoal):
	anchor = A(SPAN(current.T('Suggest'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='suggest_review_to', vars=dict(recommendationId=recommendationId, reviewerId=row['id'], myGoal=myGoal), user_signature=True), _class='button')
	return anchor



def mkSuggestedRecommendersButton(auth, db, row):
	if row.status == 'Pending' or row.status == 'Awaiting consideration':
		return A((db.v_suggested_recommenders[row.id]).suggested_recommenders, _href=URL(c='manage', f='suggested_recommenders', vars=dict(articleId=row.id)))
	else:
		return SPAN((db.v_article_recommender[row.id]).recommender)



def mkSuggestedRecommendersUserButton(auth, db, row):
	if row.status == 'Pending':
		return A((db.v_suggested_recommenders[row.id]).suggested_recommenders, _href=URL(c='user', f='suggested_recommenders', vars=dict(articleId=row.id)))
	elif row.status == 'Awaiting consideration':
		return SPAN((db.v_suggested_recommenders[row.id]).suggested_recommenders)
	else:
		return SPAN((db.v_article_recommender[row.id]).recommender)



def mkSuggestedReviewersRecommButton(auth, db, row):
	art = db.t_articles[row.article_id]
	if art.status == 'Under consideration':
		return A((db.v_reviewers[row.id]).reviewers, _href=URL(c='recommender', f='reviews', vars=dict(recommendationId=row.id)))
	else:
		return SPAN((db.v_reviewers[row.id]).reviewers)


def mkRecommReviewsButton(auth, db, row):
	if row.is_press_review:
		contrib = db(db.v_recommendation_contributors.id == row.id).select().first()
		txt = contrib.contributors
		return A(txt, _href=URL(c='recommender', f='contributions', vars=dict(recommendationId=row.id), user_signature=True))
	else:
		reviews = db(db.v_reviewers_named.id == row.id).select().first()
		txt = reviews.reviewers
		#nbRev = db(db.t_reviews.recommendation_id == row.id).count()
		#if nbRev < 2:
		#	txt = current.T('%s review') % nbRev
		#else:
		#	txt = current.T('%s reviews') % nbRev
		#return A(SPAN(txt, _class='buttontext btn btn-default'), _href=URL(c='recommender', f='reviews', vars=dict(recommendationId=row.id), user_signature=True), _class='button')
		return A(txt, _href=URL(c='recommender', f='reviews', vars=dict(recommendationId=row.id), user_signature=True))


def mkRecommendationFormat(auth, db, row):
	recommender = db.auth_user[row.recommender_id]
	art = db.t_articles[row.article_id]
	anchor = SPAN(  art.title, 
					BR(),
					B(current.T('Recommender:')+' '), SPAN('%s %s' % (recommender.first_name, recommender.last_name)),
					BR(),
					B(current.T('DOI:')+' '), mkDOI(row.doi),
					BR(),
					B(current.T('Started on:')+' '), row.recommendation_timestamp
				)
	return anchor



def mkRecommendation4ReviewFormat(auth, db, row):
	recomm = db.t_recommendations[row.recommendation_id]
	anchor = SPAN(  SPAN(mkUserWithMail(auth, db, recomm.recommender_id)),
					#BR(),
					#mkDOI(recomm.doi),
					#BR(),
					#I(current.T('Started %s days ago') % relativedelta(datetime.datetime.now(), recomm.recommendation_timestamp).days)
				)
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


def mkUser(auth, db, userId):
	resu = SPAN('')
	if userId is not None:
		theUser = db.auth_user[userId]
		if theUser:
			resu = SPAN('%s %s' % (theUser.first_name, theUser.last_name))
	return resu

def mkUserWithMail(auth, db, userId):
	resu = SPAN('')
	if userId is not None:
		theUser = db.auth_user[userId]
		if theUser:
			resu = SPAN(SPAN('%s %s' % (theUser.first_name, theUser.last_name)), A(' [%s]' % theUser.email, _href='mailto:%s' % theUser.email))
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
	#d = relativedelta(datetime.datetime.now(), t)
	#if d.years==0 and d.months==0 and d.days==0:
		#return SPAN(current.T('Today'))
	#elif d.years==0 and d.months==0 and d.days==1:
		#return SPAN(current.T('Yesterday'))
	#elif d.years==0 and d.months==0:
		#return SPAN(current.T('%s days ago') % d.days)
	#elif d.years==0 and d.months==1:
		#return SPAN(current.T('%s month and %s days ago') % (d.months, d.days))
	#elif d.years==0 and d.months>1:
		#return SPAN(current.T('%s months and %s days ago') % (d.months, d.days))
	#elif d.years==1 and d.months>1:
		#return SPAN(current.T('%s year, %s months and %s days ago') % (d.years, d.months, d.days))
	#else:
		#return SPAN(current.T('%s years, %s months and %s days ago') % (d.years, d.months, d.days))


def mkElapsed(t):
	if t:
		d = datetime.datetime.now() - t
		if d.days<2:
			return SPAN(current.T('%s day') % d.days)
		else:
			return SPAN(current.T('%s days') % d.days)
	else:
		return ''
	#d = relativedelta(datetime.datetime.now(), t)
	#if d.days < 2:
		#return SPAN(current.T('%s day') % d.days)
	#else:
		#return SPAN(current.T('%s days') % d.days)


def mkDuration(t0, t1):
	if t0 and t1:
		d = t1 - t0
		if d.days<2:
			return SPAN(current.T('%s day') % d.days)
		else:
			return SPAN(current.T('%s days') % d.days)
	else:
		return ''

