import uuid
from collections import defaultdict

import pytest

from ragbits.core.vector_stores.base import VectorStoreEntry, VectorStoreResult
from ragbits.core.vector_stores.hybrid_strategies import (
    DistributionBasedScoreFusion,
    HybridRetrivalStrategy,
    OrderedHybridRetrivalStrategy,
    ReciprocalRankFusion,
)


@pytest.fixture(name="vs_results")
def vs_results_fixture() -> list[list[VectorStoreResult]]:
    entries = [
        VectorStoreEntry(id=uuid.UUID(int=0), text="foo", image_bytes=b"foo", metadata={"foo": "foo"}),
        VectorStoreEntry(id=uuid.UUID(int=1), text="bar"),
        VectorStoreEntry(id=uuid.UUID(int=2), text="baz"),
        VectorStoreEntry(id=uuid.UUID(int=3), text="qux"),
        VectorStoreEntry(id=uuid.UUID(int=4), text="quux"),
        VectorStoreEntry(id=uuid.UUID(int=5), text="corge"),
    ]
    results = [
        [
            VectorStoreResult(entry=entries[0], vector=[1, 2, 3], score=0.95),
            VectorStoreResult(entry=entries[1], vector=[2, 3, 4], score=0.8),
            VectorStoreResult(entry=entries[2], vector=[3, 4, 5], score=0.7),
        ],
        [
            VectorStoreResult(entry=entries[1], vector=[2, 3, 4], score=1.0),
            VectorStoreResult(entry=entries[2], vector=[3, 4, 5], score=0.5),
            VectorStoreResult(entry=entries[3], vector=[4, 5, 6], score=0.6),
        ],
        [
            VectorStoreResult(entry=entries[3], vector=[4, 5, 6], score=0.9),
            VectorStoreResult(entry=entries[4], vector=[5, 6, 7], score=0.1),
            VectorStoreResult(entry=entries[5], vector=[6, 7, 8], score=-10.0),
        ],
    ]
    return results


# HybridRetrivalStrategy instance, expected order of results, expected scores
cases = [
    (OrderedHybridRetrivalStrategy(sum_scores=False), [1, 0, 3, 2, 4, 5], [1.0, 0.95, 0.9, 0.7, 0.1, -10.0]),
    (OrderedHybridRetrivalStrategy(sum_scores=True), [1, 3, 2, 0, 4, 5], [1.8, 1.5, 1.2, 0.95, 0.1, -10.0]),
    (ReciprocalRankFusion(sum_scores=False, k_constant=0), [0, 1, 3, 2, 4, 5], [1.0, 1.0, 1.0, 0.5, 0.5, 0.3333]),
    (ReciprocalRankFusion(k_constant=0), [1, 3, 0, 2, 4, 5], [1.5, 1.3333, 1.0, 0.8333, 0.5, 0.3333]),
    (ReciprocalRankFusion(k_constant=60), [1, 3, 2, 0, 4, 5], [0.0325, 0.0323, 0.0320, 0.0164, 0.0161, 0.0159]),
    (
        DistributionBasedScoreFusion(sum_scores=False),
        [1, 0, 3, 4, 2, 5],
        [0.7315, 0.7163, 0.6310, 0.6042, 0.3457, 0.2648],
    ),
    (
        DistributionBasedScoreFusion(sum_scores=True),
        [1, 3, 0, 2, 4, 5],
        [1.2044, 1.0539, 0.7163, 0.6564, 0.6042, 0.2648],
    ),
]


@pytest.mark.parametrize(("strategy", "expected_order", "expected_scores"), cases)
async def test_hybrid_strategies(
    vs_results: list[list[VectorStoreResult]],
    strategy: HybridRetrivalStrategy,
    expected_order: list[int],
    expected_scores: list[float],
):
    # Create a dictionary mapping entry IDs to the expected results for that entry
    expected_results_by_id = defaultdict(list)
    for result_list in vs_results:
        for result in result_list:
            expected_results_by_id[result.entry.id].append(result)

    merged_results = strategy.join(vs_results)

    prev_score = float("inf")
    for result, expected_index, expected_score in zip(merged_results, expected_order, expected_scores, strict=True):
        expected_id = uuid.UUID(int=expected_index)
        expected_results = expected_results_by_id[expected_id]
        assert result.entry.id == expected_id
        assert result.vector == expected_results[0].vector
        assert result.entry == expected_results[0].entry
        assert result.score == pytest.approx(expected_score, rel=1e-2)
        assert len(result.subresults) == len(expected_results)
        for subresult in result.subresults:
            assert subresult in expected_results

        # Check that the results are ordered by score
        assert result.score <= prev_score
        prev_score = result.score
