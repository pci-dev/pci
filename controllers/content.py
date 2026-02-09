from dataclasses import dataclass
import re

from gluon.contrib.markdown import WIKI
from gluon.http import HTTP  # type: ignore

from models.recommendation import Recommendation
from models.review import Review

@dataclass(frozen=True)
class DecodedDecisionRequest:
    recommendation_doi: str
    round_number: int

@dataclass(frozen=True)
class DecodedAuthorResponseRequest:
    recommendation_doi: str
    round_number: int

@dataclass(frozen=True)
class DecodedReviewRequest:
    recommendation_doi: str
    round_number: int
    evaluation_number: int

@dataclass(frozen=True)
class DecodedRecommendationRequest:
    recommendation_doi: str


DecodedRequest = DecodedDecisionRequest | DecodedAuthorResponseRequest | DecodedReviewRequest | DecodedRecommendationRequest

# We assume there are never more than nine review rounds
def _decode_evaluation_doi(path: str) -> DecodedRequest:
    match = re.match(r"^(.*)\.(rev|d|ar)(\d)?(\d*)$", path)
    if not match:
        return DecodedRecommendationRequest(
            recommendation_doi=path
        )
    recommendation_doi, evaluation_type, round_number, evaluation_number = (
        match.groups()
    )
    if evaluation_type == "d":
        if evaluation_number or not round_number:
            raise HTTP(400, "Invalid DOI")
        return DecodedDecisionRequest(
            recommendation_doi=recommendation_doi,
            round_number=int(round_number),
        )
    if evaluation_type == "ar":
        if evaluation_number or not round_number:
            raise HTTP(400, "Invalid DOI")
        return DecodedAuthorResponseRequest(
            recommendation_doi=recommendation_doi,
            round_number=int(round_number)
        )
    if evaluation_type == "rev":
        if not evaluation_number:
            raise HTTP(400, "Invalid DOI")
        if len(evaluation_number) != 1:
            raise HTTP(400, "Invalid DOI due to ambiguity")
        return DecodedReviewRequest(
            recommendation_doi=recommendation_doi,
            round_number=int(round_number),
            evaluation_number=int(evaluation_number)
        )
    # This should never happen due to regular expression
    raise HTTP(400, "Unable to decode request")


def _get_markdown_content_based_on_evaluation_type(decoded_request: DecodedRequest):
    recommendations = Recommendation.get_by_doi(decoded_request.recommendation_doi)
    if not recommendations:
        raise HTTP(404, "No recommendations found for given DOI")
    match decoded_request:
        case DecodedDecisionRequest():
            if len(recommendations) < decoded_request.round_number:
                raise HTTP(404, "Requested round does not exist")
            review_round_decision = recommendations[decoded_request.round_number - 1]
            return review_round_decision.recommendation_comments
        case DecodedAuthorResponseRequest():
            if len(recommendations) < decoded_request.round_number:
                raise HTTP(404, "Requested round does not exist")
            review_round_decision = recommendations[decoded_request.round_number - 1]
            return review_round_decision.reply
        case DecodedReviewRequest():
            if len(recommendations) < decoded_request.round_number:
                raise HTTP(404, "Requested round does not exist")
            relevant_recommendation = recommendations[decoded_request.round_number - 1]
            reviews_for_recommendation_descending = Review.get_by_recommendation_id(relevant_recommendation.id)
            if len(reviews_for_recommendation_descending) < decoded_request.evaluation_number:
                raise HTTP(404, "Requested review does not exist")
            review_location_in_the_array = decoded_request.evaluation_number - 1
            relevant_review = reviews_for_recommendation_descending[review_location_in_the_array]
            return relevant_review.review
        case DecodedRecommendationRequest():
            last_recommendation = recommendations[-1]
            return last_recommendation.recommendation_comments
    # This should never happen because we have handled all possible types
    return None


def doi():
    if request.args is None:
        return HTTP(400, "No DOI supplied")

    path_param = "/".join(request.args)
    decodedRequest = _decode_evaluation_doi(path_param)
    if decodedRequest is None:
        raise HTTP(400, "Invalid DOI")

    markdown_content = _get_markdown_content_based_on_evaluation_type(decodedRequest)
    markdown_content = markdown_content or "Review text not available."

    contentAsHtml = WIKI(markdown_content, safe_mode="")

    return contentAsHtml
