import gc
import os
import pytz
from re import sub, match
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import *
from collections import OrderedDict

import io
from PIL import Image

from gluon import current, IS_IN_DB
from gluon.tools import Auth
from gluon.html import *
from gluon.template import render
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Mail
from gluon.sqlhtml import *

from app_modules import common_tools

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
    if (doi is not None) and (doi != ""):
        if match("^http", doi):
            return A(B(doi), _href=doi, _class="doi_url", _target="_blank")
        else:
            return A(B(doi), _href="https://doi.org/" + sub(r"doi: *", "", doi), _class="doi_url", _target="_blank")
    else:
        return SPAN("", _class="doi_url")


def mkSimpleDOI(doi):
    if (doi is not None) and (doi != ""):
        if match("^http", doi):
            return A(doi, _href=doi)
        else:
            return A(doi, _href="https://doi.org/" + sub(r"doi: *", "", doi))
    else:
        return ""


def mkLinkDOI(doi):
    if (doi is not None) and (doi != ""):
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
        resu.append(TD(A(" [%s]" % userRow.email, _href="mailto:%s" % userRow.email) if withMail else TD("")))
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
def mkUser_U(auth, db, theUser, linked=False, scheme=False, host=False, port=False):
    if theUser:
        if linked:
            resu = A(
                B("%s %s" % (theUser.first_name, theUser.last_name)),
                _href=URL(c="public", f="user_public_page", scheme=scheme, host=host, port=port, vars=dict(userId=theUser.id)),
                _class="cyp-user-profile-link",
            )
        else:
            resu = SPAN("%s %s" % (theUser.first_name, theUser.last_name))
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
def mkUserWithMail(auth, db, userId, linked=False, scheme=False, host=False, port=False):
    resu = SPAN("?")
    if userId is not None:
        theUser = db(db.auth_user.id == userId).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name, db.auth_user.email).last()
        if theUser:
            if linked:
                resu = SPAN(
                    A(
                        "%s %s" % (theUser.first_name, theUser.last_name),
                        _href=URL(c="public", f="user_public_page", scheme=scheme, host=host, port=port, vars=dict(userId=userId)),
                    ),
                    A(" [%s]" % theUser.email, _href="mailto:%s" % theUser.email),
                )
            else:
                resu = SPAN(SPAN("%s %s" % (theUser.first_name, theUser.last_name)), A(" [%s]" % theUser.email, _href="mailto:%s" % theUser.email))
        else:
            resu = SPAN("?")
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
def mkStatusDiv(auth, db, status, showStage=False, stage1Id=None, reportStage="Stage not set"):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles(db)
    status_txt = (current.T(status)).upper()
    color_class = statusArticles[status]["color_class"] or "default"
    hint = statusArticles[status]["explaination"] or ""

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
# Builds a coloured status label with pre-decision concealed
def mkStatusDivUser(auth, db, status, showStage=False, stage1Id=None, reportStage="Stage not set"):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles(db)
    if status.startswith("Pre-"):
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
    if status.startswith("Pre-"):
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
def mkReviewStateDiv(auth, db, state):
    # state_txt = (current.T(state)).upper()
    state_txt = (state or "").upper()
    if state == "Awaiting response" or state == "Willing to review":
        color_class = "warning"
    elif state == "Declined by recommender":
        color_class = "danger"
    elif state == "Awaiting review":
        color_class = "info"
    elif state == "Review completed":
        color_class = "success"
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
                im.thumbnail(size, Image.ANTIALIAS)
                imgByteArr = io.BytesIO()
                im.save(imgByteArr, format="PNG")
                imgByteArr = imgByteArr.getvalue()
                user.update_record(picture_data=imgByteArr)
        except:
            pass
    return


######################################################################################################################################################################
def makeArticleThumbnail(auth, db, articleId, size=(150, 150)):
    art = db(db.t_articles.id == articleId).select().last()
    if art and art.picture_data:
        try:
            im = Image.open(io.BytesIO(art.picture_data))
            width, height = im.size
            if width > 200 or height > 200:
                im.thumbnail(size, Image.ANTIALIAS)
                imgByteArr = io.BytesIO()
                im.save(imgByteArr, format="PNG")
                imgByteArr = imgByteArr.getvalue()
                art.update_record(picture_data=imgByteArr)
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
def mkAnonymousArticleField(auth, db, anon, value):
    if anon is True:
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
        if scheduledSubmissionActivated and art.doi is None and art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        if urlArticle:
            anchor = DIV(
<<<<<<< HEAD
                A(B(art.title or "", _class="article-title"), _href=urlArticle),
                SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
                BR(),
                doi_text,
                _class="ellipsis-over-350",
=======
                A(B(art.title), _href=urlArticle), BR(), SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)), BR(), doi_text, _class="ellipsis-over-350",
>>>>>>> b2133f2 (add DEFAULT_DATE_FORMAT to format date differently for RR and other PCIs)
            )
        else:
            anchor = DIV(
                B(art.title or ""),
                SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
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
        if scheduledSubmissionActivated and art.doi is None and art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        if urlArticle:
            anchor = DIV(
                A(B(art.title or "", _class="article-title"), _href=urlArticle),
                BR(),
                SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
                BR(),
                doi_text,
                BR(),
                B(current.T("Status: "), mkStatusSimple(auth, db, art.status)),
            )
        else:
            anchor = DIV(
                B(art.title or ""),
                SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
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
        if scheduledSubmissionActivated and art.doi is None and art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        anchor = DIV(
            B(art.title, _class="article-title"),
            DIV(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
            doi_text,
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
        if scheduledSubmissionActivated and art.doi is None and art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        anchor = DIV(
            B(art.title or "", _class="article-title"),
            DIV(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
            doi_text,
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
            if scheduledSubmissionActivated and art.doi is None and art.scheduled_submission_date is not None:
                doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

            anchor = DIV(
                B(recomm.recommendation_title),
                SPAN(current.T(" by ")),
                recommenders,
                mkDOI(recomm.recommendation_doi),
                P(),
                SPAN(current.T("A recommendation of ")),
                I(art.title or "", _class="article-title"),
                SPAN(current.T(" by ")),
                SPAN(mkAnonymousArticleField(auth, db, art.anonymous_submission, art.authors)),
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
    citeRecomm = SPAN(SPAN(whoDidItCite), " ", myRecomm.last_change.strftime("(%Y)"), " ", (myRecomm.recommendation_title or ""), ". ", I(applongname) + citeNum, SPAN(" "), doi)
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
            SPAN(art.title or "", _class="article-title"),
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
            hrevs.append(LI(mkUserWithMail(auth, db, rev.contributor_id)))
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
def getRecommAndReviewAuthors(auth, db, article=dict(), recomm=dict(), with_reviewers=False, as_list=False, linked=False, host=False, port=False, scheme=False):
    whoDidIt = []

    if hasattr(recomm, "article_id"):
        article = db(db.t_articles.id == recomm.article_id).select(db.t_articles.id, db.t_articles.already_published).last()

    if hasattr(article, "id"):
        mainRecommenders = db((db.t_recommendations.article_id == article.id) & (db.t_recommendations.recommender_id == db.auth_user.id)).select(
            db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name
        )

        coRecommenders = db(
            (db.t_recommendations.article_id == article.id)
            & (db.t_press_reviews.recommendation_id == db.t_recommendations.id)
            & (db.auth_user.id == db.t_press_reviews.contributor_id)
        ).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)

        allRecommenders = mainRecommenders | coRecommenders

        if article.already_published:  # NOTE: POST-PRINT
            nr = len(allRecommenders)
            ir = 0
            for theUser in allRecommenders:
                ir += 1
                if as_list:
                    whoDidIt.append("%s %s" % (theUser.first_name, theUser.last_name))
                else:
                    whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme))
                    if ir == nr - 1 and ir >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif ir < nr:
                        whoDidIt.append(", ")

        else:  # NOTE: PRE-PRINT
            if with_reviewers:
                namedReviewers = db(
                    (db.t_recommendations.article_id == article.id)
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    & (db.auth_user.id == db.t_reviews.reviewer_id)
                    & (db.t_reviews.anonymously == False)
                    & (db.t_reviews.review_state == "Review completed")
                ).select(db.auth_user.ALL, distinct=db.auth_user.ALL, orderby=db.auth_user.last_name)
                na = db(
                    (db.t_recommendations.article_id == article.id)
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    & (db.auth_user.id == db.t_reviews.reviewer_id)
                    & (db.t_reviews.anonymously == True)
                    & (db.t_reviews.review_state == "Review completed")
                ).count(distinct=db.auth_user.id)
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
                    whoDidIt.append("%s %s" % (theUser.first_name, theUser.last_name))
                else:
                    whoDidIt.append(mkUser_U(auth, db, theUser, linked=linked, host=host, port=port, scheme=scheme))
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
                    whoDidIt.append("%s %s" % (theUser.first_name, theUser.last_name))
                else:
                    whoDidIt.append(mkUser_U(auth, db, theUser, linked=False, host=host, port=port, scheme=scheme))
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
            I(mkAnonymousArticleField(auth, db, hideSubmitter, B(mkUser_U(auth, db, submitter, linked=True)),)),
<<<<<<< HEAD
            I(art.upload_timestamp.strftime(" %Y-%m-%d %H:%M") if art.upload_timestamp else ""),
=======
            I(art.upload_timestamp.strftime(" " + DEFAULT_DATE_FORMAT + " %H:%M") if art.upload_timestamp else ""),
>>>>>>> b2133f2 (add DEFAULT_DATE_FORMAT to format date differently for RR and other PCIs)
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
