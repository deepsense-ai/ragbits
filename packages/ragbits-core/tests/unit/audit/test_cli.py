from unittest.mock import MagicMock, patch

from ragbits.core.audit.cli import CLISpan, CLITraceHandler, SpanStatus

TEST_NAME_1 = "process_1"
TEST_NAME_2 = "process_2"
TEST_INPUT = {"documents": ["article_1.pdf", "article_2.pdf"]}
PROCESS_TIME = [1234567890.0, 1234567895.0]


def test_init_cli_span() -> None:
    with patch("time.perf_counter", side_effect=PROCESS_TIME):
        test_instance = CLISpan(
            name=TEST_NAME_1,
            attributes=TEST_INPUT,
        )

        assert test_instance.name == TEST_NAME_1
        assert test_instance.start_time == PROCESS_TIME[0]
        assert test_instance.end_time is None
        assert test_instance.status == SpanStatus.STARTED
        assert test_instance.parent is None

        second_instance = CLISpan(
            name=TEST_NAME_2,
            attributes=TEST_INPUT,
            parent=test_instance,
        )

        assert second_instance.name == TEST_NAME_2
        assert second_instance.parent == test_instance


def test_cli_span_end_method() -> None:
    with patch("time.perf_counter", side_effect=PROCESS_TIME):
        test_instance = CLISpan(
            name=TEST_NAME_1,
            attributes={},
        )

        assert test_instance.start_time == PROCESS_TIME[0]
        assert test_instance.status == SpanStatus.STARTED
        assert test_instance.end_time is None

        test_instance.end()

        assert test_instance.end_time == PROCESS_TIME[1]
        assert test_instance.status == SpanStatus.STARTED


def test__cli_trace_stop() -> None:
    trace_handler = CLITraceHandler()
    parent_span = trace_handler.start(name=TEST_NAME_1, inputs={})
    child_span = trace_handler.start(name=TEST_NAME_2, inputs=TEST_INPUT, current_span=parent_span)
    outputs = {"k1": "v1"}

    assert trace_handler.live is not None

    original_live_stop = trace_handler.live.stop
    trace_handler.live = MagicMock()
    trace_handler.live.stop = MagicMock()
    original_span_end = child_span.end
    child_span.end = MagicMock(side_effect=original_span_end)  # type: ignore

    trace_handler.stop(outputs=outputs, current_span=child_span)

    assert child_span.parent == parent_span
    assert child_span.end_time is not None
    assert child_span.status == SpanStatus.COMPLETED
    assert child_span.attributes == {"inputs.documents": "['article_1.pdf', 'article_2.pdf']", "outputs.k1": "v1"}
    assert child_span.end_time is not None

    trace_handler.live.stop.assert_not_called()
    child_span.end.assert_called_once()

    trace_handler.stop(outputs, parent_span)

    assert parent_span.end_time is not None
    assert parent_span.status == SpanStatus.COMPLETED
    assert parent_span.attributes == {"outputs.k1": "v1"}
    trace_handler.live.stop.assert_called_once()

    original_live_stop()


def test__cli_trace_error() -> None:
    trace_handler = CLITraceHandler()
    parent_span = trace_handler.start(name=TEST_NAME_1, inputs=TEST_INPUT)
    child_span = trace_handler.start(name=TEST_NAME_2, inputs=TEST_INPUT, current_span=parent_span)
    exception = Exception("Test exception")

    assert trace_handler.live is not None

    original_live_stop = trace_handler.live.stop
    trace_handler.live = MagicMock()
    trace_handler.live.stop = MagicMock()
    child_span.end = MagicMock()  # type: ignore

    trace_handler.error(error=exception, current_span=child_span)

    assert child_span.status == SpanStatus.ERROR
    assert child_span.attributes == {
        "inputs.documents": "['article_1.pdf', 'article_2.pdf']",
        "error.message": "Test exception",
    }
    child_span.end.assert_called_once()
    trace_handler.live.stop.assert_not_called()

    trace_handler.error(error=exception, current_span=parent_span)

    assert parent_span.status == SpanStatus.ERROR
    assert parent_span.attributes == {
        "inputs.documents": "['article_1.pdf', 'article_2.pdf']",
        "error.message": "Test exception",
    }
    assert parent_span.end_time is not None
    trace_handler.live.stop.assert_called_once()

    original_live_stop()
