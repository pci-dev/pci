# -*- coding: utf-8 -*-
from app_modules import emailing


def send_mails_for_published_dois():
        articles = db((db.t_articles.doi_of_published_article.contains('pcjournal')) & (db.t_articles.status == "Recommended")).select(db.t_articles.id)
        for article in articles:
                emailing.send_message_to_recommender_and_reviewers(auth, db, article.id)

send_mails_for_published_dois()
