from app_modules import common_small_html
from app_modules import common_tools

from gluon import current
from gluon.html import *
from gluon.contrib.markdown import WIKI
from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)
scheme = myconf.take("alerts.scheme")
host = myconf.take("alerts.host")
port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))


def getArticleImage(article):
    if article.uploaded_picture is not None and article.uploaded_picture != "":
        article_img = IMG(_src=URL("default", "download", scheme=scheme, host=host, port=port, args=article.uploaded_picture), _alt="article picture", _style="width: 150px",)
    else:
        article_img = IMG(_src=URL("static", "images/small-background.png", scheme=scheme, host=host, port=port), _alt="article picture", _style="width: 150px",)
    return article_img


def makeArticleWithRecommRow(auth, db, article):
    recomm = db((db.t_recommendations.article_id == article.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()

    recomm_authors = common_small_html.getRecommAndReviewAuthors(auth, db, article=article, with_reviewers=True, linked=True, host=host, port=port, scheme=scheme)

    article_img = getArticleImage(article)

    return TABLE(
        TR(
            TD(DIV(common_small_html.mkLastChange(article.last_status_change), DIV(article_img, _style="margin-top: 10px")), _style="vertical-align: top; width: 150px"),
            TD(
                DIV(
                    H3(article.title, _style="margin: 0 0 5px; font-weight: bold"),
                    LABEL(article.authors, _style="margin: 0 0 15px; font-weight: normal; color: #888"),
                    DIV(
                        H4(recomm.recommendation_title, _style="margin: 0 0 5px; font-weight: bold; font-style: italic;"),
                        SPAN(recomm_authors, _style="margin: 0 0 10px; font-style: italic; color: #888"),
                        P(
                            A(
                                current.T("See more"),
                                _href=URL(c="articles", f="rec", vars=dict(id=article.id), scheme=scheme, host=host, port=port),
                                _style="font-size: 12px; padding: 4px 15px; background-color: #93c54b; color: #ffffff; border-radius: 5px; font-weight: bold;",
                            ),
                            _style="margin: 10px 0",
                        ),
                        _style="border-left: 1px solid #ddd; padding-left: 15px; margin-top: 15px",
                    ),
                    _style="margin-left: 10px",
                ),
                _style="vertical-align: top;",
            ),
        ),
        _style="background: #f7f9fb; border-radius: 5px; margin: 15px 0; padding: 5px; width:100%",
    )


def makeArticleRow(article, linkType):
    article_img = getArticleImage(article)

    target_link = ""
    if linkType == "review":
        target_link = A(
            current.T("See more"),
            _href=URL(c="user", f="ask_to_review", vars=dict(articleId=article.id), scheme=scheme, host=host, port=port),
            _style="font-size: 12px; padding: 4px 15px; background-color: #93c54b; color: #ffffff; border-radius: 5px; font-weight: bold;",
        )

    elif linkType == "recommendation":
        target_link = A(
            current.T("See more"),
            _href=URL(c="recommender", f="article_details", vars=dict(articleId=article.id), scheme=scheme, host=host, port=port,),
            _style="font-size: 12px; padding: 4px 15px; background-color: #93c54b; color: #ffffff; border-radius: 5px; font-weight: bold;",
        )

    return TABLE(
        TR(
            TD(DIV(common_small_html.mkLastChange(article.last_status_change), DIV(article_img, _style="margin-top: 10px")), _style="vertical-align: top; width: 150px"),
            TD(
                DIV(
                    H3(article.title, _style="margin: 0 0 5px; font-weight: bold"),
                    LABEL(article.authors, _style="margin: 0 0 5px; font-weight: normal; color: #888"),
                    P(common_small_html.mkDOI(article.doi), _style="margin: 0 0 15px;"),
                    target_link,
                    _style="margin-left: 10px; margin-bottom: 15px",
                ),
                _style="vertical-align: top;",
            ),
        ),
        _style="background: #f7f9fb; border-radius: 5px; margin: 15px 0; padding: 5px; width:100%",
    )
