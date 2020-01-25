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
	
