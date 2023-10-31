# -*- coding: utf-8 -*-
import feedparser
import requests
from datetime import datetime, timedelta, timezone
from app_modules import emailing

now = datetime.now(timezone.utc)
time_range = timedelta(days=31)

url = "https://peercommunityjournal.org/en/latest/feed/pcj/"
feed = feedparser.parse(url)
prefix = "https://doi.org/"

def get_article_id(doi):
    article_id = None
    url = f'https://api.crossref.org/works/{doi}'
    response = requests.get(url)
    if response.ok:
        data = response.json()
        references = data["message"]["reference"]
        for reference in references:
            try:
                if "10.24072" in reference["DOI"]:
                    article_id = int(reference["DOI"][9:].split(".")[-1][1:])
            except:
                pass
    return article_id

def update_article(id, published_doi):
    article = db((db.t_articles.id == id) & (db.t_articles.doi_of_published_article == None) & (db.t_articles.status == "Recommended")).select().last()
    if article:
        article.update_record(doi_of_published_article=published_doi)
        emailing.send_message_to_recommender_and_reviewers(auth, db, id)


for entry in feed.entries:
    entry_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")
    if now - entry_date <= time_range:
        published_doi = entry.id
        article_id = get_article_id(published_doi.strip(prefix))
        update_article(article_id, published_doi) if article_id else None



