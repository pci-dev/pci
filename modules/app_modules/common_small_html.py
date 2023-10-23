import gc
import os
from typing import Optional, cast
import pytz
from re import sub, match
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import *
from collections import OrderedDict

import io
from PIL import Image

from gluon import current, IS_IN_DB, IS_IN_SET
from gluon.globals import Request
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail
from gluon.sqlhtml import *
from models.article import Article
from models.review import Review, ReviewState
from models.user import User
from pydal import DAL

from app_modules.helper import getText
from app_modules import common_tools
from app_modules.hypothesis import Hypothesis
from app_modules.orcid import OrcidTools

myconf = AppConfig(reload=True)

pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

######################################################################################################################################################################
# Time and date
######################################################################################################################################################################
def mkLastChange(t):
    if t:
        d = datetime.datetime.now() - t
        if d.days == 0:
            return SPAN(current.T("Today"))
        elif d.days == 1:
            return SPAN(current.T("Yesterday"))
        else:
            tdt = t.strftime(DEFAULT_DATE_FORMAT + " ")
            return SPAN(tdt)
    else:
        return ""


######################################################################################################################################################################
def mkElapsedDays(t):
    if t:
        d = datetime.datetime.now() - t
        if d.days == 0:
            return SPAN(current.T("Today"))
        elif d.days == 1:
            return SPAN(current.T("Yesterday"))
        else:
            return SPAN(current.T("%s days ago") % (d.days))
    else:
        return ""


######################################################################################################################################################################
def mkElapsed(t):
    if t:
        d = datetime.datetime.now() - t
        if d.days < 2:
            return SPAN(current.T("%s day") % d.days)
        else:
            return SPAN(current.T("%s days") % d.days)
    else:
        return ""


######################################################################################################################################################################
# Transforms  DOI
# After CrossRef syntax must be: https://doi.org/xxxx.xx/xxx.xx
def mkDOI(doi):
    doi_url = mkLinkDOI(doi)
    if doi_url:
        return A(B(doi), _href=doi_url, _class="doi_url", _target="_blank")
    else:
        return SPAN("", _class="doi_url")


def mkSimpleDOI(doi):
    doi_url = mkLinkDOI(doi)
    return A(doi, _href=doi_url) if doi_url else ""


def mkLinkDOI(doi: str):
    if doi:
        if match("^http", doi):
            return doi
        else:
            return "https://doi.org/" + sub(r"doi: *", "", doi)
    else:
        return ""


######################################################################################################################################################################
# User text or link
######################################################################################################################################################################
def mkUserRow(auth, db, userRow, withPicture=False, withMail=False, withRoles=False):
    resu = []
    if withPicture:
        if userRow.uploaded_picture is not None and userRow.uploaded_picture != "":
            img = IMG(_alt="avatar", _src=URL("default", "download", args=userRow.uploaded_picture), _class="pci-userPicture", _style="float:left;")
        else:
            img = IMG(_alt="avatar", _src=URL(c="static", f="images/default_user.png"), _class="pci-userPicture", _style="float:left;")
        resu.append(TD(img))
    name = ""
    if (userRow.first_name or "") != "":
        name += userRow.first_name
    if (userRow.last_name or "") != "":
        if name != "":
            name += " "
        name += userRow.last_name.upper()
    resu.append(TD(A(name, _target="blank", _href=URL(c="public", f="user_public_page", vars=dict(userId=userRow.id)))))
    affil = ""
    if (userRow.laboratory or "") != "":
        affil += userRow.laboratory
    if (userRow.institution or "") != "":
        if affil != "":
            affil += ", "
        affil += userRow.institution
    if (userRow.city or "") != "":
        if affil != "":
            affil += ", "
        affil += userRow.city
    if (userRow.country or "") != "":
        if affil != "":
            affil += ", "
        affil += userRow.country
    resu.append(TD(I(affil)))
    if withMail:
        resu.append(TD((" [%s]" % userRow.email) if withMail else TD("")))
    if withRoles:
        rolesQy = db((db.auth_membership.user_id == userRow.id) & (db.auth_membership.group_id == db.auth_group.id)).select(db.auth_group.role, orderby=db.auth_group.role)
        rolesList = []
        for roleRow in rolesQy:
            rolesList.append(roleRow.role)
        roles = ", ".join(rolesList)
        resu.append(TD(B(roles)))
    return TR(resu, _class="pci-UsersTable-row")


######################################################################################################################################################################
def mkUser(auth, db, userId, linked=False, scheme=False, host=False, port=False):
    if userId is not None:
        theUser = db(db.auth_user.id == userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
        return mkUser_U(auth, db, theUser, linked=linked, scheme=scheme, host=host, port=port)
    else:
        return SPAN("")


######################################################################################################################################################################
def mkUserId(auth, db, userId, linked=False, scheme=False, host=False, port=False):
    resu = SPAN("")
    if userId is not None:
        if linked:
            resu = A(B(str(userId)), _href=URL(c="public", f="user_public_page", scheme=scheme, host=host, port=port, vars=dict(userId=userId)), _class="cyp-user-profile-link")
        else:
            resu = SPAN(str(userId))
    return resu


######################################################################################################################################################################
def mkUser_U(auth, db, theUser, linked=False, scheme=False, host=False, port=False, reverse=False):
    if theUser:
        if linked:
            if reverse: b_tag = B("%s, %s." % (theUser.last_name, theUser.first_name[0]))
            else: b_tag = B("%s %s" % (theUser.first_name, theUser.last_name))
            resu = A(
                b_tag,
                _href=URL(c="public", f="user_public_page", scheme=scheme, host=host, port=port, vars=dict(userId=theUser.id)),
                _class="cyp-user-profile-link",
            )
        else:
            if reverse: resu = SPAN("%s, %s." % (theUser.last_name, theUser.first_name[0]))
            else: resu = SPAN("%s %s" % (theUser.first_name, theUser.last_name))
    else:
        resu = SPAN("?")
    return resu


######################################################################################################################################################################
def mkUserWithAffil_U(auth, db, theUser, linked=False, scheme=False, host=False, port=False):
    if theUser:
        if linked:
            resu = SPAN(
                A(
                    "%s %s" % (theUser.first_name, theUser.last_name),
                    _href=URL(c="public", f="user_public_page", scheme=scheme, host=host, port=port, vars=dict(userId=theUser.id)),
                ),
                I(" -- %s, %s -- %s, %s" % (theUser.laboratory, theUser.institution, theUser.city, theUser.country)),
            )
        else:
            resu = SPAN(
                SPAN("%s %s" % (theUser.first_name, theUser.last_name)), I(" -- %s, %s -- %s, %s" % (theUser.laboratory, theUser.institution, theUser.city, theUser.country))
            )
    else:
        resu = SPAN("?")
    return resu


######################################################################################################################################################################
def mkUserWithMail(auth, db, userId, linked=False, scheme=False, host=False, port=False, reverse=False, orcid=False):
    if userId is not None:
        theUser = db(db.auth_user.id == userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email, db.auth_user.orcid).last()
    else:
        theUser = None

    user_with_mail = _mkUser(theUser, linked, reverse)
    if orcid:
        return OrcidTools.build_name_with_orcid(user_with_mail, theUser.orcid)
    else:
        return user_with_mail


def _mkUser(theUser, linked=False, reverse=False):
        if theUser:
            if reverse: name = "%s, %s" % (theUser.last_name, theUser.first_name)
            else: name = "%s %s" % (theUser.first_name, theUser.last_name)
            if linked:
                resu = SPAN(
                    A(
                        name,
                        _href=URL(c="public", f="user_public_page",
                            scheme=scheme, host=host, port=port, vars=dict(userId=userId)),
                    ),
                    SPAN(" [%s]" % theUser.email))
            else:
                resu = SPAN(
                    SPAN(name),
                    SPAN(" [%s]" % theUser.email))
        else:
            resu = SPAN("?")

        return resu


def mkUserNoSpan(auth, db, userId):
    if userId is not None:
        theUser = db(db.auth_user.id == userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
    else:
        theUser = None

    resu = "%s %s" % (theUser.first_name, theUser.last_name)

    return resu

######################################################################################################################################################################
# Article status
######################################################################################################################################################################
statusArticles = dict()


def mkStatusArticles(db):
    statusArticles.clear()
    for sa in db(db.t_status_article).select():
        statusArticles[sa["status"]] = sa


######################################################################################################################################################################
def mkStatusSimple(auth, db, status):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles(db)
    status_txt = (current.T(status)).upper()
    color_class = statusArticles[status]["color_class"] or "default"
    hint = statusArticles[status]["explaination"] or ""
    return SPAN(status_txt, _style="margin: 0; padding:0", _class="pci-status " + color_class, _title=current.T(hint))


######################################################################################################################################################################
# Builds a coloured status label
def mkStatusDiv(auth, db, status, showStage=False, stage1Id=None, reportStage="Stage not set", submission_change=False):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles(db)
    status_txt = (current.T(status)).upper()
    color_class = statusArticles[status]["color_class"] or "default"
    hint = statusArticles[status]["explaination"] or ""
    change_text = "Triage revision" if submission_change else "Initial submission"

    if showStage:
        if auth.has_membership(role="manager"):
            stage1Url = URL(c="manager", f="recommendations", vars=dict(articleId=stage1Id))
        elif auth.has_membership(role="recommender"):
            stage1Url = URL(c="recommender", f="recommendations", vars=dict(articleId=stage1Id))
            # stage1Url = URL(c="recommender", f="article_details" ,vars=dict(articleId=stage1Id))
        else:
            stage1Url = URL(c="user", f="recommendations", vars=dict(articleId=stage1Id))

        if stage1Id is not None:
            reportStage = "STAGE 2"
            stage1Link = SPAN(BR(), B("(", A(current.T("View stage 1"), _href=stage1Url), ")"))
        else:
            reportStage = "STAGE 1"
            stage1Link = ""

        if reportStage is not None:
            result = DIV(
                DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint), _style="text-align: center;"),
                DIV(B(current.T(reportStage)), stage1Link, _class="pci-status-addition", _style="text-align: center; width: 150px;"),
                DIV(B(current.T(change_text)), _class="pci-status-addition", _style="text-align: center;"),
            )
        else:
            result = DIV(
                DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint), _style="text-align: center;"),
                DIV(B(current.T("Stage not set")), stage1Link, _class="pci-status-addition", _style="text-align: center; width: 150px;"),
                DIV(B(current.T(change_text)), _class="pci-status-addition", _style="text-align: center;"),
            )

    else:
        result = DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint))

    return result


######################################################################################################################################################################
# Builds a coloured status label with pre-decision concealed
def mkStatusDivUser(auth, db, status, showStage=False, stage1Id=None, reportStage="Stage not set"):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles(db)
    if status.startswith("Pre-") and status != "Pre-submission":
        status2 = "Under consideration"
    else:
        status2 = status
    status_txt = (current.T(status2)).upper()
    color_class = statusArticles[status2]["color_class"] or "default"
    hint = statusArticles[status2]["explaination"] or ""

    if showStage:
        if auth.has_membership(role="manager"):
            stage1Url = URL(c="manager", f="recommendations", vars=dict(articleId=stage1Id))
        elif auth.has_membership(role="recommender"):
            stage1Url = URL(c="recommender", f="recommendations", vars=dict(articleId=stage1Id))
            # stage1Url = URL(c="recommender", f="article_details" ,vars=dict(articleId=stage1Id))
        else:
            stage1Url = URL(c="user", f="recommendations", vars=dict(articleId=stage1Id))

        if stage1Id is not None:
            reportStage = "STAGE 2"
            stage1Link = SPAN(BR(), B("(", A(current.T("View stage 1"), _href=stage1Url), ")"))
        else:
            reportStage = "STAGE 1"
            stage1Link = ""

        if reportStage is not None:
            result = DIV(
                DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint), _style="text-align: center;"),
                DIV(B(current.T(reportStage)), stage1Link, _style="text-align: center; width: 150px;"),
            )
        else:
            result = DIV(
                DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint), _style="text-align: center;"),
                DIV(B(current.T("Stage not set")), stage1Link, _style="text-align: center; width: 150px;"),
            )

    else:
        result = DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint))

    return result


######################################################################################################################################################################
def mkStatusBigDiv(auth, db, status, printable=False):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles(db)
    status_txt = (current.T(status)).upper()
    color_class = statusArticles[status]["color_class"] or "default"
    hint = statusArticles[status]["explaination"] or ""

    if printable:
        printable_class = " printable"
    else:
        printable_class = ""

    return DIV(status_txt, _class="pci-status-big " + color_class + printable_class, _title=current.T(hint))


######################################################################################################################################################################
def mkStatusBigDivUser(auth, db, status, printable=False):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles(db)
    if status.startswith("Pre-") and status != "Pre-submission":
        status2 = "Under consideration"
    else:
        status2 = status
    status_txt = (current.T(status2)).upper()
    color_class = statusArticles[status2]["color_class"] or "default"
    hint = statusArticles[status2]["explaination"] or ""

    if printable:
        printable_class = " printable"
    else:
        printable_class = ""

    return DIV(status_txt, _class="pci-status-big " + color_class + printable_class, _title=current.T(hint))


######################################################################################################################################################################
# Other status
######################################################################################################################################################################
def mkReviewStateDiv(auth: Auth, db: DAL, state: str, review: Optional[Review] = None):
    # state_txt = (current.T(state)).upper()
    state_txt = (state or "").upper()
    if state == ReviewState.AWAITING_RESPONSE.value or state == ReviewState.WILLING_TO_REVIEW.value:
        color_class = "warning"
    elif state == ReviewState.DECLINED_BY_RECOMMENDER.value:
        color_class = "danger"
    elif state == ReviewState.AWAITING_REVIEW.value:
        color_class = "info"
    elif state == ReviewState.REVIEW_COMPLETED.value:
        color_class = "success"
    elif state == ReviewState.NEED_EXTRA_REVIEW_TIME.value:
        color_class = "success"
        if review:
            if review.due_date:
                state_txt = review.due_date.strftime('%b %d, %Y').upper() + " REVIEW DATE REQUESTED"
            elif review.review_duration:
                state_txt = review.review_duration.upper() + " REVIEW TIME REQUESTED"
    else:
        color_class = "default"
    return DIV(state_txt, _class="cyp-review-state pci-status " + color_class)


######################################################################################################################################################################
def mkContributionStateDiv(auth, db, state):
    # state_txt = (current.T(state)).upper()
    state_txt = (state or "").upper()
    if state == "Pending":
        color_class = "warning"
    elif state == "Under consideration":
        color_class = "info"
    elif state == "Recommendation agreed":
        color_class = "success"
    else:
        color_class = "default"
    return DIV(state_txt, _class="pci-status " + color_class)


######################################################################################################################################################################
# Image resizing
######################################################################################################################################################################
def makeUserThumbnail(auth, db, userId, size=(150, 150)):
    user = db(db.auth_user.id == userId).select().last()
    if user.picture_data:
        try:
            im = Image.open(io.BytesIO(user.picture_data))
            width, height = im.size
            if width > 200 or height > 200:
                im.thumbnail(size, Image.LANCZOS) # ANTIALIAS
                imgByteArr = io.BytesIO()
                im.save(imgByteArr, format="PNG")
                imgByteArr = imgByteArr.getvalue()
                user.update_record(picture_data=imgByteArr)
        except:
            pass
    return


######################################################################################################################################################################
# Other images helper
######################################################################################################################################################################
def mkAnonymousMask(auth, db, anon):
    if anon is True:
        return DIV(IMG(_alt="anonymous", _src=URL(c="static", f="images/mask.png")), _style="text-align:center;")
    else:
        return ""


######################################################################################################################################################################
def mkAnonymousArticleField(auth, db, anon, value, articleId):
    recomm = db(db.t_recommendations.article_id == articleId).select().last()
    isRecommender = recomm and recomm.recommender_id == auth.user_id
    if anon is True and not isRecommender:
        return IMG(_alt="anonymous", _src=URL(c="static", f="images/mask.png"))
    else:
        return value


######################################################################################################################################################################
def mkJournalImg(auth, db, press):
    if press is True:
        return DIV(IMG(_alt="published", _src=URL(c="static", f="images/journal.png")), _style="text-align:center;")
    else:
        return ""


######################################################################################################################################################################
# Buttons
######################################################################################################################################################################
def mkViewEditRecommendationsRecommenderButton(auth, db, row):
    return A(
        SPAN(current.T("View / Edit"), _class="buttontext btn btn-default pci-button"),
        _href=URL(c="recommender", f="recommendations", vars=dict(articleId=row.article_id)),
        _class="button",
        _title=current.T("View and/or edit article"),
    )


######################################################################################################################################################################
# code for a "Back" button
# go to the target instead, if any.
def mkBackButton(text=current.T("Back"), target=None):
    if target:
        return A(I(_class="glyphicon glyphicon-chevron-left"), SPAN(text), _href=target, _class="pci2-flex-row pci2-align-items-center pci2-tool-link pci2-yellow-link")
    else:
        return A(
            I(_class="glyphicon glyphicon-chevron-left"),
            SPAN(text),
            _onclick="window.history.back();",
            _class="pci2-flex-row pci2-align-items-center pci2-tool-link pci2-yellow-link",
        )


######################################################################################################################################################################
# Article recomm presentation
######################################################################################################################################################################
def mkRepresentArticleLightLinked(auth, db, article_id, urlArticle=None):
    anchor = ""
    art = db.t_articles[article_id]

    if art:
        # Scheduled submission status (instead of DOI)
        doi_text = mkDOI(art.doi)
        if scheduledSubmissionActivated and  art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        if urlArticle:
            anchor = DIV(
                A(B(md_to_html(art.title)), _href=urlArticle), BR(), SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors, art.id)), BR(), doi_text, _class="ellipsis-over-350",
            )
        else:
            anchor = DIV(
                B(md_to_html(art.title) or ""),
                SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors, art.id)),
                BR(),
                doi_text,
                _class="ellipsis-over-350",
            )

    return anchor


######################################################################################################################################################################
def mkRepresentArticleLightLinkedWithStatus(auth, db, article_id, urlArticle=None):
    anchor = ""
    art = db.t_articles[article_id]
    if art:
        # Scheduled submission status (instead of DOI)
        doi_text = mkDOI(art.doi)
        if scheduledSubmissionActivated and  art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        if urlArticle:
            anchor = DIV(
                A(B(md_to_html(art.title) or "", _class="article-title"), _href=urlArticle),
                BR(),
                SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors, art.id)),
                BR(),
                doi_text,
                BR(),
                B(current.T("Status: "), mkStatusSimple(auth, db, art.status)),
            )
        else:
            anchor = DIV(
                B(md_to_html(art.title) or ""),
                SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors, art.id)),
                BR(),
                doi_text,
                _class="ellipsis-over-350",
            )

    return anchor


######################################################################################################################################################################
def mkRepresentArticleLight(auth, db, article_id):
    anchor = ""
    art = db.t_articles[article_id]
    if art:
        # Scheduled submission status (instead of DOI)
        doi_text = mkDOI(art.doi)
        if scheduledSubmissionActivated and  art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        anchor = DIV(
            B(md_to_html(art.title), _class="article-title"),
            DIV(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors, art.id)),
            doi_text,
            BR(),
            SPAN(" " + current.T("ArticleID") + " #" + str(art.id)),            
            BR(),
            SPAN(" " + current.T("version") + " " + art.ms_version) if art.ms_version else "",
            (BR() + SPAN(art.article_source) if art.article_source else ""),
        )
    return anchor


######################################################################################################################################################################
# Builds a nice representation of an article WITHOUT recommendations link
def mkArticleCellNoRecomm(auth, db, art0):
    anchor = ""
    if art0:
        if "t_articles" in art0:
            art = art0.t_articles
        else:
            art = art0

        # Scheduled submission status (instead of DOI)
        doi_text = mkDOI(art.doi)
        if scheduledSubmissionActivated and  art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        anchor = DIV(
            B(md_to_html(art.title) or "", _class="article-title"),
            DIV(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors, art.id)),
            doi_text,
            BR(),
            SPAN(" " + current.T("ArticleID") + " #" + str(art.id)),
            BR(),
            SPAN(" " + current.T("version") + " " + art.ms_version) if art.ms_version else "",
            (BR() + SPAN(art.article_source) if art.article_source else ""),
        )
    return anchor


######################################################################################################################################################################
def mkArticleCellNoRecommFromId(auth, db, recommId):
    anchor = ""
    recomm = db.t_recommendations[recommId]
    if recomm:
        art = db.t_articles[recomm.article_id]
        if art:
            # if art.already_published:
            recommenders = [mkUser(auth, db, recomm.recommender_id)]
            contribsQy = db(db.t_press_reviews.recommendation_id == recommId).select()
            n = len(contribsQy)
            i = 0
            for contrib in contribsQy:
                i += 1
                if i < n:
                    recommenders += ", "
                else:
                    recommenders += " and "
                recommenders += mkUser(auth, db, contrib.contributor_id)
            recommenders = SPAN(recommenders)
            # else:
            # recommenders = mkUser(auth, db, recomm.recommender_id)
            doi_text = mkDOI(art.doi)
            if scheduledSubmissionActivated and  art.scheduled_submission_date is not None:
                doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

            anchor = DIV(
                B(md_to_html(recomm.recommendation_title)),
                SPAN(current.T(" by ")),
                recommenders,
                mkDOI(recomm.recommendation_doi),
                P(),
                SPAN(current.T("A recommendation of ")),
                I(md_to_html(art.title) or "", _class="article-title"),
                SPAN(current.T(" by ")),
                SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors, art.id)),
                (SPAN(current.T(" in ")) + SPAN(art.article_source) if art.article_source else ""),
                BR(),
                doi_text,
                BR(),
                (SPAN(current.T(" version ") + art.ms_version) if art.ms_version else ""),
            )
    return anchor


######################################################################################################################################################################
# Make text string from data
######################################################################################################################################################################
def mkRecommCitation(auth, db, myRecomm):
    applongname = myconf.take("app.longname")

    citeNum = ""
    doi = ""
    if myRecomm is None or not hasattr(myRecomm, "recommendation_doi"):
        return SPAN("?")
    whoDidItCite = getRecommAndReviewAuthors(auth, db, recomm=myRecomm, with_reviewers=False, linked=False)
    if myRecomm.recommendation_doi:
        citeNumSearch = re.search("([0-9]+$)", myRecomm.recommendation_doi, re.IGNORECASE)
        if citeNumSearch:
            citeNum = ", " + citeNumSearch.group(1)
        doi = SPAN("DOI: ", mkDOI(myRecomm.recommendation_doi))
    citeRecomm = SPAN(SPAN(whoDidItCite), " ", myRecomm.last_change.strftime("(%Y)"), " ", (md_to_html(myRecomm.recommendation_title) or ""), ". ", I(applongname) + citeNum, SPAN(" "), doi)
    return citeRecomm or ""


######################################################################################################################################################################
def mkArticleCitation(auth, db, myRecomm):
    applongname = myconf.take("app.longname")

    if myRecomm is None or not hasattr(myRecomm, "article_id"):
        return SPAN("?")
    else:
        art = db((db.t_articles.id == myRecomm.article_id)).select().last()
        artSrc = art.article_source or ""
        version = myRecomm.ms_version or ""
        citeArticle = SPAN(
            SPAN(art.authors),
            " ",
            SPAN(md_to_html(art.title) or "", _class="article-title"),
            ". ",
            SPAN(art.last_status_change.strftime("%Y, ")),
            artSrc,
            ". ",
            I("Version ", version, " peer-reviewed and recommended by ", applongname, "."),
            " DOI: ",
            mkDOI(art.doi),
        )
        return citeArticle


######################################################################################################################################################################
def mkCoRecommenders(auth, db, row, goBack=URL()):
    butts = []
    hrevs = []
    art = db.t_articles[row.article_id]
    revs = db(db.t_press_reviews.recommendation_id == row.id).select()
    for rev in revs:
        if rev.contributor_id:
            hrevs.append(LI(TAG(rev.contributor_details) if rev.contributor_details else mkUserWithMail(auth, db, rev.contributor_id)))
        else:
            hrevs.append(LI(I(current.T("not registered"))))
    butts.append(UL(hrevs, _class="pci-inCell-UL"))
    if len(hrevs) > 0:
        txt = current.T("ADD / REMOVE")
    else:
        txt = current.T("ADD")
    if art.status == "Under consideration":
        myVars = dict(recommId=row["id"], goBack=goBack)
        butts.append(A(txt, _class="btn btn-default pci-smallBtn pci-recommender", _href=URL(c="recommender", f="add_contributor", vars=myVars, user_signature=True)))
    return DIV(butts, _class="pci-w200Cell")


# Only in admin
######################################################################################################################################################################
def mkReviewersString(auth, db, articleId):
    reviewers = []
    reviewsQy = db(
        (db.t_reviews.recommendation_id == db.t_recommendations.id)
        & (db.t_recommendations.article_id == articleId)
        & (db.t_reviews.anonymously == False)
        & (db.t_reviews.review_state == "Review completed")
    ).select(db.t_reviews.reviewer_id, distinct=True)
    if reviewsQy is not None:
        nR = len(reviewsQy)
        i = 0
        for rw in reviewsQy:
            if rw.reviewer_id:
                i += 1
                if i > 1:
                    if i < nR:
                        reviewers += ", "
                    else:
                        reviewers += " and "
                reviewers += mkUser(auth, db, rw.reviewer_id).flatten()
    reviewsQyAnon = db(
        (db.t_reviews.recommendation_id == db.t_recommendations.id)
        & (db.t_recommendations.article_id == articleId)
        & (db.t_reviews.anonymously == True)
        & (db.t_reviews.review_state == "Review completed")
    ).select(db.t_reviews.reviewer_id, distinct=True)
    if reviewsQyAnon is not None:
        nRA = len(reviewsQyAnon)
        if nRA > 0:
            if len(reviewers) > 0:
                reviewers += " and "
            if nRA > 1:
                reviewers += "%s anonymous reviewers" % nRA
            else:
                reviewers += "one anonymous reviewer"
    reviewersStr = "".join(reviewers)
    return reviewersStr


######################################################################################################################################################################
# builds names list (recommender, co-recommenders, reviewers)
def getRecommAndReviewAuthors(auth, db, article=dict(), recomm=dict(), with_reviewers=False, as_list=False, linked=False,
                              host=False, port=False, scheme=False,
                              this_recomm_only=False, citation=False,
                             ):
    whoDidIt = []

    if hasattr(recomm, "article_id"):
        article = db(db.t_articles.id == recomm.article_id).select(db.t_articles.id, db.t_articles.already_published).last()

    if hasattr(article, "id"):
        select_recomm = ((db.t_recommendations.id == recomm.id)
                            if this_recomm_only else
                        (db.t_recommendations.article_id == article.id))

        mainRecommenders = db(select_recomm).select(
            db.t_recommendations.ALL, distinct=db.t_recommendations.recommender_id)

        coRecommenders = db(
            select_recomm
            & (db.t_press_reviews.recommendation_id == db.t_recommendations.id)
        ).select(db.t_press_reviews.ALL, distinct=db.t_press_reviews.contributor_id)

        allRecommenders = mkRecommenderandContributorList(mainRecommenders) + mkRecommenderandContributorList(coRecommenders)

        if article.already_published:  # NOTE: POST-PRINT
            nr = len(allRecommenders)
            ir = 0
            for theUser in allRecommenders:
                ir += 1
                if as_list:
                    whoDidIt.append(mk_user_name(theUser))
                elif citation:
                    if theUser['id']:
                        theUser = db.auth_user[theUser['id']]
                        whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme, reverse=True))
                    else:
                        whoDidIt.append(get_name_from_details(theUser['details'], reverse=True))
                    if ir == nr - 1 and ir >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif ir < nr:
                        whoDidIt.append(", ")
                else:
                    if theUser['id']:
                        theUser = db.auth_user[theUser['id']]
                        whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme))
                    else:
                        whoDidIt.append(get_name_from_details(theUser['details']))
                    if ir == nr - 1 and ir >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif ir < nr:
                        whoDidIt.append(", ")

        else:  # NOTE: PRE-PRINT
            if with_reviewers:
                namedReviewers = db(
                    (db.t_recommendations.article_id == article.id)
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    & (db.t_reviews.anonymously == False)
                    & (db.t_reviews.review_state == "Review completed")
                ).select(db.t_reviews.ALL, distinct=db.t_reviews.reviewer_id)
                na = db(
                    (db.t_recommendations.article_id == article.id)
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    & (db.t_reviews.anonymously == True)
                    & (db.t_reviews.review_state == "Review completed")
                ).select(db.t_reviews.reviewer_id, db.t_reviews.reviewer_details, distinct=True)
                na = len(na)
                na1 = 1 if na > 0 else 0
            else:
                namedReviewers = []
                na = 0
            nr = len(allRecommenders)
            nw = len(namedReviewers)
            ir = 0

            for theUser in allRecommenders:
                ir += 1
                if as_list:
                    whoDidIt.append(mk_user_name(theUser))
                elif citation:
                    if theUser['id']:
                        theUser = db.auth_user[theUser['id']]
                        whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme, reverse=True))
                    else:
                        whoDidIt.append(get_name_from_details(theUser['details'], reverse=True))                  
                    if ir == nr - 1 and ir >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif ir < nr:
                        whoDidIt.append(", ")
                else:
                    if theUser['id']:
                        theUser = db.auth_user[theUser['id']]
                        whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme))
                    else:
                        whoDidIt.append(get_name_from_details(theUser['details'], reverse=True))
                    if ir == nr - 1 and ir >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif ir < nr:
                        whoDidIt.append(", ")
            if nr > 0:
                if nw + na > 0:
                    whoDidIt.append(current.T(" based on reviews by "))
                elif nw + na == 1:
                    whoDidIt.append(current.T(" based on review by "))
            iw = 0
            for theUser in namedReviewers:
                iw += 1
                if as_list:
                    whoDidIt.append(mk_user_name(theUser, "reviewer_"))
                else:
                    if theUser.reviewer_id:
                        theUser = db.auth_user[theUser.reviewer_id]
                        whoDidIt.append(mkUser_U(auth, db, theUser, linked=False, host=host, port=port, scheme=scheme))
                    else:
                        whoDidIt.append(mk_user_name(theUser, "reviewer_"))
                    if iw == nw + na1 - 1 and iw >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif iw < nw + na1:
                        whoDidIt.append(", ")

            if not as_list:
                if na > 1:
                    whoDidIt.append(current.T("%d anonymous reviewers") % (na))
                elif na == 1:
                    whoDidIt.append(current.T("%d anonymous reviewer") % (na))

    return whoDidIt


def mk_user_name(user, _type=""):
    return (
        get_name_from_details(user[_type+"details"])
        or mkUser_U(None, None, user[_type+"id"]).flatten()
    )


def get_name_from_details(user_details, reverse=False):
    user_details = user_details[:user_details.rfind(' [')] \
            if user_details else ""

    if user_details != "" and reverse:
        reverse = "%s, %s"%(user_details.split(' ')[1], str(user_details.split(' ')[0])[1])

    return user_details


######################################################################################################################################################################
def getArticleSubmitter(auth, db, art):
    class FakeSubmitter(object):
        id = None
        first_name = ""
        last_name = "[undisclosed]"

    hideSubmitter = True

    qyIsRecommender = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommender_id == auth.user_id)).count()

    qyIsCoRecommender = db(
        (db.t_recommendations.article_id == art.id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id) & (db.t_press_reviews.contributor_id == auth.user_id)
    ).count()

    submitter = None
    if (art.anonymous_submission is False) or (qyIsRecommender > 0) or (qyIsCoRecommender > 0) or (auth.has_membership(role="manager")):
        submitter = db(db.auth_user.id == art.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
        if submitter is None:
            submitter = FakeSubmitter()
        hideSubmitter = False

    if art.already_published is False:
        result = DIV(
            I(current.T("Submitted by ")),
            I(mkAnonymousArticleField(auth, db, hideSubmitter,
                B(get_name_from_details(art.submitter_details)
                if art.submitter_details else mkUser_U(auth, db, submitter, linked=True)), art.id)),
            I(art.upload_timestamp.strftime(" " + DEFAULT_DATE_FORMAT + " %H:%M") if art.upload_timestamp else ""),
        )
    else:
        result = ""

    return result


######################################################################################################################################################################
def mkRecommendersString(auth, db, recomm):
    recommenders = [mkUser(auth, db, recomm.recommender_id).flatten()]
    contribsQy = db(db.t_press_reviews.recommendation_id == recomm.id).select()
    n = len(contribsQy)
    i = 0
    for contrib in contribsQy:
        i += 1
        if i < n:
            recommenders += ", "
        else:
            recommenders += " and "
        recommenders += mkUser(auth, db, contrib.contributor_id).flatten()
    recommendersStr = "".join(recommenders)
    return recommendersStr

######################################################################################################################################################################
def mkReviewerInfo(auth, db, user, orcid: bool = False):
    anchor = ""
    if user:
        if "auth_user" in user:
            user = user.auth_user
        else:
            user = user
        last_name = user.last_name or ""
        first_name = user.first_name or ""
        reviewer_name = last_name  + " " + first_name
        institution = user.institution
        institution = "" if institution is None else institution + ", "
        expertise = user.cv
        areas_of_expertise = current.T("Areas of expertise")

        reviewer_name_html = reviewer_name
        if orcid:
            reviewer_name_html = OrcidTools.build_name_with_orcid(reviewer_name, user.orcid)

        anchor = DIV(
            B(reviewer_name_html, _class="article-title"),
            DIV(institution, user.country or ""),
            DIV(A(B(user.website), _href=user.website, _class="doi_url", _target="_blank") if user.website else ""),
            DIV(A(areas_of_expertise, _tabindex="0",  _role="button",
                    _title=(f"{reviewer_name}'s {areas_of_expertise.lower()}"),
                    **{'_data-toggle':'popover',  '_data-trigger':'focus', '_data-content':f'{expertise}'})
                if expertise else ""),
        )
    return anchor

######################################################################################################################################################################
def mkReviewerStat(auth, db, stat):
    anchor = ""
    if stat:
        anchor = DIV(
            DIV((stat[0], " Review(s)") if int(stat[0]) > 0 else ""),
            DIV((stat[1], " Recommendation(s)") if int(stat[1]) > 0 else ""),
            DIV((stat[2], " Co-Recommendation(s)") if int(stat[2]) > 0 else ""),
            DIV(A("See recommender's profile", _href=URL(c="public", f="user_public_page", vars=dict(userId=stat[4])), _target="_blank") if stat[3] == "True" else ""),
        )
    return anchor

######################################################################################################################################################################
def mkRecommenderandContributorList(query):
    result = []
    for i in query:
        try:
            result_dict = {'id': i.recommender_id, 'details': i.recommender_details}
        except:
             result_dict = {'id': i.contributor_id, 'details': i.contributor_details}
        result.append(result_dict)
    return result
######################################################################################################################################
def fetch_url(data):
    result = []
    for doi in data:
        url = mkDOI(doi)
        result.append(url)
    return result

################################################################################
def md_to_html(text: Optional[str]):
    return SPAN(
            TAG(WIKI(text or ""))[0].components
    ) # WIKI returns XML('<p>htmlized text</p>'), replace P with SPAN

################################################################################
def mkSearchWidget(chars):
    container = DIV(_id='about-search-widget')
    label = LABEL('Quick access', _style='margin-right: 20px')
    span = SPAN(_class='pci-capitals')
    for char in chars:
        span.append(A(char, _href='#' + char, _style="margin-right: 20px"))

    container.append(label)
    container.append(BR())
    container.append(span)

    return container

#################################################################################

def confirmationDialog(text):
    return DIV( 
    DIV(TAG(current.T(text)), _class="modal-body"), 
    DIV(SPAN(current.T("confirm"), _type="button", **{'_data-dismiss': 'modal'}, _class="btn btn-info", _id="confirm-dialog"),
        SPAN(current.T("cancel"), _type="button", **{'_data-dismiss': 'modal'}, _class="btn btn-default", _id="cancel-dialog"),
    _class="modal-footer"), _id="confirmation-modal", _class="modal fade", _role="dialog")

##################################################################################

def hypothesis_dialog(article: Row):
    hypothesis_client = Hypothesis(article)

    if not hypothesis_client.has_stored_annotation():
        hypothesis_client.store_annotation(hypothesis_client.generate_annotation_text())

    form = FORM(
            DIV(H5(TAG(current.T("Hypothes.is")), _class="modal-title", _id="info-dialog-title"), _class="modal-header"),
            DIV(TAG(current.T("The following annotation is going to be posted on Biorxiv with Hypothes.is:") + "<br/>"),
                TEXTAREA(hypothesis_client.get_stored_annotation(), _name=f'hypothesis_annotation_form', _class='form-control'),
                _class="modal-body", id="info-modal-body"), 
            DIV(INPUT(_type="submit", **{'_data-dismiss': 'modal'}, _class="btn btn-info", _id="confirm-dialog"),
                SPAN(current.T("cancel"), _type="button", **{'_data-dismiss': 'modal'}, _class="btn btn-default", _id="cancel-dialog"),
            _class="modal-footer"), _id="info-dialog", _class="modal fade", _role="dialog")
    
    if form.process().accepted:
        hypothesis_client.store_annotation(form.vars.hypothesis_annotation_form)
        redirect(URL(c="manager_actions", f="do_recommend_article", vars=dict(articleId=article.id), user_signature=True))

    return form

#############################################################################

def write_edit_upload_review_button(review_id: int):
    return A(current.T('Write, edit or upload your review'),
            _href=URL(c='user', f='edit_review', vars=dict(reviewId=review_id)),
            _class="buttontext btn btn-default",
            _style="color: #3e3f3a; background-color: white;"
        )
###################################################################################

def custom_mail_dialog(article_id: int, subject: str, message: str, submit_url: str):
    form = DIV(
            DIV(H5(TAG(subject), _value=subject, _class="modal-title mail-dialog-title", _id=f"mail-dialog-title-{article_id}"), _class="modal-header"),
            DIV(TEXTAREA(message, _name='mail_templates_contents', _class='form-control', _id=f'mail_templates_contents_{article_id}'),
                _class="modal-body"),
            DIV(A(current.T("send"), _type="button", **{'_data-dismiss': 'modal'}, _href=submit_url, _class="btn btn-info confirm-mail-dialog", _id=f"confirm-mail-dialog-{article_id}"),
                SPAN(current.T("cancel"), _type="button", **{'_data-dismiss': 'modal'}, _class="btn btn-default cancel-mail-dialog", _id=f"cancel-mail-dialog-{article_id}"),
            _class="modal-footer"), _id=f"mail-dialog-{article_id}", _class="modal fade mail-dialog", _role="dialog")

    return form

###################################################################################

def complete_profile_dialog(next: str):
    return DIV( 
    DIV(TAG('Some information from your profile is missing. Do you want to complete your profile now?'), _class="modal-body"), 
    DIV(A(current.T("Complete my profile"), _href=URL("default", "user/profile", user_signature=True, vars=dict(_next=next)), _class="btn btn-info", _id="complete-profile-confirm-dialog"),
        SPAN(current.T("Later"), _type="button", **{'_data-dismiss': 'modal'}, _class="btn btn-default", _id="complete-profile-cancel-dialog"),
    _class="modal-footer"), _id="complete-profile-modal", _class="modal fade", _role="dialog")

####################################################################################

def complete_orcid_dialog(db: DAL): 
    radio_label_style = "display: inline;"
    radio_container_style = "margin-top: 5px;"
    url = cast(str, URL("default", "orcid_choice"))
    
    return DIV(
        OrcidTools.get_orcid_formatter_script(),
        common_tools.get_script('complete_orcid_dialog.js'),
        DIV(
            IMG(_alt="ORCID_LOGO", _src=URL(c="static", f="images/ORCID_ID.svg"), _heigth="50px", _width="50px", _style="margin-left: 10px"),
            H4(current.T('You have not declared your ORCID number yet'), _class="modal-body", _style="display: inline-block; font-weight: bold; position: relative; top: 3px; white-space: break-spaces; max-width: 90%"),
            _style="white-space: nowrap; width: fit-content"),
        HR( _class="hr"),
        DIV(
            DIV(INPUT(_type="radio", _id="yes-orcid", _name="orcid_radio", _value="yes",  _checked="checked"), LABEL(current.T("Please, set my ORCID number in my profile"), _for="yes-orcid", _style=radio_label_style), _style="display: inline-block; margin-right: 20px"),
            OrcidTools.configure_orcid_input(INPUT(_id="auth_user_orcid", _type="text", _name="orcid", _class="form-control pci2-input", _style="width: 180px; margin-top: 5px; display: inline-block")),
            P(current.T("(provide your ORCID number as follow: 0000-000X-XXX-XXX)"), _style="font-size: smaller; margin-bottom: 0px;"),
            DIV(INPUT(_type="radio", _id="no-orcid", _name="orcid_radio", _value="no"), LABEL(current.T("You prefer not to provide an ORCID number; we will not remind you to fill it in"), _for="no-orcid", _style=radio_label_style), _style=radio_container_style),
            DIV(INPUT(_type="radio", _id="later-orcid", _name="orcid_radio", _value="later"), LABEL("Remind me later", _for="later-orcid", _style=radio_label_style), _style=radio_container_style + "margin-bottom: 20px"),
        _style="margin-left: 10px; margin-right: 10px; margin-bottom: 10px"
        ),

        DIV(BUTTON(current.T("Submit"), _class="btn btn-info", _id="complete-orcid-dialog-confirm", _onclick=f"submitForm('{url}')"), _class="modal-footer", _style="justify-content: left; display: flex"),
        _id="complete-profile-modal", _class="modal fade", _role="dialog", _style="min-width: 330px; max-width: 585px; top: 50%; left: 50%; width: 50%; transform:translate(-50%,-50%);")

####################################################################################

def invitation_to_review_form(request: Request, auth: Auth, db: DAL, article_id: int, user: User, review: Review, more_delay: bool):
    disclaimerText = DIV(getText(request, auth, db, "#ConflictsForReviewers"))
    dueTime = review.review_duration.lower() if review.review_duration else 'three weeks'

    form = FORM(
        INPUT(_value=article_id, _type="hidden", name="articleId"),
        INPUT(_value="true", _type="hidden", _name="ethics_approved"),
        DIV(
            LABEL(
                INPUT(_type="checkbox", _name="no_conflict_of_interest", _id="no_conflict_of_interest", _value="yes"),
                B(TAG(current.T("I declare that I have no conflict of interest with the authors or the content of the article")))
            ),
            _class="checkbox"
        ),
        SPAN(disclaimerText),
        _id="invitation-to-review-form", _enctype="multipart/form-data", _method="POST"
    )

    if not more_delay:
        form.append(DIV(
            LABEL(
                INPUT(_type="checkbox", _name="due_time", _id="due_time", _value="yes"),
                B(TAG(current.T('I agree to post my review within %s.') % dueTime))
            ),
            _class="checkbox")
        )
    
    form.append(DIV(
        LABEL(
            INPUT(_type="checkbox", _name="anonymous_agreement", _id="anonymous_agreement", _value="yes"),
            B(TAG(current.T('In the event that authors submit their article to a journal once recommended by PCI, I agree that my name and my Email address may be passed on in confidence to that journal.')))
        ),
        _class="checkbox"
    ))

    if not user.ethical_code_approved:
        form.append(
            DIV(
                LABEL(
                    INPUT(_type="checkbox", _name="cgu_checkbox", _id="cgu_checkbox", _value="yes"),
                    B(
                        TAG(current.T("I agree to comply with the ")),
                        A(TAG(current.T("General Terms of Use")), _target="_blank", _href=URL('about', 'gtu')),
                        TAG(" and the "),
                        A(TAG(current.T("code of conduct")), _target="_blank", _href=URL('about', 'ethics'))
                    )
                ),
                _class="checkbox"   
            )
        )

    if more_delay:
        form.append(
            DIV(
                LABEL(
                    INPUT(_type="checkbox", _name="new_delay_agreement", _id="new_delay_agreement", _value="yes"),
                    B(TAG(current.T('I agree to post my review within the following duration.')))
                ),
            _class="checkbox"
            )
        )

        delay_form = SQLFORM.factory(
            Field("review_duration", type="text", label=current.T("Choose the duration before posting my review"), default=dueTime.capitalize(), requires=IS_IN_SET(db.review_duration_choices, zero=None)),
            buttons=[]
        )
        form.append(delay_form.components[0])

    form.append(
        DIV(
            INPUT(_type="submit", _class="btn btn-success pci-panelButton", _value=current.T('Yes, I would like to review this preprint')),
            A(current.T('No thanks, I\'d rather not'), _href=URL(c='user_actions', f='decline_review',  vars=dict(reviewId=review.id, key=review.quick_decline_key)), _class="buttontext btn btn-warning"),
            _class="pci2-flex-center"
        )
    )

    return form
