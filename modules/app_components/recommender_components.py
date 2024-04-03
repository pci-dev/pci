# -*- coding: utf-8 -*-
from typing import Any, Dict, List, cast
from models.article import is_scheduled_submission
from gluon import current
from gluon.globals import Request, Response
from gluon.tools import Auth
from gluon.html import *
from app_modules import common_tools
from gluon.sqlhtml import *
from gluon.contrib.appconfig import AppConfig
from models.article import Article, ArticleStatus
from models.recommendation import Recommendation
from pydal import DAL

from app_modules import common_small_html
from models.review import Review, ReviewState

myconf = AppConfig(reload=True)

pciRRactivated = myconf.get("config.registered_reports", default=False)

######################################################################################################################################################################
def getReviewsSubTable(auth: Auth, db: DAL, response: Response, request: Request, recommendation: Recommendation):
    article = Article.get_by_id(recommendation.article_id)
    if not article:
        return None

    manager_coauthor = common_tools.check_coauthorship(auth.user_id, article)
    if manager_coauthor: return DIV(STRONG(current.T('Since you are a coauthor of this article,'),BR(),STRONG('you cannot see the review process.')))

    recommendation_round = Recommendation.get_current_round_number(recommendation)
    reviews = Review.get_by_recommendation_id(recommendation.id, order_by=~db.t_reviews.last_change)
    nb_unfinished_reviews = Review.get_unfinished_reviews(recommendation)
    is_recommender_also_reviewer = Review.is_reviewer_also_recommender(recommendation)

    allowed_to_see_reviews = True
    if (nb_unfinished_reviews > 0) and is_recommender_also_reviewer:
        allowed_to_see_reviews = False

    nb_completed = 0
    nb_on_going = 0

    review_list: List[Dict[str, Any]] = []
    for review in reviews:
            review_vars: Dict[str, Any] = dict(
                reviewer=common_small_html.mkUserWithMail(auth, db, review.reviewer_id),
                status=common_small_html.mkReviewStateDiv(auth, db, review.review_state, review),
                lastChange=common_small_html.mkElapsedDays(review.last_change),
                actions=[],
            )
            review_vars["actions"].append(dict(text=current.T("View e-mails"), link=URL(c="recommender", f="review_emails", vars=dict(reviewId=review.id))))
            review_vars["actions"].append(dict(text=current.T("Prepare an e-mail"), link=URL(c="recommender", f="send_reviewer_generic_mail", vars=dict(reviewId=review.id))))

            if allowed_to_see_reviews and review.review_state == ReviewState.REVIEW_COMPLETED.value:
                review_vars["actions"].append(dict(text=current.T("See review"), link=URL(c="recommender", f="one_review", vars=dict(reviewId=review.id))))

            if review.review_state == ReviewState.WILLING_TO_REVIEW.value:
                review_vars["actions"].append(dict(text=current.T("Accept"), link=URL(c="recommender_actions", f="accept_review_request", vars=dict(reviewId=review.id))))
                review_vars["actions"].append(dict(text=current.T("Decline"), link=URL(c="recommender_actions", f="decline_review_request", vars=dict(reviewId=review.id))))

            if review.review_state == ReviewState.AWAITING_REVIEW.value and not (recommendation.is_closed):
                review_vars["actions"].append(
                        dict(text=current.T("Prepare a cancellation"), link=URL(c="recommender", f="send_review_cancellation", vars=dict(reviewId=review.id)))
                    )   

            if article.status in (ArticleStatus.UNDER_CONSIDERATION.value, ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value) and not (recommendation.is_closed):
                if (review.reviewer_id == auth.user_id) and (review.review_state == ReviewState.AWAITING_REVIEW.value):
                    review_vars["actions"].append(dict(text=current.T("Write, edit or upload your review"), link=URL(c="user", f="edit_review", vars=dict(reviewId=review.id))))

                if (review.reviewer_id != auth.user_id) and ((review.review_state or ReviewState.AWAITING_RESPONSE.value) == ReviewState.AWAITING_RESPONSE.value):
                    review_vars["actions"].append(
                        dict(text=current.T("Prepare a cancellation"), link=URL(c="recommender", f="send_review_cancellation", vars=dict(reviewId=review.id)))
                    )
            if review.review_state == ReviewState.AWAITING_RESPONSE.value and article.status != ArticleStatus.RECOMMENDED.value:
                review_vars["actions"].append(
                    dict(
                        text=current.T("Decline invitation manually"), 
                        link=URL(c="recommender_actions", f="del_reviewer_with_confirmation", vars=dict(
                            reviewId=review.id, 
                            rediectUrl=URL(args=request.args, vars=request.get_vars)
                        ))
                    )
                )

            if review.review_state == ReviewState.NEED_EXTRA_REVIEW_TIME.value:
                review_vars["actions"].append(dict(text=current.T("Accept"), link=URL(c="recommender_actions", f="accept_new_delay_to_reviewing", vars=dict(reviewId=review.id), user_signature=True)))
                review_vars["actions"].append(dict(text=current.T("Decline"), link=URL(c="recommender_actions", f="decline_new_delay_to_reviewing", vars=dict(reviewId=review.id), user_signature=True)))

            if review.review_state == ReviewState.AWAITING_REVIEW.value:
                if pciRRactivated and article.report_stage == "STAGE 1" and (article.is_scheduled or is_scheduled_submission(article)):
                   pass
                else:
                    review_vars["actions"].append(dict(
                        text=current.T("Change date of the review due"),
                        link=URL(c="recommender_actions", f="change_review_due_date", vars=dict(reviewId=review.id))
                    ))
            
            review_list.append(review_vars)
            if review.review_state == ReviewState.REVIEW_COMPLETED.value:
                nb_completed += 1
            if review.review_state == ReviewState.AWAITING_REVIEW.value:
                nb_on_going += 1

    show_decision_link = False
    write_decision_link = None
    invite_reviewer_link = None
    show_searching_for_reviewers_button = None
    show_remove_searching_for_reviewers_button = None
    if (
        not (recommendation.is_closed)
        and ((recommendation.recommender_id == auth.user_id) or auth.has_membership(role="manager") or auth.has_membership(role="administrator"))
        and (article.status in (ArticleStatus.UNDER_CONSIDERATION.value, ArticleStatus.SCHEDULED_SUBMISSION_UNDER_CONSIDERATION.value))
    ):
        invite_reviewer_link = cast(str, URL(c="recommender", f="reviewers", vars=dict(recommId=recommendation.id)))

        show_searching_for_reviewers_button = not article.is_searching_reviewers
        show_remove_searching_for_reviewers_button = article.is_searching_reviewers

        show_decision_link = True
        if (nb_completed >= 2 and nb_on_going == 0) or recommendation_round > 1 or (pciRRactivated):
            write_decision_link = cast(str, URL(c="recommender", f="edit_recommendation", vars=dict(recommId=recommendation.id)))

    round_number = recommendation_round
    component_vars = dict(
        recommId=recommendation.id,
        roundNumber=round_number,
        reviewList=review_list,
        showDecisionLink=show_decision_link,
        inviteReviewerLink=invite_reviewer_link,
        writeDecisionLink=write_decision_link,
        showSearchingForReviewersButton=False,
        showRemoveSearchingForReviewersButton=show_remove_searching_for_reviewers_button,
        isArticleSubmitter=(article.user_id == auth.user_id),
        pciRRactivated=pciRRactivated
    )

    return XML(response.render("components/review_sub_table.html", component_vars))
