from dataclasses import dataclass
import html
import os
from app_modules.common_tools import extract_doi
from typing import Any, Dict, List, Optional, Tuple, cast
from app_modules.httpClient import HttpClient
from gluon.html import DIV, XML
from models.article import Article
from models.press_reviews import PressReview
from models.recommendation import Recommendation, RecommendationState
from models.review import Review, ReviewState
from models.user import User
import re
from gluon.template import render # type: ignore

from gluon import current

db = current.db

CROSSREF_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../templates/crossref")

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


    def get_all_filename(self):
        filenames: List[str] = []

        if self.article[1]:
            filenames.append(self.article[1])

        for decision in self.decisions:
            if decision[2]:
                filenames.append(decision[2])

        for author_reply in self.author_replies:
            if author_reply[2]:
                filenames.append(author_reply[2])

        for reviews in self.reviews.values():
            for review in reviews:
                if review[2]:
                    filenames.append(review[2])

        return filenames


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


def get_status(recommendation_xml: CrossrefXML):
    response = ""

    try:
        filenames = recommendation_xml.get_all_filename()
        for filename in filenames:
            req = _get_status(filename)
            req.raise_for_status()
            if req.text:
                response = f"{response}\n{req.text}"
    except Exception as e:
        return f"error: {e.__class__.__name__}"

    return response


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


def _get_status(filename: str):
    return HttpClient().get(
        f"{crossref.api_url}/submissionDownload",
        params=dict(
            usr=crossref.login,
            pwd=crossref.passwd,
            file_name=filename,
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

    xml = render( # type: ignore
        filename=os.path.join(CROSSREF_TEMPLATE_DIR, "article.xml"),
        context=dict(
            he=he,
            crossref=crossref,
            batch_id=batch_id,
            timestamp=timestamp,
            pci=pci,
            recomm_date=recomm_date,
            recomm_title=recomm_title,
            recommender=recommender,
            co_recommenders=co_recommenders,
            item_number=item_number,
            recomm_description_text=recomm_description_text,
            interwork_type=interwork_type,
            interwork_ref=interwork_ref,
            recomm_doi=recomm_doi,
            recomm_url=recomm_url,
            recomm_citations=XML(recomm_citations)
        ))

    return cast(str, xml), batch_id


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

    xml = render( # type: ignore
        filename=os.path.join(CROSSREF_TEMPLATE_DIR, "review.xml"),
        context=dict(
            he=he,
            crossref=crossref,
            batch_id=batch_id,
            timestamp=timestamp,
            pci=pci,
            round=round,
            status=status,
            contributor_tag=XML(contributor_tag),
            article=article,
            review_date=review_date,
            interwork_type=interwork_type,
            interwork_ref=interwork_ref,
            review_doi=review_doi,
            review_url=review_url
        ))

    return cast(str, xml), batch_id


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

    xml = render( # type: ignore
        filename=os.path.join(CROSSREF_TEMPLATE_DIR, "author_reply.xml"),
        context=dict(
            he=he,
            crossref=crossref,
            batch_id=batch_id,
            timestamp=timestamp,
            pci=pci,
            round=round,
            status=status,
            author=author,
            article=article,
            recommendation_date=recommendation_date,
            interwork_type=interwork_type,
            interwork_ref=interwork_ref,
            author_reply_doi=author_reply_doi,
            author_reply_url=author_reply_url
        ))

    return cast(str, xml), batch_id


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

    xml = render( # type: ignore
        filename=os.path.join(CROSSREF_TEMPLATE_DIR, "decision.xml"),
        context=dict(
            he=he,
            crossref=crossref,
            batch_id=batch_id,
            timestamp=timestamp,
            pci=pci,
            round=round,
            status=status,
            recommender=recommender,
            title=title,
            recommendation_date=recommendation_date,
            interwork_type=interwork_type,
            interwork_ref=interwork_ref,
            decision_doi=decision_doi,
            decision_url=decision_url
        ))

    return cast(str, xml), batch_id
