# -*- coding: utf-8 -*-

import os
from re import match
from zipfile import ZipFile
import io
from gluon import current
from gluon.html import *
from gluon.sqlhtml import SQLFORM
from gluon.validators import IS_LIST_OF
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
def get_script(scriptName):
    return SCRIPT(_src=URL("static", "js/pci/"+scriptName), _type="text/javascript")


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

#####################################################################################################
def divert_review_pdf_to_multi_upload():
    field = current.db.t_reviews.review_pdf

    field.widget = lambda field, value, kwargs: \
            SQLFORM.widgets.upload.widget(field, value, _multiple='true')
    field.requires[1] = IS_LIST_OF(field.requires[1])

def zip_uploaded_files(files):
    writer = io.BytesIO()
    with ZipFile(writer, 'w') as zf:
        for f in files:
            zf.writestr(f.filename, f.value)

    return writer.getvalue()


def handle_multiple_uploads(review, files):
    if len(files) > 1:
        data = zip_uploaded_files(files)
        name = "uploaded_review.zip"
    elif len(files) and files[0] is not None:
        _ = files[0]
        data = _.value
        name = _.filename
    else:
        return

    filename = current.db.t_reviews.review_pdf.store(data, name)
    review.update_record(review_pdf=filename, review_pdf_data=data)


###################################################################
absoluteButtonScript = get_script("web2py_button_absolute.js")
