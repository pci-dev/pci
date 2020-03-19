# -*- coding: utf-8 -*-

import re
import copy
import datetime

from gluon.contrib.markdown import WIKI
from app_modules.common import *
from app_modules.helper import *

# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get('config.trgm_limit', default=0.4)
parallelSubmissionAllowed = myconf.get('config.parallel_submission', default=False)


######################################################################################################################################################################
@auth.requires_login()
def do_cancel_article():
	articleId = request.vars['articleId']
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if art.user_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		art.status = 'Cancelled'
		art.update_record()
		session.flash = T('Preprint submission cancelled')
		redirect(URL(c='user', f='my_articles', user_signature=True))



######################################################################################################################################################################
@auth.requires_login()
def suggest_article_to():
	articleId = int(request.vars['articleId'])
	recommenderId = int(request.vars['recommenderId'])
	exclude = request.vars['exclude']
	excludeList = []
	if exclude:
		#excludeList = map(int, exclude.split(','))
		for v in exclude:
			excludeList.append(int(v))
	myVars = request.vars
	do_suggest_article_to(auth, db, articleId, recommenderId)
	excludeList.append(recommenderId)
	myVars['exclude'] = excludeList
	session.flash = T('Suggested recommender "%s" added.') % mkUser(auth, db, recommenderId).flatten()
	#redirect(request.env.http_referer)
	#redirect(URL(c='user', f='add_suggested_recommender', vars=dict(articleId=articleId), user_signature=True))
	#redirect(URL(c='user', f='search_recommenders', vars=dict(articleId=articleId, exclude=excludeList), user_signature=True))
	redirect(URL(c='user', f='search_recommenders', vars=myVars, user_signature=True))




######################################################################################################################################################################
@auth.requires_login()
def del_suggested_recommender():
	suggId = request.vars['suggId']
	if suggId:
		if db( (db.t_suggested_recommenders.id==suggId) & (db.t_articles.id==db.t_suggested_recommenders.article_id) & (db.t_articles.user_id==auth.user_id) ).count() > 0:
			db( (db.t_suggested_recommenders.id==suggId) ).delete()
	redirect(request.env.http_referer)



######################################################################################################################################################################
@auth.requires_login()
def article_revised():
	articleId = request.vars['articleId']
	if articleId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if not((art.user_id == auth.user_id or auth.has_membership(role='manager')) and art.status == 'Awaiting revision'):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		#print('article_revised')
		art.status = 'Under consideration'
		art.update_record()
		last_recomm = db(db.t_recommendations.article_id==art.id).select(orderby=db.t_recommendations.id).last()
		last_recomm.is_closed = True
		last_recomm.update_record()
		newRecomm = db.t_recommendations.insert(article_id=art.id, recommender_id=last_recomm.recommender_id, no_conflict_of_interest=last_recomm.no_conflict_of_interest, doi=art.doi, ms_version=art.ms_version, is_closed=False, recommendation_state='Ongoing', recommendation_title=None)
		# propagate co-recommenders
		corecommenders = db(db.t_press_reviews.recommendation_id==last_recomm.id).select(db.t_press_reviews.contributor_id)
		if len(corecommenders) > 0 :
			# NOTE: suspend emailing trigger declared as : db.t_press_reviews._after_insert.append(lambda s,i: newPressReview(s,i))
			db.t_press_reviews._after_insert = []
			for corecommender in corecommenders:
				db.t_press_reviews.validate_and_insert(recommendation_id=newRecomm.id, contributor_id=corecommender.contributor_id)
		redirect(URL(c='user', f='my_articles', user_signature=True))


######################################################################################################################################################################
@auth.requires_login()
def do_accept_new_review():
	if 'reviewId' not in request.vars:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	reviewId = request.vars['reviewId']
	if isinstance(reviewId, list):
		reviewId = reviewId[1]
	theUser = db.auth_user[auth.user_id]
	if 'ethics_approved' in request.vars and theUser.ethical_code_approved is False:
		theUser.ethical_code_approved = True
		theUser.update_record()
	if not(theUser.ethical_code_approved):
		raise HTTP(403, "403: "+T('ERROR: Ethical code not approved'))
	if 'no_conflict_of_interest' not in request.vars:
		raise HTTP(403, "403: "+T('ERROR: Value "no conflict of interest" missing'))
	noConflict = request.vars['no_conflict_of_interest']
	if noConflict != "yes":
		raise HTTP(403, "403: "+T('ERROR: No conflict of interest not checked'))
	rev = db.t_reviews[reviewId]
	if rev is None:
		raise HTTP(404, "404: "+T('ERROR: Review unavailable'))
	if rev.reviewer_id != auth.user_id:
		raise HTTP(403, "403: "+T('ERROR: Forbidden access'))
	rev.review_state = 'Under consideration'
	rev.no_conflict_of_interest = True
	rev.acceptation_timestamp = datetime.datetime.now()
	rev.update_record()
	# email to recommender sent at database level
	recomm = db.t_recommendations[rev.recommendation_id]
	redirect(URL(c='user', f='recommendations', vars=dict(articleId=recomm.article_id)))
	#redirect(URL(c='user', f='my_reviews', vars=dict(pendingOnly=False), user_signature=True))


######################################################################################################################################################################
@auth.requires_login()
def decline_new_review():
	if 'reviewId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	reviewId = request.vars['reviewId']
	rev = db.t_reviews[reviewId]
	if rev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if rev.reviewer_id != auth.user_id:
		session.flash = T('Unauthorized', lazy=False)
		redirect(URL(c='user', f='my_reviews'))
	#db(db.t_reviews.id==reviewId).delete()
	rev.review_state = 'Declined'
	rev.update_record()
	# email to recommender sent at database level
	redirect(URL(c='user', f='my_reviews', vars=dict(pendingOnly=True), user_signature=True))



######################################################################################################################################################################
@auth.requires_login()
def review_completed():
	if 'reviewId' not in request.vars:
		raise HTTP(404, "404: "+T('Unavailable'))
	reviewId = request.vars['reviewId']
	rev = db.t_reviews[reviewId]
	if rev is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if rev.reviewer_id != auth.user_id:
		session.flash = T('Unauthorized', lazy=False)
		redirect(URL(c='user', f='my_reviews'))
	rev.review_state = 'Completed'
	rev.update_record()
	# email to recommender sent at database level
	redirect(URL(c='user', f='my_reviews'))


######################################################################################################################################################################
## (gab) Unused ?
######################################################################################################################################################################
# @auth.requires_login()
# def do_delete_article():
# 	articleId = request.vars['articleId']
# 	if articleId is None:
# 		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
# 	art = db.t_articles[articleId]
# 	if art is None:
# 		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
# 	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
# 	if art.user_id != auth.user_id:
# 		session.flash = auth.not_authorized()
# 		redirect(request.env.http_referer)
# 	else:
# 		db(db.t_articles.id == articleId).delete()
# 		session.flash = T('Preprint submission deleted')
# 		redirect(URL(c='user', f='my_articles', user_signature=True))


# ######################################################################################################################################################################
# def suggest_article_to_all(articleId, recommenderIds):
# 	added = []
# 	for recommenderId in recommenderIds:
# 		do_suggest_article_to(auth, db, articleId, recommenderId)
# 		added.append(mkUser(auth, db, recommenderId))
# 	#redirect(URL(c='user', f='add_suggested_recommender', vars=dict(articleId=articleId), user_signature=True))
# 	session.flash = T('Suggested recommenders %s added.') % (', '.join(added))
# 	redirect(request.env.http_referer)
