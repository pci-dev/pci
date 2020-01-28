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
		lastRecomm = db( (db.t_recommendations.article_id == article.id) ).select(orderby=db.t_recommendations.id).last()
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
	