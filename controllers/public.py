# -*- coding: utf-8 -*-

from app_modules.helper import *

from app_components import article_components

from gluon.storage import Storage


######################################################################################################################################################################
def index():
    request.function = "user_public_page"

    if "userId" in request.vars:
        return user_public_page()
    if auth.user:
        request.vars["userId"] = auth.user.id
        return user_public_page()
    else:
        redirect(URL("../.."))


def user_public_page():
    response.view = "default/user_public_profile.html"
    try:
        userId = request.vars["userId"]
        user = db.auth_user[userId]

        return profile_page(user)
    except:
        return dict(
            pageHelp=getHelp(request, auth, db, "#PublicUserCard"),
            titleIcon="briefcase",
            pageTitle=getTitle(request, auth, db, "#PublicUserCardTitle"),
            customText=B(T("Unavailable"))
        )


def profile_page(user):
            # (gab) is always on false ????
                withMail = False
                userId = user.id

                nameTitle = (user.last_name or "").upper(), " ", (user.first_name or "")
                pageTitle = (
                    (user.last_name or "").upper(),
                    " ",
                    (user.first_name or ""),
                    "'s profile",
                )

                name = LI(B(nameTitle))
                addr = LI(I((user.laboratory or ""), ", ", (user.institution or ""), ", ", (user.city or ""), ", ", (user.country or ""),))
                uthema = user.thematics
                if not isinstance(uthema, list):
                    if uthema is None:
                        uthema = []
                    else:
                        uthema = [uthema]
                thema = LI(", ".join(uthema))
                mail = LI(A(" [%s]" % user.email, _href="mailto:%s" % user.email) if withMail else "")

                if user.uploaded_picture is not None and user.uploaded_picture != "":
                    img = IMG(_alt="avatar", _src=URL("default", "download", args=user.uploaded_picture), _class="pci-userPicture")
                else:
                    img = IMG(_alt="avatar", _src=URL(c="static", f="images/default_user.png"), _class="pci-userPicture")

                if (user.cv or "") != "":
                    userCv = user.cv
                else:
                    userCv = ""

                rolesQy = db((db.auth_membership.user_id == userId) & (db.auth_membership.group_id == db.auth_group.id)).select(db.auth_group.role)
                rolesList = []
                for roleRow in rolesQy:
                    rolesList.append(roleRow.role)
                roles = LI(B(", ".join(rolesList)))

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

                lastRecomms = db.get_last_recomms()

                recommsQy = db(db.t_articles.id.belongs(recommsQy0)).select(db.t_articles.ALL, distinct=True, orderby=~db.t_articles.last_status_change,)
                nbRecomms = len(recommsQy)
                recomms = []
                for row in recommsQy:
                    recomms.append(article_components.getRecommArticleRowCard(auth, db, response, row, lastRecomms.get(row.id), withImg=True, withScore=False, withDate=True, fullURL=False,))

                # reviews
                reviews = []
                reviewsQy = db(
                    (db.t_reviews.reviewer_id == userId)
                    & ~(db.t_reviews.anonymously == True)
                    & (db.t_reviews.review_state == "Review completed")
                    & (db.t_reviews.recommendation_id == db.t_recommendations.id)
                    # & (db.t_recommendations.recommendation_state == 'Recommended')
                    & (db.t_recommendations.article_id == db.t_articles.id)
                    & (db.t_articles.status == "Recommended")
                ).select(db.t_articles.ALL, distinct=True, orderby=~db.t_articles.last_status_change,)

                nbReviews = len(reviewsQy)
                for row in reviewsQy:
                    reviews.append(article_components.getRecommArticleRowCard(auth, db, response, row, lastRecomms.get(row.id), withImg=True, withScore=False, withDate=True, fullURL=False,))

                return dict(
                    pageHelp=getHelp(request, auth, db, "#PublicUserCard"),
                    titleIcon="briefcase",
                    pageTitle=pageTitle,
                    uneditableTitle=True,
                    nbRecomms=nbRecomms,
                    recommendationsList=DIV(recomms, _class="pci2-articles-list"),
                    nbReviews=nbReviews,
                    reviewsList=DIV(reviews, _class="pci2-articles-list"),
                    userAvatar=img,
                    userName=nameTitle,
                    userInfosList=UL(addr, mail, thema, roles) if withMail else UL(addr, thema, roles),
                    userCv=userCv,
                    userWebsite=user.website,
                )
