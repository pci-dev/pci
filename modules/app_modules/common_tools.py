# -*- coding: utf-8 -*-

import os

######################################################################################################################################################################
# (gab)
def get_template(folderName, templateName):
	with open(os.path.join(os.path.dirname(__file__), '../../templates', folderName, templateName), 'r') as myfile:
  		data = myfile.read()
	return data
