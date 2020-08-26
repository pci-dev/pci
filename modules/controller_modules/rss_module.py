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

from app_modules import common_tools

myconf = AppConfig(reload=True)


######################################################################################################################################################################
# RSS MODULES
######################################################################################################################################################################
def mkRecommArticleRss(auth, db, row):
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    recomm = db((db.t_recommendations.article_id == row.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()
    if recomm is None:
        return None
    if row.uploaded_picture is not None and row.uploaded_picture != "":
        img = IMG(_alt="article picture", _src=URL("default", "download", scheme=scheme, host=host, port=port, args=row.uploaded_picture), _style="padding:8px;")
    else:
        img = None
    link = URL(c="articles", f="rec", vars=dict(id=row.id), scheme=scheme, host=host, port=port)
    whoDidIt = common_small_html.getRecommAndReviewAuthors(auth, db, recomm=row, with_reviewers=False, linked=False, host=host, port=port, scheme=scheme)
    desc = DIV()
    article = DIV(CENTER(I(row.title), BR(), SPAN(row.authors), BR(), common_small_html.mkDOI(row.doi)), _style="border:2px solid #cccccc; margin-bottom:8px; font-size:larger;")
    desc.append(article)
    if img:
        desc.append(CENTER(img))
    desc.append(BR())

    what = SPAN()

    what.append(CAT(SPAN(u"Recommended by "), SPAN(whoDidIt)))
    what.append(" ")
    what.append(A(current.T("view"), _href=link))
    desc.append(what)

    desc.append(DIV(WIKI(recomm.recommendation_comments or u"", safe_mode=False), _style="font-size:smaller;"))
    desc.append(HR())

    xdesc = desc.xml()
    title = recomm.recommendation_title or u"(no title)"

    local = pytz.timezone("Europe/Paris")
    local_dt = local.localize(row.last_status_change, is_dst=None)
    created_on = local_dt.astimezone(pytz.utc)

    return dict(guid=link, title=title, link=link, description=xdesc, created_on=created_on)


######################################################################################################################################################################
def mkRecommArticleRss4bioRxiv(auth, db, row):
    ## Template:
    # <link providerId="PCI">
    # <resource>
    # <title>Version 3 of this preprint has been peer-reviewed and recommended by Peer Community in Evolutionary Biology</title>
    # <url>https://dx.doi.org/10.24072/pci.evolbiol.100055</url>
    # <doi>recomm_doi : 10.8483/42422442</doi>
    # <editor>Charles Baer</editor>
    # <date>2018-08-08</date>
    # <reviewers>anonymous and anonymous</reviewers>
    # <logo>https://peercommunityindotorg.files.wordpress.com/2018/09/small_logo_pour_pdf.png</logo>
    # </resource>
    # <doi>10.1101/273367</doi>
    # </link>
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    recomm = db((db.t_recommendations.article_id == row.id) & (db.t_recommendations.recommendation_state == "Recommended")).select(orderby=db.t_recommendations.id).last()
    if recomm is None:
        return None
    version = recomm.ms_version or ""
    pci = myconf.take("app.description")
    title = "Version %(version)s of this preprint has been peer-reviewed and recommended by %(pci)s" % locals()
    url = URL(c="articles", f="rec", vars=dict(id=row.id), scheme=scheme, host=host, port=port)

    recommendersStr = common_small_html.mkRecommendersString(auth, db, recomm)
    reviewersStr = common_small_html.mkReviewersString(auth, db, row.id)


    local = pytz.timezone("Europe/Paris")
    local_dt = local.localize(row.last_status_change, is_dst=None)
    created_on = local_dt.astimezone(pytz.utc)

    return dict(
        title=title,
        url=url,
        recommender=recommendersStr,
        reviewers=reviewersStr,
        date=created_on.strftime("%Y-%m-%d"),
        logo=XML(URL(c="static", f="images/small-background.png", scheme=scheme, host=host, port=port)),
        doi=row.doi,
        recomm_doi=recomm.doi
    )