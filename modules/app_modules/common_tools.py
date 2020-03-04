# -*- coding: utf-8 -*-

import os
from re import sub, match
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
	