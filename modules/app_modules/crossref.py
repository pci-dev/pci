import html
from app_modules.common_tools import extract_doi
from typing import Any, List, Optional
from app_modules.httpClient import HttpClient
from gluon.html import DIV, XML
from models.article import Article
from models.press_reviews import PressReview
from models.recommendation import Recommendation
from models.user import User
import re

from gluon import current


db = current.db

class pci:
    host = str(db.cfg.host or "")
    issn = str(db.cfg.issn or "")
    url = f"https://{host}.peercommunityin.org"
    doi = f"10.24072/pci.{host}"
    long_name = str(db.conf.get("app.description") or "")
    short_name = str(db.conf.get("app.longname") or "")
    email = str(db.conf.get("contacts.contact") or "")

class crossref:
    version = "4.3.7"
    base = "http://www.crossref.org/schema"
    xsd = f"{base}/crossref{version}.xsd"

    login = str(db.conf.get("crossref.login") or "")
    passwd = str(db.conf.get("crossref.passwd") or "")
    api_url = str(db.conf.get("crossref.api") or "https://doi.crossref.org/servlet")

QUEUED = '<doi_batch_diagnostic status="queued">'
FAILED = '<record_diagnostic status="Failure">'


def post_and_forget(recomm: Recommendation, xml: Optional[str] = None):
    filename = get_filename(recomm)
    try:
        assert crossref.login, "crossref.login not set"
        resp = post(filename, xml or crossref_xml(recomm))
        resp.raise_for_status()
    except Exception as e:
        return f"error: {e}"


def get_status(recomm: Recommendation):
    try:
        req = _get_status(recomm)
        req.raise_for_status()
        return req.text
    except Exception as e:
        return f"error: {e.__class__.__name__}"


def get_filename(recomm: Recommendation):
    return f"pci={pci.host}:rec={recomm.id}"


def mk_affiliation(user: User):
    if hasattr(user, "is_pseudo"):
        return "(unavailable)"

    affiliation = ""
    if user.laboratory:
        affiliation += user.laboratory
    if user.laboratory and user.institution:
        affiliation += ", "
    if user.institution:
        affiliation += f"{user.institution}"
    if user.city or user.country:
        affiliation += " – "
    if user.city:
        affiliation += user.city
    if user.city and user.country:
        affiliation += ", "
    if user.country:
        affiliation += user.country

    return affiliation


def post(filename: str, crossref_xml: str):
    return HttpClient().post(
        f"{crossref.api_url}/deposit",
        params=dict(
            operation="doMDUpload",
            login_id=crossref.login,
            login_passwd=crossref.passwd,
        ),
        files={filename: crossref_xml},
    )


def _get_status(recomm: Recommendation):
    return HttpClient().get(
        f"{crossref.api_url}/submissionDownload",
        params=dict(
            usr=crossref.login,
            pwd=crossref.passwd,
            file_name=get_filename(recomm),
            type="result",
        )
    )


def get_identifier(doi_str: Optional[str]):
    url = (doi_str or "").strip()
    is_doi = re.match(r"https?://doi\.org/", url, re.IGNORECASE)
    ref = url if not is_doi else url[len(is_doi[0]):]
    typ = "doi" if is_doi else "other"

    return typ, ref


def get_recommendation_doi(recomm: Recommendation):
    _, ref = get_identifier(recomm.recommendation_doi)

    return ref or f"{pci.doi}.1"+str(recomm.article_id).zfill(5)


def get_citation_list(recomm: Recommendation):
    references = Recommendation.get_references(recomm, True)
    citations: List[str] = []
    for i, reference in enumerate(references):
        doi = extract_doi(reference)
        if doi:
            doi = doi.replace('https://doi.org/', '')
            citations.append(f"<citation key=\"ref{i + 1}\"><doi>{doi}</doi></citation>")
        else:
            citations.append(f"<citation key=\"refunstruc{i + 1}\"><unstructured_citation>{reference}</unstructured_citation></citation>")
    return citations


def he(non_html_str: Optional[Any]):
    """Html escape (he)"""

    if non_html_str is None:
        return ""
    
    if isinstance(non_html_str, DIV) or isinstance(non_html_str, XML):
        non_html_str = str(non_html_str.flatten()) # type: ignore
    elif not isinstance(non_html_str, str):
        non_html_str = str(non_html_str)
    
    non_html_str = re.sub(r'\*(.*?)\*', r'\1', non_html_str)
    return html.escape(non_html_str)


def crossref_xml(recomm: Recommendation):
    article = Article.get_by_id(recomm.article_id)
    if not article:
        return "Article not found!"

    recomm_url = f"{pci.url}/articles/rec?id={article.id}"
    recomm_doi = get_recommendation_doi(recomm)
    recomm_date = recomm.validation_timestamp.date() if recomm.validation_timestamp else None
    if not recomm_date:
        return "Missing recommendation validation timestamp!"
    
    recomm_title = recomm.recommendation_title
    recomm_description_text = Article.get_article_reference(article)
    recomm_citations = "\n        ".join(get_citation_list(recomm))

    recommender = User.get_by_id(recomm.recommender_id)
    if not recommender:
        return "Recommender not found!"
    
    co_recommenders: List[User] = []
    for row in PressReview.get_by_recommendation(recomm.id):
        if row.contributor_id:
            co_recommender = User.get_by_id(row.contributor_id)
            if co_recommender:
                co_recommenders.append(co_recommender)

    for user in [recommender] + co_recommenders:
        user.affiliation = mk_affiliation(user) # type: ignore

    interwork_type, interwork_ref = get_identifier(article.doi)
    item_number = recomm_doi[-6:]

    timestamp = recomm.last_change.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    batch_id = f"pci={pci.host}:rec={recomm.id}"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <doi_batch
        xmlns="{crossref.base}/{crossref.version}"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="
            {crossref.base}/{crossref.version}
            {crossref.xsd}"
        version="{crossref.version}">
    <head>
        <doi_batch_id>{he(batch_id)}</doi_batch_id>
        <timestamp>{timestamp}</timestamp>
        <depositor>
            <depositor_name>peercom</depositor_name>
            <email_address>{he(pci.email)}</email_address>
        </depositor>
        <registrant>Peer Community In</registrant>
    </head>
    <body>
    <journal>

    <journal_metadata language="en">
        <full_title>{he(pci.long_name)}</full_title>
        <abbrev_title>{he(pci.short_name)}</abbrev_title>
        """ + (f"""
        <issn media_type='electronic'>{pci.issn}</issn>
        """ if pci.issn else "") + f"""
        <doi_data>
            <doi>{he(pci.doi)}</doi>
            <resource>{he(pci.url)}/</resource>
        </doi_data>
    </journal_metadata>

    <journal_issue>
        <publication_date media_type='online'>
            <month>{recomm_date.month}</month>
            <day>{recomm_date.day}</day>
            <year>{recomm_date.year}</year>
        </publication_date>
    </journal_issue>

    <journal_article publication_type='full_text'>

    <titles>
        <title>
            {he(recomm_title)}
        </title>
    </titles>

    <contributors>
        <person_name sequence='first' contributor_role='author'>
            <given_name>{he(recommender.first_name)}</given_name>
            <surname>{he(recommender.last_name)}</surname>
            <affiliation>{he(recommender.affiliation)}</affiliation>
        </person_name>
        """ + "\n".join([f"""
        <person_name sequence='additional' contributor_role='author'>
            <given_name>{he(co_recommender.first_name)}</given_name>
            <surname>{he(co_recommender.last_name)}</surname>
            <affiliation>{he(co_recommender.affiliation)}</affiliation>
        </person_name>
        """ for co_recommender in co_recommenders ]) + f"""
    </contributors>

    <publication_date media_type='online'>
        <month>{recomm_date.month}</month>
        <day>{recomm_date.day}</day>
        <year>{recomm_date.year}</year>
    </publication_date>

    <publisher_item>
        <item_number item_number_type="article_number">{he(item_number)}</item_number>
    </publisher_item>

    <program xmlns="http://www.crossref.org/AccessIndicators.xsd">
        <free_to_read/>
        <license_ref applies_to="vor" start_date="{recomm_date.isoformat()}">
            https://creativecommons.org/licenses/by/4.0/
        </license_ref>
    </program>

    <program xmlns="http://www.crossref.org/relations.xsd">
    <related_item>
        <description>
            {he(recomm_description_text)}
        </description>
        <inter_work_relation
            relationship-type="isReviewOf"
            identifier-type="{interwork_type}">
            {he(interwork_ref)}
        </inter_work_relation>
    </related_item>
    </program>

    <doi_data>
        <doi>{he(recomm_doi)}</doi>
        <resource>
            {he(recomm_url)}
        </resource>

        <collection property="crawler-based">
        <item crawler="iParadigms">
        <resource>
            {he(recomm_url)}
        </resource>
        </item>
        </collection>

        <collection property="text-mining">
        <item>
        <resource content_version="vor">
            {he(recomm_url)}
        </resource>
        </item>
        </collection>
    </doi_data>

    <citation_list>
        {recomm_citations}
    </citation_list>

    </journal_article>
    </journal>
    </body>
    </doi_batch>
    """
