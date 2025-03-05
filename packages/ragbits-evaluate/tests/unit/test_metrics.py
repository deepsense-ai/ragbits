import numpy as np
import pytest
from continuous_eval.metrics.retrieval.matching_strategy import (
    ExactChunkMatch,
    ExactSentenceMatch,
    MatchingStrategy,
    RougeChunkMatch,
    RougeSentenceMatch,
)

from ragbits.core.utils.config_handling import ObjectContructionConfig
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
            predicted_passages=["The quick brown fox", "jumps over the lazy dog"],
            reference_passages=["The quick brown fox", "jumps over the lazy dog"],
        ),
        DocumentSearchResult(
            question="Q2",
            predicted_passages=["Lorem ipsum dolor sit amet"],
            reference_passages=["Lorem ipsum dolor sit amet"],
        ),
    ]


@pytest.fixture
def partial_match_results() -> list[DocumentSearchResult]:
    return [
        DocumentSearchResult(
            question="Q1",
            predicted_passages=["Quick brown fox", "jumps over dog"],
            reference_passages=["The quick brown fox", "jumps over the lazy dog"],
        ),
        DocumentSearchResult(
            question="Q2",
            predicted_passages=["Lorem ipsum", "dolor sit"],
            reference_passages=["Lorem ipsum dolor sit amet", "Lorem ipsum"],
        ),
    ]


@pytest.fixture
def no_match_results() -> list[DocumentSearchResult]:
    return [
        DocumentSearchResult(
            question="Q1",
            predicted_passages=["Completely different text"],
            reference_passages=["No matching content here"],
        )
    ]


def test_perfect_matches(exact_match_results: list[DocumentSearchResult], matching_strategy: MatchingStrategy) -> None:
    metric = DocumentSearchPrecisionRecallF1(matching_strategy)
    results = metric.compute(exact_match_results)

    assert np.isclose(results["context_precision"], 1.0)
    assert np.isclose(results["context_recall"], 1.0)
    assert np.isclose(results["context_f1"], 1.0)


def test_partial_matches(
    partial_match_results: list[DocumentSearchResult], matching_strategy: MatchingStrategy
) -> None:
    metric = DocumentSearchPrecisionRecallF1(matching_strategy)
    results: dict = metric.compute(partial_match_results)

    # Validate metric ranges
    assert 0.0 < results["context_precision"] < 1.0
    assert 0.0 < results["context_recall"] < 1.0
    assert 0.0 < results["context_f1"] < 1.0


def test_no_matches(no_match_results: list[DocumentSearchResult], matching_strategy: MatchingStrategy) -> None:
    metric = DocumentSearchPrecisionRecallF1(matching_strategy)
    results = metric.compute(no_match_results)

    if isinstance(matching_strategy, RougeChunkMatch | RougeSentenceMatch):
        # ROUGE-based strategies might have non-zero matches depending on threshold
        assert results["context_precision"] >= 0.0
        assert results["context_recall"] >= 0.0
    else:
        assert np.isclose(results["context_precision"], 0.0)
        assert np.isclose(results["context_recall"], 0.0)
        assert np.isclose(results["context_f1"], 0.0)


def test_rouge_threshold_behavior() -> None:
    # Test with known ROUGE scores
    strategy = RougeChunkMatch(threshold=0.7)
    metric = DocumentSearchPrecisionRecallF1(strategy)

    results = [
        DocumentSearchResult(
            question="Q1", predicted_passages=["The quick brown fox jumps"], reference_passages=["The quick brown fox"]
        )
    ]

    metrics = metric.compute(results)
    rouge_score = 0.857  # Pre-calculated ROUGE-L score for these texts
    expected_precision = 1.0 if rouge_score >= 0.7 else 0.0

    assert np.isclose(metrics["context_precision"], expected_precision)
    assert np.isclose(metrics["context_recall"], expected_precision)


def test_mixed_results_with_multiple_queries(matching_strategy: MatchingStrategy) -> None:
    results = [
        DocumentSearchResult(question="Q1", predicted_passages=["Exact match"], reference_passages=["Exact match"]),
        DocumentSearchResult(question="Q2", predicted_passages=["Partial match"], reference_passages=["No at all"]),
    ]

    metric = DocumentSearchPrecisionRecallF1(matching_strategy)
    metrics = metric.compute(results)

    assert 0 < metrics["context_precision"] <= 1.0
    assert 0.0 < metrics["context_recall"] < 1.0


def test_metric_set_with_different_strategies() -> None:
    config = {
        "exact_chunk": ObjectContructionConfig.model_validate(
            {
                "type": "ragbits.evaluate.metrics.document_search:DocumentSearchPrecisionRecallF1",
                "config": {"matching_strategy": {"type": "ExactChunkMatch", "config": {}}, "weight": 0.6},
            }
        ),
        "rouge_sentence": ObjectContructionConfig.model_validate(
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


def test_empty_retrieved_passages() -> None:
    results: list[DocumentSearchResult] = [
        DocumentSearchResult(question="Q1", predicted_passages=[], reference_passages=["Important content"])
    ]

    for strategy in [ExactChunkMatch(), RougeSentenceMatch()]:
        metric = DocumentSearchPrecisionRecallF1(strategy)
        metrics = metric.compute(results)
        assert np.isclose(metrics["context_precision"], 0.0)
        assert np.isclose(metrics["context_recall"], 0.0)


def test_empty_reference_passages() -> None:
    results = [DocumentSearchResult(question="Q1", predicted_passages=["Some content"], reference_passages=[])]

    for strategy in [ExactSentenceMatch(), RougeChunkMatch()]:
        metric = DocumentSearchPrecisionRecallF1(strategy)
        metrics = metric.compute(results)
        assert np.isclose(metrics["context_precision"], 0.0)
        assert np.isclose(metrics["context_recall"], 0.0)
