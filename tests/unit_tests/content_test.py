from dataclasses import dataclass
from typing import Iterator, Optional, Any
from unittest.mock import MagicMock, patch

import pytest
from gluon.http import HTTP  # type: ignore

import controllers.content as controllers_module
from controllers.content import (
    DecodedAuthorResponseRequest,
    DecodedRecommendationRequest,
    DecodedDecisionRequest,
    DecodedReviewRequest,
    _decode_evaluation_doi,
    _get_markdown_content_based_on_evaluation_type,
)

@dataclass(frozen=True)
class RecommendationMock:
    recommendation_comments: Optional[str] = None
    reply: Optional[str] = None
    id: int = 1


@dataclass(frozen=True)
class ReviewMock:
    review: Optional[str] = None

@pytest.fixture(name="recommendation_class_mock")
def _recommendation_class_mock() -> Iterator[MagicMock]:
    with patch.object(controllers_module, "Recommendation") as mock:
        yield mock


@pytest.fixture(name="review_class_mock")
def _review_class_mock() -> Iterator[MagicMock]:
    with patch.object(controllers_module, "Review") as mock:
        yield mock


class TestDecodeEvaluationDoi:
    def test_should_raise_exception_for_decisions_without_round_number(
            self
        ):
            with pytest.raises(HTTP):
                _decode_evaluation_doi("10.1234/xyz.d")

    def test_should_raise_exception_for_decisions_that_have_evaluation_number(
            self
        ):
            with pytest.raises(HTTP):
                _decode_evaluation_doi("10.1234/xyz.d13")

    def test_should_raise_exception_for_author_response_that_have_evaluation_number(
            self
        ):
            with pytest.raises(HTTP):
                _decode_evaluation_doi("10.1234/xyz.ar13")

    def test_should_raise_error_if_requested_evaluation_number_is_empty(
            self,
        ):
            with pytest.raises(HTTP):
                _decode_evaluation_doi("10.1234/xyz.rev1")

    def test_should_raise_error_if_requested_rev_with_three_digits_due_to_ambiguity(
            self,
        ):
            with pytest.raises(HTTP):
                _decode_evaluation_doi("10.1234/xyz.rev111")

class TestGetMarkdownContentBasedOnEvaluationType:
    @pytest.mark.parametrize(
        "case",
        [
            {
                "path": "10.1234/xyz.rev12",
                "expected": DecodedReviewRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=1,
                    evaluation_number=2,
                ),
            },
            {
                "path": "10.1234/xyz.d1",
                "expected": DecodedDecisionRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=1
                ),
            },
            {
                "path": "10.1234/xyz.ar3",
                "expected": DecodedAuthorResponseRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=3
                ),
            },
            {
                "path": "10.1234/xyz",
                "expected": DecodedRecommendationRequest(
                    recommendation_doi="10.1234/xyz"
                ),
            },
        ],
        ids=lambda c: c["path"]
    )
    def test_decode_evaluation_doi(self, case):
        result = _decode_evaluation_doi(case["path"])
        assert result == case["expected"]

    def test_should_pass_doi_to_get_by_doi_function(
        self,
        recommendation_class_mock: MagicMock,
    ):
        _get_markdown_content_based_on_evaluation_type(
            DecodedReviewRequest(
                recommendation_doi="10.1234/xyz",
                round_number=1,
                evaluation_number=2,
            )
        )
        recommendation_class_mock.get_by_doi.assert_called_once_with("10.1234/xyz")

    def test_should_return_raise_error_if_there_are_no_recommendations_expressed_as_none(
        self,
        recommendation_class_mock: MagicMock,
    ):
        recommendation_class_mock.get_by_doi.return_value = None
        with pytest.raises(HTTP):
            _get_markdown_content_based_on_evaluation_type(
            DecodedReviewRequest(
                recommendation_doi="10.1234/xyz",
                round_number=1,
                evaluation_number=2,
            )
        )

    def test_should_return_raise_error_if_there_are_no_recommendations_expressed_as_an_empty_list(
        self,
        recommendation_class_mock: MagicMock,
    ):
        recommendation_class_mock.get_by_doi.return_value = []
        with pytest.raises(HTTP):
            _get_markdown_content_based_on_evaluation_type(
            DecodedReviewRequest(
                recommendation_doi="10.1234/xyz",
                round_number=1,
                evaluation_number=2,
            )
        )

    class TestDecisionType:
        def test_requested_round_does_not_exist(
            self,
            recommendation_class_mock: MagicMock,
        ):
            recommendation_class_mock.get_by_doi.return_value = [{}]
            result = _get_markdown_content_based_on_evaluation_type(
                DecodedDecisionRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=2
                )
            )
            assert result is None

        def test_recommendation_comments_of_rounds_before_the_last_are_the_decision_content(
            self,
            recommendation_class_mock: MagicMock,
        ):
            recommendation_class_mock.get_by_doi.return_value = [
                RecommendationMock(),
                RecommendationMock(recommendation_comments="Foo bar"),
                RecommendationMock()
            ]
            result = _get_markdown_content_based_on_evaluation_type(
                DecodedDecisionRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=2
                )
            )
            assert result == "Foo bar"

    class TestAuthorResponseType:
        def test_should_return_none_if_requested_round_does_not_exist(
            self,
            recommendation_class_mock: MagicMock,
        ):
            recommendation_class_mock.get_by_doi.return_value = [{}]
            result = _get_markdown_content_based_on_evaluation_type(
                DecodedAuthorResponseRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=2
                )
            )
            assert result is None

        def test_recommendation_comments_of_rounds_before_the_last_are_the_author_response_content(
            self,
            recommendation_class_mock: MagicMock,
        ):
            recommendation_class_mock.get_by_doi.return_value = [
                RecommendationMock(),
                RecommendationMock(reply="Foo bar"),
                RecommendationMock()
            ]
            result = _get_markdown_content_based_on_evaluation_type(
                DecodedAuthorResponseRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=2
                )
            )
            assert result == "Foo bar"

    class TestReviewType:
        def test_should_pass_recommendation_id_to_get_by_recommendation_id_function(
            self,
            recommendation_class_mock: MagicMock,
            review_class_mock: MagicMock,
        ):
            expected_recommendation = RecommendationMock(id=42)
            recommendation_class_mock.get_by_doi.return_value = [
                expected_recommendation
            ]
            _get_markdown_content_based_on_evaluation_type(
                DecodedReviewRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=1,
                    evaluation_number=2,
                )
            )
            review_class_mock.get_by_recommendation_id.assert_called_once_with(expected_recommendation.id)

        def test_should_return_none_if_requested_round_does_not_exist(
            self,
            recommendation_class_mock: MagicMock,
        ):
            recommendation_class_mock.get_by_doi.return_value = [{}]
            result = _get_markdown_content_based_on_evaluation_type(
                DecodedReviewRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=2,
                    evaluation_number=1,
                )
            )
            assert result is None

        def test_should_return_none_if_requested_evaluation_number_does_not_exist(
            self,
            recommendation_class_mock: MagicMock,
            review_class_mock: MagicMock
        ):
            recommendation_class_mock.get_by_doi.return_value = [
                RecommendationMock(id=2)
            ]
            review_class_mock.get_by_recommendation_id.return_value = [{}]
            result = _get_markdown_content_based_on_evaluation_type(
                DecodedReviewRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=1,
                    evaluation_number=2,
                )
            )
            assert result is None

        def test_should_return_review_content_of_requested_evaluation_number_and_round_number(
            self,
            recommendation_class_mock: MagicMock,
            review_class_mock: MagicMock
        ):
            recommendation_class_mock.get_by_doi.return_value = [
                RecommendationMock(id=2)
            ]
            review_class_mock.get_by_recommendation_id.return_value = [
                ReviewMock(review="First review"),
                ReviewMock(review="Second review"),
            ]
            result = _get_markdown_content_based_on_evaluation_type(
                DecodedReviewRequest(
                    recommendation_doi="10.1234/xyz",
                    round_number=1,
                    evaluation_number=2,
                )
            )
            assert result == "Second review"

    class TestRecommendationType:
        def test_should_return_recommendation_content_when_no_evalation_or_round_number_is_present(
                self,
                recommendation_class_mock: MagicMock,
        ):
            recommendation_class_mock.get_by_doi.return_value = [
                RecommendationMock(recommendation_comments="First decision content"),
                RecommendationMock(recommendation_comments="Second decision content"),
                RecommendationMock(recommendation_comments="Third decision content"),
                RecommendationMock(recommendation_comments="Final recommendation content"),
            ]
            result = _get_markdown_content_based_on_evaluation_type(
                DecodedRecommendationRequest(recommendation_doi="10.1234/xyz")
            )
            assert result == "Final recommendation content"
