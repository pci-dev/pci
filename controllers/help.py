# -*- coding: utf-8 -*-
from app_modules.helper import *

######################################################################################################################################################################
def help_generic():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#GenericHelpTitle'),
		myText=getText(request, auth, db, '#GenericHelpInfo'),
		shareable=True,
	)

######################################################################################################################################################################
def help_guidelines():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#GuidelinesHelpTitle'),
		myText=getText(request, auth, db, '#GuidelinesHelpInfo'),
	)

######################################################################################################################################################################
def help_practical():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#PracticalHelpTitle'),
		myText=getText(request, auth, db, '#PracticalHelpInfo'),
	)

######################################################################################################################################################################
def faq():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#FAQTitle'),
		myText=getText(request, auth, db, '#FAQInfo'),
		shareable=True,
	)

######################################################################################################################################################################
def cite():
	response.view='default/info.html'
	return dict(
		myTitle=getTitle(request, auth, db, '#CiteTitle'),
		myText=getText(request, auth, db, '#CiteInfo'),
		shareable=True,
	)

#  (gab) is this used ?

# ######################################################################################################################################################################
# def help_user():
# 	response.view='default/info.html'
# 	return dict(
# 		myTitle=getTitle(request, auth, db, '#UserHelpTitle'),
# 		myText=getText(request, auth, db, '#UserHelpInfo'),
# 	)


# ######################################################################################################################################################################
# def help_recommender():
# 	response.view='default/info.html'
# 	return dict(
# 		myTitle=getTitle(request, auth, db, '#RecommenderHelpTitle'),
# 		myText=getText(request, auth, db, '#RecommenderHelpInfo'),
# 	)



# ######################################################################################################################################################################
# def help_manager():
# 	response.view='default/info.html'
# 	return dict(
# 		myTitle=getTitle(request, auth, db, '#ManagerHelpTitle'),
# 		myText=getText(request, auth, db, '#ManagerHelpInfo'),
# 	)


# ######################################################################################################################################################################
# def help_admin():
# 	response.view='default/info.html'
# 	return dict(
# 		myTitle=getTitle(request, auth, db, '#AdministratorHelpTitle'),
# 		myText=getText(request, auth, db, '#AdministratorHelpInfo'),
# 	)