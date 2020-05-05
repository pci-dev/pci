# -*- coding: utf-8 -*-
from app_modules.helper import *

######################################################################################################################################################################
def help_generic():
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#GenericHelpTitle"),
        customText=getText(request, auth, db, "#GenericHelpInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="help_generic", host=host, scheme=scheme, port=port),
    )


######################################################################################################################################################################
def help_guidelines():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#GuidelinesHelpTitle"), customText=getText(request, auth, db, "#GuidelinesHelpInfo"),)


######################################################################################################################################################################
def help_practical():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#PracticalHelpTitle"), customText=getText(request, auth, db, "#PracticalHelpInfo"),)


######################################################################################################################################################################
def faq():
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#FAQTitle"),
        customText=getText(request, auth, db, "#FAQInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="faq", host=host, scheme=scheme, port=port),
    )


######################################################################################################################################################################
def cite():
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#CiteTitle"),
        customText=getText(request, auth, db, "#CiteInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="cite", host=host, scheme=scheme, port=port),
    )


#  (gab) is this used ?

# ######################################################################################################################################################################
# def help_user():
# 	response.view='default/info.html'
# 	return dict(
# 		pageTitle=getTitle(request, auth, db, '#UserHelpTitle'),
# 		customText=getText(request, auth, db, '#UserHelpInfo'),
# 	)


# ######################################################################################################################################################################
# def help_recommender():
# 	response.view='default/info.html'
# 	return dict(
# 		pageTitle=getTitle(request, auth, db, '#RecommenderHelpTitle'),
# 		customText=getText(request, auth, db, '#RecommenderHelpInfo'),
# 	)


# ######################################################################################################################################################################
# def help_manager():
# 	response.view='default/info.html'
# 	return dict(
# 		pageTitle=getTitle(request, auth, db, '#ManagerHelpTitle'),
# 		customText=getText(request, auth, db, '#ManagerHelpInfo'),
# 	)


# ######################################################################################################################################################################
# def help_admin():
# 	response.view='default/info.html'
# 	return dict(
# 		pageTitle=getTitle(request, auth, db, '#AdministratorHelpTitle'),
# 		customText=getText(request, auth, db, '#AdministratorHelpInfo'),
# 	)
