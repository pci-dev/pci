# -*- coding: utf-8 -*-
from app_modules.helper import *

pciRRactivated = myconf.get("config.registered_reports", default=False)

######################################################################################################################################################################
def index():
    return help_generic()


def help_generic():
    response.view = "default/info.html"
    tweeterAcc = myconf.get("social.twitter")
    return dict(
        pageTitle=getTitle("#GenericHelpTitle"),
        customText=getText("#GenericHelpInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="help_generic", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def help_practical():
    response.view = "default/info.html"
    tweeterAcc = myconf.get("social.twitter")
    return dict(
        pageTitle=getTitle("#PracticalHelpTitle"),
        customText=getText("#PracticalHelpInfo"),
        tweeterAcc=tweeterAcc,
    )


######################################################################################################################################################################
def faq():
    response.view = "default/info.html"
    tweeterAcc = myconf.get("social.twitter")
    return dict(
        pageTitle=getTitle("#FAQTitle"),
        customText=getText("#FAQInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="faq", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def cite():
    response.view = "default/info.html"
    tweeterAcc = myconf.get("social.twitter")
    return dict(
        pageTitle=getTitle("#CiteTitle"),
        customText=getText("#CiteInfo"),
        shareable=True,
        currentUrl=URL(c="about", f="cite", host=host, scheme=scheme, port=port),
        tweeterAcc=tweeterAcc,
        pciRRactivated=pciRRactivated,
    )


######################################################################################################################################################################
def top_guidelines():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#TopGuidelinesTitle"), customText=getText("#TopGuidelinesInfo"),)


######################################################################################################################################################################
def guide_for_authors():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#GuideForAuthorsTitle"), customText=getText("#GuideForAuthorsInfo"),)


######################################################################################################################################################################
def guide_for_reviewers():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#GuideForReviewersTitle"), customText=getText("#GuideForReviewersInfo"),)


######################################################################################################################################################################
def guide_for_recommenders():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#GuideForRecommendersTitle"), customText=getText("#GuideForRecommendersInfo"),)


######################################################################################################################################################################
def become_a_recommenders():
    response.view = "default/info.html"
    return dict(pageTitle=getTitle("#BecomeARecommendersTitle"), customText=getText("#BecomeARecommendersInfo"),)
