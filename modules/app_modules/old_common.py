# -*- coding: utf-8 -*-


from typing import Any, List
from dateutil.relativedelta import *

from gluon.html import *
from gluon.contrib.markdown import WIKI # type: ignore
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon.sqlhtml import *
from models.article import Article


from app_modules import common_small_html
from app_modules import common_tools

from app_modules.common_tools import URL


myconf = AppConfig(reload=True)
pciRRactivated = myconf.get("config.registered_reports", default=False)

DEFAULT_DATE_FORMAT = common_tools.getDefaultDateFormat()

######################################################################################################################################################################
# Show reviews of cancelled articles for CNeuro
def reviewsOfCancelled(art: Article):
    db = current.db
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

        for recomm in recomms:

            whoDidIt = common_small_html.getRecommAndReviewAuthors(recomm=recomm, with_reviewers=True, linked=not (printable), fullURL=True)

            myReviews: List[Any] = []
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
                                common_small_html.mkUser(review.reviewer_id, linked=not (printable)),
                                (", " + review.last_change.strftime(DEFAULT_DATE_FORMAT + " %H:%M") if review.last_change else ""),
                            )
                        )
                    myReviews.append(BR())
                    if len(review.review or "") > 2:
                        myReviews.append(DIV(WIKI(review.review, safe_mode=''), _class="pci-bigtext margin"))
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
                        DIV(WIKI(recomm.reply, safe_mode=''), _class="pci-bigtext"),
                        DIV(
                            A(current.T("Download author's reply (PDF file)"), _href=URL("default", "download", args=recomm.reply_pdf), _style="margin-bottom: 64px;"),
                            _class="pci-bigtext margin",
                        ),
                        _style="margin-top:32px;",
                    )
                else:
                    reply = DIV(H4(B(current.T("Author's reply:"))), DIV(WIKI(recomm.reply, safe_mode=''), _class="pci-bigtext"), _style="margin-top:32px;",)
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
            myContents.append( # type: ignore
                DIV(
                    HR(),
                    H3("Revision round #%s" % recommRound),
                    SPAN(I(recomm.last_change.strftime(DEFAULT_DATE_FORMAT) + " ")) if recomm.last_change else "",
                    H2(recomm.recommendation_title if ((recomm.recommendation_title or "") != "") else current.T("Decision")),
                    H4(current.T(" by "), SPAN(whoDidIt)),
                    DIV(WIKI(recomm.recommendation_comments or "", safe_mode=''), _class="pci-bigtext"),
                    DIV(I(current.T("Preprint DOI:") + " "), common_small_html.mkDOI(recomm.doi), BR()) if ((recomm.doi or "") != "") else "",
                    DIV(myReviews, _class="pci-reviews") if len(myReviews) > 0 else "",
                    reply,
                    _class="pci-recommendation-div"
                )
            )
            recommRound -= 1

        return myContents
