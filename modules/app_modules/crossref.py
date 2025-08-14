from dataclasses import dataclass
import datetime
import html
import os
import subprocess
from time import sleep
from app_modules.common_tools import extract_doi
from typing import Dict, List, Optional, Tuple, cast
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

class XMLException(Exception):
    pass


@dataclass
class RecommendationXML:
    content: str
    filename: str

    @staticmethod
    def build(recommendation: Recommendation):
        article = Article.get_by_id(recommendation.article_id)
        if not article:
            return RecommendationXML(f"Article with id {recommendation.article_id} not found!", "")

        if not recommendation.validation_timestamp:
            return RecommendationXML(f"Missing recommendation validation timestamp for recommendation with id {recommendation.id}!", "")

        recomm_url = f"{pci.url}/articles/rec?id={article.id}"
        recomm_doi = _get_recommendation_doi(recommendation)
        recomm_title = recommendation.recommendation_title
        recomm_description_text = Article.get_article_reference(article)
        recomm_citations = "\n        ".join(_get_citation_list(recommendation))

        recommender = User.get_by_id(recommendation.recommender_id)
        if not recommender:
            return RecommendationXML(f"Recommender with id {recommendation.recommender_id} not found!", "")

        interwork_type, interwork_ref = _get_identifier(article.doi)
        item_number = recomm_doi[-6:]

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        batch_id = f"pci={pci.host}:rec={recommendation.id}"

        xml = render( # type: ignore
            filename=os.path.join(CROSSREF_TEMPLATE_DIR, "recommendation.xml"),
            context=dict(
                he=he,
                crossref=crossref,
                batch_id=batch_id,
                timestamp=timestamp,
                pci=pci,
                recomm_date=recommendation.validation_timestamp.date(),
                recomm_title=recomm_title,
                recommender=(recommender, User.get_affiliation(recommender)),
                co_recommenders=get_co_recommender_infos(recommendation.id),
                item_number=item_number,
                recomm_description_text=recomm_description_text,
                interwork_type=interwork_type,
                interwork_ref=interwork_ref,
                recomm_doi=recomm_doi,
                recomm_url=recomm_url,
                recomm_citations=XML(recomm_citations)
            ))

        return RecommendationXML(cast(str, xml), batch_id)


@dataclass
class DecisionElementXML:
    round: int
    content: str
    filename: str

    @staticmethod
    def build(article: Article, recommendation: Recommendation, round: int, total_round: int):
        if not recommendation.validation_timestamp:
            return DecisionElementXML(round, f"Missing validation timestamp for the recommendation with id {recommendation.id}", "")

        if not recommendation.last_change:
            return DecisionElementXML(round, f"Missing last_change for the recommendation with id {recommendation.id}", "")

        if not recommendation.recommender_id:
            return DecisionElementXML(round, f"Missing recommender for the recommendation with id {recommendation.id}", "")

        recommender = User.get_by_id(recommendation.recommender_id)
        if not recommender:
            return DecisionElementXML(round, f"Missing user with id {recommendation.recommender_id}", "")

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        recommendation_date = recommendation.validation_timestamp.date()
        interwork_type, interwork_ref = _get_identifier(article.doi)

        article_title = _get_article_title(article, round)

        if recommendation.recommendation_state == RecommendationState.RECOMMENDED.value:
            if recommendation.recommendation_title:
                title = f"Recommendation of: {article_title}"
            else:
                title = recommendation.recommendation_title

            decision_doi = _get_recommendation_doi(recommendation)
            decision_url = f"{pci.url}/articles/rec?id={article.id}"
            batch_id = f"pci={pci.host}:rec={recommendation.id}"
            status = "accept"
        else:
            title = f"Decision Revise: {article_title}"
            decision_doi = get_decision_doi(recommendation, round)
            decision_url = f"{pci.url}/articles/rec?id={article.id}#d-{recommendation.id}"
            batch_id = f"pci={pci.host}:rec={recommendation.id}:d={recommendation.id}"

            if round >= 2 and total_round >= 3:
                status = "minor-revision"
            else:
                status = "major-revision"

        item_number = ".".join(decision_doi.split(".")[-2:])
        last_decision = round == total_round

        xml = render( # type: ignore
            filename=os.path.join(CROSSREF_TEMPLATE_DIR, "decision.xml"),
            context=dict(
                he=he,
                crossref=crossref,
                batch_id=batch_id,
                timestamp=timestamp,
                pci=pci,
                round=round - 1,
                status=status,
                recommender=(recommender, User.get_affiliation(recommender)),
                co_recommenders=get_co_recommender_infos(recommendation.id),
                title=title,
                recommendation_date=recommendation_date,
                interwork_type=interwork_type,
                interwork_ref=interwork_ref,
                decision_doi=decision_doi,
                decision_url=decision_url,
                item_number=item_number,
                add_doi_data=last_decision
            ))

        return DecisionElementXML(round, cast(str, xml), batch_id)


@dataclass
class AuthorReplyElementXML:
    round: int
    content: str
    filename: str

    @staticmethod
    def build(article: Article, recommendation: Recommendation, round: int, next_recommendation: Recommendation):
        if not recommendation.validation_timestamp:
            return AuthorReplyElementXML(round, f"Missing validation timestamp for the recommendation with id {recommendation.id}", "")

        if not next_recommendation.recommendation_timestamp:
            return AuthorReplyElementXML(round, f"Missing recommendation_timestamp for the recommendation with id {next_recommendation.id}", "")

        if not article.user_id:
            return AuthorReplyElementXML(round, f"Missing author for the article with id {article.id}", "")

        authors = Article.get_authors(article)
        if len(authors) == 0:
            return AuthorReplyElementXML(round, f"Missing user with id {article.user_id}", "")

        batch_id = f"pci={pci.host}:rec={recommendation.id}:ar={recommendation.id}"

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        next_recommendation_date = next_recommendation.recommendation_timestamp.date()
        interwork_type, interwork_ref = _get_identifier(article.doi)

        author_reply_doi = get_author_reply_doi(recommendation, round)
        author_reply_url = f"{pci.url}/articles/rec?id={article.id}#ar-{recommendation.id}"
        item_number = ".".join(author_reply_doi.split(".")[-2:])

        xml = render( # type: ignore
            filename=os.path.join(CROSSREF_TEMPLATE_DIR, "author_reply.xml"),
            context=dict(
                he=he,
                crossref=crossref,
                batch_id=batch_id,
                timestamp=timestamp,
                pci=pci,
                round=round - 1,
                authors=authors,
                article_title=_get_article_title(article, round),
                author_reply_date=next_recommendation_date,
                interwork_type=interwork_type,
                interwork_ref=interwork_ref,
                author_reply_doi=author_reply_doi,
                author_reply_url=author_reply_url,
                item_number=item_number
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
            return ReviewElementXML(no_review_round, f"Missing acceptation timestamp for the review {no_review_round} of round {round}", "")

        if not review.last_change:
            return ReviewElementXML(no_review_round, "Missing last_change for the review {no_review_round} of round {round}", "")

        batch_id = f"pci={pci.host}:rec={recommendation.id}:rev={review.id}"

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
        review_date = review.acceptation_timestamp.date()
        interwork_type, interwork_ref = _get_identifier(article.doi)

        review_doi = get_review_doi(recommendation, no_review_round, round)
        review_url = f"{pci.url}/articles/rec?id={article.id}#review-{review.id}"
        item_number = ".".join(review_doi.split(".")[-2:])

        if review.anonymously:
            contributor_tag = '<anonymous contributor_role="reviewer" sequence="first" />'
        else:
            reviewer = User.get_by_id(review.reviewer_id)
            if not reviewer:
                return ReviewElementXML(no_review_round, f"Reviewer with id {review.reviewer_id} not found!", "")

            reviewer_first_name = reviewer.first_name if reviewer.first_name else "?"
            reviewer_last_name = reviewer.last_name if reviewer.last_name else "?"

            contributor_tag = f"""
    <person_name contributor_role="reviewer" sequence="first">
        <given_name>{he(reviewer_first_name)}</given_name>
        <surname>{he(reviewer_last_name)}</surname>
    </person_name>
            """

        article_title = _get_article_title(article, round)
        article_title = f"{article_title}/Reviewer#{no_review_round}"

        xml = render( # type: ignore
            filename=os.path.join(CROSSREF_TEMPLATE_DIR, "review.xml"),
            context=dict(
                he=he,
                crossref=crossref,
                batch_id=batch_id,
                timestamp=timestamp,
                pci=pci,
                round=round - 1,
                contributor_tag=XML(contributor_tag),
                article_title=article_title,
                review_date=review_date,
                interwork_type=interwork_type,
                interwork_ref=interwork_ref,
                review_doi=review_doi,
                review_url=review_url,
                item_number=item_number
            ))

        return ReviewElementXML(no_review_round, cast(str, xml), batch_id)



@dataclass
class CrossrefXML:
    decisions: List[DecisionElementXML]
    author_replies: List[AuthorReplyElementXML]
    reviews: Dict[int, List[ReviewElementXML]]

    def __init__(self):
        self.decisions = []
        self.author_replies = []
        self.reviews = {}


    def get_all_filenames(self):
        filenames: List[str] = []

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


    def raise_error(self):
        for decision in self.decisions:
            if not decision.filename:
                raise XMLException(decision.content)

        for author_reply in self.author_replies:
            if not author_reply.filename:
                raise XMLException(author_reply.content)

        for reviews in self.reviews.values():
            for review in reviews:
                if not review.filename:
                    raise XMLException(review.content)


    @staticmethod
    def build(article: Article):
        recommendations = list(Article.get_last_recommendations(article.id, order_by=current.db.t_recommendations.id))
        all_reviews = Review.get_by_article_id_and_state(article.id,
                                                        ReviewState.REVIEW_COMPLETED,
                                                        order_by=current.db.t_reviews.id)

        total_round = len(recommendations)
        xml = CrossrefXML()

        for i, recommendation in enumerate(recommendations):
            reviews = filter(lambda r: r.recommendation_id == recommendation.id, all_reviews)
            round = Recommendation.get_current_round_number(recommendation)

            if recommendation.recommendation_state != RecommendationState.RECOMMENDED.value:
                next_recommendation = recommendations[i + 1]
                xml_author_reply = AuthorReplyElementXML.build(article, recommendation, round, next_recommendation)
                xml.author_replies.append(xml_author_reply)

            xml_decision= DecisionElementXML.build(article, recommendation, round, total_round)
            xml.decisions.append(xml_decision)

            round_reviews: List[ReviewElementXML] = []
            for j, review in enumerate(reviews):
                xml_review = ReviewElementXML.build(article, recommendation, review, round, j + 1)
                round_reviews.append(xml_review)

            xml.reviews[round] = round_reviews

        return xml


    def get_status(self):
        response = ""

        try:
            filenames = self.get_all_filenames()
            self.raise_error()

            for filename in filenames:
                req = _get_status(filename)
                req.raise_for_status()
                if req.text:
                    response = f"{response.strip()}\n\n===== {filename.strip()} =====\n\n{req.text.strip()}"
        except XMLException as e:
            return f"error: {e}"
        except Exception as e:
            return f"error: {e.__class__.__name__}"

        return response.strip()


    def get_status_code(self):
        status = self.get_status()
        return (
        3 if status.startswith("error:") else
        2 if QUEUED in status else
        1 if FAILED in status else
        0
    )


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

QUEUED = '<doi_batch_diagnostic status="queued"'
FAILED = '<record_diagnostic status="Failure"'


def async_post_to_crossref(article: Article, xml: Optional[CrossrefXML] = None):
    if xml:
        post_to_crossref(article, xml, False)
    else:
        app_name = current.request.application

        python_path = 'python'
        if os.path.isfile('/var/www/venv/bin/python'):
            python_path = '/var/www/venv/bin/python'

        cmd: List[str] = [
            python_path,
            'web2py.py',
            '-M',
            '-S',
            app_name,
            '-R',
            f'applications/{app_name}/utils/send_to_crossref.py',
            '-A',
            str(article.id),
        ]

        p = subprocess.Popen(cmd)
        del p


def post_to_crossref(article: Article, xml: CrossrefXML, check_status: bool = True):
    post_response = _send_xml_to_crossref(xml)

    if check_status:
        count = 0
        status = xml.get_status_code()
        while status == 2: # Wait state skipping QUEUE
            sleep(2)
            status = xml.get_status_code()
            count += 1
            if count == 10:
                break


        if status != 0:
            post_response = _send_xml_to_crossref(xml)

            status = xml.get_status_code()
            count = 0
            while status == 2: # Wait state skipping QUEUE
                sleep(2)
                status = xml.get_status_code()
                count += 1
                if count == 10:
                    break

            if status != 0 or post_response:
                db(db.t_articles.id == article.id).update(show_all_doi=False)
                db.commit()
                return post_response

    if not post_response:
        db(db.t_articles.id == article.id).update(show_all_doi=True)
        db.commit()

    return post_response


def _send_xml_to_crossref(xml: CrossrefXML):
    try:
        xml.raise_error()
        assert crossref.login, "crossref.login not set"

        recommendation = sorted(xml.decisions, key=lambda d: len(d.filename))[0]
        resp = _post(recommendation.content, recommendation.filename)
        resp.raise_for_status()

        for decision in xml.decisions:
            if decision.filename == recommendation.filename:
                continue

            resp = _post(decision.content, decision.filename)
            resp.raise_for_status()

        for author_reply in xml.author_replies:
            resp = _post(author_reply.content, author_reply.filename)
            resp.raise_for_status()

        for _, reviews in xml.reviews.items():
            for review in reviews:
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


def _get_article_title(article: Article, round: int):
    article_title = he(article.title).strip()
    if not article_title.endswith('.'):
        article_title = f"{article_title}."
    article_title = f"{article_title} Round#{round}"
    return article_title


def get_co_recommender_infos(recommendation_id: int):
    co_recommenders_infos: List[Tuple[User, str]] = []
    for row in PressReview.get_by_recommendation(recommendation_id):
        if row.contributor_id:
            co_recommender = User.get_by_id(row.contributor_id)
            if co_recommender:
                co_recommenders_infos.append((co_recommender, User.get_affiliation(co_recommender)))
    return co_recommenders_infos


def get_review_doi(recommendation: Recommendation, no_review_round: int, round: int):
    recommendation_doi = _get_recommendation_doi(recommendation)
    return f"{recommendation_doi}.rev{round}{no_review_round}"


def get_author_reply_doi(recommendation: Recommendation, round: int):
    recommendation_doi = _get_recommendation_doi(recommendation)
    return f"{recommendation_doi}.ar{round}"


def get_decision_doi(recommendation: Recommendation, round: int):
    recommendation_doi = _get_recommendation_doi(recommendation)
    return f"{recommendation_doi}.d{round}"
