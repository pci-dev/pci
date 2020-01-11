# -*- coding: utf-8 -*-

import re
import copy
import tempfile
from datetime import datetime, timedelta
import glob
import os

from gluon import current

# sudo pip install tweepy
#import tweepy

import codecs
#import html2text
from gluon.contrib.markdown import WIKI
from app_modules.common import *
from app_modules.helper import *

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

# frequently used constants
from app_modules.emailing import mail_layout, mail_sleep
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.get('config.trgm_limit') or 0.4
parallelSubmissionAllowed = myconf.get('config.parallel_submission', default=False)
not_considered_delay_in_days = myconf.get('config.unconsider_limit_days', default=20)


######################################################################################################################################################################
## Manager Modules
######################################################################################################################################################################
def mkRecommenderButton(row, auth, db):
	last_recomm = db( db.t_recommendations.article_id==row.id ).select(orderby=db.t_recommendations.id).last()
	if last_recomm:
		resu = SPAN(mkUserWithMail(auth, db, last_recomm.recommender_id))
		corecommenders = db(db.t_press_reviews.recommendation_id==last_recomm.id).select(db.t_press_reviews.contributor_id)
		if len(corecommenders) > 0:
			resu.append(BR())
			resu.append(B(current.T('Co-recommenders:')))
			resu.append(BR())
			for corecommender in corecommenders:
				resu.append(SPAN(mkUserWithMail(auth, db, corecommender.contributor_id))+BR())
		return DIV(resu, _class="pci-w200Cell")
	else:
		return ''

def mkSuggestedRecommendersManagerButton(row, whatNext, auth, db):
	if row.already_published:
		return ''
	butts = []
	suggRecomsTxt = []
	exclude = [str(auth.user_id)]
	#sr = db.v_suggested_recommenders[row.id].suggested_recommenders
	suggRecomms = db(db.t_suggested_recommenders.article_id==row.id).select()
	for sr in suggRecomms:
		exclude.append(str(sr.suggested_recommender_id))
		suggRecomsTxt.append(mkUserWithMail(auth, db, sr.suggested_recommender_id)+(XML(' <b>(declined)</b>') if sr.declined else SPAN(''))
			+BR()
			+A(current.T('See emails...'), _href=URL(c='manager', f='suggested_recommender_emails', vars=dict(srId=sr.id)), _target="blank", _class='btn btn-link pci-smallBtn pci-recommender', _style='margin-bottom:12px;')
			#+A(T('see emails'), _href=URL(c='manager', f='suggested_recommender_emails', vars=dict(srId=sr.id)), _target="_blank", _class='btn pci-smallBtn pci-emailing-btn')
			+BR())
	myVars = dict(articleId=row.id, whatNext=whatNext)
	if len(exclude)>0:
		myVars['exclude'] = ','.join(exclude)
	if len(suggRecomsTxt)>0: 
		butts.append(DIV(suggRecomsTxt))
		if row.status in ('Awaiting consideration', 'Pending'):
			butts.append( A(current.T('Manage'), _class='btn btn-default pci-manager', _href=URL(c='manager', f='suggested_recommenders', vars=myVars)) )
	#for thema in row.thematics:
		#myVars['qy_'+thema] = 'on'
	#butts.append( BR() )
	if row.status in ('Awaiting consideration', 'Pending'):
		butts.append( A(current.T('Add'), _class='btn btn-default pci-manager', _href=URL(c='manager', f='search_recommenders', vars=myVars, user_signature=True)) )
	return DIV(butts, _class="pci-w200Cell")
