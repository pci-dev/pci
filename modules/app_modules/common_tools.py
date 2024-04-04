# -*- coding: utf-8 -*-

from functools import reduce
from re import match
import re
from typing import Any, Dict, List, Optional, cast
from zipfile import ZipFile
import io
from gluon import current
from gluon.globals import Request
from gluon.html import *
from gluon.sqlhtml import SQLFORM
from gluon.tools import Auth
from gluon.validators import IS_LIST_OF
from models.article import Article
from models.membership import Membership
from models.review import Review, ReviewState
from models.suggested_recommender import SuggestedRecommender
from models.user import User
from pydal import DAL

from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)
pciRRactivated = myconf.get("config.registered_reports", default=False)

######################################################################################################################################################################
def takePort(p: Optional[str]):
    # print('port="%s"' % p)
    if p is None:
        return False
    elif match("^[0-9]+$", p):
        return int(p)
    else:
        return False


######################################################################################################################################################################
def get_script(scriptName: str):
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


def check_coauthorship(user_id, article):
    manager_authors = (article.manager_authors or "").split(',')
    for manager in manager_authors:
        if manager == str(user_id): return True
    return False


def get_manager_coauthors(db, artId):
    article = db(db.t_articles.id == artId).select().last()
    manager_authors = (article.manager_authors or "").split(',')
    
    return manager_authors


def extract_manager_ids(form, manager_ids):
    # extract the positively checked manager co-author IDs from the form
    manager_authors = []
    for m_id in manager_ids:
        form_field = form.vars['chk_' + m_id]
        if form_field == 'on': manager_authors.append(m_id)

    return ','.join(manager_authors)


def get_managers(db):
    # collect managers (that are not admins)
    admins = [row.user_id for row in db(
            (db.auth_membership.group_id == db.auth_group.id) &
            (db.auth_group.role.belongs(['administrator', 'developer']))
    ).select(db.auth_membership.user_id, distinct=True)]
    manager_query = db(
            (db.auth_user._id == db.auth_membership.user_id) &
            (db.auth_membership.group_id == db.auth_group.id) &
            (~db.auth_user.id.belongs(admins)) &
            (db.auth_group.role == 'manager')
    ).select()
    users = []
    for manager in manager_query:
        manager = manager.auth_user
        user = ['%s'%(manager['id']), '%s %s, %s'%(manager['first_name'], manager['last_name'], manager['laboratory'])]
        if user not in users: users.append(user)

    return users


def get_exclude_suggested_recommender(auth: Auth, db: DAL, article_id: int) -> List[int]:
    article = Article.get_by_id(article_id)
    if not article:
        return []
    
    suggested_recommenders_id: List[int] = []

    suggested_recommenders = SuggestedRecommender.get_suggested_recommender_by_article(article_id)

    if suggested_recommenders and len(suggested_recommenders) > 0:
        for suggested_recommender in suggested_recommenders:
            suggested_recommenders_id.append(suggested_recommender.suggested_recommender_id)
    
    current_user_id = cast(int, auth.user_id)
    suggested_recommenders_id.append(current_user_id)

    submitter_id = article.user_id
    if submitter_id:
        suggested_recommenders_id.append(submitter_id)

    return suggested_recommenders_id


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

def find_reviewer_number(db: DAL, review: Review, count_anon: int):
    '''
    function finds a number for the reviewer in order to differentiate between anonymous reviewers;
    it needs to be kept in mind that reviewers keep their number in different rounds of evaluation.
    '''
    recommendations = db((db.t_articles.id == db.t_recommendations.article_id) & (db.t_recommendations.id == review.recommendation_id)).select()
    article_id = recommendations[0].t_articles.id
    recomms = db(db.t_recommendations.article_id == article_id).select(orderby=db.t_recommendations.id)

    if len(recomms) == 1: return str(count_anon)
    else:
        current_reviewer = review.reviewer_id
        anon_reviewers = []
        for recomm in recomms:
            reviews = db(db.t_reviews.recommendation_id == recomm.id).select()
            for review in reviews:
                if review.anonymously == True:
                    if review.reviewer_id not in anon_reviewers:
                        anon_reviewers.append(review.reviewer_id)
                    if review.reviewer_id == current_reviewer:
                        return str(len(anon_reviewers))

    return str(count_anon)

###########################################""""

def get_reset_password_key(request: Request):
    if 'key' in request.vars:
        vkey = cast(str, request.vars['key'])
        if isinstance(vkey, list):
            return vkey[1]
        if vkey == "":
            return None
        return vkey
    else:
        return None
    
def get_article_id(request: Request):
    if 'articleId' in request.vars:
        articleId = cast(str, request.vars['articleId'])
        if isinstance(articleId, list):
            return int(articleId[1])
        if articleId == "":
            return None
        return int(articleId)
    else:
        return None
    
def get_review_id(request: Request):
    if 'reviewId' in request.vars:
        review_id = cast(str, request.vars['reviewId'])
        if isinstance(review_id, list):
            return int(review_id[0])
        if review_id == "":
            return None
        return int(review_id)
    else:
        return None
    
def get_next(request: Request):
    if '_next' in request.vars:
        next = cast(str, request.vars['_next'])
        if isinstance(next, list):
            return next[0]
        if next == "" or next == 'None':
            return None
        return next
    else:
        return None

###################################################################

def sget(dictionary: Dict[Any, Any], *keys: Any):
    return reduce(lambda d, key: d.get(key, None) if isinstance(d, dict) else None, keys, dictionary)

###################################################################

def separate_suggestions(suggested_reviewers: List[str]):
    suggested_by_author: List[str] = []
    suggestor_2_suggestions: Dict[str, List[str]] = {}
    for reviewer in suggested_reviewers:
        if ' suggested:' in reviewer:
            suggestor_re = match('(.*) suggested:(.*)', reviewer)
            if suggestor_re:
                suggestor = suggestor_re.group(1)
                suggestion = suggestor_re.group(2)
                if suggestor in suggestor_2_suggestions.keys():
                    suggestions: Any = suggestor_2_suggestions[suggestor]
                    suggestions.append(suggestion)
                    suggestor_2_suggestions[suggestor] = suggestions
                else:
                    suggestor_2_suggestions[suggestor] = [suggestion]
        else:
            suggested_by_author.append(reviewer)

    return suggested_by_author, suggestor_2_suggestions

###################################################################

def delete_user_from_PCI(user: User):
    Membership.remove_all_membership(user.id)
    Review.change_reviews_state(user.id, 
                                [ReviewState.ASK_FOR_REVIEW,
                                ReviewState.AWAITING_REVIEW,
                                ReviewState.AWAITING_RESPONSE,
                                ReviewState.WILLING_TO_REVIEW,
                                ReviewState.NEED_EXTRA_REVIEW_TIME],
                                ReviewState.DECLINED)
    User.empty_user_data(user)
    return User.set_deleted(user)

###################################################################

def get_urls_in_string(text: str) -> List[str]:
    urls = re.findall(r"(https?://?\w+\.\S*[^.,;?!:<>{}\[\]()\"'\s])", text)
    return urls
