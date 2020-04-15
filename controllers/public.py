# -*- coding: utf-8 -*-
from app_modules.common import *
from app_modules.helper import *


######################################################################################################################################################################
def user_public_page():
    response.view = "default/gab_user_public_layout.html"
    resu = None
    myContents = ""
    if not ("userId" in request.vars):
        session.flash = T("Unavailable")
        redirect(request.env.http_referer)
    else:
        userId = request.vars["userId"]
        if userId:
            user = db.auth_user[userId]
            # (gab) is always on false ????
            withMail = False
            if user:
                nameTitle = (user.last_name or "").upper(), " ", (user.first_name or "")
                pageTitle = (
                    (user.last_name or "").upper(),
                    " ",
                    (user.first_name or ""),
                    "'s profile",
                )

                name = LI(B(nameTitle))
                addr = LI(I((user.laboratory or ""), ", ", (user.institution or ""), ", ", (user.city or ""), ", ", (user.country or ""),))
                thema = LI(", ".join(user.thematics))
                mail = LI(A(" [%s]" % user.email, _href="mailto:%s" % user.email) if withMail else "")

                if user.uploaded_picture is not None and user.uploaded_picture != "":
                    img = IMG(_alt="avatar", _src=URL("default", "download", args=user.uploaded_picture), _class="pci-userPicture", _style="float:left;",)
                else:
                    img = IMG(_alt="avatar", _src=URL(c="static", f="images/default_user.png"), _class="pci-userPicture", _style="float:left;",)

                if (user.cv or "") != "":
                    userCv = user.cv
                else:
                    userCv = ""

                rolesQy = db((db.auth_membership.user_id == userId) & (db.auth_membership.group_id == db.auth_group.id)).select(db.auth_group.role)
                rolesList = []
                for roleRow in rolesQy:
                    rolesList.append(roleRow.role)
                roles = LI(B(", ".join(rolesList)))

                # recommendations ## Patch SP 2020-01-06
                recommsQy0sql = (
                    """
						SELECT t_articles.id
						FROM t_articles
						JOIN t_recommendations ON (
							t_recommendations.article_id = t_articles.id
							AND t_recommendations.recommendation_state = 'Recommended'
							AND t_recommendations.id IN (
								SELECT DISTINCT recommendation_id FROM t_press_reviews WHERE t_press_reviews.contributor_id = %(userId)s
								UNION
								SELECT id FROM t_recommendations WHERE recommender_id = %(userId)s
							)
						)
						WHERE t_articles.status = 'Recommended'
						ORDER BY t_articles.last_status_change DESC
					"""
                    % locals()
                )
                recommsQy0 = []
                for t in db.executesql(recommsQy0sql):
                    recommsQy0.append(t[0])

                recommsQy = db(db.t_articles.id.belongs(recommsQy0)).select(db.t_articles.ALL, distinct=True, orderby=~db.t_articles.last_status_change,)
                nbRecomms = len(recommsQy)
                recomms = []
                for row in recommsQy:
                    recomms.append(common_components.getRecommArticleRowCard(auth, db, response, row, withImg=True, withScore=False, withDate=True, fullURL=False,))

                # reviews
                reviews = []
                reviewsQy = db(
                    (db.t_reviews.reviewer_id == userId)
                    & ~(db.t_reviews.anonymously == True)
                    & (db.t_reviews.review_state == "Completed")
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    # & (db.t_recommendations.recommendation_state == 'Recommended')
                    & (db.t_recommendations.article_id == db.t_articles.id)
                    & (db.t_articles.status == "Recommended")
                ).select(db.t_articles.ALL, distinct=True, orderby=~db.t_articles.last_status_change,)

                nbReviews = len(reviewsQy)
                for row in reviewsQy:
                    reviews.append(common_components.getRecommArticleRowCard(auth, db, response, row, withImg=True, withScore=False, withDate=True, fullURL=False,))

                resu = dict(
                    myHelp=getHelp(request, auth, db, "#PublicUserCard"),
                    titleIcon="briefcase",
                    myTitle=pageTitle,
                    uneditableTitle=True,
                    totalUserRecommendations=SPAN(SPAN(current.T(" %%{Recommendation(nbRecomms)} : ", dict(nbRecomms=nbRecomms),)), B(nbRecomms, _class="pci2-main-color-text"),),
                    totalUserRecommendationsFlex=SPAN(
                        SPAN(current.T(" %%{Recommendation(nbRecomms)} : ", dict(nbRecomms=nbRecomms),), _class="pci2-flex-grow",),
                        B(nbRecomms, _class="pci2-main-color-text"),
                        _class="pci2-flex-row pci2-flex-grow",
                    ),
                    recommendationsList=DIV(recomms, _class="pci2-articles-list"),
                    totalUserReviews=SPAN(SPAN(current.T(" %%{Review(nbReviews)} : ", dict(nbReviews=nbReviews))), B(nbReviews, _class="pci2-main-color-text"),),
                    totalUserReviewsFlex=SPAN(
                        SPAN(current.T(" %%{Review(nbReviews)} : ", dict(nbReviews=nbReviews)), _class="pci2-flex-grow",),
                        B(nbReviews, _class="pci2-main-color-text"),
                        _class="pci2-flex-row pci2-flex-grow",
                    ),
                    reviewsList=DIV(reviews, _class="pci2-articles-list"),
                    userAvatar=img,
                    userName=nameTitle,
                    userInfosList=UL(addr, mail, thema, roles) if withMail else UL(addr, thema, roles),
                    userCv=userCv,
                    totalUserSubmittedPreprints=SPAN(SPAN(current.T("submitted %%{preprint(nbReviews)} : ", dict(nbReviews=3),)), B(3, _class="pci2-main-color-text"),),
                    totalUserSubmittedPreprintsFlex=SPAN(
                        SPAN(current.T(" Submitted %%{preprint(nbReviews)} : ", dict(nbReviews=3),), _class="pci2-flex-grow",),
                        B(3, _class="pci2-main-color-text"),
                        _class="pci2-flex-row pci2-flex-grow",
                    ),
                    totalUserComments=SPAN(SPAN(current.T(" %%{comment(nbReviews)} : ", dict(nbReviews=1))), B(1, _class="pci2-main-color-text"),),
                    totalUserCommentsFlex=SPAN(
                        SPAN(current.T(" %%{Comment(nbReviews)} : ", dict(nbReviews=1)), _class="pci2-flex-grow",),
                        B(1, _class="pci2-main-color-text"),
                        _class="pci2-flex-row pci2-flex-grow",
                    ),
                )
        else:
            myContents = B(T("Unavailable"))

    if resu is None:
        resu = dict(myHelp=getHelp(request, auth, db, "#PublicUserCard"), titleIcon="briefcase", myTitle=getTitle(request, auth, db, "#PublicUserCardTitle"), myText=myContents,)
    return resu

