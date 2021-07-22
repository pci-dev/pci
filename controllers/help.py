# -*- coding: utf-8 -*-
from app_modules.helper import *

pciRRactivated = myconf.get("config.registered_reports", default=False)

######################################################################################################################################################################
def index():
    return help_generic()


def help_generic():
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#GenericHelpTitle"),
        customText=getText(request, auth, db, "#GenericHelpInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="help_generic", host=host, scheme=scheme, port=port),
        pciRRactivated=pciRRactivated,
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
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def cite():
    response.view = "default/info.html"
    return dict(
        pageTitle=getTitle(request, auth, db, "#CiteTitle"),
        customText=getText(request, auth, db, "#CiteInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="cite", host=host, scheme=scheme, port=port),
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def top_guidelines():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#TopGuidelinesTitle"), customText=getText(request, auth, db, "#TopGuidelinesInfo"),)


######################################################################################################################################################################
def guide_for_authors():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#GuideForAuthorsTitle"), customText=getText(request, auth, db, "#GuideForAuthorsInfo"),)


######################################################################################################################################################################
def guide_for_reviewers():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#GuideForReviewersTitle"), customText=getText(request, auth, db, "#GuideForReviewersInfo"),)


######################################################################################################################################################################
def guide_for_recommenders():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#GuideForRecommendersTitle"), customText=getText(request, auth, db, "#GuideForRecommendersInfo"),)


######################################################################################################################################################################
def become_a_recommenders():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle(request, auth, db, "#BecomeARecommendersTitle"), customText=getText(request, auth, db, "#BecomeARecommendersInfo"),)
