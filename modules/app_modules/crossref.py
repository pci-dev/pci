import requests
from time import sleep
from gluon.html import TAG
from app_modules.common_small_html import md_to_html


def init_conf(db):

 class pci:
    host = db.cfg.host
    issn = db.cfg.issn
    url = f"https://{host}.peercommunityin.org"
    doi = f"10.24072/pci.{host}"
    long_name = db.conf.get("app.description")
    short_name = db.conf.get("app.longname")
    email = db.conf.get("contacts.contact")

 class crossref:
    version = "4.3.7"
    base = "http://www.crossref.org/schema"
    xsd = f"{base}/crossref{version}.xsd"

    login = db.conf.get("crossref.login")
    passwd = db.conf.get("crossref.passwd")
    api_url = db.conf.get("crossref.api") or "https://doi.crossref.org/servlet"

 globals().update(locals())


def post_and_forget(recomm, xml=None):
    recomm._filename = filename = get_filename(recomm)
    try:
        assert crossref.login, "crossref.login not set"
        resp = post(filename, xml or crossref_xml(recomm))
        resp.raise_for_status()
    except Exception as e:
        return f"error: {e}"


def wait_for_status(recomm):
    try:
        return _wait_for_status(recomm)
    except Exception as e:
        return f"error: {e}"


def get_filename(recomm):
    return f"pci={pci.host}:rec={recomm.id}"


def mk_recomm_description(recomm, article):
    title = md_to_html(article.title).flatten()
    return " ".join([
        "A recommendation of:",
        f"{article.authors}",
        f"({article.article_year})",
        f"{title}.",
        f"{article.preprint_server},",
        f"ver.{article.ms_version}",
        f"peer-reviewed and recommended by {pci.short_name}",
        f"{article.doi}",
        #article.article_source,
    ]) if not article.article_source \
    else " ".join([
        "A recommendation of:",
        f"{article.authors}",
        f"{title}.",
        f"{article.article_source}",
        f"peer-reviewed and recommended by {pci.short_name}",
        f"{article.doi}",
    ])


def mk_affiliation(user):
    _ = user
    return f"{_.laboratory}, {_.institution} – {_.city}, {_.country}"


def post(filename, crossref_xml):
    return requests.post(
        f"{crossref.api_url}/deposit",
        params=dict(
            operation="doMDUpload",
            login_id=crossref.login,
            login_passwd=crossref.passwd,
        ),
        files={filename: crossref_xml},
    )


def _wait_for_status(recomm):
    for _ in range(5):
        status = get_status(recomm).text
        if "record_diagnostic" in status:
            return status
        sleep(1)

    raise Exception("wait_for_status: timeout")


def get_status(recomm):
    return requests.get(
        f"{crossref.api_url}/submissionDownload",
        params=dict(
            usr=crossref.login,
            pwd=crossref.passwd,
            file_name=get_filename(recomm),
            type="result",
        )
    )


def get_identifier(doi_str):
    url = (doi_str or "").strip()
    typ = "doi" if "://doi.org/" in url[:16] else "other"
    ref = url if typ != "doi" else url[16+url.find("https://"):]

    return typ, ref


def get_recommendation_doi(recomm):
    _, ref = get_identifier(recomm.recommendation_doi)

    return ref or f"{pci.doi}.1"+str(recomm.article_id).zfill(5)


def crossref_xml(recomm):
    article = db.t_articles[recomm.article_id]

    recomm_url = f"{pci.url}/articles/rec?id={article.id}"
    recomm_doi = get_recommendation_doi(recomm)
    recomm_date = recomm.validation_timestamp.date()
    recomm_title = recomm.recommendation_title
    recomm_description_text = mk_recomm_description(recomm, article)

    recommender = db.auth_user[recomm.recommender_id]
    co_recommenders = [ db.auth_user[row.contributor_id] for row in
            db(
                db.t_press_reviews.recommendation_id == recomm.id
            ).select() ]

    for user in [recommender] + co_recommenders:
        user.affiliation = mk_affiliation(user)

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
        <doi_batch_id>{batch_id}</doi_batch_id>
        <timestamp>{timestamp}</timestamp>
        <depositor>
            <depositor_name>peercom</depositor_name>
            <email_address>{pci.email}</email_address>
        </depositor>
        <registrant>Peer Community In</registrant>
    </head>
    <body>
    <journal>

    <journal_metadata language="en">
        <full_title>{TAG(pci.long_name)}</full_title>
        <abbrev_title>{TAG(pci.short_name)}</abbrev_title>
        """ + (f"""
        <issn media_type='electronic'>{pci.issn}</issn>
        """ if pci.issn else "") + f"""
        <doi_data>
            <doi>{pci.doi}</doi>
            <resource>{pci.url}/</resource>
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
            {TAG(recomm_title)}
        </title>
    </titles>

    <contributors>
        <person_name sequence='first' contributor_role='author'>
            <given_name>{TAG(recommender.first_name)}</given_name>
            <surname>{TAG(recommender.last_name)}</surname>
            <affiliation>{TAG(recommender.affiliation)}</affiliation>
        </person_name>
        """ + "\n".join([f"""
        <person_name sequence='additional' contributor_role='author'>
            <given_name>{TAG(co_recommender.first_name)}</given_name>
            <surname>{TAG(co_recommender.last_name)}</surname>
            <affiliation>{TAG(co_recommender.affiliation)}</affiliation>
        </person_name>
        """ for co_recommender in co_recommenders ]) + f"""
    </contributors>

    <publication_date media_type='online'>
        <month>{recomm_date.month}</month>
        <day>{recomm_date.day}</day>
        <year>{recomm_date.year}</year>
    </publication_date>

    <publisher_item>
        <item_number item_number_type="article_number">{item_number}</item_number>
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
            {TAG(recomm_description_text)}
        </description>
        <inter_work_relation
            relationship-type="isReviewOf"
            identifier-type="{interwork_type}">
            {interwork_ref}
        </inter_work_relation>
    </related_item>
    </program>

    <doi_data>
        <doi>{recomm_doi}</doi>
        <resource>
            {recomm_url}
        </resource>

        <collection property="crawler-based">
        <item crawler="iParadigms">
        <resource>
            {recomm_url}
        </resource>
        </item>
        </collection>

        <collection property="text-mining">
        <item>
        <resource content_version="vor">
            {recomm_url}
        </resource>
        </item>
        </collection>
    </doi_data>

    </journal_article>
    </journal>
    </body>
    </doi_batch>
    """
