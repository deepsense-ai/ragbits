import pytest

from ragbits.core.utils.helpers import batched


@pytest.mark.parametrize(
    ("input_data", "batch_size", "expected"),
    [
        ([], 3, []),
        ([], None, []),
        ([1, 2, 3], None, [[1, 2, 3]]),
        ([1, 2, 3], 5, [[1, 2, 3]]),
        ([1, 2, 3], 3, [[1, 2, 3]]),
        ([1, 2, 3, 4, 5, 6], 2, [[1, 2], [3, 4], [5, 6]]),
        ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
    ],
    ids=[
        "empty_iterable",
        "none_batch_size",
        "none_batch_size_with_remainder",
        "batch_size_larger_than_data",
        "batch_size_equal_to_data",
        "batch_size_divides_data_evenly",
        "batch_size_with_remainder",
    ],
)
def test_batched(input_data: list[int], batch_size: int, expected: list[list[int]]) -> None:
    result = list(batched(input_data, batch_size))
    assert result == expected
