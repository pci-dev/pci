# -*- coding: utf-8 -*-

import os
import datetime
from re import sub, match
from copy import deepcopy
import datetime
from dateutil.relativedelta import *

from gluon import current, IS_IN_DB
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail
from sqlhtml import *

myconf = AppConfig(reload=True)

statusArticles = dict()
def mkStatusArticles(db):
	statusArticles.clear()
	for sa in db(db.t_status_article).select():
		statusArticles[sa['status']] = sa



# Builds the right-panel for home page
def mkPanel(myconf, auth, inSearch=False):
	if inSearch:
		panel = [LI(A(current.T('Search recommended articles'), _href='#TOP', _class='btn btn-default'), _class="list-group-item list-group-item-centered"),]
	else:
		panel = [LI(A(current.T('Search recommended articles'), _href=URL('public', 'recommended_articles'), _class='btn btn-default'), _class="list-group-item list-group-item-centered"),]
	if auth.user_id is not None:
		#panel.append(LI(A(current.T("Request a recommendation"), _href=URL('user', 'my_articles', args=['new', 't_articles'], user_signature=True), _class="btn btn-success"), _class="list-group-item list-group-item-centered"))
		panel.append(LI(A(current.T("Submit an article for a recommendation"), _href=URL('user', 'new_submission', user_signature=True), _class="btn btn-success"), _class="list-group-item list-group-item-centered"))
	else:
		panel.append(LI(A(current.T("Log in before requesting a recommendation"), _href=URL('default', 'user')), _class="list-group-item"))
	if auth.has_membership('recommender'):
		panel.append(LI(A(current.T("Start a recommendation process"), _href=URL('recommender', 'new_submission', user_signature=True), _class="btn btn-info"), _class="list-group-item list-group-item-centered"))
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
				LABEL(current.T('Search for')), 
				INPUT(_name='qyKeywords', keepvalues=True, _class='searchField', value=kwVal), 
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




def mkUserRow(userRow, withMail=False):
	resu = []
	resu.append(TD(B( (userRow.last_name or ''), ' ', (userRow.first_name or '') )))
	resu.append(TD(I( (userRow.laboratory or ''), ', ', (userRow.institution or ''), ', ', (userRow.city or ''), ', ', (userRow.country or '') )))
	if withMail:
		resu.append(TD(A(' [%s]' % userRow.email, _href='mailto:%s' % userRow.email) if withMail else ''))
	if (userRow.uploaded_picture is not None and userRow.uploaded_picture != ''):
		resu.append(TD((IMG(_src=URL('default', 'download', args=userRow.uploaded_picture), _class='pci-userPicture'))))
	else:
		resu.append((IMG(_src=URL(c='static',f='images/default_user.png'), _class='pci-userPicture')))
	return TR(resu, _class='pci-UsersTable-row')




def mkArticleRow(row, withScore=False, withDate=False):
	resu = []
	if withScore:
			resu.append(TD(row.score, _class='pci-lastArticles-date'))
	if row.authors and len(row.authors)>1000:
		authors = row.authors[:1000]+'...'
	else:
		authors = row.authors or ''
	resu.append(
				TD(
					B(row.title),
					BR(),
					SPAN(authors),
					BR(),
					mkDOI(row.doi),
					A(current.T('See recommendation...'), 
						_href=URL(c='public', f='recommendations', vars=dict(articleId=row.id)),
						_target='blank',
						_style="color:green;margin-left:20px;",
					)
				)
			)
	if withDate:
			resu.append(TD(mkLastChange(row.last_status_change), _class='pci-lastArticles-date'))
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

# Builds a nice representation of an article WITH recommendations link
def mkArticleCell(auth, db, art):
	anchor = ''
	if art:
		anchor = DIV(
					B(art.title),
					BR(),
					SPAN(art.authors),
					BR(),
					mkDOI(art.doi),
					(BR()+SPAN(art.article_source) if art.article_source else ''),
					A(current.T('See recommendation...'), 
								_href=URL(c='public', f='recommendations', vars=dict(articleId=art.id)),
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



def mkViewArticle4ReviewButton(auth, db, row):
	anchor = ''
	recomm = db.t_recommendations[row.recommendation_id]
	if recomm:
		art = db.t_articles[recomm.article_id]
		if art:
			anchor = DIV(
						B(art.title),
						BR(),
						SPAN(art.authors),
						BR(),
						mkDOI(art.doi),
					)
	return anchor



# Builds a search button for recommenders matching keywords
def mkSearchRecommendersButton(auth, db, row):
	#if statusArticles is None or len(statusArticles) == 0:
		#mkStatusArticles(db)
	anchor = ''
	if row['status'] == 'Awaiting consideration' or row['status'] == 'Pending':
		myVars = dict(articleId=row['id'])
		for thema in row['thematics']:
			myVars['qy_'+thema] = 'on'
		#NOTE: useful or useless? 
		#myVars['qyKeywords'] = ' '.join(row['thematics'])
		anchor = A(SPAN('+ '+current.T('Suggest'),BR(),current.T('recommenders'), _class='buttontext btn btn-default'), _href=URL(c='manage', f='search_recommenders', vars=myVars, user_signature=True), _class='button')
	return anchor



# Builds a search button for recommenders matching keywords
def mkSearchRecommendersUserButton(auth, db, row):
	#if statusArticles is None or len(statusArticles) == 0:
		#mkStatusArticles(db)
	anchor = ''
	if row['status'] == 'Awaiting consideration' or row['status'] == 'Pending':
		myVars = dict(articleId=row['id'])
		for thema in row['thematics']:
			myVars['qy_'+thema] = 'on'
		#NOTE: useful or useless? 
		#myVars['qyKeywords'] = ' '.join(row['thematics'])
		anchor = A(SPAN('+ '+current.T('Suggest'),BR(),current.T('recommenders'), _class='buttontext btn btn-default'), _href=URL(c='user', f='search_recommenders', vars=myVars, user_signature=True), _class='button')
	return anchor



# Builds a search button for reviewers matching keywords
def mkSearchReviewersButton(auth, db, row):
	#if statusArticles is None or len(statusArticles) == 0:
		#mkStatusArticles(db)
	anchor = ''
	article = db.t_articles[row['article_id']]
	if article and article['status'] == 'Under consideration':
		myVars = dict(recommendationId=row['id'])
		for thema in article['thematics']:
			myVars['qy_'+thema] = 'on'
		#NOTE: useful or useless? 
		#myVars['qyKeywords'] = ' '.join(article['thematics'])
		if row['is_press_review'] and row['auto_nb_agreements']==0:
			myVars['4press'] = 'on'
			anchor = A(SPAN('+ '+current.T('Add'),BR(),current.T('contributors'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='search_reviewers', vars=myVars, user_signature=True), _class='button')
		elif row['is_press_review'] is False:
			myVars['4review'] = 'on'
			anchor = A(SPAN('+ '+current.T('Add'),BR(),current.T('reviewers'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='search_reviewers', vars=myVars, user_signature=True), _class='button')
	return anchor




# Builds a status button which allow to open recommendations only when recommended and recommendations exists
def mkStatusDiv(auth, db, status):
	if statusArticles is None or len(statusArticles) == 0:
		mkStatusArticles(db)
	status_txt = (current.T(status)).upper()
	color_class = statusArticles[status]['color_class'] or 'default'
	hint = statusArticles[status]['explaination'] or ''
	return DIV(status_txt, _class='pci-status '+color_class, _title=current.T(hint))





def mkRecommendationsButton(auth, db, art, target):
	anchor = ''
	#if art.auto_nb_recommendations > 0:
		#anchor = A(SPAN(current.T('%s recommendations') % (art.auto_nb_recommendations), _class='buttontext btn btn-default'), _href=target, _class='button')
	anchor = A(SPAN(art.auto_nb_recommendations, _class='buttontext btn btn-default'), _href=target, _class='button')
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
						BR()+SPAN(art.article_source) if art.article_source else ''
				)
	return anchor



def mkBackButton(target=None):
	if target:
		return A(SPAN(current.T('Back'), _class='buttontext btn btn-default'), _href=target, _class='button')
	else:
		return A(SPAN(current.T('Back'), _class='buttontext btn btn-default'), _onclick='window.history.back();', _class='button')




def mkRecommendedArticle(auth, db, art, printable, with_comments=False):
	submitter = db.auth_user[art.user_id]
	allowOpinion = None
	myContents = DIV(
					SPAN(I(current.T('Submitted by')+' '+(submitter.first_name or '')+' '+(submitter.last_name or '')+' '+(art.upload_timestamp.strftime('%Y-%m-%d %H:%M') if art.upload_timestamp else '')) if submitter else '')
					,H4(art.authors)
					,H3(art.title)
					,(mkDOI(art.doi)+BR()) if (art.doi) else SPAN('')
					,(SPAN(art.article_source)+BR() if art.article_source else '')
					,SPAN(I(current.T('Keywords:')+' '+art.keywords)+BR() if art.keywords else '')
					,B(current.T('Abstract'))+BR()
					,DIV(WIKI(art.abstract or ''), _class='pci-bigtext')
					, _class=('pci-article-div-printable' if printable else 'pci-article-div')
				)
	if (art.user_id == auth.user_id) and (art.status in ('Pending', 'Awaiting revision')) and not(printable):
		myContents.append(DIV(A(SPAN(current.T('Edit article'), _class='buttontext btn btn-default'), _href=URL(c='user', f='edit_my_article', vars=dict(articleId=art.id), user_signature=True)), _class='pci-EditButtons'))
	recomms = db(db.t_recommendations.article_id == art.id).select(orderby=db.t_recommendations.last_change)
	for recomm in recomms:
		recommender = db.auth_user[recomm.recommender_id]
		if recomm.is_press_review:
			contributors = db.v_recommendation_contributors[recomm.id]['contributors']
			lastchange = recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else None
			whowhen = current.T('Recommendation by')+' '+(recommender.first_name or '')+' '+(recommender.last_name or '')+(', '+lastchange or '')+' with '+(contributors or '')
			myContents.append(
				DIV( HR()
					,SPAN(I(whowhen))
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
						SPAN(I(current.T('Reviewed by')+' '+current.T('anonymous reviewer')+(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
					)
				else:
					reviewer = db.auth_user[recomm.recommender_id]
					myReviews.append(
						SPAN(I(current.T('Reviewed by')+' '+(reviewer.first_name or '')+' '+(reviewer.last_name or '')+(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
					)
				myReviews.append(BR())
				myReviews.append(DIV(WIKI(review.review or ''), _class='pci-bigtext margin'))
			myContents.append(
				DIV( HR()
					,SPAN(I(current.T('Recommendation by')+' '+(recommender.first_name or '')+' '+(recommender.last_name or '')+(', '+recomm.last_change.strftime('%Y-%m-%d %H:%M') if recomm.last_change else '')))
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
			if not(recomm.is_closed) and (art.user_id == auth.user_id) and (art.status == 'Awaiting revision') and not(printable):
				myContents.append(DIV(A(SPAN(current.T('Edit reply'), _class='buttontext btn btn-default'), _href=URL(c='user', f='edit_reply', vars=dict(recommId=recomm.id), user_signature=True)), _class='pci-EditButtons'))
			if not(recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == 'Under consideration') and not(printable):
				myContents.append(DIV(A(SPAN(current.T('Edit recommendation'), _class='buttontext btn btn-default'), _href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recomm.id), user_signature=True)), _class='pci-EditButtons'))
				allowOpinion = recomm.id
			
			
	myContents.append(HR())
	if (art.user_id == auth.user_id) and (art.status == 'Awaiting revision') and not(printable):
		myContents.append(DIV(A(SPAN(current.T('Revision terminated: submit new version and close revision process'), _class='buttontext btn btn-success'), _href=URL(c='user', f='article_revised', vars=dict(articleId=art.id), user_signature=True), _title=current.T('Click here when the revision is terminated in order to submit the new version')), _class='pci-EditButtons-centered'))
	if (art.user_id == auth.user_id) and (art.status not in ('Rejected', 'Pre-recommended', 'Recommended')) and not(printable):
		myContents.append(DIV(A(SPAN(current.T('I wish to cancel this recommendation request'), _class='buttontext btn btn-warning'), _href=URL(c='user', f='article_cancelled', vars=dict(articleId=art.id), user_signature=True), _title=current.T('Click here in order to cancel this recommendation request')), _class='pci-EditButtons')) 
	if allowOpinion:
		#myContents.append(H1('TODO: opinion form'))
		myContents.append( FORM(
				LABEL(current.T('Final recommendation:')), 
				DIV(
					SPAN(INPUT(_name='recommender_opinion', _type='radio', _value='do_recommend'), current.T('I recommend this article'), _class='pci-radio pci-recommend'),
					SPAN(INPUT(_name='recommender_opinion', _type='radio', _value='do_revise'), current.T('This article worth a revision'), _class='pci-radio pci-review'),
					SPAN(INPUT(_name='recommender_opinion', _type='radio', _value='do_reject'), current.T('I reject this article'), _class='pci-radio pci-reject'),
					_style="height:48px;"
				),
				INPUT(_value=current.T('submit'), _type='submit', _class='btn btn-primary pci-radio'),
				_class='pci-opinionform', keepvalues=True,
				_action=URL(c='recommender', f='process_opinion', vars=dict(recommendationId=allowOpinion), user_signature=True),
				_name='opinionForm'
			))
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
		return A(XML((db.v_suggested_recommenders[row.id]).suggested_recommenders.replace(', ', '<br>')), _href=URL(c='manage', f='suggested_recommenders', vars=dict(articleId=row.id)))
	else:
		return SPAN((db.v_article_recommender[row.id]).recommender)



def mkSuggestedRecommendersUserButton(auth, db, row):
	butts = []
	if row.status == 'Pending':
		sr = db.v_suggested_recommenders[row.id].suggested_recommenders
		if sr:
			butts.append( A(XML(sr.replace(', ', '<br>')), _href=URL(c='user', f='suggested_recommenders', vars=dict(articleId=row.id))) )
		myVars = dict(articleId=row['id'])
		for thema in row['thematics']:
			myVars['qy_'+thema] = 'on'
		butts.append( BR() )
		butts.append( A(current.T('[+ADD]'), _href=URL(c='user', f='search_recommenders', vars=myVars, user_signature=True)) )
	else:
		butts.append( SPAN((db.v_suggested_recommenders[row.id]).suggested_recommenders) )
	return butts



def mkSollicitedRev(auth, db, row):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db(db.t_reviews.recommendation_id == row.id).select()
	for rev in revs:
		hrevs.append(LI(mkUserWithMail(auth, db, rev.reviewer_id)))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	if art.status == 'Under consideration':
		myVars = dict(recommId=row['id'])
		butts.append( A('['+current.T('MANAGE')+'] ', _href=URL(c='recommender', f='reviews', vars=myVars, user_signature=True)) )
		for thema in art['thematics']:
			myVars['qy_'+thema] = 'on'
		butts.append( A('['+current.T('+ADD')+'] ', _href=URL(c='recommender', f='search_reviewers', vars=myVars, user_signature=True)) )
	return butts

def mkDeclinedRev(auth, db, row):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db( (db.t_reviews.recommendation_id == row.id) & (db.t_reviews.review_state == "Declined") ).select()
	for rev in revs:
		hrevs.append(LI(mkUserWithMail(auth, db, rev.reviewer_id)))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	return butts

def mkOngoingRev(auth, db, row):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db( (db.t_reviews.recommendation_id == row.id) & (db.t_reviews.review_state == "Under consideration") ).select()
	for rev in revs:
		hrevs.append(LI(mkUserWithMail(auth, db, rev.reviewer_id)))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	return butts

def mkClosedRev(auth, db, row):
	butts = []
	hrevs = []
	art = db.t_articles[row.article_id]
	revs = db( (db.t_reviews.recommendation_id == row.id) & (db.t_reviews.review_state == "Terminated") ).select()
	for rev in revs:
		hrevs.append(LI(mkUserWithMail(auth, db, rev.reviewer_id)))
	butts.append( UL(hrevs, _class='pci-inCell-UL') )
	return butts




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



def mkViewEditRecommendationsUserButton(auth, db, row):
	return A(SPAN(current.T('View / Edit'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='user', f='recommendations', vars=dict(articleId=row.id), user_signature=True), _class='button', _title=current.T('View and/or edit article'))

def mkViewEditRecommendationsRecommenderButton(auth, db, row):
	return A(SPAN(current.T('Check & Edit'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='recommender', f='recommendations', vars=dict(articleId=row.article_id), user_signature=True), _class='button', _title=current.T('View and/or edit article'))
