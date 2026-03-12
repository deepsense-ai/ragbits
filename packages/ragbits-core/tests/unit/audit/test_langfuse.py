from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

langfuse = pytest.importorskip("langfuse")
StatefulSpanClient = langfuse.client.StatefulSpanClient
StatefulTraceClient = langfuse.client.StatefulTraceClient

from ragbits.core.audit.traces.langfuse import LangfuseSpan, LangfuseTraceHandler  # noqa: E402

TEST_NAME_1 = "process_1"
TEST_NAME_2 = "process_2"
TEST_INPUT = {"documents": ["article_1.pdf", "article_2.pdf"]}
TEST_OUTPUT = {"result": "success"}


@pytest.fixture
def mock_langfuse() -> Generator[MagicMock, None, None]:
    with patch("ragbits.core.audit.traces.langfuse.Langfuse") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance

        # Setup mock trace client
        mock_trace = MagicMock(spec=StatefulTraceClient)
        mock_trace.id = "trace-123"
        mock_instance.trace.return_value = mock_trace

        # Setup mock span client
        mock_span = MagicMock(spec=StatefulSpanClient)
        mock_span.id = "span-456"
        mock_instance.span.return_value = mock_span

        yield mock_instance


def test_langfuse_span_init() -> None:
    mock_trace = MagicMock(spec=StatefulTraceClient)
    mock_trace.id = "trace-123"

    mock_span_client = MagicMock(spec=StatefulSpanClient)
    mock_span_client.id = "span-456"

    # Test root span
    root_span = LangfuseSpan(client=mock_trace, trace=mock_trace, is_root=True)
    assert root_span.client == mock_trace
    assert root_span.trace == mock_trace
    assert root_span.is_root is True
    assert root_span.observation_id is None

    # Test nested span
    nested_span = LangfuseSpan(client=mock_span_client, trace=mock_trace, is_root=False)
    assert nested_span.client == mock_span_client
    assert nested_span.trace == mock_trace
    assert nested_span.is_root is False
    assert nested_span.observation_id == "span-456"


def test_langfuse_trace_handler_init(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()
    assert handler._langfuse is not None


def test_langfuse_trace_handler_start_root(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()

    span = handler.start(name=TEST_NAME_1, inputs=TEST_INPUT, current_span=None)

    assert span is not None
    assert span.is_root is True
    mock_langfuse.trace.assert_called_once()
    call_kwargs = mock_langfuse.trace.call_args[1]
    assert call_kwargs["name"] == TEST_NAME_1
    assert "inputs.documents" in call_kwargs["input"]


def test_langfuse_trace_handler_start_nested(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()

    # Create root span first
    root_span = handler.start(name=TEST_NAME_1, inputs={}, current_span=None)

    # Create nested span
    nested_span = handler.start(name=TEST_NAME_2, inputs=TEST_INPUT, current_span=root_span)

    assert nested_span is not None
    assert nested_span.is_root is False
    assert nested_span.trace == root_span.trace
    mock_langfuse.span.assert_called_once()
    call_kwargs = mock_langfuse.span.call_args[1]
    assert call_kwargs["name"] == TEST_NAME_2
    assert call_kwargs["trace_id"] == root_span.trace.id


def test_langfuse_trace_handler_stop_root(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()

    root_span = handler.start(name=TEST_NAME_1, inputs={}, current_span=None)
    handler.stop(outputs=TEST_OUTPUT, current_span=root_span)

    root_span.client.update.assert_called_once()
    call_kwargs = root_span.client.update.call_args[1]
    assert "outputs.result" in call_kwargs["output"]
    mock_langfuse.flush.assert_called_once()


def test_langfuse_trace_handler_stop_nested(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()

    root_span = handler.start(name=TEST_NAME_1, inputs={}, current_span=None)
    nested_span = handler.start(name=TEST_NAME_2, inputs={}, current_span=root_span)

    handler.stop(outputs=TEST_OUTPUT, current_span=nested_span)

    nested_span.client.end.assert_called_once()
    call_kwargs = nested_span.client.end.call_args[1]
    assert "outputs.result" in call_kwargs["output"]
    # flush should not be called for nested spans
    mock_langfuse.flush.assert_not_called()


def test_langfuse_trace_handler_error_root(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()

    root_span = handler.start(name=TEST_NAME_1, inputs={}, current_span=None)
    exception = ValueError("Test error")

    handler.error(error=exception, current_span=root_span)

    root_span.client.update.assert_called_once()
    call_kwargs = root_span.client.update.call_args[1]
    assert "error.message" in call_kwargs["output"]
    assert call_kwargs["metadata"] == {"error": True}
    mock_langfuse.flush.assert_called_once()


def test_langfuse_trace_handler_error_nested(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()

    root_span = handler.start(name=TEST_NAME_1, inputs={}, current_span=None)
    nested_span = handler.start(name=TEST_NAME_2, inputs={}, current_span=root_span)
    exception = ValueError("Test error")

    handler.error(error=exception, current_span=nested_span)

    nested_span.client.end.assert_called_once()
    call_kwargs = nested_span.client.end.call_args[1]
    assert "error.message" in call_kwargs["output"]
    assert call_kwargs["level"] == "ERROR"
    assert call_kwargs["status_message"] == "Test error"
    mock_langfuse.flush.assert_not_called()


def test_langfuse_trace_handler_context_manager(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()

    with handler.trace(TEST_NAME_1, **TEST_INPUT) as outputs:
        outputs.result = "success"

    mock_langfuse.trace.assert_called_once()
    mock_langfuse.flush.assert_called_once()


def test_langfuse_trace_handler_nested_context_manager(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()

    with handler.trace(TEST_NAME_1) as outer_outputs:
        outer_outputs.step = "outer"
        with handler.trace(TEST_NAME_2, **TEST_INPUT) as inner_outputs:
            inner_outputs.step = "inner"

    # Root trace created, then nested span
    mock_langfuse.trace.assert_called_once()
    mock_langfuse.span.assert_called_once()
    # Flush called once for root completion
    mock_langfuse.flush.assert_called_once()


def test_langfuse_trace_handler_exception_handling(mock_langfuse: MagicMock) -> None:
    handler = LangfuseTraceHandler()

    with pytest.raises(ValueError, match="Test exception"), handler.trace(TEST_NAME_1):
        raise ValueError("Test exception")

    # Should have called update with error info
    mock_langfuse.trace.return_value.update.assert_called()
    mock_langfuse.flush.assert_called()
