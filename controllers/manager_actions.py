# -*- coding: utf-8 -*-

import re
import copy
import tempfile
from datetime import datetime, timedelta
import glob
import os

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
## Manager Actions
######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_validate_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Pending':
		art.status = 'Awaiting consideration'
		art.update_record()
		session.flash = T('Request now available to recommenders')
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))




######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_cancel_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		#art.status = 'Cancelled' #TEST
		art.status = 'Rejected'
		art.update_record()
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_recommend_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Pre-recommended':
		art.status = 'Recommended'
		art.update_record()
		redirect(URL(c='articles', f='rec', vars=dict(id=art.id), user_signature=True))
	else:
		redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_revise_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Pre-revision':
		art.status = 'Awaiting revision'
		art.update_record()
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def do_reject_article():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Pre-rejected':
		art.status = 'Rejected'
		art.update_record()
	redirect(URL(c='manager', f='recommendations', vars=dict(articleId=articleId), user_signature=True))

######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def suggest_article_to():
	articleId = request.vars['articleId']
	whatNext = request.vars['whatNext']
	recommenderId = request.vars['recommenderId']
	db.t_suggested_recommenders.update_or_insert(suggested_recommender_id=recommenderId, article_id=articleId)
	redirect(whatNext)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def set_not_considered():
	if not('articleId' in request.vars):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	if art.status == 'Awaiting consideration':
		session.flash = T('Article set "Not considered"')
		art.status = 'Not considered'
		art.update_record()
	redirect(request.env.http_referer)


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='manager'))
def send_suggested_recommender_reminder():
	if ('suggRecommId' in request.vars):
		suggRecommId = request.vars['suggRecommId']
		do_send_reminder_email_to_suggested_recommender(session, auth, db, suggRecommId)
	else:
		session.flash = T('Unavailable')
	redirect(request.env.http_referer)