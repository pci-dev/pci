# -*- coding: utf-8 -*-

import gc
import os
import pytz, datetime
from re import sub, match
from copy import deepcopy
from datetime import datetime, timedelta
from dateutil.relativedelta import *
from collections import OrderedDict

from furl import furl
import time

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

from app_modules import common_small_html
from app_components import common_components
from app_modules import common_tools

myconf = AppConfig(reload=True)


######################################################################################################################################################################
def mkReviewsSubTable(auth, db, recomm):
    art = db.t_articles[recomm.article_id]
    recomm_round = db((db.t_recommendations.article_id == recomm.article_id) & (db.t_recommendations.id <= recomm.id)).count()
    reviews = db(db.t_reviews.recommendation_id == recomm.id).select(
        db.t_reviews.reviewer_id, db.t_reviews.review_state, db.t_reviews.acceptation_timestamp, db.t_reviews.last_change, db.t_reviews._id, orderby=~db.t_reviews.last_change
    )
    nbUnfinishedReviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state.belongs("Pending", "Under consideration"))).count()
    isRecommenderAlsoReviewer = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.reviewer_id == recomm.recommender_id)).count()
    allowed_to_see_reviews = True
    if (nbUnfinishedReviews > 0) and (isRecommenderAlsoReviewer == 1):
        allowed_to_see_reviews = False
    if len(reviews) > 0:
        resu = TABLE(TR(TH("Reviewer"), TH("Status"), TH("Last change"), TH(""), TH("Actions")), _class="table")
    else:
        resu = TABLE()
    nbCompleted = 0
    nbOnGoing = 0
    for myRev in reviews:
        myRow = TR(
            TD(common_small_html.mkUserWithMail(auth, db, myRev.reviewer_id)),
            TD(common_small_html.mkReviewStateDiv(auth, db, myRev.review_state)),
            TD(common_small_html.mkElapsedDays(myRev.last_change)),
        )
        myRow.append(
            TD(
                A(
                    current.T("See emails"),
                    _class="btn btn-default pci-smallBtn pci-recommender",
                    _target="blank",
                    _href=URL(c="recommender", f="review_emails", vars=dict(reviewId=myRev.id)),
                )
            )
        )
        lastCol = TD()
        if allowed_to_see_reviews and myRev.review_state == "Completed":
            lastCol.append(SPAN(A(current.T("See review"), _class="btn btn-default", _target="blank", _href=URL(c="recommender", f="one_review", vars=dict(reviewId=myRev.id)))))
        if art.status == "Under consideration" and not (recomm.is_closed):
            if (myRev.reviewer_id == auth.user_id) and (myRev.review_state == "Under consideration"):
                lastCol.append(
                    SPAN(
                        A(current.T("Write, edit or upload your review"), _class="btn btn-default pci-reviewer", _href=URL(c="user", f="edit_review", vars=dict(reviewId=myRev.id)))
                    )
                )
            if (myRev.reviewer_id != auth.user_id) and ((myRev.review_state or "Pending") in ("Pending", "Under consideration")):
                if myRev.review_state == "Under consideration":
                    btn_txt = current.T("Send an overdue message")
                else:
                    btn_txt = current.T("Send a reminder")
                lastCol.append(SPAN(A(btn_txt, _class="btn btn-info pci-recommender", _href=URL(c="recommender", f="send_review_reminder", vars=dict(reviewId=myRev.id)))))
            if (myRev.reviewer_id != auth.user_id) and ((myRev.review_state or "Pending") == "Pending"):
                lastCol.append(
                    SPAN(
                        A(
                            current.T("Send a cancellation notification"),
                            _class="btn btn-warning pci-recommender",
                            _href=URL(c="recommender", f="send_review_cancellation", vars=dict(reviewId=myRev.id)),
                        )
                    )
                )
        myRow.append(lastCol)
        resu.append(myRow)
        if myRev.review_state == "Completed":
            nbCompleted += 1
        if myRev.review_state == "Under consideration":
            nbOnGoing += 1
    myVars = dict(recommId=recomm["id"])
    if (
        not (recomm.is_closed)
        and ((recomm.recommender_id == auth.user_id) or auth.has_membership(role="manager") or auth.has_membership(role="administrator"))
        and (art.status == "Under consideration")
    ):
        buts = TR()
        buts.append(TD(A(SPAN(current.T("Invite a reviewer"), _class="btn btn-default pci-recommender"), _href=URL(c="recommender", f="reviewers", vars=myVars))))
        buts.append(TD())
        buts.append(TD())
        buts.append(TD())
        if (nbCompleted >= 2 and nbOnGoing == 0) or recomm_round > 1:
            buts.append(
                TD(
                    A(
                        SPAN(current.T("Write or edit your decision / recommendation"), _class="btn btn-success pci-recommender"),
                        _href=URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id)),
                    )
                )
            )
        else:
            buts.append(
                TD(
                    A(
                        SPAN(
                            current.T("Write your decision / recommendation"),  # once two or more reviews are completed'),
                            _title=current.T("Write your decision or recommendation once all reviews are completed. At least two reviews are required."),
                            _style="white-space:normal;",
                            _class="btn btn-default pci-recommender disabled",
                        ),
                        _style="width:300px;",
                    )
                )
            )
        resu.append(buts)
    return DIV(H3("Round #%s" % recomm_round), resu, _class="pci-reviewers-table-div")


######################################################################################################################################################################
# Show reviews of cancelled articles for CNeuro
def reviewsOfCancelled(auth, db, art):
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    applongname = myconf.take("app.longname")
    track = None
    printable = False
    with_reviews = True
    nbReviews = db(
        (db.t_recommendations.article_id == art.id)
        & (db.t_reviews.recommendation_id == db.t_recommendations.id)
        & (db.t_reviews.review_state.belongs("Under consideration", "Completed"))
    ).count(distinct=db.t_reviews.id)
    if art.status == "Cancelled" and nbReviews > 0:

        myArticle = DIV(
            DIV(H1(current.T("Submitted article:"))),
            SPAN((art.authors or "") + ". ", _class="pci-recomOfAuthors"),
            SPAN((art.title or "") + " ", _class="pci-recomOfTitle"),
            (SPAN((art.article_source + ". "), _class="pci-recomOfSource") if art.article_source else " "),
            (common_small_html.mkDOI(art.doi)) if (art.doi) else SPAN(""),
            SPAN(" " + current.T("version") + " " + art.ms_version) if art.ms_version else "",
            _class="pci-recommOfArticle",
        )
        myContents = DIV(myArticle, _class=("pci-article-div-printable" if printable else "pci-article-div"))
        recomms = db((db.t_recommendations.article_id == art.id)).select(orderby=~db.t_recommendations.id)
        recommRound = len(recomms)
        headerDone = False

        for recomm in recomms:

            whoDidIt = common_small_html.getRecommAndReviewAuthors(auth, db, recomm=recomm, with_reviewers=True, linked=not (printable), host=host, port=port, scheme=scheme)

            myReviews = ""
            myReviews = []
            headerDone = False
            # Check for reviews
            reviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Completed")).select(orderby=db.t_reviews.id)
            for review in reviews:
                if with_reviews:
                    # display the review
                    if review.anonymously:
                        myReviews.append(
                            H4(
                                current.T("Reviewed by")
                                + " "
                                + current.T("anonymous reviewer")
                                + (", " + review.last_change.strftime("%Y-%m-%d %H:%M") if review.last_change else "")
                            )
                        )
                    else:
                        myReviews.append(
                            H4(
                                current.T("Reviewed by"),
                                " ",
                                common_small_html.mkUser(auth, db, review.reviewer_id, linked=not (printable)),
                                (", " + review.last_change.strftime("%Y-%m-%d %H:%M") if review.last_change else ""),
                            )
                        )
                    myReviews.append(BR())
                    if len(review.review or "") > 2:
                        myReviews.append(DIV(WIKI(review.review), _class="pci-bigtext margin"))
                        if review.review_pdf:
                            myReviews.append(
                                DIV(
                                    A(current.T("Download the review (PDF file)"), _href=URL("default", "download", args=review.review_pdf), _style="margin-bottom: 64px;"),
                                    _class="pci-bigtext margin",
                                )
                            )
                    elif review.review_pdf:
                        myReviews.append(
                            DIV(
                                A(current.T("Download the review (PDF file)"), _href=URL("default", "download", args=review.review_pdf), _style="margin-bottom: 64px;"),
                                _class="pci-bigtext margin",
                            )
                        )
                    else:
                        pass

            if recomm.reply:
                if recomm.reply_pdf:
                    reply = DIV(
                        H4(B(current.T("Author's reply:"))),
                        DIV(WIKI(recomm.reply), _class="pci-bigtext"),
                        DIV(
                            A(current.T("Download author's reply (PDF file)"), _href=URL("default", "download", args=recomm.reply_pdf), _style="margin-bottom: 64px;"),
                            _class="pci-bigtext margin",
                        ),
                        _style="margin-top:32px;",
                    )
                else:
                    reply = DIV(H4(B(current.T("Author's reply:"))), DIV(WIKI(recomm.reply), _class="pci-bigtext"), _style="margin-top:32px;",)
            elif recomm.reply_pdf:
                reply = DIV(
                    H4(B(current.T("Author's reply:"))),
                    DIV(
                        A(current.T("Download author's reply (PDF file)"), _href=URL("default", "download", args=recomm.reply_pdf), _style="margin-bottom: 64px;"),
                        _class="pci-bigtext margin",
                    ),
                    _style="margin-top:32px;",
                )
            else:
                reply = ""
            myContents.append(
                DIV(
                    HR(),
                    H3("Revision round #%s" % recommRound),
                    SPAN(I(recomm.last_change.strftime("%Y-%m-%d") + " ")) if recomm.last_change else "",
                    H2(recomm.recommendation_title if ((recomm.recommendation_title or "") != "") else T("Decision")),
                    H4(current.T(" by "), SPAN(whoDidIt))  # mkUserWithAffil(auth, db, recomm.recommender_id, linked=not(printable)))
                    # ,SPAN(SPAN(current.T('Recommendation:')+' '), common_small_html.mkDOI(recomm.recommendation_doi), BR()) if ((recomm.recommendation_doi or '')!='') else ''
                    # ,DIV(SPAN('A recommendation of:', _class='pci-recommOf'), myArticle, _class='pci-recommOfDiv')
                    ,
                    DIV(WIKI(recomm.recommendation_comments or ""), _class="pci-bigtext"),
                    DIV(I(current.T("Preprint DOI:") + " "), common_small_html.mkDOI(recomm.doi), BR()) if ((recomm.doi or "") != "") else "",
                    DIV(myReviews, _class="pci-reviews") if len(myReviews) > 0 else "",
                    reply,
                    _class="pci-recommendation-div"
                    # , _style='margin-left:%spx' % (leftShift)
                )
            )
            recommRound -= 1

    return myContents
