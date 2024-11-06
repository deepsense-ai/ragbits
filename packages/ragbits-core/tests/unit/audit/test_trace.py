import asyncio
from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

from ragbits.core.audit import _get_function_inputs, set_trace_handlers, trace, traceable
from ragbits.core.audit.base import TraceHandler


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
