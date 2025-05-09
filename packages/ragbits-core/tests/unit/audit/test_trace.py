import asyncio
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ragbits.core.audit.traces import _get_function_inputs, set_trace_handlers, trace, traceable
from ragbits.core.audit.traces.base import AttributeFormatter, TraceHandler
from ragbits.core.vector_stores import VectorStoreEntry


class MockTraceHandler(TraceHandler):
    def start(self, name: str, inputs: dict, current_span: None = None) -> None:
        pass

    def stop(self, outputs: dict, current_span: None) -> None:
        pass

    def error(self, error: Exception, current_span: None) -> None:
        pass


@pytest.fixture
def mock_handler() -> MockTraceHandler:
    handler = MockTraceHandler()
    set_trace_handlers(handler)
    return handler


def test_trace_context_with_name(mock_handler: MockTraceHandler) -> None:
    current_span = MagicMock()
    mock_handler.start = MagicMock(return_value=current_span)  # type: ignore
    mock_handler.stop = MagicMock()  # type: ignore
    mock_handler.error = MagicMock()  # type: ignore

    with trace(name="test", input1="value1") as outputs:
        outputs.result = "success"

    mock_handler.start.assert_called_once_with(name="test", inputs={"input1": "value1"}, current_span=None)
    mock_handler.stop.assert_called_once_with(outputs={"result": "success"}, current_span=current_span)
    mock_handler.error.assert_not_called()


def test_trace_context_without_name(mock_handler: MockTraceHandler) -> None:
    current_span = MagicMock()
    mock_handler.start = MagicMock(return_value=current_span)  # type: ignore
    mock_handler.stop = MagicMock()  # type: ignore
    mock_handler.error = MagicMock()  # type: ignore

    with trace() as outputs:
        outputs.result = "success"

    mock_handler.start.assert_called_once_with(name="test_trace_context_without_name", inputs={}, current_span=None)
    mock_handler.stop.assert_called_once_with(outputs={"result": "success"}, current_span=current_span)
    mock_handler.error.assert_not_called()


def test_trace_context_exception(mock_handler: MockTraceHandler) -> None:
    current_span = MagicMock()
    mock_handler.start = MagicMock(return_value=current_span)  # type: ignore
    mock_handler.stop = MagicMock()  # type: ignore
    mock_handler.error = MagicMock()  # type: ignore

    with pytest.raises(ValueError), trace(name="test"):
        raise (error := ValueError("test error"))

    mock_handler.start.assert_called_once_with(name="test", inputs={}, current_span=None)
    mock_handler.error.assert_called_once_with(error=error, current_span=current_span)
    mock_handler.stop.assert_not_called()


def test_traceable_sync(mock_handler: MockTraceHandler) -> None:
    current_span = MagicMock()
    mock_handler.start = MagicMock(return_value=current_span)  # type: ignore
    mock_handler.stop = MagicMock()  # type: ignore
    mock_handler.error = MagicMock()  # type: ignore

    @traceable
    def sample_sync_function(a: int, b: str = "default") -> str:
        return f"{a}-{b}"

    result = sample_sync_function(1, b="test")
    assert result == "1-test"

    mock_handler.start.assert_called_once_with(
        name="test_traceable_sync.<locals>.sample_sync_function",
        inputs={"a": 1, "b": "test"},
        current_span=None,
    )
    mock_handler.stop.assert_called_once_with(outputs={"returned": "1-test"}, current_span=current_span)


async def test_traceable_async(mock_handler: MockTraceHandler) -> None:
    current_span = MagicMock()
    mock_handler.start = MagicMock(return_value=current_span)  # type: ignore
    mock_handler.stop = MagicMock()  # type: ignore
    mock_handler.error = MagicMock()  # type: ignore

    @traceable
    async def sample_async_function(x: int) -> int:
        await asyncio.sleep(0.01)
        return x * 2

    result = await sample_async_function(5)
    assert result == 10

    mock_handler.start.assert_called_once_with(
        name="test_traceable_async.<locals>.sample_async_function",
        inputs={"x": 5},
        current_span=None,
    )
    mock_handler.stop.assert_called_once_with(outputs={"returned": 10}, current_span=current_span)


def test_traceable_no_return(mock_handler: MockTraceHandler) -> None:
    current_span = MagicMock()
    mock_handler.start = MagicMock(return_value=current_span)  # type: ignore
    mock_handler.stop = MagicMock()  # type: ignore
    mock_handler.error = MagicMock()  # type: ignore

    @traceable
    def void_function(x: int) -> None:
        pass

    void_function(1)
    mock_handler.start.assert_called_once_with(
        name="test_traceable_no_return.<locals>.void_function",
        inputs={"x": 1},
        current_span=None,
    )
    mock_handler.stop.assert_called_once_with(outputs={}, current_span=current_span)


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


@pytest.mark.parametrize(
    ("input_data", "prefix", "expected"),
    [
        # Empty dict
        ({}, None, {}),
        ({}, "prefix", {}),
        # Simple types
        (
            {"str": "value", "int": 42, "float": 3.14, "bool": True},
            None,
            {"str": "value", "int": 42, "float": 3.14, "bool": True},
        ),
        # # With prefix
        ({"str": "value", "int": 42}, "prefix", {"prefix.str": "value", "prefix.int": 42}),
        # # Nested dict
        ({"nested": {"key1": "value1", "key2": 42}}, None, {"nested.key1": "value1", "nested.key2": 42}),
        # Lists and tuples
        ({"list": [1, 2, 3], "tuple": ("a", "b", "c")}, None, {"list": "[1, 2, 3]", "tuple": "['a', 'b', 'c']"}),
        # Complex objects in lists
        (
            {
                "objects": [
                    {"a": 1},
                    datetime(2023, 1, 1),
                    Path("/path/to/file"),
                    ["short", "list"],
                    "LongString" + "A" * (AttributeFormatter.max_string_length + 50),
                ]
            },
            "test",
            {
                "test.objects.[0].a": 1,
                "test.objects.[1].datetime": "datetime.datetime(2023, 1, 1, 0, 0)",
                "test.objects.[2].PosixPath": "PosixPath('/path/to/file')",
                "test.objects.[3]": "['short', 'list']",
                "test.objects.[4]": "LongString" + "A" * (AttributeFormatter.max_string_length - 10) + "...",
            },
        ),
        # Mixed nested structure
        (
            {"level1": {"level2": {"string": "value", "list": [1, {"x": "y"}]}}},
            "test",
            {"test.level1.level2.string": "value", "test.level1.level2.list": "[1, {'x': 'y'}]"},
        ),
        # Empty dict and list
        ({"a": [], "b": {}, "c": ""}, "empty", {"empty.a": "[]", "empty.b": "{}", "empty.c": ""}),
        # Long list and long string
        (
            {
                "vector": [0.01, 0.02, 0.03, 0.04] * 1534,
                "vcs": VectorStoreEntry(
                    id="9c7d6b27-4ef1-537c-ad7c-676edb8bc8a8",
                    text="Some text",
                    image_bytes=None,
                    metadata={
                        "for_shortening": "A" * AttributeFormatter.max_string_length
                        + "B" * AttributeFormatter.max_string_length
                    },
                ),
                "not_for_shortening": {
                    "response": "A" * AttributeFormatter.max_string_length + "B" * AttributeFormatter.max_string_length
                },
            },
            "test",
            {
                "test.vector": "[0.01, '...', 0.04](total 6136 elements)",
                "test.vcs.VectorStoreEntry.id.UUID": "UUID('9c7d6b27-4ef1-537c-ad7c-676edb8bc8a8')",
                "test.vcs.VectorStoreEntry.text": "Some text",
                "test.vcs.VectorStoreEntry.image_bytes": "None",
                "test.vcs.VectorStoreEntry.metadata.for_shortening": "A" * AttributeFormatter.max_string_length + "...",
                "test.not_for_shortening.response": "A" * AttributeFormatter.max_string_length
                + "B" * AttributeFormatter.max_string_length,
            },
        ),
    ],
)
def test_format_attributes(input_data: dict, prefix: str, expected: dict) -> None:
    formatter = AttributeFormatter(input_data, prefix)
    formatter.process_attributes()
    result = formatter.flattened
    assert result == expected
