# -*- coding: utf-8 -*-
import ftplib
import lxml.etree as ET
from datetime import timedelta
from datetime import date
from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)
server = myconf.get('PMC_FTP.server')
username = myconf.get('PMC_FTP.username')
password = myconf.get('PMC_FTP.password')
filepath = myconf.get('PMC_FTP.file_path')
appName = myconf.get("app.description")

timelapse = myconf.get('PMC_FTP.duration')
host = db.cfg.host
session = ftplib.FTP(server, username, password)
session.encoding = 'utf-8'
filename = "preprints.xml"

def build_xml(article):
    et = ET.parse(filename)
    root = et.getroot()
    link_tag = ET.SubElement(root, 'link', {'providerId': '1826'})
    resource_tag = ET.SubElement(link_tag, 'resource')
    title_tag = ET.SubElement(resource_tag, 'title')
    title_tag.text = f"Version {article.t_articles.ms_version} of of this preprint has been peer-reviewed and recommended by  {appName}"
    url_tag = ET.SubElement(resource_tag, 'url')
    url_tag.text = article.t_recommendations.recommendation_doi or f"https://doi.org/10.24072/pci.{host}.1{str(article.t_articles.id).zfill(5)}"
    doi_tag = ET.SubElement(link_tag, 'doi')
    doi_tag.text = article.t_articles.doi
    ET.indent(root)
    et.write(filename)


articles = db(
    (db.t_recommendations.article_id == db.t_articles.id) & (db.t_articles.status == "Recommended") 
    & ((db.t_articles.preprint_server.contains('bioRxiv')) | (db.t_articles.doi.contains('10.1101'))) 
    & (db.t_recommendations.id == db.v_article_recommender.recommendation_id)
    & (db.t_recommendations.validation_timestamp > date.today() - timedelta(days=timelapse))
    ).select(
        db.t_articles.id, db.t_articles.doi, db.t_articles.ms_version, db.t_recommendations.recommendation_doi
    )

with open(filename, "wb") as file:
    session.retrbinary(f'RETR {filepath}', file.write)

for article in articles:
    build_xml(article)

with open(filename, 'rb') as file:
    session.storbinary(f'STOR {filepath}', file)

session.quit()
