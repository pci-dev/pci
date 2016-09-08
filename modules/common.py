# -*- coding: utf-8 -*-

from re import sub, match
from copy import deepcopy
from gluon import current
from gluon.tools import Auth
from gluon.html import *
from gluon.contrib.markdown import WIKI


statusArticles = dict()


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
					A(SPAN(current.T('Check all thematic fields'), _class='buttontext btn btn-default'), _onclick="jQuery('input[type=checkbox]').each(function(k){if (this.name.match('^qy_')) {jQuery(this).prop('checked', true);} });", _class="pci-flushright"),
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
			if art.user_id is not None:
				submitter = db.auth_user[art.user_id]
			resu = DIV(
						SPAN(I(current.T('Submitted by')+' %s %s %s, %s' % (submitter.user_title, submitter.first_name, submitter.last_name, art.upload_timestamp.strftime('%Y-%m-%d %H:%M') if art.upload_timestamp else '')))
						,H4(art.authors)
						,H3(art.title)
						,A(art.doi, _href="http://dx.doi.org/"+sub(r'doi: *', '', art.doi), _class="doi_url", _target="_blank")+BR() if (art.doi) else SPAN('')
						,SPAN(I(current.T('Keywords:')+' '))+I(art.keywords or '')
						,BR()+B(current.T('Abstract'))+BR()
						,DIV(WIKI(art.abstract), _class='pci-bigtext')
						, _class='pci-article-div'
					)
	return resu



# Builds a search button for recommenders matching keywords
def mkSearchRecommendersButton(auth, db, row):
	anchor = ''
	if row['status'] == 'Awaiting consideration' or row['status'] == 'Pending':
		myVars = dict(articleId=row['id'])
		for thema in row['thematics']:
			myVars['qy_'+thema] = 'on'
		myVars['qyKeywords'] = ' '.join(row['thematics'])
		anchor = A(SPAN(current.T('Who?'), _class='buttontext btn btn-default'), _href=URL(c='manage', f='search_recommenders', vars=myVars, user_signature=True), _class='button')
	return anchor



# Builds a search button for recommenders matching keywords
def mkSearchRecommendersUserButton(auth, db, row):
	anchor = ''
	if row['status'] == 'Awaiting consideration' or row['status'] == 'Pending':
		myVars = dict(articleId=row['id'])
		for thema in row['thematics']:
			myVars['qy_'+thema] = 'on'
		myVars['qyKeywords'] = ' '.join(row['thematics'])
		anchor = A(SPAN(current.T('Who?'), _class='buttontext btn btn-default'), _href=URL(c='user', f='search_recommenders', vars=myVars, user_signature=True), _class='button')
	return anchor



# Builds a search button for reviewers matching keywords
def mkSearchReviewersButton(auth, db, row):
	anchor = ''
	article = db.t_articles[row['article_id']]
	if article['status'] == 'Under consideration':
		myVars = dict(recommendationId=row['id'])
		for thema in article['thematics']:
			myVars['qy_'+thema] = 'on'
		myVars['qyKeywords'] = ' '.join(article['thematics'])
		anchor = A(SPAN(current.T('Who?'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='search_reviewers', vars=myVars, user_signature=True), _class='button')
	return anchor



# Builds an article status button from a recommendation row
def mkRecommStatusButton(auth, db, row):
	if len(statusArticles) == 0:
		print 'statusArticles...'
		for sa in db(db.t_status_article).select():
			statusArticles[sa['status']] = sa
	anchor = ''
	article = db.t_articles[row.article_id]
	status_txt = current.T(article['status']).replace('-', '- ')
	color_class = statusArticles[article['status']]['color_class'] or 'btn-default'
	hint = statusArticles[article['status']]['explaination'] or ''
	anchor = A(SPAN(status_txt, _class='buttontext btn pci-button '+color_class), _href=URL(c='default', f='under_consideration_one_article', args=[row.article_id], user_signature=True), _class='button', _title=current.T(hint))
	return anchor



# Builds a status button which allow to open recommendations only when recommended and recommendations exists
def mkStatusButton(auth, db, row):
	if len(statusArticles) == 0:
		print 'statusArticles...'
		for sa in db(db.t_status_article).select():
			statusArticles[sa['status']] = sa
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
	if len(statusArticles) == 0:
		print 'statusArticles...'
		for sa in db(db.t_status_article).select():
			statusArticles[sa['status']] = sa
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
	if len(statusArticles) == 0:
		print 'statusArticles...'
		for sa in db(db.t_status_article).select():
			statusArticles[sa['status']] = sa
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
	if len(statusArticles) == 0:
		print 'statusArticles...'
		for sa in db(db.t_status_article).select():
			statusArticles[sa['status']] = sa
	anchor = ''
	articleId = row['id']
	status_txt = '%s (n=%s)' % (current.T(row['status']).replace('-', '- '), row['auto_nb_recommendations'])
	color_class = statusArticles[row['status']]['color_class'] or 'btn-default'
	hint = statusArticles[row['status']]['explaination'] or ''
	anchor = A(SPAN(status_txt, _class='buttontext btn pci-button '+color_class), _href=URL(c='manage', f='manage_recommendations', vars=dict(article=articleId), user_signature=True), _class='button', _title=current.T(hint))
	return anchor



def mkViewArticle4ReviewButton(auth, db, row):
	anchor = ''
	recomm = db.t_recommendations[row.recommendation_id]
	if recomm:
		art = db.t_articles[recomm.article_id]
		if art:
			anchor = DIV(
						A(art.title, _href=URL(c='default', f='under_review_one_article', args=[recomm.article_id], user_signature=True)),
						BR(),
						B(current.T('Authors:')+' '), SPAN(art.authors)
					)
	return anchor



def mkViewArticle4RecommendationButton(auth, db, row):
	anchor = ''
	art = db.t_articles[row.article_id]
	if art:
		anchor = DIV(
					A(art.title, _href=URL(c='default', f='under_consideration_one_article', args=[row.article_id], user_signature=True)),
						BR(),
						B(current.T('Authors:')+' '), SPAN(art.authors)
				)
	return anchor



def mkBackButton():
	return A(SPAN(current.T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')




def mkRecommendedArticle(auth, db, art, printable, with_comments=False):
	submitter = db.auth_user[art.user_id]
	myContents = DIV(
					SPAN(I(current.T('Submitted by %s %s %s, %s') % (submitter.user_title, submitter.first_name, submitter.last_name, art.upload_timestamp.strftime('%Y-%m-%d %H:%M') if art.upload_timestamp else '')))
					,H4(art.authors)
					,H3(art.title)
					,(mkDOI(art.doi)+BR()) if (art.doi) else SPAN('')
					,SPAN(I(current.T('Keywords:')+' '))+I(art.keywords or '')
					,BR()+B(current.T('Abstract'))+BR()
					,DIV(WIKI(art.abstract), _class='pci-bigtext')
					, _class=('pci-article-div-printable' if printable else 'pci-article-div')
				)
	
	recomms = db(db.t_recommendations.article_id == art.id).select(orderby=db.t_recommendations.last_change)
	for recomm in recomms:
		recommender = db.auth_user[recomm.recommender_id]
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
					SPAN(I('%s %s %s %s, %s' % (current.T('Reviewed by'), reviewer.user_title, reviewer.first_name, reviewer.last_name, recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
				)
			myReviews.append(BR())
			myReviews.append(DIV(WIKI(review.review or ''), _class='pci-bigtext margin'))
		myContents.append(
			DIV( HR()
				,SPAN(I('%s %s %s %s, %s' % (current.T('Recommendation by'), recommender.user_title, recommender.first_name, recommender.last_name, recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
				,BR()
				,SPAN(current.T('Manuscript doi:')+' ', mkDOI(recomm.doi)+BR()) if (recomm.doi) else SPAN('')
				,B(current.T('Recommendation & Reviews'))+BR()
				,DIV(WIKI(recomm.recommendation_comments or ''), _class='pci-bigtext margin')
				,DIV(myReviews, _class='pci-bigtext margin') if len(myReviews)>0 else ''
				, _class='pci-recommendation-div'
			)
		)
		if recomm.reply is not None and len(recomm.reply) > 0:
			myContents.append(B(current.T('Reply:'))+BR()
							,DIV(WIKI(art.recomm.reply), _class='pci-bigtext'))
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

def mkSuggestReviewToButton(auth, db, row, recommendationId):
	anchor = A(SPAN(current.T('Suggest'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='suggest_review_to', vars=dict(recommendationId=recommendationId, reviewerId=row['id']), user_signature=True), _class='button')
	return anchor



def mkSuggestedRecommendersUserButton(auth, db, row):
	if row.status == 'Pending':
		return A((db.v_suggested_recommenders[row.id]).suggested_recommenders, _href=URL(c='user', f='suggested_recommenders', vars=dict(articleId=row.id)))
	else:
		return SPAN((db.v_suggested_recommenders[row.id]).suggested_recommenders)



def mkSuggestedReviewersRecommButton(auth, db, row):
	art = db.t_articles[row.article_id]
	if art.status == 'Under consideration':
		return A((db.v_reviewers[row.id]).reviewers, _href=URL(c='recommender', f='reviews', vars=dict(recommendationId=row.id)))
	else:
		return SPAN((db.v_reviewers[row.id]).reviewers)


def mkRecommReviewsButton(auth, db, row):
	nbRev = db(db.t_reviews.recommendation_id == row.id).count()
	if nbRev < 2:
		txt = current.T('%s review') % nbRev
	else:
		txt = current.T('%s reviews') % nbRev
	return A(SPAN(txt, _class='buttontext btn btn-default'), _href=URL(c='recommender', f='reviews', vars=dict(recommendationId=row.id), user_signature=True), _class='button')


def mkRecommendationFormat(auth, db, row):
	recommender = db.auth_user[row.recommender_id]
	art = db.t_articles[row.article_id]
	anchor = SPAN(art.title, 
					BR(),
					B(current.T('Recommender:')), SPAN(' %s %s %s' % (recommender.user_title, recommender.first_name, recommender.last_name)),
					BR(),
					B(current.T('DOI:')), mkDOI(row.doi)
				)
	return anchor


