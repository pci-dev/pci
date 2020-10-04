# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import re
import os

# from gluon.contrib.markdown import WIKI

from datetime import date, datetime
import calendar
from time import sleep

# import socket
# host=socket.getfqdn()
from gluon.contrib.appconfig import AppConfig

from app_components import article_components

from app_modules import emailing
from app_modules import common_tools
from app_modules import common_small_html

myconf = AppConfig(reload=True)
MAIL_HTML_LAYOUT = os.path.join(os.path.dirname(__file__), "..", "views", "mail", "mail.html")

@auth.requires(auth.has_membership(role="developper"))
def test_flash():
    session.flash = "Coucou !"
    redirect(request.env.http_referer)


@auth.requires(auth.has_membership(role="administrator") or auth.has_membership(role="developper"))
def testUserRecommendedAlert():
    if "userId" in request.vars:
        userId = request.vars["userId"]
    conditions = ["client" not in request, auth.user]
    if any(conditions):
        if userId:
            userId = auth.user_id
            user = db.auth_user[userId]
            if user:
                articleIdsQy = db.executesql("SELECT * FROM alert_last_recommended_article_ids_for_user(%s);", placeholders=[userId])
                if len(articleIdsQy) > 0:
                    artIds = articleIdsQy[0][0]
                    if artIds:
                        query = db((db.t_articles.id.belongs(artIds))).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)
                        n = len(query)
                        myRows = []
                        odd = True
                        for row in query:
                            myRows.append(article_components.getRecommArticleRowCard(auth, db, response, row, withImg=False, withScore=False, withDate=True, fullURL=True))

                            odd = not (odd)
                        msgContents = DIV(TABLE(TBODY(myRows), _style="width:100%; background-color:transparent; border-collapse: separate; border-spacing: 0 8px;"),)
                        if len(myRows) > 0:
                            emailing.send_alert_new_recommendations(session, auth, db, userId, msgContents)

            redirect(request.env.http_referer)
        else:
            raise HTTP(404, "404: " + T("Unavailable"))
    else:
        raise HTTP(403, "403: " + T("Unauthorized"))


# function called daily
# @auth.requires_login()
def alertUsersLastRecommendations():
    print("Starting cron alerts...")
    conditions = ["client" not in request, auth.has_membership(role="manager")]
    if any(conditions):
        my_date = date.today()
        my_day = calendar.day_name[my_date.weekday()]
        usersQy = db(db.auth_user.alerts.contains(my_day, case_sensitive=False)).select()
        for user in usersQy:
            userId = user.id
            articleIdsQy = db.executesql("SELECT * FROM alert_last_recommended_article_ids_for_user(%s);", placeholders=[userId])
            if len(articleIdsQy) > 0:
                artIds = articleIdsQy[0][0]
                if artIds:
                    query = db(
                        (db.t_articles.id.belongs(artIds)) & (db.t_recommendations.article_id == db.t_articles.id) & (db.t_recommendations.recommendation_state == "Recommended")
                    ).select(db.t_articles.ALL, orderby=~db.t_articles.last_status_change)
                    n = len(query)
                    myRows = []
                    odd = True
                    for row in query:
                        myRows.append(article_components.getRecommArticleRowCard(auth, db, response, row, withImg=False, withScore=False, withDate=True, fullURL=True))
                        odd = not (odd)
                    msgContents = DIV(DIV(myRows, _style="width:100%; background-color:transparent; border-collapse: separate; border-spacing: 0 8px;"),)
                    if len(myRows) > 0:
                        emailing.send_alert_new_recommendations(session, auth, db, userId, msgContents)
                        user.last_alert = datetime.now()
                        user.update_record()
                        db.commit()
        
        redirect(request.env.http_referer)

