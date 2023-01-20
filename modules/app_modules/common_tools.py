# -*- coding: utf-8 -*-

import os
from re import match
from gluon.html import *
import gluon.http

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)
pciRRactivated = myconf.get("config.registered_reports", default=False)

######################################################################################################################################################################
def takePort(p):
    # print('port="%s"' % p)
    if p is None:
        return False
    elif match("^[0-9]+$", p):
        return int(p)
    else:
        return False


######################################################################################################################################################################
def get_script(scriptName, folderName="static/js/pci"):
    with open(os.path.join(os.path.dirname(__file__), "../..", folderName, scriptName), encoding="utf-8") as myfile:
        data = myfile.read()
    return SCRIPT(data, _type="text/javascript")


######################################################################################################################################################################
def getShortText(text, length):
    if len(text) > length:
        text = text[0:length] + "..."
    return text


######################################################################################################################################################################
def getDefaultDateFormat():
    return "%d %b %Y"

######################################################################################################################################################################
def pci_redirect(url):
    print("sURL:")
    print(surl)
    scr = HTML(HEAD(XML('<meta http-equiv="Cache-control" content="no-cache">'), SCRIPT('document.location.href="%s"' % surl, _type="text/javascript")))
    print(scr)
    raise HTTP(200, scr)


###################################################################
def get_prev_recomm(db, recomm):
    last_recomm = db(
            (db.t_recommendations.article_id == recomm.article_id) &
            (db.t_recommendations.id < recomm.id)
    ).select(orderby=db.t_recommendations.id).last()

    return last_recomm

###################################################################
absoluteButtonScript = get_script("web2py_button_absolute.js")
