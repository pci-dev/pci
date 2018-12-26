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
from gluon.contrib.markdown import WIKI
from common import *
from helper import *
from html2text import *

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

@auth.requires(auth.has_membership(role='manager') or auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
def convert_pdf_to_markdown():
	form = SQLFORM.factory(
		Field('up_file', label=T("PDF File:"), type='upload', uploadfolder='uploads', requires=IS_UPLOAD_FILENAME(extension='pdf')),
		upload=URL('download')
	)
	myText = None
	if form.accepts(request.vars, formname="form"):
		f = request.vars['up_file']
		# create temp file from in-memory file contents
		ff = tempfile.NamedTemporaryFile(delete=False, suffix=f.filename)
		#print "ff.name:", ff.name
		ff.write(f.value)
		ff.close() # file is not immediately deleted because we used delete=False
		cmd = 'pdftohtml -enc UTF-8 -noframes "%s"' % (ff.name) ; print(cmd) ; os.system(cmd)
		hf_name = ff.name.replace('.pdf', '.html')
		# Cleans output a bit
		cmd = 'sed -i -e \'s/&#160;/ /g\' "%s"' % (hf_name) ; print(cmd) ; os.system(cmd) # remove stupid whitechars
		cmd = 'sed -i -e \'s#<hr/># #g\' "%s"' % (hf_name) ; print(cmd) ; os.system(cmd) # remove page breaks
		cmd = 'sed -i -re \'s#<br/>([A-Za-z0-9])# \\1#g\' "%s"' % (hf_name) ; print(cmd) ; os.system(cmd) # remove line breaks
		# Try to convert html -> Markdown using Python library html2text
		try:
			with codecs.open(hf_name, 'r', encoding="utf-8") as myHtmlFile:
				myHtml = myHtmlFile.read()
				myText = html2text.html2text(myHtml)
				print('html2text successed on file "%s"'%(hf_name))
		# if fails fallback to pandoc
		except Exception, e:
			print str(e)
			print('html2text failed on file "%s", switch to pandoc' %(hf_name))
			cmd = 'pandoc --smart --normalize --columns=9999 -t markdown "%s"' % (hf_name)
			with os.popen(cmd) as messages:
				myText = []
				for m in messages:
					myText.append(m)
				myText = '\n'.join(myText)
		# Keep tmp tidy!
		map(os.unlink, glob.glob(ff.name.replace('.pdf', '*')))
	# If any text to be displayed, add it as an editable field in the form
	if myText:
		#form[0][0][0].append(HR())
		form[0].append(DIV(TEXTAREA(value=XML(myText), _class='pci-converted-pdf-area'), _class='form-group'))

	response.view='default/myLayout.html'
	return dict(
			form=form, 
			myTitle=getTitle(request, auth, db, '#ConvertPDFTitle'),
			myHelp=getHelp(request, auth, db, '#ConvertPDFComments'),
		)


#TODO: gros merdier !
#@auth.requires(auth.has_membership(role='manager') or auth.has_membership(role='administrator') or auth.has_membership(role='developper'))
#def convert_pdf_to_html():
	#form = SQLFORM.factory(
		#Field('up_file', label=T("PDF File:"), type='upload', uploadfolder='uploads', requires=IS_UPLOAD_FILENAME(extension='pdf')),
		##Field('converted_html', label=T('Converted HTML'), type='text', length=2097152, widget=ckeditor.widget),
		#keepvalues=True,
	#)
	#myText = None
	#if form.accepts(request.vars, formname="form"):
		#f = request.vars['up_file']
		## create temp file from in-memory file contents
		#ff = tempfile.NamedTemporaryFile(delete=False, suffix=f.filename)
		##print "ff.name:", ff.name
		#ff.write(f.value)
		#ff.close() # file is not immediately deleted because we used delete=False
		#cmd = 'pdftohtml -enc UTF-8 -nomerge -noframes "%s"' % (ff.name) ; print(cmd) ; os.system(cmd)
		#hf_name = ff.name.replace('.pdf', '.html')
		## Cleans output a bit
		##cmd = 'sed -i -e \'s/&#160;/ /g\' "%s"' % (hf_name) ; print(cmd) ; os.system(cmd) # remove stupid whitechars
		##cmd = 'sed -i -e \'s#<hr/># #g\' "%s"' % (hf_name) ; print(cmd) ; os.system(cmd) # remove page breaks
		##cmd = 'sed -i -re \'s#<br/>([A-Za-z0-9])# \\1#g\' "%s"' % (hf_name) ; print(cmd) ; os.system(cmd) # remove line breaks
		#cmd = 'cat "%s"' % (hf_name)
		#with os.popen(cmd) as messages:
			#myText = []
			#for m in messages:
				#myText.append(m)
			#myText = XML('\n'.join(myText))
		#map(os.unlink, glob.glob(ff.name.replace('.pdf', '*')))
		##form.vars.converted_html=myText
		##NO!#form[0].append(DIV(TEXTAREA(value=XML(myText), _class='pci-converted-pdf-area', _widget=ckeditor.widget), _class='form-group'))
		##NO!#form.fields.append(Field('converted_html', label=T('Converted HTML'), type='text', length=2097152, default=myText, widget=ckeditor.widget))
		#form = SQLFORM.factory(
			#Field('converted_html', label=T('Converted HTML'), type='text', length=2097152, default=myText, widget=ckeditor.widget),
		#)

	#response.view='default/myLayout.html'
	#return dict(
			#form=form, 
			#myTitle=getTitle(request, auth, db, '#ConvertPDFTitle'),
			#myHelp=getHelp(request, auth, db, '#ConvertPDFComments'),
		#)


