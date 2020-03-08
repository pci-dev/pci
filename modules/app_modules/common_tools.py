# -*- coding: utf-8 -*-

import os
from re import sub, match
from gluon.html import *
import gluon.http

from collections import OrderedDict

from app_modules import common_html
from app_modules import common_small_html

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

######################################################################################################################################################################
# (gab)
def get_template(folderName, templateName):
	with open(os.path.join(os.path.dirname(__file__), '../../templates', folderName, templateName), encoding='utf-8') as myfile:
  		data = myfile.read()
	return data

def getShortText(text, length):
	if len(text)>length:
		text = text[0:length] + '...'
	return text
	
######################################################################################################################################################################
def pci_redirect(url):
	print("sURL:")
	print(surl)
	scr = HTML(HEAD(XML('<meta http-equiv="Cache-control" content="no-cache">'), SCRIPT('document.location.href="%s"'%surl, _type='text/javascript')))
	print(scr)
	raise HTTP(200, scr)
