from typing import Any, Dict, List, Optional, Tuple, Union, cast
from re import sub, match
from datetime import datetime
from app_components import ongoing_recommendation
from dateutil.relativedelta import *

import bs4
import io
from PIL import Image

from gluon import current, IS_IN_SET
from gluon.html import *
from gluon.contrib.markdown import WIKI # type: ignore
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon.sqlhtml import *
from models.article import Article, ArticleStatus, StepNumber
from models.recommendation import Recommendation
from models.press_reviews import PressReview
from models.review import Review, ReviewState
from models.user import User
from models.suggested_recommender import SuggestedRecommender

from app_modules.helper import getText
from app_modules import common_tools
from app_modules.hypothesis import Hypothesis
from app_modules.orcid import OrcidTools

from gluon import current

from app_modules.common_tools import URL, doi_to_url

myconf = AppConfig(reload=True)


pciRRactivated = myconf.get("config.registered_reports", default=False)
scheduledSubmissionActivated = myconf.get("config.scheduled_submissions", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

######################################################################################################################################################################
# Time and date
######################################################################################################################################################################
def mkLastChange(t: Optional[datetime.datetime]):
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
def mkElapsedDays(t: Optional[datetime.datetime]):
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
def mkElapsed(t: datetime.datetime):
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
def mkDOI(doi: Optional[str]):
    doi_url = mkLinkDOI(doi)
    if doi_url:
        return A(B(doi), _href=doi_url, _class="doi_url", _target="_blank")
    else:
        return SPAN("", _class="doi_url")


def mkSimpleDOI(doi: Optional[str]):
    doi_url = mkLinkDOI(doi)
    return A(doi, _href=doi_url) if doi_url else ""


def mkLinkDOI(doi: Optional[str]):
    if doi:
        doi = doi.strip()
        if match("^http", doi):
            return doi
        else:
            return "https://doi.org/" + sub(r"doi: *", "", doi)
    else:
        return ""


######################################################################################################################################################################
def mkUser(userId: Optional[int], linked: bool = False, orcid: bool = False, orcid_exponant: bool = False, reverse: bool = False, mail_link: bool = False):
    if userId is not None:
        theUser = User.get_by_id(userId)
        if theUser:
            return mkUser_U(theUser, linked=linked, orcid=orcid, orcid_exponant=orcid_exponant, reverse=reverse, mail_link=mail_link)
        else:
            return SPAN("")
    else:
        return SPAN("")


######################################################################################################################################################################
def mkUserId(userId, linked=False, fullURL=False):
    resu = SPAN("")
    if userId is not None:
        if linked:
            resu = A(B(str(userId)), _href=URL(c="public", f="user_public_page", scheme=fullURL, vars=dict(userId=userId)), _class="cyp-user-profile-link")
        else:
            resu = SPAN(str(userId))
    return resu


######################################################################################################################################################################
def cut_composed_name(name: str):
    particles = name.split(" ")
    names: List[str] = []

    for particle in particles:
        if len(particle) == 0:
            continue

        if "-" in particle:
            dash_name = particle.split('-')
            els: List[str] = []

            for d in dash_name:
                if len(d) == 0:
                    continue
                els.append(f"{d[0].upper()}.")

            particle = "-".join(els)
            names.append(particle)
        else:
            names.append(f"{particle[0].upper()}.")

    return " ".join(names)


def mkUser_U(user: User, linked: bool = False, reverse: bool = False, orcid: bool = False, orcid_exponant: bool = False, mail_link: bool = False):
    if not user:
        return SPAN("?")

    first_name = user.first_name or "?"
    last_name = user.last_name or "?"

    if reverse:
        first_name = cut_composed_name(first_name)
        name = f"{last_name}, {first_name}"
    else:
        name = f"{first_name} {last_name}"

    if mail_link and user.email and not user.deleted:
        result = A(B(name),
                    _href=f"mailto:{user.email}",
                    _class="cyp-user-profile-link")
    elif linked and not user.deleted:
        result = A(B(name),
                    _href=URL(c="public", f="user_public_page",scheme=True, vars=dict(userId=user.id)),
                    _class="cyp-user-profile-link")
    else:
        result = SPAN(name)

    if orcid:
        result = OrcidTools.build_name_with_orcid(result, user.orcid, height='15px', width='15px', style='margin-right: 3px')
    if orcid_exponant:
        style = 'margin-right: 3px; position: relative; bottom: 12px; left: 2px'
        result = OrcidTools.build_name_with_orcid(result, user.orcid, height='12px', width='12px', style=style, force_style=True)
    return result


######################################################################################################################################################################
def mkUserWithAffil_U(theUser: User, linked=False, fullURL=False):
    if theUser:
        if linked and not theUser.deleted:
            resu = SPAN(
                A(
                    "%s %s" % (theUser.first_name, theUser.last_name),
                    _href=URL(c="public", f="user_public_page", scheme=fullURL, vars=dict(userId=theUser.id)),
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
def mkUserWithMail(userId: Optional[int], linked: bool = False, reverse: bool = False, orcid: bool = False):
    db = current.db
    if userId is not None:
        theUser: Optional[User] = db(db.auth_user.id == userId).select().last()
    else:
        theUser = None

    user_with_mail = mk_user(theUser, linked, reverse)
    if orcid and theUser:
        return OrcidTools.build_name_with_orcid(user_with_mail, theUser.orcid)
    else:
        return user_with_mail


def mk_user(theUser: Optional[User], linked: bool = False, reverse: bool = False):
        if theUser:
            if reverse: name = "%s, %s" % (theUser.last_name, theUser.first_name)
            else: name = "%s %s" % (theUser.first_name, theUser.last_name)
            if linked and not theUser.deleted:
                resu = SPAN(
                    A(
                        name,
                        _href=URL(c="public", f="user_public_page",
                            scheme=True, vars=dict(userId=theUser.id)),
                    ),
                    SPAN(" [%s]" % theUser.email))
            else:
                resu = SPAN(
                    SPAN(name),
                    SPAN(" [%s]" % theUser.email))
        else:
            resu = SPAN("?")

        return resu

######################################################################################################################################################################
# Article status
######################################################################################################################################################################
statusArticles: Optional[Dict[str, Dict[str, Optional[str]]]] = dict()


def mkStatusArticles():
    db = current.db
    statusArticles.clear()
    for sa in db(db.t_status_article).select():
        statusArticles[sa["status"]] = sa


######################################################################################################################################################################
def mkStatusSimple(status):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles()
    status_txt = (current.T(status)).upper()
    color_class = statusArticles[status]["color_class"] or "default"
    hint = statusArticles[status]["explaination"] or ""
    return SPAN(status_txt, _style="margin: 0; padding:0", _class="pci-status " + color_class, _title=current.T(hint))


######################################################################################################################################################################
# Builds a coloured status label
def mkStatusDiv(status: str, showStage: bool = False, stage1Id: Optional[int] = None, reportStage: Optional[str] = "Stage not set", submission_change: Optional[bool] = False):
    auth = current.auth
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles()
    status_txt = (current.T(status)).upper()
    color_class = statusArticles[status]["color_class"] or "default" if statusArticles is not None else "default"
    hint = statusArticles[status]["explaination"] or "" if statusArticles is not None else ""
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

        result = DIV(
            DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint), _style="text-align: center;"),
            DIV(B(current.T(reportStage)), stage1Link, _class="pci-status-addition", _style="text-align: center; width: 150px;"),
            DIV(B(current.T(change_text)), _class="pci-status-addition", _style="text-align: center;"),
        )


    else:
        result = DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint))

    return result


######################################################################################################################################################################
# Builds a coloured status label with pre-decision concealed
def mkStatusDivUser(status: str, showStage: bool = False, stage1Id: Optional[int] = None):
    auth = current.auth
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles()
    if status.startswith("Pre-") and status != "Pre-submission":
        status2 = "Under consideration"
    else:
        status2 = status
    status_txt = (current.T(status2)).upper()

    color_class = (statusArticles.get(status2, {}).get("color_class", "default") if statusArticles else "default") or "default"
    hint = (statusArticles.get(status2, {}).get("explaination", "") if statusArticles else "") or ""

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

        result = DIV(
            DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint), _style="text-align: center;"),
            DIV(B(current.T(reportStage)), stage1Link, _style="text-align: center; width: 150px;"),
        )
    else:
        result = DIV(status_txt, _class="pci-status " + color_class, _title=current.T(hint))

    return result


######################################################################################################################################################################
def mkStatusBigDiv(status: str, printable: bool = False):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles()
    status_txt = (current.T(status)).upper()
    color_class = statusArticles[status]["color_class"] or "default"
    hint = statusArticles[status]["explaination"] or ""

    if printable:
        printable_class = " printable"
    else:
        printable_class = ""

    return DIV(status_txt, _class="pci-status-big " + color_class + printable_class, _title=current.T(hint))


######################################################################################################################################################################
def mkStatusBigDivUser(status: str, printable: bool = False):
    if statusArticles is None or len(statusArticles) == 0:
        mkStatusArticles()
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
def mkReviewStateDiv(state: Optional[str], review: Optional[Review] = None):
    # state_txt = (current.T(state)).upper()
    state_txt = (state or "").upper()
    if state == ReviewState.AWAITING_RESPONSE.value or state == ReviewState.WILLING_TO_REVIEW.value:
        color_class = "warning"
    elif state == ReviewState.DECLINED_BY_RECOMMENDER.value:
        color_class = "danger"
    elif state == ReviewState.AWAITING_REVIEW.value:
        color_class = "info"
        if review:
            due_date = Review.get_due_date(review)
            state_txt = f"{state_txt}: DUE {due_date.strftime('%b %d, %Y').upper()}"
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
def mkContributionStateDiv(state):
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
def makeUserThumbnail(userId, size=(150, 150)):
    db = current.db
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
def mkAnonymousMask(anon):
    if anon is True:
        return DIV(IMG(_alt="anonymous", _src=URL(c="static", f="images/mask.png")), _style="text-align:center;")
    else:
        return ""


######################################################################################################################################################################
def mkAnonymousArticleField(anon: Optional[bool], value: Any, articleId: int):
    auth = current.auth
    recomm = Article.get_last_recommendation(articleId)
    isRecommender = recomm and recomm.recommender_id == auth.user_id
    if anon is True and not isRecommender:
        return IMG(_alt="anonymous", _src=URL(c="static", f="images/mask.png"))
    else:
        return value


######################################################################################################################################################################
def mkJournalImg(press):
    if press is True:
        return DIV(IMG(_alt="published", _src=URL(c="static", f="images/journal.png")), _style="text-align:center;")
    else:
        return ""


######################################################################################################################################################################
# Buttons
######################################################################################################################################################################
def mkViewEditRecommendationsRecommenderButton(row):
    return A(
        SPAN(current.T("View / Edit"), _class="buttontext btn btn-default pci-button"),
        _href=URL(c="recommender", f="recommendations", vars=dict(articleId=row.article_id)),
        _class="button",
        _title=current.T("View and/or edit article"),
    )


######################################################################################################################################################################
# code for a "Back" button
# go to the target instead, if any.
def mkBackButton(text: str = current.T("Back"), target: Optional[str] = None):
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
def mkRepresentArticleLightLinked(article_id: int, urlArticle: Optional[str] = None):
    db = current.db
    anchor = ""
    art = db.t_articles[article_id]

    if art:
        # Scheduled submission status (instead of DOI)
        doi_text = mkDOI(art.doi)
        if scheduledSubmissionActivated and  art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        if urlArticle:
            anchor = DIV(
                A(B(md_to_html(art.title)), _href=urlArticle), BR(), SPAN(mkAnonymousArticleField(art.anonymous_submission, art.authors, art.id)), BR(), doi_text, _class="ellipsis-over-350",
            )
        else:
            anchor = DIV(
                B(md_to_html(art.title) or ""),
                SPAN(mkAnonymousArticleField(art.anonymous_submission, art.authors, art.id)),
                BR(),
                doi_text,
                _class="ellipsis-over-350",
            )

    return anchor


######################################################################################################################################################################
def mkRepresentArticleLightLinkedWithStatus(article_id: int, urlArticle: Optional[str] = None):
    db = current.db
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
                SPAN(mkAnonymousArticleField(art.anonymous_submission, art.authors, art.id)),
                BR(),
                doi_text,
                BR(),
                B(current.T("Status: "), mkStatusSimple(art.status)),
            )
        else:
            anchor = DIV(
                B(md_to_html(art.title) or ""),
                SPAN(mkAnonymousArticleField(art.anonymous_submission, art.authors, art.id)),
                BR(),
                doi_text,
                _class="ellipsis-over-350",
            )

    return anchor


######################################################################################################################################################################
def mkRepresentArticleLight(article_id: int):
    db = current.db
    anchor = ""
    art = db.t_articles[article_id]
    if art:
        # Scheduled submission status (instead of DOI)
        doi_text = mkDOI(art.doi)
        if scheduledSubmissionActivated and  art.scheduled_submission_date is not None:
            doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(art.scheduled_submission_date))))

        anchor = DIV(
            B(md_to_html(art.title), _class="article-title"),
            DIV(mkAnonymousArticleField(art.anonymous_submission, art.authors, art.id)),
            doi_text,
            BR(),
            SPAN(" " + current.T("ArticleID") + " #" + str(art.id)),
            BR(),
            SPAN(" " + current.T("version") + " " + art.ms_version) if art.ms_version else "",
            (BR() + SPAN(art.article_source) if art.article_source else ""),
        )
    return anchor


def represent_article_with_recommendation_info(recommendation_id: int):
    recommendation = Recommendation.get_by_id(recommendation_id)
    if not recommendation:
        return ''

    article = Article.get_by_id(recommendation.article_id)
    if not article:
        return ''

    html = ''

    if scheduledSubmissionActivated and  article.scheduled_submission_date is not None:
        doi_text = SPAN(B("Scheduled submission: ", _style="color: #ffbf00"), B(I(str(article.scheduled_submission_date))))
    else:
        doi_text = mkDOI(recommendation.doi)

    html = DIV(
            B(md_to_html(article.title), _class="article-title"),
            DIV(mkAnonymousArticleField(article.anonymous_submission, article.authors, article.id)),
            doi_text,
            BR(),
            SPAN(" " + current.T("ArticleID") + " #" + str(article.id)),
            BR(),
            SPAN(" " + current.T("version") + " " + recommendation.ms_version) if recommendation.ms_version else "",
            (BR() + SPAN(article.article_source) if article.article_source else ""),
        )

    return html


def represent_article_manager_board(article: Article, last_recommendation: Optional[Recommendation]):
    html: List[Union[DIV, str]] = []

    title = " ".join((article.title or "").split(" ")[:7])
    if article.title and len(article.title) > len(title):
        title += "…"

    html.append(B(title, _class="article-title", _title=article.title))

    html.append(BR())
    html.append(f"ArticleID #{article.id}")

    html.append(BR())
    html.append("Submitter: ")
    html.append(mkUser(article.user_id, mail_link=True, reverse=True))

    if last_recommendation:
        html.append(BR())
        html.append("Recommender: ")
        html.append(mkUser(last_recommendation.recommender_id, mail_link=True, reverse=True))

        press_reviews = PressReview.get_by_recommendation(last_recommendation.id)
        if len(press_reviews) > 0:
            html.append(BR())
            html.append("Co-recommender: " if len(press_reviews) == 1 else "Co-recommenders: ")
        for i, press_review in enumerate(press_reviews):
            if press_review.contributor_id:
                co_recommender = mkUser(press_review.contributor_id, mail_link=True, reverse=True)
                html.append(co_recommender)
                if i + 1 < len(press_reviews):
                    html.append(', ')


    return DIV(*html, _style="width: max-content; max-width: 250px;")


def represent_link_column_manager_board(article: Article, last_recommendation: Optional[Recommendation]):
    actions: List[DIV] = []
    manager_actions =  ongoing_recommendation.get_recommendation_status_buttons(article, last_recommendation)

    if article.status == ArticleStatus.PRE_SUBMISSION.value:
        validate_stage_button = ongoing_recommendation.validate_stage_button(article)
        if validate_stage_button:
            validate_stage_button: ... = validate_stage_button.components[0]
            validate_stage_button.attributes['_style'] = ''
            validate_stage_button.attributes['_class'] = ''
            validate_stage_button.components[0].attributes['_class'] = ''
            validate_stage_button.components[0].attributes['_style'] = ''
            actions.append(validate_stage_button)

    if article.status == ArticleStatus.PENDING.value:
        put_in_pre_submission_button = ongoing_recommendation.put_in_presubmission_button(article, True)
        if put_in_pre_submission_button:
            actions.append(put_in_pre_submission_button)

    if (article.status in (ArticleStatus.AWAITING_CONSIDERATION.value, ArticleStatus.PENDING.value, ArticleStatus.PRE_SUBMISSION.value)):
        actions.append(ongoing_recommendation.not_considered_button(article, True))

    if len(actions) > 0:
        actions.append(LI(_role="separator", _class="divider"))

    return \
    DIV(
        ongoing_recommendation.view_edit_button(article),
        DIV(
            BUTTON(
                "Actions",
                SPAN(_class="caret", _style="position: relative; left: 5px; bottom: 2px;"),
                _class="btn btn-default dropdown-toggle" if len(actions) == 0 else "btn btn-danger dropdown-toggle",
                _type="button",
                _id=f"action_{article.id}",
                **{'_data-toggle':'dropdown', '_aria-haspopup': 'true', '_aria-expanded': 'false'},
                _style="display: block",
            ),
            UL(
                *actions,
                *manager_actions,
            _class="dropdown-menu"),
        _class="btn-group"),
        _style="display: flex; align-items: center; flex-direction: column;"
    )


def represent_alert_manager_board(article: Article):
    alert_date = article.alert_date

    if not alert_date:
        return ''
    else:
        if alert_date <= datetime.date.today():
            style = "color: #d9534f;"
        else:
            style = ""

        return DIV(
            STRONG(alert_date.strftime(DEFAULT_DATE_FORMAT), _style=style, _class="article-alert"),
            _style="width: 50px;")


def represent_current_step_manager_board(article: Article):
    current_step = article.current_step
    if current_step:
        return XML(current_step)
    else:
        return ''


def represent_rdv_date(article: Article):
    input = INPUT(_type="date",
                  _id=f"rdv_date_{article.id}",
                  _name=f"rdv_date_{article.id}",
                  _value=article.rdv_date,
                  _min=datetime.date.today(),
                  _onchange=f'rdvDateInputChange({article.id}, "{URL(c="manager", f="edit_rdv_date", scheme=True)}")',
                  _style="flex")

    if not article.rdv_date:
        value = I(_class="glyphicon glyphicon-edit")
        style = "font-size: 15px;"
    else:
        value = article.rdv_date.strftime(DEFAULT_DATE_FORMAT)
        style = "background: none; color: inherit; border: 1px solid #dfd7ca; padding: 2px 2px 3px 2px; white-space: normal; width: 50px;"

    button = BUTTON(value,
                    _popovertarget=f"rdv-date-popover-{article.id}",
                    _class="your-rdv btn btn-default",
                    _style=style)

    return DIV(button,
                CENTER(H3("Change RDV date", _style="margin-bottom: 20px;"),
                    input,
                    _popover="",
                    _id=f"rdv-date-popover-{article.id}",
                    _style="border: none; border-radius: 4px; padding: 10px 20px 20px 20px; box-shadow: rgba(0, 0, 0, 0.25) 0px 54px 55px, rgba(0, 0, 0, 0.12) 0px -12px 30px, rgba(0, 0, 0, 0.12) 0px 4px 6px, rgba(0, 0, 0, 0.17) 0px 12px 13px, rgba(0, 0, 0, 0.09) 0px -3px 5px;"),
            _style="width: 50px;",
            _id=f"container-rdv-date-{article.id}")


######################################################################################################################################################################
# Builds a nice representation of an article WITHOUT recommendations link
def mkArticleCellNoRecomm(art0):
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
            DIV(mkAnonymousArticleField(art.anonymous_submission, art.authors, art.id)),
            doi_text,
            BR(),
            SPAN(" " + current.T("ArticleID") + " #" + str(art.id)),
            BR(),
            SPAN(" " + current.T("version") + " " + art.ms_version) if art.ms_version else "",
            (BR() + SPAN(art.article_source) if art.article_source else ""),
        )
    return anchor


######################################################################################################################################################################
def mkArticleCellNoRecommFromId(recommId: int):
    db = current.db
    anchor = ""
    recomm = db.t_recommendations[recommId]
    if recomm:
        art = db.t_articles[recomm.article_id]
        if art:
            recommenders = [mkUser(recomm.recommender_id)]
            contribsQy = Recommendation.get_co_recommenders(recommId)
            n = len(contribsQy)
            i = 0
            for contrib in contribsQy:
                i += 1
                if i < n:
                    recommenders += ", "
                else:
                    recommenders += " and "
                recommenders.append(mkUser(contrib.contributor_id))
            recommenders = SPAN(recommenders)

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
                SPAN(mkAnonymousArticleField(art.anonymous_submission, art.authors, art.id)),
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
def mkRecommCitation(myRecomm):
    applongname = myconf.take("app.longname")

    citeNum = ""
    doi = ""
    if myRecomm is None or not hasattr(myRecomm, "recommendation_doi"):
        return SPAN("?")
    whoDidItCite = getRecommAndReviewAuthors(recomm=myRecomm, with_reviewers=False, linked=False)
    if myRecomm.recommendation_doi:
        citeNumSearch = re.search("([0-9]+$)", myRecomm.recommendation_doi, re.IGNORECASE)
        if citeNumSearch:
            citeNum = ", " + citeNumSearch.group(1)
        doi = SPAN("DOI: ", mkDOI(myRecomm.recommendation_doi))
    citeRecomm = SPAN(SPAN(whoDidItCite), " ", myRecomm.last_change.strftime("(%Y)"), " ", (md_to_html(myRecomm.recommendation_title) or ""), ". ", I(applongname) + citeNum, SPAN(" "), doi)
    return citeRecomm or ""


######################################################################################################################################################################
def mkArticleCitation(myRecomm):
    db = current.db
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
def mkCoRecommenders(row: Recommendation, goBack: str = URL()):
    db = current.db
    butts: List[Union[UL, A]] = []
    hrevs: List[LI] = []
    art = db.t_articles[row.article_id]
    revs = Recommendation.get_co_recommenders(row.id)
    for rev in revs:
        if rev.contributor_id:
            hrevs.append(LI(mkUserWithMail(rev.contributor_id)))
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
def mkReviewersString(articleId):
    db = current.db
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
                reviewers += mkUser(rw.reviewer_id).flatten()
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
def getRecommAndReviewAuthors(
                              article: Union[Article, Dict[Any, Any]] = dict(),
                              recomm: Union[Recommendation, Dict[Any, Any]] = dict(),
                              with_reviewers: bool = False,
                              as_list: bool = False,
                              linked: bool = False,
                              this_recomm_only: bool = False,
                              citation: bool = False,
                              orcid: bool = False,
                              orcid_exponant: bool = False
                             ) -> List[Any]:
    db = current.db
    recomm = cast(Recommendation, recomm)

    whoDidIt: List[Union[str, DIV]] = []

    if hasattr(recomm, "article_id"):
        article = db(db.t_articles.id == recomm.article_id).select(db.t_articles.id, db.t_articles.already_published).last()

    article = cast(Article, article)

    if hasattr(article, "id"):
        select_recomm = ((db.t_recommendations.id == recomm.id)
                            if this_recomm_only else
                        (db.t_recommendations.article_id == article.id))

        mainRecommenders: List[Recommendation] = db(select_recomm).select(
            db.t_recommendations.ALL, distinct=db.t_recommendations.recommender_id)

        coRecommenders = Recommendation.get_co_recommenders([reco.id for reco in mainRecommenders])

        allRecommenders = mkRecommenderandContributorList(mainRecommenders) + mkRecommenderandContributorList(coRecommenders)

        if article.already_published:  # NOTE: POST-PRINT
            nr = len(allRecommenders)
            ir = 0
            for theUser in allRecommenders:
                ir += 1
                if as_list:
                    whoDidIt.append(mkUser_U(theUser['id']).flatten()) # type: ignore
                elif citation:
                    if theUser['id']:
                        theUser = db.auth_user[theUser['id']]
                        whoDidIt.append(mkUser_U(theUser, linked=linked, reverse=True, orcid=orcid, orcid_exponant=orcid_exponant))
                    if ir == nr - 1 and ir >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif ir < nr:
                        whoDidIt.append(", ")
                else:
                    if theUser['id']:
                        theUser = db.auth_user[theUser['id']]
                        whoDidIt.append(mkUser_U(theUser, linked=linked, orcid=orcid, orcid_exponant=orcid_exponant))
                    if ir == nr - 1 and ir >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif ir < nr:
                        whoDidIt.append(", ")

        else:  # NOTE: PRE-PRINT
            na1 = 0

            if with_reviewers:
                namedReviewers: List[Review] = db(
                    (db.t_recommendations.article_id == article.id)
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    & (db.t_reviews.anonymously == False)
                    & (db.t_reviews.review_state == "Review completed")
                ).select(db.t_reviews.ALL, distinct=db.t_reviews.reviewer_id)
                na: List[int] = db(
                    (db.t_recommendations.article_id == article.id)
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    & (db.t_reviews.anonymously == True)
                    & (db.t_reviews.review_state == "Review completed")
                ).select(db.t_reviews.reviewer_id, distinct=True)
                len_na = len(na)
                if len_na > 0:
                    na1 = 1
            else:
                namedReviewers = []
                len_na = 0
            nr = len(allRecommenders)
            nw = len(namedReviewers)
            ir = 0

            for theUser in allRecommenders:
                ir += 1
                if as_list:
                    whoDidIt.append(mkUser_U(theUser['id']).flatten()) # type: ignore
                elif citation:
                    if theUser['id']:
                        theUser = db.auth_user[theUser['id']]
                        whoDidIt.append(mkUser_U(theUser, linked=linked, reverse=True, orcid=orcid, orcid_exponant=orcid_exponant))
                    if ir == nr - 1 and ir >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif ir < nr:
                        whoDidIt.append(", ")
                else:
                    if theUser['id']:
                        theUser = db.auth_user[theUser['id']]
                        whoDidIt.append(mkUser_U(theUser, linked=linked, orcid=orcid, orcid_exponant=orcid_exponant))
                    if ir == nr - 1 and ir >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif ir < nr:
                        whoDidIt.append(", ")
            if nr > 0:
              if not as_list:
                if nw + len_na > 0:
                    whoDidIt.append(current.T(" based on reviews by "))
                elif nw + len_na == 1:
                    whoDidIt.append(current.T(" based on review by "))
            iw = 0
            for theUser in namedReviewers:
                iw += 1
                if as_list:
                    whoDidIt.append(mkUser_U(theUser['reviewer_id']).flatten()) # type: ignore
                else:
                    if theUser.reviewer_id:
                        theUser = db.auth_user[theUser.reviewer_id]
                        whoDidIt.append(mkUser_U(theUser, linked=False))
                    else:
                        whoDidIt.append(mkUser_U(theUser['reviewer_id']).flatten()) # type: ignore
                    if iw == nw + na1 - 1 and iw >= 1:
                        whoDidIt.append(current.T(" and "))
                    elif iw < nw + na1:
                        whoDidIt.append(", ")

            if not as_list:
                if len_na > 1:
                    whoDidIt.append(current.T("%d anonymous reviewers") % (len_na))
                elif len_na == 1:
                    whoDidIt.append(current.T("%d anonymous reviewer") % (len_na))

    return whoDidIt

#########################

def build_citation(article: Article, final_recommendation: Recommendation, for_latex: bool = False):
    recommendation_authors = getRecommAndReviewAuthors(
                        article=article,
                        with_reviewers=False, linked=False,
                        recomm=final_recommendation, this_recomm_only=True,
                        citation=True)

    if final_recommendation.recommendation_doi:
        recommendation_doi = doi_to_url(final_recommendation.recommendation_doi)

        if for_latex:
            cite_ref = mkSimpleDOI(recommendation_doi)
        else:
            cite_ref = mkDOI(recommendation_doi)
    else:
        cite_ref = False

    if cite_ref:
        cite_url = cite_ref
    else:
        cite_url = URL(c="articles", f="rec", vars=dict(id=article.id), scheme=True)
        cite_ref = A(cite_url, _href=cite_url)

    if for_latex:
        cite = DIV(
            SPAN(recommendation_authors),
                " ",
                final_recommendation.last_change.strftime("(%Y)"),
                " ",
                md_to_html(final_recommendation.recommendation_title),
                ". ",
                I(myconf.take("app.description")) + ", " + (Recommendation.get_doi_id(final_recommendation) or "") + ". ",
                cite_ref
        )
    else:
        cite = DIV(
            SPAN(
                B("Cite this recommendation as:", _class="pci2-main-color-text"),
                BR(),
                SPAN(recommendation_authors),
                " ",
                final_recommendation.last_change.strftime("(%Y)"),
                " ",
                md_to_html(final_recommendation.recommendation_title),
                ". ",
                I(myconf.take("app.description") + ", " + (Recommendation.get_doi_id(final_recommendation) or "") + ". "),
                cite_ref,
            ),
            _class="pci-citation",
        )

    return cite


######################################################################################################################################################################
def getArticleSubmitter(art: Article):
    db, auth = current.db, current.auth

    class FakeSubmitter(object):
        id = -1
        first_name = ""
        last_name = "[undisclosed]"
        deleted = False

    hideSubmitter = True

    qyIsRecommender = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommender_id == auth.user_id)).count()

    qyIsCoRecommender = db(
        (db.t_recommendations.article_id == art.id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id) & (db.t_press_reviews.contributor_id == auth.user_id)
    ).count()

    submitter = None
    if (art.anonymous_submission is False) or (qyIsRecommender > 0) or (qyIsCoRecommender > 0) or (auth.has_membership(role="manager")):
        submitter = User.get_by_id(art.user_id)
        if submitter is None:
            submitter = FakeSubmitter()
        hideSubmitter = False

    if art.already_published is False:
        result = DIV(
            I(current.T("Submitted by ")),
            I(mkAnonymousArticleField(hideSubmitter,B(mkUser_U(submitter, linked=True)), art.id)),
            I(art.upload_timestamp.strftime(" " + DEFAULT_DATE_FORMAT + " %H:%M") if art.upload_timestamp else ""),
        )
    else:
        result = ""

    return result

###########################################################################################################################
def group_reviewers(reviews: List[Review]):
    result = []
    for review in reviews:
        name = Review.get_reviewer_name(review)
        group = "accepted reviewer"
        if review.review_state == "Awaiting response":
            group = "invited reviewer"

        result.append({"group": group, "name" : name})
    return result

######################################################################################################################################################################
def mkRecommendersString(recomm: Recommendation):
    recommenders: List[Any] = [mkUser(recomm.recommender_id).flatten()] # type: ignore
    contribsQy = Recommendation.get_co_recommenders(recomm.id)
    n = len(contribsQy)
    i = 0
    for contrib in contribsQy:
        i += 1
        if i < n:
            recommenders += ", "
        else:
            recommenders += " and "
        recommenders += cast(Any, mkUser(contrib.contributor_id).flatten()) # type: ignore
    recommendersStr = "".join(recommenders)
    return recommendersStr

######################################################################################################################################################################
def mk_reviewer_info(user: User, orcid: bool = False):
    anchor = ""
    if user:
        if "auth_user" in user:
            user = user.auth_user
        else:
            user = user
        last_name = user.last_name or ""
        first_name = user.first_name or ""
        reviewer_name = first_name  + " " + last_name
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
def mkRecommenderandContributorList(records: List[Union[Recommendation, PressReview]]):
    result: List[Dict[str, Any]] = []
    for record in records:
        if hasattr(record, 'recommender_id'):
            result_dict: Dict[str, Any] = {'id': record.recommender_id, 'details': mkUserWithMail(record.recommender_id).flatten()} # type: ignore
        elif hasattr(record, 'contributor_id'):
             result_dict: Dict[str, Any] = {'id': record.contributor_id, 'details': mkUserWithMail(record.contributor_id).flatten()} # type: ignore
        else:
            raise Exception('DB record is not a Recommendation or PressReview.')
        result.append(result_dict)
    return result
######################################################################################################################################
def fetch_url(data: List[str]):
    result: List[DIV] = []
    for doi in data:
        doi = doi.strip()

        if doi.strip() == "https://":
            continue

        url = mkDOI(doi)
        result.append(url)
    return result

################################################################################
def md_to_html(text: Optional[str]):
    return SPAN(
            TAG(str(WIKI(text or "")))[0].components
    ) # WIKI returns XML('<p>htmlized text</p>'), replace P with SPAN

################################################################################
def mkSearchWidget(chars: List[str]):
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

def confirmationDialog(text: str, url: str = ''):
    return DIV(
    DIV(TAG(current.T(text)), _class="modal-body"),
    DIV(SPAN(current.T("confirm"), _type="button", **{'_data-dismiss': 'modal'}, _class="btn btn-info", _id="confirm-dialog", _redirect=url),
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

def complete_orcid_dialog():
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

def invitation_to_review_form(article_id: int, user: User, review: Review, more_delay: bool):
    disclaimerText = DIV(getText("#ConflictsForReviewers"))
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
            Field("review_duration", type="text", label=current.T("Choose the duration before posting my review"), default=dueTime.capitalize(), requires=IS_IN_SET(current.db.review_duration_choices, zero=None)),
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

####################################################################################

def unsubscribe_checkbox():
    html = DIV(
            DIV(
                LABEL(
                    INPUT(_type="checkbox", _name="unsubscribe_checkbox", _id="unsubscribe_checkbox"),
                    "Please check this box if you want to delete your account.",
                    _style="font-weight: normal"
                ), _class="col-sm-offset-3 col-sm-9", **{'_data-toggle': 'collapse', '_data-target': '#unsubscribe-text', '_aria-expanded': 'false', '_aria-controls': 'unsubscribe-text'}
            ),
            DIV(
                DIV(
                    B("WARNING"),
                    ": All of your personal information will be removed from the site except in the following situations: If you are the author of any public reviews, public editorial decisions, public recommendations, or if you are the submitter of a recommended article, your name will still be present in the PCI database and will be publicly visible on the recommendation page of the corresponding article. If you are the author of any public anonymous reviews, hidden reviews, hidden editorial decisions, or if you are the submitter of an article that has not been recommended, your name will still be present in the PCI database, but will not be publicly viewable.",
                    _class="well"),
            _class="collapse col-sm-offset-3 col-sm-9", _id="unsubscribe-text"),

          _class="form-group")

    html.append(common_tools.get_script('unsubscribe.js')) # type: ignore
    html.append(confirmationDialog('You are about to permanently delete your account, are you sure?', URL('default', 'unsubscribe', user_signature=True))) # type: ignore
    return html

####################################################################################

def suggested_recommender_list(article_id: int):
    suggested_recommenders = SuggestedRecommender.get_by_article(article_id)
    if not suggested_recommenders or len(suggested_recommenders) == 0:
        return

    suggested_recommenders_html = DIV(_style="margin-top: 20px")
    suggested_recommenders_html.append(H2(I(_class="glyphicon glyphicon-user", _style="margin-right: 10px;"), 'Suggested recommenders',
                                          _class="pci2-recomm-article-h2 pci2-flex-grow pci2-flex-row pci2-align-items-center"))

    recommender_list = UL()
    for suggested_recommender in suggested_recommenders:
        name_with_mail = mkUserWithMail(suggested_recommender.suggested_recommender_id)
        recommender_list.append(LI(name_with_mail))
    suggested_recommenders_html.append(recommender_list)

    return suggested_recommenders_html

####################################################################################

def get_current_step_article(article: Article) -> Optional[Tuple[StepNumber, SPAN]]:
    timeline = ongoing_recommendation.getRecommendationProcessForSubmitter(article, False, "%d\xa0%b")['content']
    if not isinstance(timeline, DIV):
        return

    parser = bs4.BeautifulSoup(str(timeline.components[-1].text), 'html.parser') # type: ignore
    step_done_els: ... = parser.find_all(class_="step-done") # type: ignore
    if len(step_done_els) == 0:
        return

    step_done_container = step_done_els[-1]

    step_number: StepNumber = StepNumber(0)
    if step_done_container.has_attr('data-step'):
        step_number = StepNumber(int(step_done_container.attrs['data-step']))

    step_done_content = cast(List[Any], step_done_els[-1].find(class_="step-description").contents)
    img = f"{_get_current_step_img(step_done_els)}"

    title = ""
    els = ""
    for el in step_done_content:
        if el is None:
            continue

        if isinstance(el, str):
            els += el
        else:
            if el.name == 'h3':
                title += f"{el}"
            else:
                els += f"{el}"

    classes = _get_step_classes(step_done_container, els)

    return step_number, SPAN(
        SPAN(step_number, _class="step-number"),
        DIV(
            DIV(XML(img), XML(title), _class="pci-status-title-mini"),
            XML(els),
            _class=classes
        )
    )


def _is_final_step_done(step_done_container: ...):
    final_step_done = False

    if step_done_container.has_attr('class'):
        step_done_container_class = step_done_container.attrs['class']
        if 'step-done' in step_done_container_class \
            and 'progress-last-step-div' in step_done_container_class \
                and 'current-step' not in step_done_container_class:
            final_step_done = True

    return final_step_done


def _get_step_classes(step_done_container: ..., els: str):
    classes = "pci-status-mini"

    if _is_final_step_done(step_done_container):
        classes += " final-step-done-mini"

    step_text = els.lower()
    if 'awaiting revision' in step_text:
        classes += " warning-step"

    if 'needed' in step_text or 'submission pending validation' in step_text:
        classes += " danger-step"

    return classes



def _get_current_step_img(step_done_els: ...) -> Union[DIV, None]:
    step_done_img = cast(List[Union[str, bs4.element.Tag, None]],
                                                 step_done_els[-1].find(class_="progress-step-circle").contents)
    img: Optional[bs4.element.Tag] = None
    for el in step_done_img:
        if isinstance(el, bs4.element.Tag):
            img = el

    if not img:
        return None
    else:
        return DIV(XML(f"{img}"), _class="mini-progress-step-circle pci2-flex-center")
