import datetime
from typing import List

from app_modules.common_tools import URL
from gluon import current

from models.article import Article, ArticleStatus


class SiteMapUrl:
    loc: str
    lastmod: str


def index():
    articles = Article.get_by_status([ArticleStatus.RECOMMENDED], order_by=~current.db.t_articles.id)
    urls: List[SiteMapUrl] = []
    date_format = "%Y-%m-%d"

    for article in articles:
        url = SiteMapUrl()
        url.loc = URL(c="articles", f="rec", vars=dict(articleId=article.id), scheme=True)
        url.lastmod = (
                article.last_status_change or datetime.datetime.today()
        ).strftime(date_format)

        urls.append(url)

    current.response.headers['Content-Type'] = 'text/xml'
    current.response.view = "sitemap.html"

    return dict(urls=urls)
