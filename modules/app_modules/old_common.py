# -*- coding: utf-8 -*-

import gc
import os
import pytz
from re import sub, match
from copy import deepcopy
import datetime
from datetime import timedelta
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
from app_modules import common_tools


myconf = AppConfig(reload=True)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

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
        & (db.t_reviews.review_state.belongs("Awaiting review", "Review completed"))
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
            reviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state == "Review completed")).select(orderby=db.t_reviews.id)
            for review in reviews:
                if with_reviews:
                    # display the review
                    if review.anonymously:
                        myReviews.append(
                            H4(
                                current.T("Reviewed by")
                                + " "
                                + current.T("anonymous reviewer")
                                + (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review.last_change else "")
                            )
                        )
                    else:
                        myReviews.append(
                            H4(
                                current.T("Reviewed by"),
                                " ",
                                common_small_html.mkUser(auth, db, review.reviewer_id, linked=not (printable)),
                                (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review.last_change else ""),
                            )
                        )
                    myReviews.append(BR())
                    if len(review.review or "") > 2:
                        myReviews.append(DIV(WIKI(review.review, safe_mode=False), _class="pci-bigtext margin"))
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
                        DIV(WIKI(recomm.reply, safe_mode=False), _class="pci-bigtext"),
                        DIV(
                            A(current.T("Download author's reply (PDF file)"), _href=URL("default", "download", args=recomm.reply_pdf), _style="margin-bottom: 64px;"),
                            _class="pci-bigtext margin",
                        ),
                        _style="margin-top:32px;",
                    )
                else:
                    reply = DIV(H4(B(current.T("Author's reply:"))), DIV(WIKI(recomm.reply, safe_mode=False), _class="pci-bigtext"), _style="margin-top:32px;",)
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
                    SPAN(I(recomm.last_change.strftime(DEFAULT_DATE_FORMAT) + " ")) if recomm.last_change else "",
                    H2(recomm.recommendation_title if ((recomm.recommendation_title or "") != "") else T("Decision")),
                    H4(current.T(" by "), SPAN(whoDidIt))  # mkUserWithAffil(auth, db, recomm.recommender_id, linked=not(printable)))
                    # ,SPAN(SPAN(current.T('Recommendation:')+' '), common_small_html.mkDOI(recomm.recommendation_doi), BR()) if ((recomm.recommendation_doi or '')!='') else ''
                    # ,DIV(SPAN('A recommendation of:', _class='pci-recommOf'), myArticle, _class='pci-recommOfDiv')
                    ,
                    DIV(WIKI(recomm.recommendation_comments or "", safe_mode=False), _class="pci-bigtext"),
                    DIV(I(current.T("Preprint DOI:") + " "), common_small_html.mkDOI(recomm.doi), BR()) if ((recomm.doi or "") != "") else "",
                    DIV(myReviews, _class="pci-reviews") if len(myReviews) > 0 else "",
                    reply,
                    _class="pci-recommendation-div"
                    # , _style='margin-left:%spx' % (leftShift)
                )
            )
            recommRound -= 1

    return myContents


######################################################################################################################################################################
##WARNING The most sensitive function of the whole website!!
##WARNING Be *VERY* careful with rights management
def mkFeaturedArticle(auth, db, art, printable=False, with_comments=False, quiet=True, scheme=False, host=False, port=False, to_submitter=False):
    class FakeSubmitter(object):
        id = None
        first_name = ""
        last_name = "[undisclosed]"

    submitter = FakeSubmitter()
    hideSubmitter = True
    qyIsRecommender = db((db.t_recommendations.article_id == art.id) & (db.t_recommendations.recommender_id == auth.user_id)).count()
    qyIsCoRecommender = db(
        (db.t_recommendations.article_id == art.id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id) & (db.t_press_reviews.contributor_id == auth.user_id)
    ).count()
    if (art.anonymous_submission is False) or (qyIsRecommender > 0) or (qyIsCoRecommender > 0) or (auth.has_membership(role="manager")):
        submitter = db(db.auth_user.id == art.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
        if submitter is None:
            submitter = FakeSubmitter()
        hideSubmitter = False
    allowOpinion = None
    ###NOTE: article facts
    if art.uploaded_picture is not None and art.uploaded_picture != "":
        img = DIV(
            IMG(
                _alt="article picture", _src=URL("static", "uploads", args=art.uploaded_picture, scheme=scheme, host=host, port=port), _style="max-width:150px; max-height:150px;"
            )
        )
    else:
        img = ""
    myArticle = DIV(
        DIV(XML("<div class='altmetric-embed' data-badge-type='donut' data-doi='%s'></div>" % sub(r"doi: *", "", (art.doi or ""))), _style="text-align:right;")
        # NOTE: publishing tools not ready yet...
        # ,DIV(
        # A(current.T('Publishing tools'), _href=URL(c='admin', f='rec_as_latex', vars=dict(articleId=art.id)), _class='btn btn-info')
        # ,A(current.T('PDF Front page'), _href=URL(c='admin', f='fp_as_pdf', vars=dict(articleId=art.id)), _class='btn btn-info')
        # ,A(current.T('PDF Recommendation'), _href=URL(c='admin', f='rec_as_pdf', vars=dict(articleId=art.id)), _class='btn btn-info')
        # ,A(current.T('Complete PDF Recommendation'), _href=URL(c='admin', f='rec_as_pdf', vars=dict(articleId=art.id, withHistory=1)), _class='btn btn-info')
        # ,_style='text-align:right; margin-top:12px; margin-bottom:8px;'
        # ) if ((auth.has_membership(role='administrator') or auth.has_membership(role='developer'))) else ''
        ,
        img,
        H3(art.title or ""),
        H4(common_small_html.mkAnonymousArticleField(auth, db, hideSubmitter, (art.authors or ""), art.id)),
        common_small_html.mkDOI(art.doi) if (art.doi) else SPAN(""),
        SPAN(" " + current.T("version") + " " + art.ms_version) if art.ms_version else "",
        BR(),
        DIV(
            I(current.T("Submitted by ")),
            I(common_small_html.mkAnonymousArticleField(auth, db, hideSubmitter, (submitter.first_name or "") + " " + (submitter.last_name or ""), art.id)),
            I(art.upload_timestamp.strftime(" " + DEFAULT_DATE_FORMAT + " %H:%M") if art.upload_timestamp else ""),
        )
        if (art.already_published is False)
        else "",
        (B("Parallel submission") if art.parallel_submission else ""),
        (SPAN(art.article_source) + BR() if art.article_source else ""),
    )
    # Allow to display cover letter if role is manager or above
    if not (printable) and not (quiet):
        if len(art.cover_letter or "") > 2:
            myArticle.append(
                DIV(
                    A(
                        current.T("Show / Hide Cover letter"),
                        _onclick="""jQuery(function(){ if ($.cookie('PCiHideCoverLetter') == 'On') {
													$('DIV.pci-onoffCoverLetter').show(); 
													$.cookie('PCiHideCoverLetter', 'Off', {expires:365, path:'/'});
												} else {
													$('DIV.pci-onoffCoverLetter').hide(); 
													$.cookie('PCiHideCoverLetter', 'On', {expires:365, path:'/'});
												}
										})""",
                        _class="btn btn-default",
                    ),
                    _class="pci-EditButtons",
                )
            )
            myArticle.append(SCRIPT("$.cookie('PCiHideCoverLetter', 'On', {expires:365, path:'/'});"))
            myArticle.append(DIV(B(current.T("Cover letter")), BR(), WIKI((art.cover_letter or ""), safe_mode=False), _class="pci-bigtext pci-onoffCoverLetter"))
        else:
            myArticle.append(DIV(A(current.T("No Cover letter"), _class="btn btn-default disabled"), _class="pci-EditButtons"))
    if not (printable) and not (quiet):
        myArticle.append(
            DIV(
                A(
                    current.T("Show / Hide Abstract"),
                    _onclick="""jQuery(function(){ if ($.cookie('PCiHideAbstract') == 'On') {
												$('DIV.pci-onoffAbstract').show(); 
												$.cookie('PCiHideAbstract', 'Off', {expires:365, path:'/'});
											} else {
												$('DIV.pci-onoffAbstract').hide(); 
												$.cookie('PCiHideAbstract', 'On', {expires:365, path:'/'});
											}
									})""",
                    _class="btn btn-default pci-public",
                ),
                _class="pci-EditButtons",
            )
        )
        myArticle.append(SCRIPT("$.cookie('PCiHideAbstract', 'On', {expires:365, path:'/'});"))
        myArticle.append(
            DIV(
                B(current.T("Abstract")),
                BR(),
                WIKI((art.abstract or ""), safe_mode=False),
                SPAN(I(current.T("Keywords:") + " " + art.keywords) + BR() if art.keywords else ""),
                _class="pci-bigtext pci-onoffAbstract",
            )
        )
    else:
        myArticle.append(
            DIV(
                B(current.T("Abstract")),
                BR(),
                WIKI((art.abstract or ""), safe_mode=False),
                SPAN(I(current.T("Keywords:") + " " + art.keywords) + BR() if art.keywords else ""),
                _class="pci-bigtext",
            )
        )
    if ((art.user_id == auth.user_id) and (art.status in ("Pending", "Awaiting revision"))) and not (printable) and not (quiet):
        # author's button allowing article edition
        myArticle.append(
            DIV(
                A(
                    SPAN(current.T("Edit article"), _class="buttontext btn btn-info pci-submitter"),
                    _href=URL(c="user", f="edit_my_article", vars=dict(articleId=art.id), user_signature=True),
                ),
                _class="pci-EditButtons",
            )
        )
    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable) and not (quiet):
        # manager's button allowing article edition
        myArticle.append(
            DIV(
                A(
                    SPAN(current.T("Manage this request"), _class="buttontext btn btn-info pci-manager"),
                    _href=URL(c="manager", f="edit_article", vars=dict(articleId=art.id), user_signature=True),
                ),
                _class="pci-EditButtons",
            )
        )
    myContents = DIV(myArticle, _class=("pci-article-div-printable" if printable else "pci-article-div"))
    # myContents = DIV('', _class=('pci-article-div-printable' if printable else 'pci-article-div'))

    recomms = db(db.t_recommendations.article_id == art.id).select(orderby=~db.t_recommendations.id)
    nbRecomms = len(recomms)
    myButtons = DIV()
    if nbRecomms > 0 and auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable) and not (quiet):
        # manager's button allowing recommendations management
        myButtons.append(
            DIV(
                A(
                    SPAN(current.T("Manage recommendations"), _class="buttontext btn btn-info pci-manager"),
                    _href=URL(c="manager", f="manage_recommendations", vars=dict(articleId=art.id), user_signature=True),
                ),
                _class="pci-EditButtons",
            )
        )

    if (
        nbRecomms == 0
        and auth.has_membership(role="recommender")
        and not (art.user_id == auth.user_id)
        and art.status == "Awaiting consideration"
        and not (printable)
        and not (quiet)
    ):
        # suggested or any recommender's button for recommendation consideration
        btsAccDec = [
            A(
                SPAN(current.T("Yes, I would like to handle the evaluation process"), _class="buttontext btn btn-success pci-recommender"),
                _href=URL(c="recommender", f="accept_new_article_to_recommend", vars=dict(articleId=art.id), user_signature=True),
                _class="button",
            ),
        ]
        amISugg = db((db.t_suggested_recommenders.article_id == art.id) & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)).count()
        if amISugg > 0:
            # suggested recommender's button for declining recommendation
            btsAccDec.append(
                A(
                    SPAN(current.T("No, I would rather not"), _class="buttontext btn btn-warning pci-recommender"),
                    _href=URL(c="recommender_actions", f="decline_new_article_to_recommend", vars=dict(articleId=art.id), user_signature=True),
                    _class="button",
                ),
            )
        myButtons.append(DIV(btsAccDec, _class="pci-opinionform"))

    if (
        (art.user_id == auth.user_id)
        and not (art.already_published)
        and (art.status not in ("Cancelled", "Rejected", "Pre-recommended", "Recommended"))
        and not (printable)
        and not (quiet)
    ):
        myButtons.append(
            DIV(
                A(
                    SPAN(current.T("I wish to cancel my submission"), _class="buttontext btn btn-warning pci-submitter"),
                    _href=URL(c="user_actions", f="do_cancel_article", vars=dict(articleId=art.id), user_signature=True),
                    _title=current.T("Click here in order to cancel this submission"),
                ),
                _class="pci-EditButtons",
            )
        )  # author's button allowing cancellation
    myContents.append(myButtons)

    ###NOTE: here start recommendations display
    iRecomm = 0
    roundNb = nbRecomms + 1
    reply_filled = False
    myRound = None
    for recomm in recomms:
        iRecomm += 1
        roundNb -= 1
        nbCompleted = 0
        nbOnGoing = 0
        myRound = DIV()
        recommender = db(db.auth_user.id == recomm.recommender_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
        whoDidIt = common_small_html.getRecommAndReviewAuthors(auth, db, recomm=recomm, with_reviewers=False, linked=not (printable), host=host, port=port, scheme=scheme)

        ###NOTE: POST-PRINT ARTICLE
        if art.already_published:
            contributors = []
            contrQy = db((db.t_press_reviews.recommendation_id == recomm.id)).select(orderby=db.t_press_reviews.id)
            for contr in contrQy:
                contributors.append(contr.contributor_id)

            myRound.append(
                DIV(
                    HR(),
                    B(SPAN(recomm.recommendation_title)) + BR() if (recomm.recommendation_title or "") != "" else "",
                    B(current.T("Recommendation by "), SPAN(whoDidIt)) + BR(),
                    SPAN(current.T("Recommendation:") + " "),
                    common_small_html.mkDOI(recomm.recommendation_doi),
                    BR(),
                    SPAN(current.T("Manuscript:") + " ", common_small_html.mkDOI(recomm.doi) + BR()) if (recomm.doi != art.doi) else SPAN(""),
                    I(recomm.last_change.strftime(DEFAULT_DATE_FORMAT)) if recomm.last_change else "",
                    DIV(WIKI((recomm.recommendation_comments or ""), safe_mode=False), _class="pci-bigtext margin"),
                    _class="pci-recommendation-div",
                )
            )
            if (recomm.recommender_id == auth.user_id) and (art.status == "Under consideration") and not (recomm.is_closed) and not (printable) and not (quiet):
                # recommender's button allowing recommendation edition
                myRound.append(
                    DIV(
                        A(
                            SPAN(current.T("Write or edit your decision / recommendation"), _class="buttontext btn btn-default pci-recommender"),
                            _href=URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id), user_signature=True),
                        ),
                        _class="pci-EditButtons",
                    )
                )

                # recommender's button allowing recommendation submission, provided there are co-recommenders

                # (gab) minimal_number_of_corecommenders is not defiend ! => set it to 0
                # if len(contributors) >= minimal_number_of_corecommenders:
                if len(contributors) >= 0:
                    if len(recomm.recommendation_comments) > 50:
                        myRound.append(
                            DIV(
                                A(
                                    SPAN(current.T("Send your recommendation to the managing board for validation"), _class="buttontext btn btn-success pci-recommender"),
                                    _href=URL(c="recommender_actions", f="recommend_article", vars=dict(recommId=recomm.id), user_signature=True),
                                    # _title=current.T('Click here to close the recommendation process of this article and send it to the managing board')
                                ),
                                _class="pci-EditButtons-centered",
                            )
                        )
                    else:
                        myRound.append(
                            DIV(
                                SPAN(I(current.T("Recommendation text too short for allowing submission"), _class="buttontext btn btn-success pci-recommender disabled")),
                                _class="pci-EditButtons-centered",
                            )
                        )
                else:
                    # otherwise button for adding co-recommender(s)
                    myRound.append(
                        DIV(
                            A(
                                SPAN(
                                    current.T("You have to add at least one contributor in order to collectively validate this recommendation"),
                                    _class="buttontext btn btn-info pci-recommender",
                                ),
                                _href=URL(c="recommender", f="add_contributor", vars=dict(recommId=recomm.id), user_signature=True),
                                _title=current.T("Click here to add contributors of this article"),
                            ),
                            _class="pci-EditButtons-centered",
                        )
                    )

                # recommender's button allowing cancellation
                myContents.append(
                    DIV(
                        A(
                            SPAN(current.T("Cancel this postprint recommendation"), _class="buttontext btn btn-warning pci-recommender"),
                            _href=URL(c="recommender_actions", f="do_cancel_press_review", vars=dict(recommId=recomm.id), user_signature=True),
                            _title=current.T("Click here in order to cancel this recommendation"),
                        ),
                        _class="pci-EditButtons-centered",
                    )
                )

        else:  ###NOTE: PRE-PRINT ARTICLE
            # Am I a co-recommender?
            amICoRecommender = db((db.t_press_reviews.recommendation_id == recomm.id) & (db.t_press_reviews.contributor_id == auth.user_id)).count() > 0
            # Am I a reviewer?
            amIReviewer = (
                db((db.t_recommendations.article_id == art.id) & (db.t_reviews.recommendation_id == db.t_recommendations.id) & (db.t_reviews.reviewer_id == auth.user_id)).count()
                > 0
            )
            # During recommendation, no one is not allowed to see last (unclosed) recommendation
            hideOngoingRecomm = ((art.status == "Under consideration") or (art.status.startswith("Pre-"))) and not (recomm.is_closed)  # (iRecomm==1)
            #  ... unless he/she is THE recommender
            if auth.has_membership(role="recommender") and (recomm.recommender_id == auth.user_id or amICoRecommender):
                hideOngoingRecomm = False
            # or a manager, provided he/she is reviewer
            if auth.has_membership(role="manager") and (art.user_id != auth.user_id) and (amIReviewer is False):
                hideOngoingRecomm = False

            if ((recomm.reply is not None) and (len(recomm.reply) > 0)) or recomm.reply_pdf is not None:
                myRound.append(HR())
                myRound.append(DIV(B(current.T("Author's Reply:"))))
            if (recomm.reply is not None) and (len(recomm.reply) > 0):
                myRound.append(DIV(WIKI(recomm.reply or "", safe_mode=False), _class="pci-bigtext margin"))
            if recomm.reply_pdf:
                myRound.append(
                    A(
                        current.T("Download author's reply (PDF file)"),
                        _href=URL("default", "download", args=recomm.reply_pdf, scheme=scheme, host=host, port=port),
                        _style="margin-bottom: 64px;",
                    )
                )
                if recomm.track_change:
                    myRound.append(BR())  # newline if both links for visibility
            if recomm.track_change:
                myRound.append(
                    A(
                        current.T("Download tracked changes file"),
                        _href=URL("default", "download", args=recomm.track_change, scheme=scheme, host=host, port=port),
                        _style="margin-bottom: 64px;",
                    )
                )
            if recomm.reply_pdf or len(recomm.reply or "") > 5:
                reply_filled = True

            # Check for reviews
            existOngoingReview = False
            myReviews = DIV()
            reviews = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.review_state != "Declined manually") & (db.t_reviews.review_state != "Declined") & (db.t_reviews.review_state != "Cancelled")).select(
                orderby=db.t_reviews.id
            )
            for review in reviews:
                if review.review_state == "Awaiting review":
                    existOngoingReview = True
                if review.review_state == "Review completed":
                    nbCompleted += 1
                if review.review_state == "Awaiting review":
                    nbOnGoing += 1
            # If the recommender is also a reviewer, did he/she already completed his/her review?
            recommReviewFilledOrNull = False  # Let's say no by default
            # Get reviews states for this case
            recommenderOwnReviewStates = db((db.t_reviews.recommendation_id == recomm.id) & (db.t_reviews.reviewer_id == recomm.recommender_id)).select(db.t_reviews.review_state)
            if len(recommenderOwnReviewStates) == 0:
                # The recommender is not also a reviewer
                recommReviewFilledOrNull = True  # He/she is allowed to see other's reviews
            else:
                # The recommender is also a reviewer
                for recommenderOwnReviewState in recommenderOwnReviewStates:
                    if recommenderOwnReviewState.review_state == "Review completed":
                        recommReviewFilledOrNull = True  # Yes, his/her review is completed

            for review in reviews:
                # No one is allowd to see ongoing reviews ...
                hideOngoingReview = True
                # ... but:
                # ... the author for a closed decision/recommendation ...
                if (art.user_id == auth.user_id) and (recomm.is_closed or art.status == "Awaiting revision"):
                    hideOngoingReview = False
                # ...  the reviewer himself once accepted ...
                if (review.reviewer_id == auth.user_id) and (review.review_state in ("Awaiting review", "Review completed")):
                    hideOngoingReview = False
                # ...  a reviewer himself once the decision made up ...
                if (
                    (amIReviewer)
                    and (recomm.recommendation_state in ("Recommended", "Rejected", "Revision"))
                    and recomm.is_closed
                    and (art.status in ("Under consideration", "Recommended", "Rejected", "Awaiting revision"))
                ):
                    hideOngoingReview = False
                # ... or he/she is THE recommender and he/she already filled his/her own review ...
                if auth.has_membership(role="recommender") and (recomm.recommender_id == auth.user_id) and recommReviewFilledOrNull:
                    hideOngoingReview = False
                # ... or he/she is A CO-recommender and he/she already filled his/her own review ...
                if auth.has_membership(role="recommender") and amICoRecommender and recommReviewFilledOrNull:
                    hideOngoingReview = False
                # ... or a manager, unless submitter or reviewer
                if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not amIReviewer:
                    hideOngoingReview = False
                # ... but, if review was declined by recommender, hide it
                if review.review_state == "Declined by recommender":
                    hideOngoingReview = True

                # print("hideOngoingReview=%s") % (hideOngoingReview)

                if (
                    (review.reviewer_id == auth.user_id)
                    and (review.reviewer_id != recomm.recommender_id)
                    and (art.status == "Under consideration")
                    and not (printable)
                    and not (quiet)
                ):
                    if review.review_state == "Awaiting response":
                        # reviewer's buttons in order to accept/decline pending review
                        myReviews.append(
                            DIV(
                                A(
                                    SPAN(current.T("Yes, I would like to review this preprint"), _class="buttontext btn btn-main-action pci-reviewer"),
                                    _href=URL(c="default", f="invitation_to_review", vars=dict(reviewId=review.id)),
                                    _class="button",
                                ),
                                A(
                                    SPAN(current.T("No thanks, I would rather not"), _class="buttontext btn btn-default pci-reviewer"),
                                    _href=URL(c="user_actions", f="decline_new_review", vars=dict(reviewId=review.id), user_signature=True),
                                    _class="button",
                                ),
                                _class="pci-opinionform",
                            )
                        )
                elif review.review_state == "Awaiting response":
                    hideOngoingReview = True
                elif review.review_state == "Willing to review":
                    hideOngoingReview = True

                if (
                    (review.reviewer_id == auth.user_id)
                    and (review.review_state == "Awaiting review")
                    and (art.status == "Under consideration")
                    and not (printable)
                    and not (quiet)
                ):
                    # reviewer's buttons in order to edit/complete pending review
                    myReviews.append(
                        DIV(
                            A(
                                SPAN(current.T("Write, edit or upload your review"), _class=""),
                                _href=URL(c="user", f="edit_review", vars=dict(reviewId=review.id), user_signature=True),
                                _class="btn btn-main-action pci-reviewer",
                            )
                        )
                    )

                if not (hideOngoingReview):
                    # display the review
                    # myReviews.append(HR())
                    # buttons allowing to edit and validate the review
                    if review.anonymously:
                        myReviews.append(
                            SPAN(
                                I(
                                    current.T("Reviewed by")
                                    + " "
                                    + current.T("anonymous reviewer")
                                    + (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review.last_change else "")
                                )
                            )
                        )
                    else:
                        reviewer = db(db.auth_user.id == review.reviewer_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
                        if reviewer is not None:
                            myReviews.append(
                                SPAN(
                                    I(
                                        current.T("Reviewed by")
                                        + " "
                                        + (reviewer.first_name or "")
                                        + " "
                                        + (reviewer.last_name or "")
                                        + (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review.last_change else "")
                                    )
                                )
                            )
                        else:
                            reviewer = db(db.auth_user.id == review.reviewer_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).last()
                            if reviewer is not None:
                                myReviews.append(
                                    SPAN(
                                        I(
                                            current.T("Reviewed by")
                                            + " "
                                            + (reviewer.first_name or "")
                                            + " "
                                            + (reviewer.last_name or "")
                                            + (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review.last_change else "")
                                        )
                                    )
                                )
                        myReviews.append(BR())

                    if len(review.review or "") > 2:
                        myReviews.append(DIV(WIKI(review.review, safe_mode=False), _class="pci-bigtext margin"))
                        if review.review_pdf:
                            myReviews.append(
                                DIV(
                                    A(
                                        current.T("Download the review (PDF file)"),
                                        _href=URL("default", "download", args=review.review_pdf, scheme=scheme, host=host, port=port),
                                        _style="margin-bottom: 64px;",
                                    ),
                                    _class="pci-bigtext margin",
                                )
                            )
                    elif review.review_pdf:
                        myReviews.append(
                            DIV(
                                A(
                                    current.T("Download the review (PDF file)"),
                                    _href=URL("default", "download", args=review.review_pdf, scheme=scheme, host=host, port=port),
                                    _style="margin-bottom: 64px;",
                                ),
                                _class="pci-bigtext margin",
                            )
                        )

            myRound.append(HR())
            if recomm.recommendation_state == "Recommended":
                if recomm.recommender_id == auth.user_id:
                    tit2 = current.T("Your recommendation")
                else:
                    tit2 = current.T("Recommendation")
            else:
                if recomm.recommender_id == auth.user_id:
                    tit2 = current.T("Your decision")
                elif recomm.is_closed:
                    tit2 = current.T("Decision")
                else:
                    tit2 = ""

            if not (recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == "Under consideration") and not (printable) and not (quiet):
                # recommender's button for recommendation edition
                if (nbCompleted >= 2 and nbOnGoing == 0) or roundNb > 1 or (pciRRactivated):
                    myRound.append(
                        DIV(
                            A(
                                SPAN(current.T("Write or edit your decision / recommendation"), _class="btn btn-default pci-recommender"),
                                _href=URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recomm.id)),
                            )
                        )
                    )
                else:
                    myRound.append(
                        DIV(
                            A(
                                SPAN(
                                    current.T("Write your decision / recommendation"),
                                    _title=current.T("Write your decision or recommendation once all reviews are completed. At least two reviews are required."),
                                    _style="white-space:normal;",
                                    _class="btn btn-default pci-recommender disabled",
                                ),
                                _style="width:300px;",
                            )
                        )
                    )

                # final opinion allowed if comments filled and no ongoing review
                if (len(recomm.recommendation_comments or "") > 5) and not (existOngoingReview):  # and len(reviews)>=2 :
                    allowOpinion = recomm.id
                else:
                    allowOpinion = -1

            # if (art.user_id==auth.user_id or auth.has_membership(role='manager')) and (art.status=='Awaiting revision') and not(recomm.is_closed) and not(printable) and not (quiet):
            if (art.user_id == auth.user_id) and (art.status == "Awaiting revision") and not (printable) and not (quiet) and (iRecomm == 1):
                myRound.append(
                    DIV(
                        A(
                            SPAN(current.T("Write, edit or upload your reply to the recommender"), _class="buttontext btn btn-info pci-submitter"),
                            _href=URL(c="user", f="edit_reply", vars=dict(recommId=recomm.id), user_signature=True),
                        ),
                        _class="pci-EditButtons",
                    )
                )

            truc = DIV(
                H3(tit2),
                I(SPAN(current.T("by ")), SPAN(whoDidIt), SPAN(", " + recomm.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if recomm.last_change else "")),
                BR(),
                SPAN(current.T("Manuscript:") + " ", common_small_html.mkDOI(recomm.doi)) if (recomm.doi) else SPAN(""),
                SPAN(" " + current.T("version") + " ", recomm.ms_version) if (recomm.ms_version) else SPAN(""),
                BR(),
                H4(recomm.recommendation_title or "") if (hideOngoingRecomm is False) else "",
                BR(),
                (DIV(WIKI(recomm.recommendation_comments or "", safe_mode=False), _class="pci-bigtext margin") if (hideOngoingRecomm is False) else ""),
                _class="pci-recommendation-div",
            )
            if hideOngoingRecomm is False and recomm.recommender_file:
                truc.append(
                    A(
                        current.T("Download recommender's annotations (PDF)"),
                        _href=URL("default", "download", args=recomm.recommender_file, scheme=scheme, host=host, port=port),
                        _style="margin-bottom: 64px;",
                    )
                )

            if not (recomm.is_closed) and (recomm.recommender_id == auth.user_id) and (art.status == "Under consideration"):
                truc.append(
                    DIV(A(SPAN(current.T("Invite a reviewer"), _class="btn btn-default pci-recommender"), _href=URL(c="recommender", f="reviewers", vars=dict(recommId=recomm.id))))
                )
            truc.append(H3(current.T("Reviews")) + DIV(myReviews, _class="pci-bigtext margin") if len(myReviews) > 0 else "")
            myRound.append(truc)

        myContents.append(H2(current.T("Round #%s") % (roundNb)))
        if myRound and (recomm.is_closed or art.status == "Awaiting revision" or art.user_id != auth.user_id):
            myContents.append(myRound)

    if auth.has_membership(role="manager") and not (art.user_id == auth.user_id) and not (printable) and not (quiet):
        if art.status == "Pending":
            myContents.append(
                DIV(
                    A(
                        SPAN(current.T("Validate this submission"), _class="buttontext btn btn-success pci-manager"),
                        _href=URL(c="manager_actions", f="do_validate_article", vars=dict(articleId=art.id), user_signature=True),
                        _title=current.T("Click here to validate this request and start recommendation process"),
                    ),
                    _class="pci-EditButtons-centered",
                )
            )
        elif art.status == "Pre-recommended" or art.status == "Pre-recommended-private":
            myContents.append(
                DIV(
                    A(
                        SPAN(current.T("Validate this recommendation"), _class="buttontext btn btn-info pci-manager"),
                        _href=URL(c="manager_actions", f="do_recommend_article", vars=dict(articleId=art.id), user_signature=True),
                        _title=current.T("Click here to validate recommendation of this article"),
                    ),
                    _class="pci-EditButtons-centered",
                )
            )
        elif art.status == "Pre-revision":
            myContents.append(
                DIV(
                    A(
                        SPAN(current.T("Validate this decision"), _class="buttontext btn btn-info pci-manager"),
                        _href=URL(c="manager_actions", f="do_revise_article", vars=dict(articleId=art.id), user_signature=True),
                        _title=current.T("Click here to validate revision of this article"),
                    ),
                    _class="pci-EditButtons-centered",
                )
            )
        elif art.status == "Pre-rejected":
            myContents.append(
                DIV(
                    A(
                        SPAN(current.T("Validate this rejection"), _class="buttontext btn btn-info pci-manager"),
                        _href=URL(c="manager_actions", f="do_reject_article", vars=dict(articleId=art.id), user_signature=True),
                        _title=current.T("Click here to validate the rejection of this article"),
                    ),
                    _class="pci-EditButtons-centered",
                )
            )
    return myContents

