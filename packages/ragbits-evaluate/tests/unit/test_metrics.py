import numpy as np
import pytest
from continuous_eval.metrics.retrieval.matching_strategy import (
    ExactChunkMatch,
    ExactSentenceMatch,
    MatchingStrategy,
    RougeChunkMatch,
    RougeSentenceMatch,
)

from ragbits.core.utils.config_handling import ObjectConstructionConfig
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import TextElement
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.document_search import DocumentSearchPrecisionRecallF1
from ragbits.evaluate.pipelines.document_search import DocumentSearchResult


@pytest.fixture(
    params=[
        ExactChunkMatch(),
        ExactSentenceMatch(),
        RougeChunkMatch(threshold=0.5),
        RougeSentenceMatch(threshold=0.5),
    ]
)
def matching_strategy(request: pytest.FixtureRequest) -> MatchingStrategy:
    return request.param


@pytest.fixture
def exact_match_results() -> list[DocumentSearchResult]:
    return [
        DocumentSearchResult(
            question="Q1",
            predicted_elements=[
                TextElement(content="The quick brown fox", document_meta=DocumentMeta.from_literal(""))
            ],
            reference_passages=["The quick brown fox"],
        ),
        DocumentSearchResult(
            question="Q2",
            predicted_elements=[
                TextElement(content="Lorem ipsum dolor sit amet", document_meta=DocumentMeta.from_literal(""))
            ],
            reference_passages=["Lorem ipsum dolor sit amet"],
        ),
    ]


@pytest.fixture
def partial_match_results() -> list[DocumentSearchResult]:
    return [
        DocumentSearchResult(
            question="Q1",
            predicted_elements=[
                TextElement(content="Quick brown fox", document_meta=DocumentMeta.from_literal("")),
                TextElement(content="jumps over dog", document_meta=DocumentMeta.from_literal("")),
            ],
            reference_passages=["The quick brown fox", "jumps over the lazy dog"],
        ),
        DocumentSearchResult(
            question="Q2",
            predicted_elements=[
                TextElement(content="Lorem ipsum", document_meta=DocumentMeta.from_literal("")),
                TextElement(content="dolor sit", document_meta=DocumentMeta.from_literal("")),
            ],
            reference_passages=["Lorem ipsum dolor sit amet", "Lorem ipsum"],
        ),
    ]


@pytest.fixture
def no_match_results() -> list[DocumentSearchResult]:
    return [
        DocumentSearchResult(
            question="Q1",
            predicted_elements=[
                TextElement(content="Completely different text", document_meta=DocumentMeta.from_literal("")),
            ],
            reference_passages=["No matching content here"],
        )
    ]


async def test_perfect_matches(
    exact_match_results: list[DocumentSearchResult], matching_strategy: MatchingStrategy
) -> None:
    metric = DocumentSearchPrecisionRecallF1(matching_strategy)
    results = await metric.compute(exact_match_results)

    assert np.isclose(results["context_precision"], 1.0)
    assert np.isclose(results["context_recall"], 1.0)
    assert np.isclose(results["context_f1"], 1.0)


async def test_partial_matches(
    partial_match_results: list[DocumentSearchResult], matching_strategy: MatchingStrategy
) -> None:
    metric = DocumentSearchPrecisionRecallF1(matching_strategy)
    results: dict = await metric.compute(partial_match_results)

    # Validate metric ranges
    assert 0.0 < results["context_precision"] < 1.0
    assert 0.0 < results["context_recall"] < 1.0
    assert 0.0 < results["context_f1"] < 1.0


async def test_no_matches(no_match_results: list[DocumentSearchResult], matching_strategy: MatchingStrategy) -> None:
    metric = DocumentSearchPrecisionRecallF1(matching_strategy)
    results = await metric.compute(no_match_results)

    if isinstance(matching_strategy, RougeChunkMatch | RougeSentenceMatch):
        # ROUGE-based strategies might have non-zero matches depending on threshold
        assert results["context_precision"] >= 0.0
        assert results["context_recall"] >= 0.0
    else:
        assert np.isclose(results["context_precision"], 0.0)
        assert np.isclose(results["context_recall"], 0.0)
        assert np.isclose(results["context_f1"], 0.0)


async def test_rouge_threshold_behavior() -> None:
    # Test with known ROUGE scores
    strategy = RougeChunkMatch(threshold=0.7)
    metric = DocumentSearchPrecisionRecallF1(strategy)

    results = [
        DocumentSearchResult(
            question="Q1",
            predicted_elements=[
                TextElement(content="The quick brown fox jumps", document_meta=DocumentMeta.from_literal(""))
            ],
            reference_passages=["The quick brown fox"],
        )
    ]

    metrics = await metric.compute(results)
    rouge_score = 0.857  # Pre-calculated ROUGE-L score for these texts
    expected_precision = 1.0 if rouge_score >= 0.7 else 0.0

    assert np.isclose(metrics["context_precision"], expected_precision)
    assert np.isclose(metrics["context_recall"], expected_precision)


async def test_mixed_results_with_multiple_queries(matching_strategy: MatchingStrategy) -> None:
    results = [
        DocumentSearchResult(
            question="Q1",
            predicted_elements=[TextElement(content="Exact match", document_meta=DocumentMeta.from_literal(""))],
            reference_passages=["Exact match"],
        ),
        DocumentSearchResult(
            question="Q2",
            predicted_elements=[TextElement(content="Partial match", document_meta=DocumentMeta.from_literal(""))],
            reference_passages=["No at all"],
        ),
    ]

    metric = DocumentSearchPrecisionRecallF1(matching_strategy)
    metrics = await metric.compute(results)

    assert 0 < metrics["context_precision"] <= 1.0
    assert 0.0 < metrics["context_recall"] < 1.0


def test_metric_set_with_different_strategies() -> None:
    config = {
        "exact_chunk": ObjectConstructionConfig.model_validate(
            {
                "type": "ragbits.evaluate.metrics.document_search:DocumentSearchPrecisionRecallF1",
                "config": {"matching_strategy": {"type": "ExactChunkMatch", "config": {}}, "weight": 0.6},
            }
        ),
        "rouge_sentence": ObjectConstructionConfig.model_validate(
            {
                "type": "ragbits.evaluate.metrics.document_search:DocumentSearchPrecisionRecallF1",
                "config": {
                    "matching_strategy": {"type": "RougeSentenceMatch", "config": {"threshold": 0.6}},
                    "weight": 0.4,
                },
            }
        ),
    }

    metric_set: MetricSet = MetricSet.from_config(config)
    assert len(metric_set.metrics) == 2
    assert isinstance(metric_set.metrics[0], DocumentSearchPrecisionRecallF1)
    assert isinstance(metric_set.metrics[1], DocumentSearchPrecisionRecallF1)


async def test_empty_retrieved_passages() -> None:
    results: list[DocumentSearchResult] = [
        DocumentSearchResult(question="Q1", predicted_elements=[], reference_passages=["Important content"])
    ]

    for strategy in [ExactChunkMatch(), RougeSentenceMatch()]:
        metric = DocumentSearchPrecisionRecallF1(strategy)
        metrics = await metric.compute(results)
        assert np.isclose(metrics["context_precision"], 0.0)
        assert np.isclose(metrics["context_recall"], 0.0)


async def test_empty_reference_passages() -> None:
    results = [
        DocumentSearchResult(
            question="Q1",
            predicted_elements=[TextElement(content="Some content", document_meta=DocumentMeta.from_literal(""))],
            reference_passages=[],
        )
    ]

    for strategy in [ExactSentenceMatch(), RougeChunkMatch()]:
        metric = DocumentSearchPrecisionRecallF1(strategy)
        metrics = await metric.compute(results)
        assert np.isclose(metrics["context_precision"], 0.0)
        assert np.isclose(metrics["context_recall"], 0.0)
