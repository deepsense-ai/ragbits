from collections.abc import Callable

import pytest

from ragbits.core.audit import _get_function_inputs


@pytest.mark.parametrize(
    ("func", "args", "kwargs", "expected"),
    [
        # Test no args and no kwargs
        (lambda: None, (), {}, {}),
        # Test only args
        (lambda a, b: None, (1, 2), {}, {"a": 1, "b": 2}),
        # Test only kwargs
        (lambda a, b: None, (), {"a": 1, "b": 2}, {"a": 1, "b": 2}),
        # Test args and kwargs
        (lambda a, b, c: None, (1,), {"b": 2, "c": 3}, {"a": 1, "b": 2, "c": 3}),
        # Test with defaults
        (lambda a, b=2: None, (1,), {}, {"a": 1, "b": 2}),
        # Test extra kwargs
        (lambda a: None, (), {"a": 1, "b": 2}, {"a": 1, "b": 2}),
        # Test empty signature
        (lambda: None, (1, 2, 3), {"a": 1, "b": 2}, {"a": 1, "b": 2}),
        # Test *args
        (lambda *args: None, (1, 2, 3), {}, {}),
        # Test **kwargs
        (lambda **kwargs: None, (), {"a": 1, "b": 2}, {"a": 1, "b": 2}),
        # Test args, kwargs, and defaults
        (lambda a, b=2, c=3: None, (1,), {"c": 4}, {"a": 1, "b": 2, "c": 4}),
    ],
)
def test_get_function_inputs(func: Callable, args: tuple, kwargs: dict, expected: dict) -> None:
    result = _get_function_inputs(func, args, kwargs)
    assert result == expected
