# -*- coding: utf-8 -*-

import os
from gluon.html import *

from collections import OrderedDict

import common_html
import common_small_html

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

######################################################################################################################################################################
# (gab)
def get_template(folderName, templateName):
	with open(os.path.join(os.path.dirname(__file__), '../../templates', folderName, templateName), 'r') as myfile:
  		data = myfile.read()
	return data

def getShortText(text, length):
	if len(text)>length:
		text = text[0:length] + '...'
	return text
	

# move somewhere
def getRecommendationMetadata(auth, db, art, lastRecomm, pdfLink, citeNum, citeUrl, citeRef, scheme, host, port):
	desc = 'A recommendation of: '+(art.authors or '')+' '+(art.title or '')+' '+(art.doi or '')
	whoDidItMeta = common_html.mkWhoDidIt4Recomm(auth, db, lastRecomm, with_reviewers=False, linked=False, as_list=True, as_items=False)
	
	# META headers
	myMeta = OrderedDict()
	myMeta['citation_title'] = lastRecomm.recommendation_title
	if len(whoDidItMeta)>0:
		# Trick for multiple entries (see globals.py:464)
		for wdi in whoDidItMeta:
			myMeta['citation_author_%s' % wdi] = OrderedDict([('name', 'citation_author'), ('content', wdi)])
	myMeta['citation_journal_title'] = myconf.take("app.description")
	myMeta['citation_publication_date'] = (lastRecomm.last_change.date()).strftime('%Y/%m/%d')
	myMeta['citation_online_date'] = (lastRecomm.last_change.date()).strftime('%Y/%m/%d')
	myMeta['citation_journal_abbrev'] = myconf.take("app.name")
	myMeta['citation_issn'] = myconf.take("app.issn")
	myMeta['citation_volume'] = '1'
	myMeta['citation_publisher'] = 'Peer Community In'
	if lastRecomm.recommendation_doi:
		myMeta['citation_doi'] = sub(r'doi: *', '', lastRecomm.recommendation_doi) # for altmetrics
	if citeNum:
		myMeta['citation_firstpage'] = citeNum
	myMeta['citation_abstract'] = desc
	if pdfLink:
		myMeta['citation_pdf_url'] = pdfLink

	#myMeta['og:title'] = lastRecomm.recommendation_title
	#myMeta['description'] = desc

	# Dublin Core fields
	myMeta['DC.title'] = lastRecomm.recommendation_title
	if len(whoDidItMeta)>0:
		myMeta['DC.creator'] = ' ; '.join(whoDidItMeta) # syntax follows: http://dublincore.org/documents/2000/07/16/usageguide/#usinghtml
	myMeta['DC.issued'] = lastRecomm.last_change.date()
	#myMeta['DC.date'] = lastRecomm.last_change.date()
	myMeta['DC.description'] = desc
	myMeta['DC.publisher'] = myconf.take("app.description")
	myMeta['DC.relation.ispartof'] = myconf.take("app.description")
	if lastRecomm.recommendation_doi:
		myMeta['DC.identifier'] = myMeta['citation_doi']
	if citeNum:
		myMeta['DC.citation.spage'] = citeNum
	myMeta['DC.language'] = 'en'
	myMeta['DC.rights'] = '(C) %s, %d' % (myconf.take("app.description"), lastRecomm.last_change.date().year)

	return myMeta