# -*- coding: utf-8 -*-

import re
import copy
import random
import os
import tempfile
import shutil

# sudo pip install tweepy
#import tweepy
from gluon.contrib.markdown import WIKI

from app_modules.common import *
from app_modules.emailing import *
from app_modules.helper import *
from app_modules import admin_module

from gluon.contrib.markmin.markmin2latex import render, latex_escape

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)


# frequently used constants
csv = False # no export allowed
expClass = dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4


######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def testMail():
	print('starting test mail')
	do_send_email_to_test(session, auth, db, auth.user_id)
	redirect(request.env.http_referer)


######################################################################################################################################################################
## (gab) note : Unused functions ?
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
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def rec_as_pdf():
	if ('articleId' in request.vars):
		articleId = request.vars['articleId']
	elif ('id' in request.vars):
		articleId = request.vars['id']
	else:
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
	if (not articleId.isdigit()):
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
	
	tmpDir = tempfile.mkdtemp()
	cwd = os.getcwd()
	os.chdir(tmpDir)
	art = db.t_articles[articleId]
	withHistory = ('withHistory' in request.vars)
	latRec = admin_module.recommLatex(articleId, tmpDir, withHistory)
	texfile = "recomm.tex"
	with open(texfile, 'w') as tmp:
		tmp.write(latRec)
		tmp.close()
	biber = myconf.take('config.biber')
	pdflatex = myconf.take('config.pdflatex')
	cmd = "%(pdflatex)s recomm ; %(biber)s recomm ; %(pdflatex)s recomm" % locals()
	os.system(cmd)
	pdffile = 'recomm.pdf'
	if os.path.isfile(pdffile):
		with open(pdffile, 'rb') as tmp:
			pdf = tmp.read()
			tmp.close()
		os.chdir(cwd)
		shutil.rmtree(tmpDir)
		response.headers['Content-Type']='application/pdf'
		response.headers['Content-Disposition'] = 'inline; filename="{0}_recommendation.pdf"'.format(art.title)
		return(pdf)
	else:
		os.chdir(cwd)
		#shutil.rmtree(tmpDir) ## For further examination
		session.flash = T('Failed :-(')
		redirect(request.env.http_referer)

######################################################################################################################################################################
@auth.requires(auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def fp_as_pdf():
	if ('articleId' in request.vars):
		articleId = request.vars['articleId']
	elif ('id' in request.vars):
		articleId = request.vars['id']
	else:
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
	if (not articleId.isdigit()):
		session.flash = T('Unavailable')
		redirect(URL('articles', 'recommended_articles', user_signature=True))
	
	art = db.t_articles[articleId]
	latFP = admin_module.frontPageLatex(articleId)
	tmpDir = tempfile.mkdtemp()
	cwd = os.getcwd()
	os.chdir(tmpDir)
	texfile = "frontpage.tex"
	with open(texfile, 'w') as tmp:
		tmp.write(latFP)
		tmp.close()
	biber = myconf.take('config.biber')
	pdflatex = myconf.take('config.pdflatex')
	cmd = "%(pdflatex)s frontpage ; %(biber)s frontpage ; %(pdflatex)s frontpage" % locals()
	os.system(cmd)
	pdffile = 'frontpage.pdf'
	if os.path.isfile(pdffile):
		with open(pdffile, 'rb') as tmp:
			pdf = tmp.read()
			tmp.close()
		os.chdir(cwd)
		shutil.rmtree(tmpDir)
		response.headers['Content-Type']='application/pdf'
		response.headers['Content-Disposition'] = 'inline; filename="{0}_frontpage.pdf"'.format(art.title)
		return(pdf)
	else:
		os.chdir(cwd)
		shutil.rmtree(tmpDir)
		session.flash = T('Failed :-(')
		redirect(request.env.http_referer)
		
