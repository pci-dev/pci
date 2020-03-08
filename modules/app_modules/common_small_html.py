
import gc
import os
import pytz
from re import sub, match
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
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

myconf = AppConfig(reload=True)
######################################################################################################################################################################
# No HTML
######################################################################################################################################################################
def takePort(p):
	#print('port="%s"' % p)
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
def mkTFDict(tfArray):
	resu = dict()
	for tf in tfArray:
		resu['qy_'+tf] = 'on'
	return resu

######################################################################################################################################################################
# Small HTML
######################################################################################################################################################################

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
			resu = A(str(userId), _href=URL(c='user', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=userId)), _class="cyp-user-profile-link")
		else:
			resu = SPAN(str(userId))
	return resu

######################################################################################################################################################################
def mkUser_U(auth, db, theUser, linked=False, scheme=False, host=False, port=False):
	if theUser:
		if linked:
			resu = A('%s %s' % (theUser.first_name, theUser.last_name), _href=URL(c='user', f='viewUserCard', scheme=scheme, host=host, port=port, vars=dict(userId=theUser.id)), _class="cyp-user-profile-link")
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

######################################################################################################################################################################
def mkViewEditRecommendationsRecommenderButton(auth, db, row):
	return A(SPAN(current.T('Check & Edit'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='recommender', f='recommendations', vars=dict(articleId=row.article_id)), _class='button', _title=current.T('View and/or edit article'))

######################################################################################################################################################################
def mkViewEditRecommendationsManagerButton(auth, db, row):
	return A(SPAN(current.T('Check & Edit'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='manager', f='recommendations', vars=dict(articleId=row.article_id)), _class='button', _title=current.T('View and/or edit article'))


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