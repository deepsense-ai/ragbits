from datetime import datetime

import pytest

from ragbits.core.audit.otel import _format_attributes


@pytest.mark.parametrize(
    ("input_data", "prefix", "expected"),
    [
        # Empty dict
        ({}, None, {}),
        ({}, "test", {}),
        # Simple types
        (
            {"str": "value", "int": 42, "float": 3.14, "bool": True},
            None,
            {"str": "value", "int": 42, "float": 3.14, "bool": True},
        ),
        # With prefix
        ({"str": "value", "int": 42}, "prefix", {"prefix.str": "value", "prefix.int": 42}),
        # Nested dict
        ({"nested": {"key1": "value1", "key2": 42}}, None, {"nested.key1": "value1", "nested.key2": 42}),
        # Lists and tuples
        ({"list": [1, 2, 3], "tuple": ("a", "b", "c")}, None, {"list": [1, 2, 3], "tuple": ["a", "b", "c"]}),
        # Complex objects in lists
        (
            {"objects": [{"a": 1}, datetime(2023, 1, 1)]},
            None,
            {"objects": ["{'a': 1}", "datetime.datetime(2023, 1, 1, 0, 0)"]},
        ),
        # Mixed nested structure
        (
            {"level1": {"level2": {"string": "value", "list": [1, {"x": "y"}]}}},
            "test",
            {"test.level1.level2.string": "value", "test.level1.level2.list": [1, "{'x': 'y'}"]},
        ),
    ],
)
def test_format_attributes(input_data: dict, prefix: str, expected: dict) -> None:
    result = _format_attributes(input_data, prefix)
    assert result == expected
