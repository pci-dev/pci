# -*- coding: utf-8 -*-

from re import match
from zipfile import ZipFile
import io
from gluon import current
from gluon.html import *
from gluon.sqlhtml import SQLFORM
from gluon.validators import IS_LIST_OF

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
    text = text or ""
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


def get_exclude_list(request):
    excludeList = request.vars.exclude

    if type(excludeList) is str:
        excludeList = excludeList.split(",")
    try:
        return list(map(int, excludeList))
    except:
        return None


###################################################################

def generate_recommendation_doi(article_id: int):
    host = myconf.take('alerts.host')
    pci_short_name = host.split('.')[0]
    article_id_filled = str(article_id).zfill(5)
    return f'10.24072/pci.{pci_short_name}.1{article_id_filled}'

###################################################################

absoluteButtonScript = get_script("web2py_button_absolute.js")

####################################################################
def cancel_decided_article_pending_reviews(db, recomm):
    reviews = db(db.t_reviews.recommendation_id == recomm.id).select()
    for review in reviews:
        if review.review_state == "Willing to review" or review.review_state == "Awaiting review" or review.review_state == "Awaiting response":
            review.review_state = "Cancelled"
            review.update_record()

###################################################################

def find_reviewer_number(db, review, count_anon, iRecomm):
    '''
    function finds a number for the reviewer in order to differentiate between anonymous reviewers;
    it needs to be kept in mind that reviewers keep their number in different rounds of evaluation.
    '''
    recommendations = db((db.t_articles.id == db.t_recommendations.article_id) & (db.t_recommendations.id == review.recommendation_id)).select()
    article_id = recommendations[0].t_articles.id
    recomms = db(db.t_recommendations.article_id == article_id).select()
    if iRecomm == len(recomms): return str(count_anon)
    else:
        current_reviewer = review.reviewer_id
        anon_reviewers = []
        for recomm in recomms[:-1]:
            reviews = db(db.t_reviews.recommendation_id == recomm.id).select()
            for i,review in enumerate(reviews):
                if review.anonymously == True:
                    if review.reviewer_id not in anon_reviewers:
                        anon_reviewers.append(review.reviewer_id)
                    if review.reviewer_id == current_reviewer:
                        return str(len(anon_reviewers))
        return str(len(anon_reviewers) + 1)
