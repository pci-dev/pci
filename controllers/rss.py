import copy

from gluon.storage import Storage
from gluon.contrib.markdown import WIKI

from datetime import datetime, timedelta, date
from dateutil import parser
from gluon.contrib.appconfig import AppConfig
from lxml import etree

myconf = AppConfig(reload=True)

from app_modules.helper import *

from app_modules import common_tools
from app_modules import common_small_html
from controller_modules import rss_module

# frequently used constants
csv = False  # no export allowed
expClass = None  # dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)

pciRRactivated = myconf.get("config.registered_reports", default=False)

######################################################################################################################################################################
# sub function called by cache.ram below
def _rss_cacher(maxArticles):
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    title = myconf.take("app.longname")
    contact = myconf.take("contacts.managers")
    managingEditor = "%(contact)s (%(title)s contact)" % locals()
    description = T("Articles recommended by ") + myconf.take("app.description")
    favicon = XML(URL(c="static", f="images/favicon.png", scheme=scheme, host=host, port=port))
    # link = URL(c='default', f='index', scheme=scheme, host=host, port=port)
    # thisLink = URL(c='public', f='rss', scheme=scheme, host=host, port=port)
    link = URL(c="public", f="rss", scheme=scheme, host=host, port=port)

    if pciRRactivated:
        item_query = (
            (db.t_articles.status == "Recommended")
            & (db.t_articles.report_stage == "STAGE 2")
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.recommendation_state == "Recommended")
        )
    else:
        item_query = (
            (db.t_articles.status == "Recommended")
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.recommendation_state == "Recommended")
        )

    query = db(
        item_query
    ).iterselect(
        db.t_articles.id,
        db.t_articles.title,
        db.t_articles.authors,
        db.t_articles.article_source,
        db.t_articles.doi,
        db.t_articles.picture_rights_ok,
        db.t_articles.uploaded_picture,
        db.t_articles.abstract,
        db.t_articles.upload_timestamp,
        db.t_articles.user_id,
        db.t_articles.status,
        db.t_articles.last_status_change,
        db.t_articles.thematics,
        db.t_articles.keywords,
        db.t_articles.already_published,
        db.t_articles.auto_nb_recommendations,
        limitby=(0, maxArticles),
        orderby=~db.t_articles.last_status_change,
    )
    myRows = []
    most_recent = None
    for row in query:
        try:
            r = rss_module.mkRecommArticleRss(row)
            if r:
                myRows.append(r)
                if most_recent is None or row.last_status_change > most_recent:
                    most_recent = row.last_status_change
        except Exception as e:
            # raise e
            pass

    if len(myRows) == 0:
        myRows.append(dict(title=T(u"Coming soon.."), link=link, description=T(u"patience!")))
    most_recent = most_recent or parser.parse("2018-01-01")

    return dict(
        title=title,
        link=link,
        # thisLink=thisLink,
        managingEditor=managingEditor,
        created_on=most_recent,
        description=description,
        image=favicon.xml(),
        entries=myRows,
    )


######################################################################################################################################################################
# WARNING - DO NOT ACTIVATE cache.action
def rss():
    response.headers["Content-Type"] = "application/rss+xml"
    response.view = "rsslayout.rss"
    # maxArticles = int(myconf.take('rss.number') or "20")
    # timeExpire  = int(myconf.take('rss.cache') or "60")
    maxArticles = 20
    timeExpire = 60
    d = cache.ram("rss_content", lambda: _rss_cacher(maxArticles), time_expire=timeExpire)
    return d


######################################################################################################################################################################
# NOTE: custom RSS for bioRxiv
# <links>
# <link providerId="PCI">
# <resource>
# <title>Version 3 of this preprint has been peer-reviewed and recommended by Peer Community in Evolutionary Biology</title>
# <url>https://dx.doi.org/10.24072/pci.evolbiol.100055</url>
# <editor>Charles Baer</editor>
# <date>2018-08-08</date>
# <reviewers>anonymous and anonymous</reviewers>
# <logo>https://peercommunityindotorg.files.wordpress.com/2018/09/small_logo_pour_pdf.png</logo>
# </resource>
# <doi>10.1101/273367</doi>
# </link>
# </links>

def rss4biorxiv():
    result = rss4bioRxiv()
    return result

def rss4elife():
    result = rss4bioRxiv()
    return result

def rss4bioRxiv():
    response.headers["Content-Type"] = "application/rss+xml"
    response.view = "rsslayout.rss"

    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    title = myconf.take("app.longname")
    provider = myconf.take("app.name") or "PCI"
    contact = myconf.take("contacts.managers")
    managingEditor = "%(contact)s (%(title)s contact)" % locals()
    favicon = XML(URL(c="static", f="images/favicon.png", scheme=scheme, host=host, port=port))

    if pciRRactivated:
        item_query = (
            (db.t_articles.status == "Recommended")
            & (db.t_articles.report_stage == "STAGE 2")
            & (db.t_articles.already_published == False)
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.recommendation_state == "Recommended")
        )
    else:
        item_query = (
            (db.t_articles.status == "Recommended")
            & (db.t_articles.already_published == False)
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.recommendation_state == "Recommended")
        )

    query = db(
        item_query
    ).iterselect(
        db.t_articles.id,
        db.t_articles.title,
        db.t_articles.authors,
        db.t_articles.article_source,
        db.t_articles.doi,
        db.t_articles.picture_rights_ok,
        db.t_articles.uploaded_picture,
        db.t_articles.abstract,
        db.t_articles.upload_timestamp,
        db.t_articles.user_id,
        db.t_articles.status,
        db.t_articles.last_status_change,
        db.t_articles.thematics,
        db.t_articles.keywords,
        db.t_articles.already_published,
        db.t_articles.auto_nb_recommendations,
        orderby=~db.t_articles.last_status_change,
    )
    links = etree.Element("links")
    for row in query:
        # try:
        r = rss_module.mkRecommArticleRss4bioRxiv(row)
        if r:
            link = etree.Element("link", attrib=dict(providerId=provider))
            resource = etree.SubElement(link, "resource")
            title = etree.SubElement(resource, "title")
            title.text = r["title"]
            url = etree.SubElement(resource, "url")
            url.text = r["url"]

            if r["recomm_doi"]:
                recomm_doi = etree.SubElement(resource, "doi")
                recomm_doi.text = r["recomm_doi"]
            editor = etree.SubElement(resource, "recommender")
            editor.text = r["recommender"]
            reviewers = etree.SubElement(resource, "reviewers")
            reviewers.text = r["reviewers"]
            date = etree.SubElement(resource, "date")
            date.text = r["date"]
            logo = etree.SubElement(resource, "logo")
            logo.text = str(r["logo"])
            doi = etree.SubElement(link, "doi")
            doi.text = r["doi"]
            links.append(link)
    # except Exception as e:
    # raise e
    # pass
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + etree.tostring(links, pretty_print=True).decode("utf8")

######################################################################################################################################################################
def rss4altmetric():
    scheme = myconf.take("alerts.scheme")
    host = myconf.take("alerts.host")
    port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
    title = myconf.take("app.longname")
    provider = myconf.take("app.name") or "PCI"
    contact = myconf.take("contacts.managers")
    managingEditor = "%(contact)s (%(title)s contact)" % locals()
    favicon = XML(URL(c="static", f="images/favicon.png", scheme=scheme, host=host, port=port))
    response.headers["Content-Type"] = "application/rss+xml"
    response.view = "rsslayout.rss"

    if pciRRactivated:
        item_query = (
            (db.t_articles.status == "Recommended")
            & (db.t_articles.report_stage == "STAGE 2")
            & (db.t_articles.already_published == False)
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.recommendation_state == "Recommended")
        )
    else:
        item_query = (
            (db.t_articles.status == "Recommended")
            & (db.t_articles.already_published == False)
            & (db.t_recommendations.article_id == db.t_articles.id)
            & (db.t_recommendations.recommendation_state == "Recommended")
        )

    query = db(
        item_query
    ).iterselect(
        db.t_articles.id,
        db.t_articles.title,
        db.t_articles.authors,
        db.t_articles.article_source,
        db.t_articles.doi,
        db.t_articles.picture_rights_ok,
        db.t_articles.uploaded_picture,
        db.t_articles.abstract,
        db.t_articles.upload_timestamp,
        db.t_articles.user_id,
        db.t_articles.status,
        db.t_articles.last_status_change,
        db.t_articles.thematics,
        db.t_articles.keywords,
        db.t_articles.already_published,
        db.t_articles.auto_nb_recommendations,
        orderby=~db.t_articles.last_status_change,
    )
    links = etree.Element("links")
    for row in query:
        # try:
        r = rss_module.mkRecommArticleRss4bioRxiv(row)
        if r:
            link = etree.Element("link", attrib=dict(providerId=provider))
            resource = etree.SubElement(link, "resource")
            title = etree.SubElement(resource, "title")
            title.text = r["title"]
            url = etree.SubElement(resource, "link")
            url.text = r["url"]
            editor = etree.SubElement(resource, "recommender")
            editor.text = r["recommender"]
            reviewers = etree.SubElement(resource, "reviewers")
            reviewers.text = r["reviewers"]
            date = etree.SubElement(resource, "date")
            date.text = str(r["date"])
            logo = etree.SubElement(resource, "logo")
            logo.text = str(r["logo"])
            doi = etree.SubElement(link, "doi")
            doi.text = r["doi"]
            links.append(link)
    # except Exception, e:
    # raise e
    # pass
    return u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + etree.tostring(links, pretty_print=True).decode('utf8')

