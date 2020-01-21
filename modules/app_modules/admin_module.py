# -*- coding: utf-8 -*-

import re
import copy
import random
import os
import datetime
import tempfile
import shutil

# sudo pip install tweepy
#import tweepy
from gluon.contrib.markdown import WIKI

from app_modules.common import *
from app_modules.emailing import *
from app_modules.helper import *

from gluon.contrib.markmin.markmin2latex import render, latex_escape

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)


######################################################################################################################################################################
## (gab) Helper => move to modules ?
######################################################################################################################################################################
def mkRoles(row, auth, db):
	if auth.has_membership(role='administrator') or auth.has_membership(role='developper'):
		resu = ''
		if row.id:
			roles = db.v_roles[row.id]
			if roles:
				resu = SPAN(roles.roles)
		return resu

######################################################################################################################################################################
def set_as_recommender(ids, auth, db):
	if auth.has_membership(role='administrator') or auth.has_membership(role='developper'):

		# get recommender group id
		recommRoleId = (db(db.auth_group.role == 'recommender').select(db.auth_group.id).last())["id"]
		for myId in ids:
			# check not already recommender
			isAlreadyRecommender = db((db.auth_membership.user_id==myId) & (db.auth_membership.group_id==recommRoleId)).count()
			if (isAlreadyRecommender == 0):
				# insert membership
				db.auth_membership.insert(user_id=myId, group_id=recommRoleId)


######################################################################################################################################################################
def recommLatex(articleId, tmpDir, withHistory=False):
	print '******************************************************', withHistory
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
	template = """
\\documentclass[a4paper]{article}
\\usepackage[top=7cm,bottom=2.5cm,headheight=120pt,headsep=15pt,left=6cm,right=1.5cm,marginparwidth=4cm,marginparsep=0.5cm]{geometry}
\\usepackage{marginnote}
\\reversemarginpar  %% sets margin notes to the left
\\usepackage{lipsum} %% Required to insert dummy text
\\usepackage{calc}
\\usepackage{siunitx}
\\usepackage{pdfpages}
%%\\usepackage[none]{hyphenat} %% use only if there is a problem 
%% Use Unicode characters
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
\\usepackage{newunicodechar}
%%\\usepackage{textcomp}
\\usepackage{filecontents}
\\begin{filecontents}{\\jobname.bib}
%(bib)s
\\end{filecontents}
%% Clean unsupported unicode chars
\\DeclareUnicodeCharacter{B0}{\\textdegree}
\\DeclareUnicodeCharacter{A0}{ }
\\DeclareUnicodeCharacter{AD}{\\-}
\\DeclareUnicodeCharacter{20AC}{\\euro}
\\newunicodechar{−}{--}

%% Clean citations with biblatex
\\usepackage[
backend=biber,
natbib=true,
sortcites=true,
defernumbers=true,
citestyle=numeric-comp,
maxnames=99,
maxcitenames=2,
uniquename=init,
%%giveninits=true,
terseinits=true, %% change to 'false' for initials like L. D.
url=false,
]{biblatex}
\\DeclareNameAlias{default}{family-given}
\\DeclareNameAlias{sortname}{family-given}
%%\\renewcommand*{\\revsdnamepunct}{} %% no comma between family and given names
\\renewcommand*{\\nameyeardelim}{\\addspace} %% remove comma inline citations
\\renewbibmacro{in:}{%%
  \\ifentrytype{article}{}{\\printtext{\\bibstring{in}\\intitlepunct}}} %% remove 'In:' before journal name
\\DeclareFieldFormat[article]{pages}{#1} %% remove pp.
\\AtEveryBibitem{\\ifentrytype{article}{\\clearfield{number}}{}} %% don't print issue numbers
\\DeclareFieldFormat[article, inbook, incollection, inproceedings, misc, thesis, unpublished]{title}{#1} %% title without quotes
\\usepackage{csquotes}
\\RequirePackage[english]{babel} %% must be called after biblatex
\\addbibresource{\\jobname.bib}
%%\\addbibresource{%% ( bibfile ) s}
\\DeclareBibliographyCategory{ignore}
\\addtocategory{ignore}{recommendation} %% adding recommendation to 'ignore' category so that it does not appear in the References

%% Clickable references. Use \\url{www.example.com} or \\href{www.example.com}{description} to add a clicky url
\\usepackage{nameref}
\\usepackage[pdfborder={0 0 0}]{hyperref}  %% sets link border to white
\\urlstyle{same}

%% Include figures
%%\\usepackage{graphbox} %% loads graphicx package with extended options for vertical alignment of figures
\\usepackage{graphicx}

%% Line numbers
%%\\usepackage[right]{lineno}

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

%% Adjust caption style
\\usepackage[aboveskip=1pt,labelfont=bf,labelsep=period,singlelinecheck=off]{caption}

%% Headers and footers
\\usepackage{fancyhdr}  %% custom headers/footers
\\usepackage{lastpage}  %% number of page in the document
\\pagestyle{fancy}  %% enables customization of headers/footers
\\fancyhfoffset[L]{4.5cm}  %% offsets header and footer to the left to include margin
\\renewcommand{\\headrulewidth}{\\ifnum\\thepage=1 0.5pt \\else 0pt \\fi} %% header ruler only on first page
\\renewcommand{\\footrulewidth}{0.5pt}
\\lhead{\\ifnum\\thepage=1 \\includegraphics[width=13.5cm]{%(logo)s} \\else \\includegraphics[width=5cm]{%(smalllogo)s} \\fi}  %% full logo on first page, then small logo on subsequent pages 
\\chead{}
\\rhead{}
\\lfoot{\\scriptsize \\textsc{\\color{mediumgray}%(applongname)s}}
\\cfoot{}
\\rfoot{}
\\begin{document}
\\vspace*{0.5cm}
\\newcommand{\\preprinttitle}{%(Atitle)s}
\\newcommand{\\preprintauthors}{%(Aauthors)s}
\\newcommand{\\recommendationtitle}{%(title)s}
\\newcommand{\\datepub}{%(datePub)s}
\\newcommand{\\email}{%(emailRecomm)s}
\\newcommand{\\recommenders}{%(recommenders)s}
\\newcommand{\\affiliations}{%(affiliations)s}
\\newcommand{\\reviewers}{%(reviewers)s}
\\newcommand{\\DOI}{%(doi)s}
\\newcommand{\\DOIlink}{\\href{%(doiLink)s}{\\DOI}}
\\begin{flushleft}
\\baselineskip=30pt
%%\\marginpar{\\includegraphics[align=c,width=0.5cm]{%(logoOA)s} \\space \\large\\textbf{\\color{opengreen}Open Access}\\\\
\\marginpar{\\includegraphics[width=0.5cm]{%(logoOA)s} \\space \\large\\textbf{\\color{opengreen}Open Access}\\\\
\\\\
\\large\\textnormal{\\color{opengreen}RECOMMENDATION}}
{\\Huge
\\fontseries{sb}\\selectfont{\\recommendationtitle}}
\\end{flushleft}
\\vspace*{0.75cm}
%% Author(s)  %% update if multiple recommenders
\\begin{flushleft}
\\Large
\\recommenders

%% Margin information
\\marginpar{\\raggedright
\\scriptsize\\textbf{Cite as:}\\space
\\fullcite{recommendation}\\\\
\\vspace*{0.5cm}
\\textbf{Published:} \datepub\\\\
\\vspace*{0.5cm}
\\textbf{Based on reviews by:}\\\\
\\reviewers\\\\
\\vspace*{0.5cm}
\\textbf{Correspondence:}\\\\
\\href{mailto:\\email}{\\email}\\\\
%%\\vspace*{0.5cm} %% remove line if no ORCID
%%\\textbf{ORCID:}\\\\ %% remove line if no ORCID
%%\\href{https://orcid.org/\\ORCID}{\\ORCID}\\ %% remove line if no ORCID / Add \\space (initials) if multiple recommenders
\\vspace*{3cm}
%%\\textnormal{\\copyright \\space \\number\\year \\space \\recommender}\\\\ %% update if there are more than one recommender
\\vspace*{0.2cm}
%%\\includegraphics[align=c,width=0.4cm]{%(ccPng)s} \\includegraphics[align=c,width=0.4cm]{%(byPng)s} \\includegraphics[align=c,width=0.4cm]{%(ndPng)s} \\space\\space \\textnormal{\\href{https://creativecommons.org/licenses/by-nd/4.0/}{CC-BY-ND 4.0}}\\\\
\\includegraphics[width=0.4cm]{%(ccPng)s} \\includegraphics[width=0.4cm]{%(byPng)s} \\includegraphics[width=0.4cm]{%(ndPng)s} \\space\\space \\textnormal{\\href{https://creativecommons.org/licenses/by-nd/4.0/}{CC-BY-ND 4.0}}\\\\
\\vspace*{0.2cm}
\\textnormal{This work is licensed under the Creative Commons Attribution-NoDerivatives 4.0 International License.}
}
\\end{flushleft}
\\bigskip

%% Affiliation(s)
{\\raggedright \\affiliations}

%% Recommended preprint box
\\begin{flushleft}
\\noindent
\\fcolorbox{lightgray}{lightgray}{
\\parbox{\\textwidth - 2\\fboxsep}{
\\raggedright\\large{\\fontseries{sb}\\selectfont{A recommendation of}}\\
\\small \\fullcite{preprint}}}
\\end{flushleft}
\\vspace*{0.5cm}

%%%% RECOMMENDATION %%%%
%(recommendation)s

\\printbibliography[notcategory=ignore]
\\section*{Appendix}
Reviews by \\reviewers, \\href{https://dx.doi.org/\\DOI}{DOI: \\DOI}

%%%% HISTORY %%%%
%(history)s

\\end{document}

"""
	scheme=myconf.take('alerts.scheme')
	host=myconf.take('alerts.host')
	port=myconf.take('alerts.port', cast=lambda v: takePort(v) )
	applongname = latex_escape(myconf.take('app.description'))
	logo = os.path.normpath(os.path.join(request.folder, 'static', 'images', 'background.png'))
	smalllogo = os.path.normpath(os.path.join(request.folder, 'static', 'images', 'small-background.png'))
	logoOA = os.path.normpath(os.path.join(request.folder, 'static', 'images', 'Open_Access_logo_PLoS_white_green.png'))
	ccPng = os.path.normpath(os.path.join(request.folder, 'static', 'images', 'cc_large.png'))
	byPng = os.path.normpath(os.path.join(request.folder, 'static', 'images', 'by_large.png'))
	ndPng = os.path.normpath(os.path.join(request.folder, 'static', 'images', 'nd_large.png'))
	Atitle = latex_escape(art.title)
	Aauthors = latex_escape(art.authors)
	lastRecomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
	recommds = mkRecommendersList(auth, db, lastRecomm)
	n = len(recommds)
	recommenders = '\n'
	cpt = 1
	for r in recommds:
		recommenders += latex_escape(r)
		recommenders += '\\textsuperscript{%d}' % cpt
		if (cpt > 1 and cpt < n-1):
			recommenders += ', '
		elif (cpt < n):
			recommenders += ' and '
		recommenders += '\n'
		cpt += 1
	affil = mkRecommendersAffiliations(auth, db, lastRecomm)
	affiliations = '\n'
	cpt = 1
	for a in affil:
		affiliations += '\\textsuperscript{%d}' % cpt
		affiliations += latex_escape(a)
		affiliations += '\\\\\n'
		cpt += 1
	reviewers = latex_escape(mkReviewersString(auth, db, articleId))
	title = latex_escape(lastRecomm.recommendation_title)
	datePub = latex_escape((datetime.date.today()).strftime('%A %B %d %Y'))
	firstRecomm = db.auth_user[lastRecomm.recommender_id]
	if firstRecomm:
		emailRecomm = latex_escape(firstRecomm.email)
	else:
		emailRecomm = ''
	doi = latex_escape(art.doi)
	doiLink = mkLinkDOI(art.doi)
	siteUrl = URL(c='default', f='index', scheme=scheme, host=host, port=port)
	bib = recommBibtex(articleId)
	#fd, bibfile = tempfile.mkstemp(suffix='.bib')
	#bibfile = "/tmp/sample.bib"
	#with open(bibfile, 'w') as tmp:
		#tmp.write(bib)
		#tmp.close()
	recommendation = lastRecomm.recommendation_comments
	#recommendation = recommendation.decode("utf-8").replace(unichr(160), u' ').encode("utf-8") # remove unbreakable space by space ::: replaced by latex command DO NOT UNCOMMENT!
	#with open('/tmp/laRecomm.txt', 'w') as tmp:
		#tmp.write(recommendation)
		#tmp.close()
	recommendation = (render(recommendation))[0]
	
	# NOTE: Standard string for using \includepdf for external documents
	incpdfcmd = '\\includepdf[pages={-},scale=.7,pagecommand={},offset=0mm -20mm]{%s}\n'
	history = ''
	if (withHistory and art.already_published is False):
		history = '\\clearpage\\section*{Review process}\n'
		allRecomms = db(db.t_recommendations.article_id == art.id).select(orderby=~db.t_recommendations.id)
		nbRecomms = len(allRecomms)
		iRecomm = 0
		roundNb = nbRecomms+1
		for recomm in allRecomms:
			iRecomm += 1
			roundNb -= 1
			x = latex_escape('Revision round #%s' % roundNb)
			history += '\\subsection*{%s}\n' % x
			#roundRecommender = db(db.auth_user.id==recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
			whoDidIt = mkWhoDidIt4Recomm(auth, db, recomm, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)
			# Decision if not last recomm
			if iRecomm > 1:
				history += '\\subsubsection*{Decision by %s}\n' % SPAN(whoDidIt).flatten()
				x = latex_escape(recomm.recommendation_title)
				history += '{\\bf %s}\\par\n' % x
				x = (render(recomm.recommendation_comments))[0]
				history += x + '\n\n\n'
				
			# Check for reviews
			reviews = db( (db.t_reviews.recommendation_id==recomm.id) & (db.t_reviews.review_state=='Completed') ).select(orderby=~db.t_reviews.id)
			if len(reviews) > 0:
				history += '\\subsubsection*{Reviews}\n'
				history += '\\begin{itemize}\n'
				for review in reviews:
					# display the review
					if review.anonymously:
						x = latex_escape(current.T('Reviewed by')+' '+current.T('anonymous reviewer')+(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else ''))
						history += '\\item{%s}\\par\n' % x
					else:
						x = latex_escape(current.T('Reviewed by')+' '+mkUser(auth, db, review.reviewer_id, linked=False).flatten()+(', '+review.last_change.strftime('%Y-%m-%d %H:%M') if review.last_change else ''))
						history += '\\item{%s}\\par\n' % x
					if len(review.review or '')>2:
						x = (render(review.review))[0]
						history += x + '\n\n\n'
						if review.review_pdf:
							x = os.path.join(tmpDir, 'review_%d.pdf' % review.id)
							with open(x, 'w') as tmp:
								tmp.write(review.review_pdf_data)
								tmp.close()
							history += incpdfcmd % x
					elif review.review_pdf:
						x = os.path.join(tmpDir, 'review_%d.pdf' % review.id)
						with open(x, 'w') as tmp:
							tmp.write(review.review_pdf_data)
							tmp.close()
						history += incpdfcmd % x
					else:
						pass
				history += '\\end{itemize}\n'
			
			# Author's reply
			if len(recomm.reply) > 2 or recomm.reply_pdf: 
				history += '\\subsubsection*{Authors\' reply}\n'
			if len(recomm.reply) > 2: 
				x = (render(recomm.reply))[0]
				history += x + '\n\n\n'
			if recomm.reply_pdf: 
				x = os.path.join(tmpDir, 'reply_%d.pdf' % recomm.id)
				with open(x, 'w') as tmp:
					tmp.write(recomm.reply_pdf_data)
					tmp.close()
				history += incpdfcmd % x
			
	resu = template % locals()
	return(resu)


def recommBibtex(articleId):
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))

	lastRecomm = db(db.t_recommendations.article_id==articleId).select(orderby=db.t_recommendations.id).last()
	template = """@article{recommendation,
		title = {%(title)s},
		doi = {%(doi)s},
		journal = {%(applongname)s},
		author = {%(whoDidIt)s},
		year = {%(year)s},
		eid = {%(eid)s},
		}

		@article{preprint,
		title = {%(Atitle)s},
		doi = {%(Adoi)s},
		author = {%(Aauthors)s},
		year = {%(Ayear)s},
		}
	"""
	title = latex_escape(lastRecomm.recommendation_title)
	doi = latex_escape(lastRecomm.doi)
	applongname = latex_escape(myconf.take('app.description'))
	whoDidIt = latex_escape(SPAN(getRecommAndReviewAuthors(auth, db, art, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)).flatten())
	year = art.last_status_change.year
	pat = re.search('\\.(?P<num>\d+)$', doi)
	if pat:
		eid = pat.group('num') or ''
	else:
		eid = ''
	Atitle = latex_escape(art.title)
	Adoi = latex_escape(art.doi)
	Aauthors = latex_escape(art.authors)
	Ayear = year
	resu = template % locals()
	return(resu)



######################################################################################################################################################################
def frontPageLatex(articleId):
	art = db.t_articles[articleId]
	if art == None:
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))

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
\\usepackage{filecontents}
\\begin{filecontents}{\\jobname.bib}
%(bib)s
\\end{filecontents}
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
%%giveninits=true,
terseinits=true, %% change to 'false' for initials like L. D.
url=false,
dashed=false
]{biblatex}
\\DeclareNameAlias{default}{family-given}
\\DeclareNameAlias{sortname}{family-given}
%%\\renewcommand*{\\revsdnamepunct}{} %% no comma between family and given names
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
\\addbibresource{\\jobname.bib}
\\DeclareBibliographyCategory{ignore}
\\addtocategory{ignore}{recommendation} %% adding recommendation to 'ignore' category so that it does not appear in the References

%% Clickable references. Use \\url{www.example.com} or \\href{www.example.com}{description} to add a clicky url
\\usepackage{nameref}
\\usepackage[pdfborder={0 0 0}]{hyperref}  %% sets link border to white
\\urlstyle{same}

%% Include figures
%%\\usepackage{graphbox} %% loads graphicx package with extended options for vertical alignment of figures
\\usepackage{graphicx}

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
%%\\marginpar{\\includegraphics[align=c,width=0.5cm]{%(logoOA)s} \\space \\large\\textbf{\\color{pciblue}Open Access}\\\\
\\marginpar{\\includegraphics[width=0.5cm]{%(logoOA)s} \\space \\large\\textbf{\\color{pciblue}Open Access}\\\\
\\\\
\\large\\textnormal{\\color{pciblue}RESEARCH ARTICLE}}
{\\Huge\\fontseries{sb}\\selectfont{\\preprinttitle}}
\\end{flushleft}
\\vspace*{0.75cm}
%% Author(s)
\\begin{flushleft}
\\Large\\preprintauthors\\
\\
\\vspace*{0.75cm}
%% Citation
\\noindent
\\fcolorbox{lightgray}{lightgray}{
\\parbox{\\textwidth - 2\\fboxsep}{
\\raggedright\\normalsize\\textbf{Cite as:}\\newline
\\fullcite{preprint}}}\\
\\
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
	whoDidIt = latex_escape(SPAN(getRecommAndReviewAuthors(auth, db, art, with_reviewers=True, linked=False, host=host, port=port, scheme=scheme)).flatten())
	reviewers = ""
	doi = art.doi
	doiLink = mkLinkDOI(art.doi)
	siteUrl = URL(c='default', f='index', scheme=scheme, host=host, port=port)
	bib = recommBibtex(articleId)
	#fd, bibfile = tempfile.mkstemp(suffix='.bib')
	#with os.fdopen(fd, 'w') as tmp:
		#tmp.write(bib)
		#tmp.close()
	bibfile = "/tmp/sample.bib"
	with open(bibfile, 'w') as tmp:
		tmp.write(bib)
		tmp.close()
	resu = template % locals()
	return(resu)
