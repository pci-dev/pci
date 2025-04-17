from dataclasses import dataclass
import html
from app_modules.common_tools import extract_doi
from typing import Any, Dict, List, Optional, Tuple
from app_modules.httpClient import HttpClient
from gluon.html import DIV, XML
from models.article import Article
from models.press_reviews import PressReview
from models.recommendation import Recommendation, RecommendationState
from models.review import Review, ReviewState
from models.user import User
import re

from gluon import current

db = current.db

@dataclass
class CrossrefXML:
    article: Tuple[str, Optional[str]]
    decisions: List[Tuple[int, str, Optional[str]]]
    author_replies: List[Tuple[int, str, Optional[str]]]
    reviews: Dict[int, List[Tuple[int, str, Optional[str]]]]

    def __init__(self):
        self.article = ("", None)
        self.decisions = []
        self.author_replies = []
        self.reviews = {}

    @classmethod
    def from_request(cls, request: ...):
        crossref_xml = CrossrefXML()

        for form_name, xml in request.vars.items():
            form_name = str(form_name or "")
            xml = str(xml or "")

            splitted_for_name = form_name.split(";")
            if len(splitted_for_name) != 2:
                continue

            name = splitted_for_name[0]
            filename = splitted_for_name[1]

            if "article_xml" in name:
                crossref_xml.article = (xml, filename)
                continue

            round = int(splitted_for_name[0].split('_')[-1])

            if "decision_xml" in name:
                crossref_xml.decisions.append((round, xml, filename))

            if "author_reply" in name:
                crossref_xml.author_replies.append((round, xml, filename))

            if "review" in name:
                no_review = int(name.split('_')[1])
                review_info = (no_review, xml, filename)
                if round in crossref_xml.reviews:
                    crossref_xml.reviews[round].append(review_info)
                else:
                    crossref_xml.reviews[round] = [review_info]

        return crossref_xml


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


def post_and_forget(article: Article, xml: Optional[CrossrefXML] = None):
    if not xml:
        xml = crossref_recommendations_xml(article)

    try:
        assert crossref.login, "crossref.login not set"
        assert xml.article[1]
        resp = post( xml.article[0], xml.article[1])
        resp.raise_for_status()

        for author_reply in xml.author_replies:
            assert author_reply[2]
            resp = post(author_reply[1], author_reply[2])
            resp.raise_for_status()

        for decision in xml.decisions:
            assert decision[2]
            resp = post(decision[1], decision[2])
            resp.raise_for_status()

        for _, reviews in xml.reviews.items():
            for review in reviews:
                assert review[2]
                resp = post(review[1], review[2])
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


def post(crossref_xml: str,filename: str):
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
            file_name=get_filename_article(recomm),
            type="result",
        )
    )


def get_filename_article(recomm: Recommendation):
    return f"pci={pci.host}:rec={recomm.id}"


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
            citations.append(f"<citation key=\"ref{i + 1}\"><doi>{html.escape(doi)}</doi></citation>")
        else:
            citations.append(f"<citation key=\"refunstruc{i + 1}\"><unstructured_citation>{html.escape(reference)}</unstructured_citation></citation>")
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


def crossref_article_xml(recomm: Recommendation):
    article = Article.get_by_id(recomm.article_id)
    if not article:
        return "Article not found!", None

    recomm_url = f"{pci.url}/articles/rec?id={article.id}"
    recomm_doi = get_recommendation_doi(recomm)
    recomm_date = recomm.validation_timestamp.date() if recomm.validation_timestamp else None
    if not recomm_date:
        return "Missing recommendation validation timestamp!", None

    recomm_title = recomm.recommendation_title
    recomm_description_text = Article.get_article_reference(article)
    recomm_citations = "\n        ".join(get_citation_list(recomm))

    recommender = User.get_by_id(recomm.recommender_id)
    if not recommender:
        return "Recommender not found!", None

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
    """, batch_id

def crossref_recommendations_xml(article: Article):
    recommendations = Article.get_last_recommendations(article.id, order_by=current.db.t_recommendations.id)
    all_reviews = Review.get_by_article_id_and_state(article.id,
                                                     ReviewState.REVIEW_COMPLETED,
                                                     order_by=current.db.t_reviews.acceptation_timestamp)

    xml = CrossrefXML()
    xml.article = crossref_article_xml(recommendations[-1])

    for recommendation in recommendations:
        reviews = filter(lambda r: r.recommendation_id == recommendation.id, all_reviews)
        round = Recommendation.get_current_round_number(recommendation)

        xml_author_reply, filename = crossref_author_reply_xml(article, recommendation, round)
        xml.author_replies.append((round, xml_author_reply, filename))

        xml_decision, filename = crossref_decision_xml(article, recommendation, round)
        xml.decisions.append((round, xml_decision, filename))

        round_reviews: List[Tuple[int, str, Optional[str]]] = []
        for i, review in enumerate(reviews):
            xml_review, filename = crossref_review_xml(article, recommendation, review, round, i)
            round_reviews.append((i, xml_review, filename))

        xml.reviews[round] = round_reviews

    return xml


def get_review_doi(recommendation: Recommendation, no_review_round: int, round: int):
    recommendation_doi = get_recommendation_doi(recommendation)
    return f"{recommendation_doi}.rev{round}{no_review_round}"


def crossref_review_xml(article: Article, recommendation: Recommendation, review: Review, round: int, no_review_round: int):
    if not review.acceptation_timestamp:
        return "Missing acceptation timestamp for the review", None

    if not review.last_change:
        return "Missing last_change for the review", None

    batch_id = f"pci={pci.host}:rec={recommendation.id}:rev={review.id}"

    timestamp = review.last_change.strftime("%Y%m%d%H%M%S%f")[:-3]
    review_date = review.acceptation_timestamp.date()
    interwork_type, interwork_ref = get_identifier(article.doi)

    review_doi = get_review_doi(recommendation, no_review_round, round)
    review_url = f"{pci.url}/articles/rec?id={article.id}#review-{review.id}"

    if review.anonymously:
        contributor_tag = "<anonymous/>"
    else:
        reviewer = User.get_by_id(review.reviewer_id)
        if not reviewer:
            return "Reviewer not found!", None

        reviewer_first_name = reviewer.first_name if reviewer.first_name else "?"
        reviewer_last_name = reviewer.last_name if reviewer.last_name else "?"

        contributor_tag = f"""
<person_name contributor_role="reviewer" sequence="first">
    <given_name>{he(reviewer_first_name)}</given_name>
    <surname>{he(reviewer_last_name)}</surname>
</person_name>
        """

    if recommendation.recommendation_state == RecommendationState.RECOMMENDED.value:
        status = "accept"
    else:
        status = "major-revision"


    return f"""<?xml version="1.0" encoding="UTF-8"?>
<doi_batch xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
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
     	<peer_review stage="pre-publication" revision-round="{round}" type="referee-report" recommendation="{status}">
         	<contributors>
                {contributor_tag}
         	</contributors>
         	<titles>
            	<title>Review of: {he(article.title)}</title>
         	</titles>
         	<review_date>
            	<month>{review_date.month}</month>
            	<day>{review_date.day}</day>
            	<year>{review_date.year}</year>
         	</review_date>

         	<competing_interest_statement>The reviewer declared that they have no conflict of interest (as defined in the code of conduct of PCI) with the authors or with the content of the article.</competing_interest_statement>

            <program xmlns="http://www.crossref.org/AccessIndicators.xsd">
                <free_to_read/>
                <license_ref applies_to="vor" start_date="{review_date.isoformat()}">
                    https://creativecommons.org/licenses/by/4.0/
                </license_ref>
            </program>

         	<program xmlns="http://www.crossref.org/relations.xsd">
            	<related_item>
                    <inter_work_relation relationship-type="isReviewOf" identifier-type="{interwork_type}">{he(interwork_ref)}</inter_work_relation>
            	</related_item>
         	</program>
         	<doi_data>
            	<doi>{he(review_doi)}</doi>
            	<resource>{he(review_url)}</resource>
         	</doi_data>
     	</peer_review>
   	</body>
</doi_batch>
    """, batch_id


def get_author_reply_doi(recommendation: Recommendation, round: int):
    recommendation_doi = get_recommendation_doi(recommendation)
    return f"{recommendation_doi}.ar{round}"


def crossref_author_reply_xml(article: Article, recommendation: Recommendation, round: int):
    if not recommendation.validation_timestamp:
        return "Missing validation timestamp for the recommendation", None

    if not recommendation.last_change:
        return "Missing last_change for the recommendation", None

    if not article.user_id:
        return "Missing author for the article", None

    author = User.get_by_id(article.user_id)
    if not author:
        return f"Missing user with id {article.user_id}", None

    batch_id = f"pci={pci.host}:rec={recommendation.id}:ar={recommendation.id}"

    timestamp = recommendation.last_change.strftime("%Y%m%d%H%M%S%f")[:-3]
    recommendation_date = recommendation.validation_timestamp.date()
    interwork_type, interwork_ref = get_identifier(article.doi)

    author_reply_doi = get_author_reply_doi(recommendation, round)
    author_reply_url = f"{pci.url}/articles/rec?id={article.id}#ar-{recommendation.id}"

    if recommendation.recommendation_state == RecommendationState.RECOMMENDED.value:
        status = "accept"
    else:
        status = "major-revision"


    return f"""<?xml version="1.0" encoding="UTF-8"?>
<doi_batch xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
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
     	<peer_review stage="pre-publication" revision-round="{round}" type="author-comment" recommendation="{status}">
         	<contributors>
                <person_name contributor_role="author" sequence="first">
                    <given_name>{he(author.first_name)}</given_name>
                    <surname>{he(author.last_name)}</surname>
                </person_name>
         	</contributors>
         	<titles>
            	<title>Author response of: {he(article.title)}</title>
         	</titles>
         	<review_date>
            	<month>{recommendation_date.month}</month>
            	<day>{recommendation_date.day}</day>
            	<year>{recommendation_date.year}</year>
         	</review_date>

         	<competing_interest_statement>The authors declared that they comply with the PCI rule of having no financial conflicts of interest in relation to the content of the article.</competing_interest_statement>

            <program xmlns="http://www.crossref.org/AccessIndicators.xsd">
                <free_to_read/>
                <license_ref applies_to="vor" start_date="{recommendation_date.isoformat()}">
                    https://creativecommons.org/licenses/by/4.0/
                </license_ref>
            </program>

         	<program xmlns="http://www.crossref.org/relations.xsd">
            	<related_item>
                    <inter_work_relation relationship-type="isReviewOf" identifier-type="{interwork_type}">{he(interwork_ref)}</inter_work_relation>
            	</related_item>
         	</program>
         	<doi_data>
            	<doi>{he(author_reply_doi)}</doi>
            	<resource>{he(author_reply_url)}</resource>
         	</doi_data>
     	</peer_review>
   	</body>
</doi_batch>
    """, batch_id

def get_decision_doi(recommendation: Recommendation, round: int):
    recommendation_doi = get_recommendation_doi(recommendation)
    return f"{recommendation_doi}.d{round}"

def crossref_decision_xml(article: Article, recommendation: Recommendation, round: int):
    if not recommendation.validation_timestamp:
        return "Missing validation timestamp for the recommendation", None

    if not recommendation.last_change:
        return "Missing last_change for the recommendation", None

    if not recommendation.recommender_id:
        return "Missing recommender for the recommendation", None

    recommender = User.get_by_id(recommendation.recommender_id)
    if not recommender:
        return f"Missing user with id {recommendation.recommender_id}", None

    batch_id = f"pci={pci.host}:rec={recommendation.id}:d={recommendation.id}"

    timestamp = recommendation.last_change.strftime("%Y%m%d%H%M%S%f")[:-3]
    recommendation_date = recommendation.validation_timestamp.date()
    interwork_type, interwork_ref = get_identifier(article.doi)

    decision_doi = get_decision_doi(recommendation, round)
    decision_url = f"{pci.url}/articles/rec?id={article.id}#d-{recommendation.id}"

    if recommendation.recommendation_state == RecommendationState.RECOMMENDED.value:
        status = "accept"
        title = f"Editorial decision of: {he(article.title)}"
    else:
        status = "major-revision"
        title = f"Recommendation of: {he(article.title)}"


    return f"""<?xml version="1.0" encoding="UTF-8"?>
<doi_batch xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
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
     	<peer_review stage="pre-publication" revision-round="{round}" type="editor-report" recommendation="{status}">
         	<contributors>
                <person_name contributor_role="editor" sequence="first">
                    <given_name>{he(recommender.first_name)}</given_name>
                    <surname>{he(recommender.last_name)}</surname>
                </person_name>
         	</contributors>
         	<titles>
            	<title>{title}</title>
         	</titles>
         	<review_date>
            	<month>{recommendation_date.month}</month>
            	<day>{recommendation_date.day}</day>
            	<year>{recommendation_date.year}</year>
         	</review_date>

         	<competing_interest_statement>The recommender in charge of the evaluation of the article declared that they have no conflict of interest (as defined in the code of conduct of PCI) with the authors or with the content of the article.</competing_interest_statement>

            <program xmlns="http://www.crossref.org/AccessIndicators.xsd">
                <free_to_read/>
                <license_ref applies_to="vor" start_date="{recommendation_date.isoformat()}">
                    https://creativecommons.org/licenses/by/4.0/
                </license_ref>
            </program>

         	<program xmlns="http://www.crossref.org/relations.xsd">
            	<related_item>
                    <inter_work_relation relationship-type="isReviewOf" identifier-type="{interwork_type}">{he(interwork_ref)}</inter_work_relation>
            	</related_item>
         	</program>
         	<doi_data>
            	<doi>{he(decision_doi)}</doi>
            	<resource>{he(decision_url)}</resource>
         	</doi_data>
     	</peer_review>
   	</body>
</doi_batch>
    """, batch_id
