from dataclasses import dataclass
import html
import os
from app_modules.common_tools import extract_doi
from typing import Dict, List, Optional, cast
from app_modules.httpClient import HttpClient
from gluon.html import XML
from models.article import Article
from models.press_reviews import PressReview
from models.recommendation import Recommendation, RecommendationState
from models.review import Review, ReviewState
from app_modules.common_tools import he
from models.user import User
import re
from gluon.template import render # type: ignore

from gluon import current

db = current.db

CROSSREF_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "../../templates/crossref")


@dataclass
class ArticleXML:
    content: str
    filename: str

    @staticmethod
    def build(recomm: Recommendation):
        article = Article.get_by_id(recomm.article_id)
        if not article:
            return ArticleXML("Article not found!", "")

        recomm_url = f"{pci.url}/articles/rec?id={article.id}"
        recomm_doi = _get_recommendation_doi(recomm)
        recomm_date = recomm.validation_timestamp.date() if recomm.validation_timestamp else None
        if not recomm_date:
            return ArticleXML("Missing recommendation validation timestamp!", "")

        recomm_title = recomm.recommendation_title
        recomm_description_text = Article.get_article_reference(article)
        recomm_citations = "\n        ".join(_get_citation_list(recomm))

        recommender = User.get_by_id(recomm.recommender_id)
        if not recommender:
            return ArticleXML("Recommender not found!", "")

        co_recommenders: List[User] = []
        for row in PressReview.get_by_recommendation(recomm.id):
            if row.contributor_id:
                co_recommender = User.get_by_id(row.contributor_id)
                if co_recommender:
                    co_recommenders.append(co_recommender)

        for user in [recommender] + co_recommenders:
            user.affiliation = User.get_affiliation(user) # type: ignore

        interwork_type, interwork_ref = _get_identifier(article.doi)
        item_number = recomm_doi[-6:]

        timestamp = recomm.last_change.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        batch_id = get_filename_article(recomm)

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

        return ArticleXML(cast(str, xml), batch_id)


@dataclass
class DecisionElementXML:
    round: int
    content: str
    filename: str

    @staticmethod
    def build(article: Article, recommendation: Recommendation, round: int):
        if not recommendation.validation_timestamp:
            return DecisionElementXML(round, "Missing validation timestamp for the recommendation", "")

        if not recommendation.last_change:
            return DecisionElementXML(round, "Missing last_change for the recommendation", "")

        if not recommendation.recommender_id:
            return DecisionElementXML(round, "Missing recommender for the recommendation", "")

        recommender = User.get_by_id(recommendation.recommender_id)
        if not recommender:
            return DecisionElementXML(round, f"Missing user with id {recommendation.recommender_id}", "")

        batch_id = f"pci={pci.host}:rec={recommendation.id}:d={recommendation.id}"

        timestamp = recommendation.last_change.strftime("%Y%m%d%H%M%S%f")[:-3]
        recommendation_date = recommendation.validation_timestamp.date()
        interwork_type, interwork_ref = _get_identifier(article.doi)

        decision_doi = _get_decision_doi(recommendation, round)
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

        return DecisionElementXML(round, cast(str, xml), batch_id)


@dataclass
class AuthorReplyElementXML:
    round: int
    content: str
    filename: str

    @staticmethod
    def build(article: Article, recommendation: Recommendation, round: int):
        if not recommendation.validation_timestamp:
            return AuthorReplyElementXML(round, "Missing validation timestamp for the recommendation", "")

        if not recommendation.last_change:
            return AuthorReplyElementXML(round, "Missing last_change for the recommendation", "")

        if not article.user_id:
            return AuthorReplyElementXML(round, "Missing author for the article", "")

        author = User.get_by_id(article.user_id)
        if not author:
            return AuthorReplyElementXML(round, f"Missing user with id {article.user_id}", "")

        batch_id = f"pci={pci.host}:rec={recommendation.id}:ar={recommendation.id}"

        timestamp = recommendation.last_change.strftime("%Y%m%d%H%M%S%f")[:-3]
        recommendation_date = recommendation.validation_timestamp.date()
        interwork_type, interwork_ref = _get_identifier(article.doi)

        author_reply_doi = _get_author_reply_doi(recommendation, round)
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

        return AuthorReplyElementXML(round, cast(str, xml), batch_id)


@dataclass
class ReviewElementXML:
    no_in_round: int
    content: str
    filename: str

    @staticmethod
    def build(article: Article, recommendation: Recommendation, review: Review, round: int, no_review_round: int):
        if not review.acceptation_timestamp:
            return ReviewElementXML(no_review_round, "Missing acceptation timestamp for the review", "")

        if not review.last_change:
            return ReviewElementXML(no_review_round, "Missing last_change for the review", "")

        batch_id = f"pci={pci.host}:rec={recommendation.id}:rev={review.id}"

        timestamp = review.last_change.strftime("%Y%m%d%H%M%S%f")[:-3]
        review_date = review.acceptation_timestamp.date()
        interwork_type, interwork_ref = _get_identifier(article.doi)

        review_doi = _get_review_doi(recommendation, no_review_round, round)
        review_url = f"{pci.url}/articles/rec?id={article.id}#review-{review.id}"

        if review.anonymously:
            contributor_tag = "<anonymous/>"
        else:
            reviewer = User.get_by_id(review.reviewer_id)
            if not reviewer:
                return ReviewElementXML(no_review_round, "Reviewer not found!", "")

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

        return ReviewElementXML(no_review_round, cast(str, xml), batch_id)



@dataclass
class CrossrefXML:
    article: ArticleXML
    decisions: List[DecisionElementXML]
    author_replies: List[AuthorReplyElementXML]
    reviews: Dict[int, List[ReviewElementXML]]

    def __init__(self):
        self.article = ArticleXML("", "")
        self.decisions = []
        self.author_replies = []
        self.reviews = {}


    def get_all_filename(self):
        filenames: List[str] = []

        if self.article.filename:
            filenames.append(self.article.filename)

        for decision in self.decisions:
            if decision.filename:
                filenames.append(decision.filename)

        for author_reply in self.author_replies:
            if author_reply.filename:
                filenames.append(author_reply.filename)

        for reviews in self.reviews.values():
            for review in reviews:
                if review.filename:
                    filenames.append(review.filename)

        return filenames


    @staticmethod
    def build(article: Article):
        recommendations = Article.get_last_recommendations(article.id, order_by=current.db.t_recommendations.id)
        all_reviews = Review.get_by_article_id_and_state(article.id,
                                                        ReviewState.REVIEW_COMPLETED,
                                                        order_by=current.db.t_reviews.acceptation_timestamp)

        xml = CrossrefXML()
        xml.article = ArticleXML.build(recommendations[-1])

        for recommendation in recommendations:
            reviews = filter(lambda r: r.recommendation_id == recommendation.id, all_reviews)
            round = Recommendation.get_current_round_number(recommendation)

            xml_author_reply = AuthorReplyElementXML.build(article, recommendation, round)
            xml.author_replies.append(xml_author_reply)

            xml_decision= DecisionElementXML.build(article, recommendation, round)
            xml.decisions.append(xml_decision)

            round_reviews: List[ReviewElementXML] = []
            for i, review in enumerate(reviews):
                xml_review = ReviewElementXML.build(article, recommendation, review, round, i)
                round_reviews.append(xml_review)

            xml.reviews[round] = round_reviews

        return xml


    def get_status(self):
        response = ""

        try:
            filenames = self.get_all_filename()
            for filename in filenames:
                req = _get_status(filename)
                req.raise_for_status()
                if req.text:
                    response = f"{response}\n{req.text}"
        except Exception as e:
            return f"error: {e.__class__.__name__}"

        return response


    @classmethod
    def from_request(cls, request: ...):
        crossref_xml = cls()

        for form_name, xml in request.vars.items():
            form_name = str(form_name or "")
            xml = str(xml or "")

            splitted_for_name = form_name.split(";")
            if len(splitted_for_name) != 2:
                continue

            name = splitted_for_name[0]
            filename = splitted_for_name[1]

            if "article_xml" in name:
                crossref_xml.article = ArticleXML(xml, filename)
                continue

            round = int(splitted_for_name[0].split('_')[-1])

            if "decision_xml" in name:
                crossref_xml.decisions.append(DecisionElementXML(round, xml, filename))

            if "author_reply" in name:
                crossref_xml.author_replies.append(AuthorReplyElementXML(round, xml, filename))

            if "review" in name:
                no_review = int(name.split('_')[1])
                review_info = ReviewElementXML(no_review, xml, filename)
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
    version = "4.4.2"
    base = "http://www.crossref.org/schema"
    xsd = f"{base}/crossref{version}.xsd"

    login = str(db.conf.get("crossref.login") or "")
    passwd = str(db.conf.get("crossref.passwd") or "")
    api_url = str(db.conf.get("crossref.api") or "https://doi.crossref.org/servlet")

QUEUED = '<doi_batch_diagnostic status="queued">'
FAILED = '<record_diagnostic status="Failure">'


def post_and_forget(article: Article, xml: Optional[CrossrefXML] = None):
    if not xml:
        xml = CrossrefXML.build(article)

    try:
        assert crossref.login, "crossref.login not set"
        assert xml.article.filename
        resp = _post( xml.article.content, xml.article.filename)
        resp.raise_for_status()

        for author_reply in xml.author_replies:
            assert author_reply.filename
            resp = _post(author_reply.content, author_reply.filename)
            resp.raise_for_status()

        for decision in xml.decisions:
            assert decision.filename
            resp = _post(decision.content, decision.filename)
            resp.raise_for_status()

        for _, reviews in xml.reviews.items():
            for review in reviews:
                assert review.filename
                resp = _post(review.content, review.filename)
                resp.raise_for_status()

    except Exception as e:
        return f"error: {e}"


def _post(crossref_xml: str, filename: str):
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


def _get_identifier(doi_str: Optional[str]):
    url = (doi_str or "").strip()
    is_doi = re.match(r"https?://doi\.org/", url, re.IGNORECASE)
    ref = url if not is_doi else url[len(is_doi[0]):]
    typ = "doi" if is_doi else "other"

    return typ, ref


def _get_recommendation_doi(recomm: Recommendation):
    _, ref = _get_identifier(recomm.recommendation_doi)

    return ref or f"{pci.doi}.1"+str(recomm.article_id).zfill(5)


def _get_citation_list(recomm: Recommendation):
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


def _get_review_doi(recommendation: Recommendation, no_review_round: int, round: int):
    recommendation_doi = _get_recommendation_doi(recommendation)
    return f"{recommendation_doi}.rev{round}{no_review_round}"


def _get_author_reply_doi(recommendation: Recommendation, round: int):
    recommendation_doi = _get_recommendation_doi(recommendation)
    return f"{recommendation_doi}.ar{round}"


def _get_decision_doi(recommendation: Recommendation, round: int):
    recommendation_doi = _get_recommendation_doi(recommendation)
    return f"{recommendation_doi}.d{round}"
