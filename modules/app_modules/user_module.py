# -*- coding: utf-8 -*-

import re
import copy
import datetime

from gluon.contrib.markdown import WIKI
from app_modules.common import *
from app_modules.helper import *


######################################################################################################################################################################
def mkSuggestedRecommendersUserButton(auth, db, row):
    butts = []
    suggRecomsTxt = []
    # exclude = [str(auth.user_id)]
    excludeList = [auth.user_id]
    suggRecomms = db(db.t_suggested_recommenders.article_id == row["t_articles.id"]).select()
    for sr in suggRecomms:
        # excludeList.append(str(sr.suggested_recommender_id))
        excludeList.append(sr.suggested_recommender_id)
        if sr.declined:
            suggRecomsTxt.append(mkUser(auth, db, sr.suggested_recommender_id) + I(XML("&nbsp;declined")) + BR())
        else:
            suggRecomsTxt.append(mkUser(auth, db, sr.suggested_recommender_id) + BR())
    if len(suggRecomsTxt) > 0:
        butts += suggRecomsTxt
    if row["t_articles.status"] in ("Pending", "Awaiting consideration"):
        myVars = dict(articleId=row["t_articles.id"], exclude=excludeList)
        butts.append(A(current.T("Add / Manage"), _class="btn btn-default pci-submitter", _href=URL(c="user", f="add_suggested_recommender", vars=myVars, user_signature=True)))
    return DIV(butts, _class="pci-w200Cell")

