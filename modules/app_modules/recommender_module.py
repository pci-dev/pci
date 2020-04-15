# -*- coding: utf-8 -*-

import re
import copy
import datetime
from dateutil.relativedelta import *
from gluon.utils import web2py_uuid
from gluon.contrib.markdown import WIKI
from gluon.html import markmin_serializer
from app_modules.common import *
from app_modules.helper import *


# frequently used constants
myconf = AppConfig(reload=True)
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
parallelSubmissionAllowed = myconf.get("config.parallel_submission", default=False)
trgmLimit = myconf.take("config.trgm_limit") or 0.4


######################################################################################################################################################################
## Recommender Module
#######################################################################################################################################################################
def mkViewEditArticleRecommenderButton(auth, db, row):
    return A(
        SPAN(current.T("View"), _class="buttontext btn btn-default pci-button pci-recommender"),
        _href=URL(c="recommender", f="article_details", vars=dict(articleId=row.id)),
        _class="button",
    )


######################################################################################################################################################################
def reopen_review(auth, db, ids):
    if auth.has_membership(role="manager"):
        for myId in ids:
            rev = db.t_reviews[myId]
            if rev.review_state != "Under consideration":
                rev.review_state = "Under consideration"
                rev.update_record()
    elif auth.has_membership(role="recommender"):
        for myId in ids:
            rev = db.t_reviews[myId]
            recomm = db.t_recommendations[rev.recommendation_id]
            if (recomm.recommender_id == auth.user_id) and not (rev.review_state == "Under consideration"):
                rev.review_state = "Under consideration"
                rev.update_record()

