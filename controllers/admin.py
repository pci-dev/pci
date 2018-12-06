# -*- coding: utf-8 -*-

import re
import copy
import random
import os
import datetime
import tempfile

# sudo pip install tweepy
#import tweepy

from gluon.contrib.markdown import WIKI
from common import *
from emailing import *
from helper import *

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

# frequently used constants
csv = False # no export allowed
expClass = dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def testMail():
	do_send_email_to_test(session, auth, db, auth.user_id)
	redirect(request.env.http_referer)




######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def mkRoles(row):
	resu = ''
	if row.id:
		roles = db.v_roles[row.id]
		if roles:
			resu = SPAN(roles.roles)
	return resu


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def resizeAllUserImages():
	for userId in db(db.auth_user.uploaded_picture != None).select(db.auth_user.id):
		makeUserThumbnail(auth, db, userId, size=(150,150))
	redirect(request.env.http_referer)



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def resizeAllArticleImages():
	for articleId in db(db.t_articles.uploaded_picture != None).select(db.t_articles.id):
		makeArticleThumbnail(auth, db, articleId, size=(150,150))
	redirect(request.env.http_referer)



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def resizeUserImages(ids):
	for userId in ids:
		makeUserThumbnail(auth, db, userId, size=(150,150))


######################################################################################################################################################################
#@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
#def deny_login(ids):
	#for myId in ids:
		#db.executesql("UPDATE auth_user SET registration_key='blocked' WHERE id=%s;", placeholders=[myId])

######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def set_as_recommender(ids):
	# get recommender group id
	recommRoleId = (db(db.auth_group.role == "recommender").select(db.auth_group.id).last())["id"]
	for myId in ids:
		# check not already recommender
		isAlreadyRecommender = db((db.auth_membership.user_id==myId) & (db.auth_membership.group_id==recommRoleId)).count()
		if (isAlreadyRecommender == 0):
			# insert membership
			db.auth_membership.insert(user_id=myId, group_id=recommRoleId)

######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def list_users():
	selectable = None
	links = None
	create = True # allow create buttons
	if len(request.args)==0 or (len(request.args)==1 and request.args[0]=='auth_user'):
		#selectable = [  (T('Deny login to selected users'), lambda ids: [deny_login(ids)], 'class1')  ]
		selectable = [  (T('Add role \'recommender\' to selected users'), lambda ids: [set_as_recommender(ids)], 'btn btn-info pci-admin')  ]
		links = [  dict(header=T('Roles'), body=lambda row: mkRoles(row))  ]
	db.auth_user.registration_datetime.readable = True
	
	db.auth_user.uploaded_picture.represent = lambda text,row: (IMG(_src=URL('default', 'download', args=row.uploaded_picture), _width=100)) if (row.uploaded_picture is not None and row.uploaded_picture != '') else (IMG(_src=URL(r=request,c='static',f='images/default_user.png'), _width=100))
	db.auth_user.email.represent = lambda text, row: A(text, _href='mailto:%s'%text)
	
	fields = [
			db.auth_user.id, db.auth_user.registration_key, db.auth_user.uploaded_picture, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email, db.auth_user.registration_datetime, db.auth_user.laboratory, db.auth_user.institution, db.auth_user.city, db.auth_user.country, db.auth_user.thematics, db.auth_user.alerts, 
			db.auth_membership.user_id, db.auth_membership.group_id,
			db.t_articles.id, db.t_articles.title, db.t_articles.anonymous_submission, db.t_articles.authors, db.t_articles.already_published, db.t_articles.status, 
			db.t_recommendations.id, db.t_recommendations.article_id, db.t_recommendations.recommender_id, db.t_recommendations.recommendation_state, db.t_recommendations.recommendation_title, 
			db.t_reviews.id, db.t_reviews.recommendation_id, db.t_reviews.review_state, db.t_reviews.review,
			db.t_press_reviews.id, db.t_press_reviews.recommendation_id,
			db.t_comments.id, db.t_comments.article_id, db.t_comments.user_comment, db.t_comments.comment_datetime, db.t_comments.parent_id,
		]
	db.auth_user._id.readable=True
	db.auth_user._id.represent=lambda i,row: mkUserId(auth, db, i, linked=True)
	db.t_reviews.recommendation_id.label = T('Article DOI')
	db.t_articles.anonymous_submission.label = T('Anonymous submission')
	db.t_articles.anonymous_submission.represent = lambda text,row: mkAnonymousMask(auth, db, text)
	db.t_articles.already_published.represent = lambda text,row: mkJournalImg(auth, db, text)
	db.auth_user.registration_key.represent = lambda text,row: SPAN(text, _class="pci-blocked") if (text=='blocked' or text=='disabled') else text
	grid = SQLFORM.smartgrid(db.auth_user
				,fields=fields
				,linked_tables=['auth_user', 'auth_membership', 't_articles', 't_recommendations', 't_reviews', 't_press_reviews', 't_comments']
				,links=links
				,csv=False, exportclasses=dict(auth_user=expClass, auth_membership=expClass)
				,editable=dict(auth_user=True, auth_membership=False)
				,details=dict(auth_user=True, auth_membership=False)
				,searchable=dict(auth_user=True, auth_membership=False)
				,create=dict(auth_user=create, auth_membership=create, t_articles=create, t_recommendations=create, t_reviews=create, t_press_reviews=create, t_comments=create)
				,selectable=selectable
				,maxtextlength=250
				,paginate=25
			)
	if ('auth_membership.user_id' in request.args):
		if grid and grid.element(_title="Add record to database"):
				grid.element(_title="Add record to database")[0] = T('Add role')
				#grid.element(_title="Add record to database")['_title'] = T('Manually add new round of recommendation. Expert use!!')
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#AdministrateUsersText'),
				myTitle=getTitle(request, auth, db, '#AdministrateUsersTitle'),
				myHelp=getHelp(request, auth, db, '#AdministrateUsers'),
				grid=grid, 
			 )


######################################################################################################################################################################
# Prepares lists of email addresses by role
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def mailing_lists():
	content = DIV()
	for theRole in db(db.auth_group.role).select():
		content.append(H1(theRole.role))
		emails = []
		query = db( (db.auth_user._id == db.auth_membership.user_id) & (db.auth_membership.group_id == theRole.id) ).select(db.auth_user.email, orderby=db.auth_user.email)
		for user in query:
			if user.email:
				emails.append(user.email)
		list_emails = ', '.join(emails)
		content.append(list_emails)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#EmailsListsUsersText'),
				myTitle=getTitle(request, auth, db, '#EmailsListsUsersTitle'),
				myHelp=getHelp(request, auth, db, '#EmailsListsUsers'),
				content=content, 
				grid='',
			 )


######################################################################################################################################################################
#@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
#def memberships():
	#userId = request.args(1)
	#query = db.auth_membership.user_id == userId
	#db.auth_membership.user_id.default = userId
	#db.auth_membership.user_id.writable = False
	#db.auth_membership._id.readable = False
	#grid = SQLFORM.grid( query
				#,deletable=True, create=True, editable=False, details=False, searchable=False
				#,csv=csv, exportclasses=expClass
				#,maxtextlength=250
				#,paginate=25
			#)
	#response.view='admin/memberships.html'
	#return dict(
				#myTitle=getTitle(request, auth, db, '#AdministrateMembershipsTitle'),
				#myHelp=getHelp(request, auth, db, '#AdministrateMemberships'),
				#grid=grid, 
		#)



######################################################################################################################################################################
# Display the list of thematic fields
# Can be modified only by developper and administrator
@auth.requires_login()
def thematics_list():
	write_auth = auth.has_membership('administrator') or auth.has_membership('developper')
	db.t_thematics._id.readable=False
	grid = SQLFORM.grid(db.t_thematics
		,details=False,editable=True,deletable=write_auth,create=write_auth,searchable=False
		,maxtextlength = 250,paginate=100
		,csv = csv, exportclasses = expClass
		,fields=[db.t_thematics.keyword]
		,orderby=db.t_thematics.keyword
	)
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, db, '#AdministrateThematicFields'),
				myText=getText(request, auth, db, '#AdministrateThematicFieldsText'),
				myTitle=getTitle(request, auth, db, '#AdministrateThematicFieldsTitle'),
				grid=grid, 
			 )



######################################################################################################################################################################
# Lists article status
# writable by developpers only!!
@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager') or auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def article_status():
	write_auth = auth.has_membership('developper')
	db.t_status_article._id.label = T('Coded representation')
	db.t_status_article._id.represent = lambda text, row: mkStatusDiv(auth, db, row.status)
	db.t_status_article.status.writable = write_auth
	grid = SQLFORM.grid( db.t_status_article
		,searchable=False, create=write_auth, details=False, deletable=write_auth
		,editable=write_auth
		,maxtextlength=500,paginate=100
		,csv=csv, exportclasses=expClass
		,fields=[db.t_status_article.status, db.t_status_article._id, db.t_status_article.priority_level, db.t_status_article.color_class, db.t_status_article.explaination]
		,orderby=db.t_status_article.priority_level
		)
	mkStatusArticles(db)
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, db, '#AdministrateArticleStatus'),
				myText=getText(request, auth, db, '#AdministrateArticleStatusText'),
				myTitle=getTitle(request, auth, db, '#AdministrateArticleStatusTitle'),
				grid=grid, 
			 )


######################################################################################################################################################################
# PDF management
@auth.requires(auth.has_membership(role='manager') or auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def manage_pdf():
	# Do the complex query in full sql and return valid ids
	myList = []
	myQy = db.executesql('SELECT r.id FROM (t_recommendations AS r JOIN t_articles AS a ON (r.article_id=a.id)) LEFT JOIN t_pdf AS p ON r.id=p.recommendation_id WHERE p.id IS NULL AND a.status IN (\'Recommended\', \'Pre-recommended\') AND r.recommendation_state LIKE \'Recommended\';')
	for q in myQy:
		myList.append(q[0])
	mySet = db((db.t_recommendations.id.belongs(myList)))
	db.t_recommendations._format = lambda row: mkRecommendationFormat2(auth, db, row)
	db.t_pdf.recommendation_id.requires=IS_IN_DB(mySet, 't_recommendations.id', db.t_recommendations._format, orderby=db.t_recommendations.id)
	db.t_pdf.recommendation_id.widget = SQLFORM.widgets.radio.widget
	grid = SQLFORM.grid( db.t_pdf
		,details=False, editable=True, deletable=True, create=True, searchable=False
		,maxtextlength=250, paginate=20
		,csv=csv, exportclasses=expClass
		,fields=[db.t_pdf.recommendation_id, db.t_pdf.pdf]
		,orderby=~db.t_pdf.id
	)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#AdminPdfText'),
				myTitle=getTitle(request, auth, db, '#AdminPdfTitle'),
				grid=grid, 
			)


######################################################################################################################################################################
# Supports management
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def manage_supports():
	grid = SQLFORM.grid( db.t_supports
		,details=False, editable=True, deletable=True, create=True, searchable=False
		,maxtextlength=512, paginate=20
		,csv=csv, exportclasses=expClass
		,orderby=db.t_supports.support_rank
	)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#AdminSupportsText'),
				myTitle=getTitle(request, auth, db, '#AdminSupportsTitle'),
				grid=grid, 
			)


######################################################################################################################################################################
# Images management
'''
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def manage_images():
	grid = SQLFORM.grid( db.t_images
		,details=False, editable=True, deletable=True, create=True, searchable=False
		,maxtextlength=512, paginate=20
		,csv=csv, exportclasses=expClass
	)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#AdminImagesText'),
				myTitle=getTitle(request, auth, db, '#AdminImagesTitle'),
				grid=grid, 
			)
'''

######################################################################################################################################################################
# Resources management
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def manage_resources():
	grid = SQLFORM.grid( db.t_resources
		,details=False, editable=True, deletable=True, create=True, searchable=False
		,maxtextlength=512, paginate=20
		,csv=csv, exportclasses=expClass
		,orderby=db.t_resources.resource_rank
	)
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#AdminResourcesText'),
				myTitle=getTitle(request, auth, db, '#AdminResourcesTitle'),
				grid=grid, 
			)


@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def recap_reviews():
	runId = str(random.randint(1, 10000))
	db.executesql('DROP VIEW IF EXISTS _v_%(runId)s;' % locals())
	db.executesql("""CREATE OR REPLACE VIEW  _v_%(runId)s AS
	WITH
	recom AS (
		SELECT r.article_id, 
			array_to_string(array_agg(DISTINCT coalesce(ru.first_name,'')||' '||coalesce(ru.last_name,'')), ', ') AS recommenders,
			max(recommendation_doi) AS recommendation_doi
		FROM t_recommendations AS r
		LEFT JOIN auth_user AS ru ON r.recommender_id = ru.id
		GROUP BY r.article_id
	)
	, corecom AS (
		SELECT r.article_id,
			array_to_string(array_agg(DISTINCT coalesce(cru.first_name,'')||' '||coalesce(cru.last_name,'')), ', ') AS co_recommenders
		FROM t_press_reviews AS co
		LEFT JOIN auth_user AS cru ON co.contributor_id = cru.id
		LEFT JOIN t_recommendations AS r ON co.recommendation_id = r.id
		GROUP BY r.article_id
	)
	, recomms0 AS (
		SELECT r.article_id, r.id AS recom_id,
			rank() OVER (PARTITION BY r.article_id ORDER BY r.id) AS recomm_round, 
			r.recommendation_state AS decision, 
			r.recommendation_timestamp::date AS decision_start,
			r.last_change::date AS decision_last_change
		FROM t_recommendations AS r
	)
	, reviews AS (
		SELECT article_id, w.recommendation_id AS recomm_id, recomm_round,
			to_char(rank() OVER (PARTITION BY w.recommendation_id ORDER BY w.id), '00') AS reviewer_num,
			CASE WHEN anonymously THEN '[ANON] ' ELSE '' END||coalesce(wu.first_name,'')||' '||coalesce(wu.last_name,'') AS reviewer
		FROM t_reviews AS w
		LEFT JOIN auth_user AS wu ON w.reviewer_id = wu.id
		LEFT JOIN recomms0 ON w.recommendation_id = recomms0.recom_id
		WHERE w.review_state NOT IN ('Pending', 'Declined', 'Cancelled')
		UNION ALL
		SELECT article_id, recom_id AS recomm_id, recomm_round,
			'decision'::varchar AS reviewer_num,
			decision
		FROM recomms0
		UNION ALL
		SELECT article_id, recom_id AS recomm_id, recomm_round,
			'00_start'::varchar AS reviewer_num,
			decision_start::varchar
		FROM recomms0
		UNION ALL
		SELECT article_id, recom_id AS recomm_id, recomm_round,
			'last_change'::varchar AS reviewer_num,
			decision_last_change::varchar
		FROM recomms0
		UNION ALL
		SELECT article_id, recom_id AS recomm_id, recomm_round,
			'supp_info'::varchar AS reviewer_num,
			''::varchar
		FROM recomms0
	)
	SELECT  CASE WHEN a.already_published THEN 'Postprint' ELSE 'Preprint' END AS type_article,
		a.title, a.doi AS article_doi, a.id AS article_id,
		coalesce(au.first_name,'')||' '||coalesce(au.last_name,'') AS submitter,
		a.upload_timestamp::date AS submission,
		''::varchar AS first_outcome,
		coalesce(recom.recommenders, '') AS recommenders,
		coalesce(corecom.co_recommenders, '') AS co_recommenders,
		a.status AS article_status, a.last_status_change::date AS article_status_last_change,
		coalesce(recom.recommendation_doi, '') AS recommendation_doi,
		''::varchar AS recommendation_info,
		coalesce(reviews.recomm_round, 1) AS recomm_round, 
		coalesce(reviews.reviewer_num, ' 01') AS reviewer_num, 
		coalesce(reviews.reviewer, '') AS reviewer
	FROM t_articles AS a
	LEFT JOIN auth_user AS au ON a.user_id = au.id
	LEFT JOIN recom ON recom.article_id = a.id
	LEFT JOIN corecom ON corecom.article_id = a.id
	LEFT JOIN reviews ON reviews.article_id = a.id
	ORDER BY a.id DESC, recomm_round ASC;""" % locals())

	db.executesql("""SELECT colpivot('_t_%(runId)s', 
		'SELECT * FROM _v_%(runId)s', 
		array['type_article', 'title', 'article_doi', 'article_id', 'submitter', 'submission', 'first_outcome', 'recommenders', 'co_recommenders', 'article_status', 'article_status_last_change', 'recommendation_doi', 'recommendation_info'],
		array['recomm_round', 'reviewer_num'], 
		'#.reviewer',
		null
	);""" % locals())

	# Get columns as header
	head = TR()
	cols = db.executesql("""SELECT column_name FROM information_schema.columns WHERE table_name  LIKE '_t_%(runId)s'  ORDER BY ordinal_position;""" % locals())
	pat = re.compile(r"'(\d+)', '(.*)'")
	iCol = 0
	revwCols = []
	for cc in cols:
		c = cc[0]
		patMatch = pat.match(c)
		if patMatch:
			revRound = patMatch.group(1)
			field = patMatch.group(2)
			rn = re.match(r'^ ?(\d+)$', field)
			if field == '00_start':
				field = 'Start'
			elif rn:
				rwNum = int(rn.group(1))
				field = 'Rev._%s' % (rwNum)
				revwCols.append(iCol)
			c = SPAN(SPAN('ROUND_#'+revRound+' '), SPAN(field))
		head.append(TH(c))
		if iCol in revwCols:
			head.append(TH(c, SPAN(' quality')))
			head.append(TH(c, SPAN(' info')))
		iCol += 1
	grid = TABLE(_class='pci-AdminReviewsSynthesis')
	grid.append(head)
	
	resu = db.executesql("""SELECT * FROM _t_%(runId)s ORDER BY article_id;""" % locals())
	for r in resu:
		row = TR()
		iCol = 0
		for (v) in r:
			row.append(TD(v or ''))
			if iCol in revwCols:
				row.append(TD(''))
				row.append(TD(''))
			iCol += 1
		grid.append(row)
	
	db.executesql('DROP VIEW IF EXISTS _v_%(runId)s;' % locals())
	db.executesql('DROP TABLE IF EXISTS _t_%(runId)s;' % locals())
	response.view='default/myLayout.html'
	return dict(
				myText=getText(request, auth, db, '#AdminRecapReviews'),
				myTitle=getTitle(request, auth, db, '#AdminRecapReviewsTitle'),
				grid=DIV(grid, _style="width:100%; overflow-x:scroll;"), 
			)




######################################################################################################################################################################
def recommLatex(articleId):
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('public', 'recommended_articles', user_signature=True))

	template = """
\\documentclass[a4paper]{article}
\\usepackage[top=7cm,bottom=2.5cm,headheight=120pt,headsep=15pt,left=6cm,right=1.5cm,marginparwidth=4cm,marginparsep=0.5cm]{geometry}
\\usepackage{marginnote}
\\reversemarginpar  %% sets margin notes to the left
\\usepackage{lipsum} %% Required to insert dummy text
\\usepackage{calc}
\\usepackage{siunitx}
\\usepackage{xpatch}
%%\\usepackage[none]{hyphenat} %% use only if there is a problem 
%% Use Unicode characters
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
%% Clean citations with biblatex
\\usepackage[
backend=biber,
natbib=true,
sortcites=true,
defernumbers=true,
style=authoryear-comp,
maxnames=99,
maxcitenames=2,
uniquename=init,
giveninits=true,
terseinits=true, %% change to 'false' for initials like L. D.
url=false,
dashed=false
]{biblatex}
\\DeclareNameAlias{default}{family-given}
\\DeclareNameAlias{sortname}{family-given}
\\renewcommand*{\\revsdnamepunct}{} %% no comma between family and given names
\\renewcommand*{\\nameyeardelim}{\\addspace} %% remove comma inline citations
\\renewbibmacro{in:}{%%
  \\ifentrytype{article}{}{\\printtext{\\bibstring{in}\\intitlepunct}}} %% remove 'In:' before journal name
\\DeclareFieldFormat[article]{pages}{#1} %% remove pp.
\\AtEveryBibitem{\\ifentrytype{article}{\\clearfield{number}}{}} %% don't print issue numbers
\\DeclareFieldFormat[article, inbook, incollection, inproceedings, misc, thesis, unpublished]{title}{#1} %% title without quotes
\\preto\\fullcite{\\AtNextCite{\\defcounter{maxnames}{99}}} %% print all authors when using \\fullcite
\\xpretobibmacro{date+extrayear}{\\setunit{\\addperiod\space}}{}{} %% add a dot after last author (requires package xpatch)
\\usepackage{csquotes}
\\RequirePackage[english]{babel} %% must be called after biblatex
\\addbibresource{%(bibfile)s}
\\DeclareBibliographyCategory{ignore}
\\addtocategory{ignore}{recommendation} %% adding recommendation to 'ignore' category so that it does not appear in the References

%% Clickable references. Use \\url{www.example.com} or \\href{www.example.com}{description} to add a clicky url
\\usepackage{nameref}
\\usepackage[pdfborder={0 0 0}]{hyperref}  %% sets link border to white
\\urlstyle{same}

%% Include figures
\\usepackage{graphbox} %% loads graphicx ppackage with extended options for vertical alignment of figures

%% Improve typesetting in LaTex
\\usepackage{microtype}
\\DisableLigatures[f]{encoding = *, family = * }

%% Text layout and font (Open Sans)
\\setlength{\\parindent}{0.4cm}
\\linespread{1.2}
\\RequirePackage[default,scale=0.90]{opensans}

%% Defining document colors
\\usepackage{xcolor}
\\definecolor{darkgray}{HTML}{808080}
\\definecolor{mediumgray}{HTML}{6D6E70}
\\definecolor{ligthgray}{HTML}{d9d9d9}
\\definecolor{pciblue}{HTML}{74adca}
\\definecolor{opengreen}{HTML}{77933c}

%% Use adjustwidth environment to exceed text width
\\usepackage{changepage}

%% Headers and footers
\\usepackage{fancyhdr}  %% custom headers/footers
\\usepackage{lastpage}  %% number of page in the document
\\pagestyle{fancy}  %% enables customization of headers/footers
\\fancyhfoffset[L]{4.5cm}  %% offsets header and footer to the left to include margin
\\renewcommand{\\headrulewidth}{\\ifnum\\thepage=1 0.5pt \\else 0pt \\fi} %% header ruler only on first page
\\renewcommand{\\footrulewidth}{0.5pt}
\\lhead{\\includegraphics[width=13.5cm]{%(logo)s}}  %% full logo on first page 
\\chead{}
\\rhead{}
\\lfoot{\\scriptsize \\textsc{\\color{mediumgray}%(applongname)s}}
\\cfoot{}
\\rfoot{}

\\begin{document}
\\vspace*{0.5cm}
\\newcommand{\\preprinttitle}{%(title)s}
\\newcommand{\\preprintauthors}{%(authors)s}

\\newcommand{\\whodidit}{%(whoDidIt)s}
\\newcommand{\\DOI}{%(doi)s}
\\newcommand{\\DOIlink}{\\href{%(doiLink)s}{\\DOI}}

\\begin{flushleft}
\\baselineskip=30pt
\\marginpar{\\includegraphics[align=c,width=0.5cm]{%(logoOA)s} \\space \\large\\textbf{\\color{pciblue}Open Access}\\\\
\\\\
\\large\\textnormal{\\color{pciblue}RESEARCH ARTICLE}}
{\\Huge\\fontseries{sb}\\selectfont{\\preprinttitle}}
\\end{flushleft}
\\vspace*{0.75cm}
%% Author(s)
\\begin{flushleft}
\\Large\\preprintauthors\\\\
\\vspace*{0.75cm}
%% Citation
\\noindent
\\fcolorbox{lightgray}{lightgray}{
\\parbox{\\textwidth - 2\\fboxsep}{
\\raggedright\\normalsize\\textbf{Cite as:}\\newline
\\fullcite{preprint}}}\\\\
\\vspace*{1.75cm}
%% Recommendation box
\\fcolorbox{pciblue}{pciblue}{
\\parbox{\\textwidth - 2\\fboxsep}{
\\vspace{0.25cm}
\\large \\textbf{Peer-reviewed and recommended by \\href{%(siteUrl)s}{%(applongname)s}}
\\vspace{0.5cm}\\newline
\\normalsize
\\textbf{Recommendation DOI:} \\space \\DOIlink
%%\\newline
%%\\textbf{Published:} \\space \\today
\\newline
\\textbf{Recommender(s):} \\space \\whodidit
\\newline

\\vspace{0.25cm}}}

\\end{flushleft}

\\end{document}

"""
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname = myconf.take('app.description')
	logo = os.path.normpath(os.path.join(request.folder, 'static', 'images', 'background.png'))
	logoOA = os.path.normpath(os.path.join(request.folder, 'static', 'images', 'Open_Access_logo_PLoS_white_blue.png'))
	title = art.title
	authors = art.authors
	whoDidIt = SPAN(mkWhoDidIt4Article(auth, db, art, with_reviewers=True, linked=False, host=host, port=port, scheme=scheme)).flatten()
	reviewers = ""
	doi = art.doi
	doiLink = mkLinkDOI(art.doi)
	siteUrl = URL(c='default', f='index', scheme=scheme, host=host, port=port)
	fd, bibfile = tempfile.mkstemp(suffix='.bib')
	print bibfile
	bib = recommBibtex(articleId)
	with os.fdopen(fd, 'w') as tmp:
		tmp.write(bib)
	resu = template % locals()
	return(resu)

def recommBibtex(articleId):
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('public', 'recommended_articles', user_signature=True))

	lastRecomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
	template = """@article{recommendation,
title = {%(title)s},
doi = {%(doi)s},
journal = {%(applongname)s},
author = {%(whoDidIt)s},
year = {%(year)s},
eid = {%(eid)s},
},
@article{preprint,
title = {%(Atitle)s},
doi = {%(Adoi)s},
author = {%(Aauthors)s},
year = {%(Ayear)s},
}"""
	title = lastRecomm.recommendation_title
	doi = lastRecomm.doi
	applongname = myconf.take('app.description')
	whoDidIt = SPAN(mkWhoDidIt4Article(auth, db, art, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)).flatten()
	year = art.last_status_change.year
	pat = re.search('\\.(?P<num>\d+)$', doi)
	if pat:
		eid = pat.group('num') or ''
	else:
		eid = ''
	Atitle = art.title
	Adoi = art.doi
	Aauthors = art.authors
	Ayear = year
	resu = template % locals()
	return(resu)



######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def rec_as_latex():
	if ('articleId' in request.vars):
		articleId = request.vars['articleId']
	elif ('id' in request.vars):
		articleId = request.vars['id']
	else:
		session.flash = T('Unavailable')
		redirect(URL('public', 'recommended_articles', user_signature=True))
	# NOTE: check id is numeric!
	if (not articleId.isdigit()):
		session.flash = T('Unavailable')
		redirect(URL('public', 'recommended_articles', user_signature=True))
	
	bib = recommBibtex(articleId)
	latFP = recommLatex(articleId)
	message = DIV(
			H2('BibTex:'),
			PRE(bib), 
			H2('Front page:'),
			PRE(latFP),
		)
	response.view='default/info.html'
	return(dict(message=message))




######################################################################################################################################################################
#@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
#def test_tweet():
	#message = ''
	#scheme=myconf.take('alerts.scheme')
	#host=myconf.take('alerts.host')
	#port=eval(myconf.take('alerts.port'))
	#link = URL(c='about', f='social', scheme=scheme, host=host, port=port)
	#print 'To be tweeted:', A(link, _href=link)
	#tweeterAcc = myconf.get('social.tweeter')
	#consumer_key = myconf.get('social.tweeter_consumer_key')
	#consumer_secret = myconf.get('social.tweeter_consumer_secret')
	#access_token = myconf.get('social.tweeter_access_token')
	#access_token_secret = myconf.get('social.tweeter_access_token_secret')
	#if consumer_key and consumer_secret and access_token and access_token_secret :
		#try:
			#twAuth = tweepy.OAuthHandler(consumer_key, consumer_secret)
			#twAuth.set_access_token(access_token, access_token_secret)
			#api = tweepy.API(twAuth)
			#api.update_status(status="Test: "+datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')+" "+link)
			#if tweeterAcc:
				#frames = []
				#frames.append(H2('Tweeter'))
				#frames.append(DIV(XML('<a class="twitter-timeline" href="https://twitter.com/%s">Tweets by %s</a> <script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>' % (tweeterAcc, tweeterAcc)), _class='tweeterPanel'))
				#message = DIV(frames, _class='pci-socialDiv')
		#except:
			#message = T('Failure!')
			#pass
	#else:
		#message = T('Configure private/appconfig.ini')
	#response.view='default/info.html'
	#return dict(
				#myHelp=getHelp(request, auth, db, '#AdministrateTestTweet'),
				#myText=getText(request, auth, db, '#AdministrateTestTweetText'),
				#myTitle=getTitle(request, auth, db, '#AdministrateTestTweetTitle'),
				#message=message,
			 #)
