from unittest.mock import MagicMock, patch

from ragbits.core.audit.cli import CLISpan, CLITraceHandler, PrintColor, SpanStatus

TEST_NAME_1 = "process_1"
TEST_NAME_2 = "process_2"
TEST_INPUT = {"documents": ["article_1.pdf", "article_2.pdf"]}
PROCESS_TIME = [1234567890.0, 1234567895.0]


def test_init_cli_span() -> None:
    with patch("time.time", side_effect=PROCESS_TIME):
        test_instance = CLISpan(TEST_NAME_1, TEST_INPUT)
        assert test_instance.name == TEST_NAME_1
        assert test_instance.start_time == PROCESS_TIME[0]
        assert test_instance.end_time is None
        assert test_instance.status == SpanStatus.STARTED
        assert test_instance.inputs == TEST_INPUT
        assert test_instance.outputs == {}
        assert test_instance.children == []
        assert test_instance.parent is None

        second_instance = CLISpan(TEST_NAME_2, parent=test_instance)
        assert second_instance.name == TEST_NAME_2
        assert second_instance.parent == test_instance
        assert test_instance.children == []


def test_cli_span_end_method() -> None:
    with patch("time.time", side_effect=PROCESS_TIME):
        test_instance = CLISpan(TEST_NAME_1)
        assert test_instance.start_time == PROCESS_TIME[0]
        assert test_instance.status == SpanStatus.STARTED
        assert test_instance.end_time is None

        test_instance.end()
        assert test_instance.end_time == PROCESS_TIME[1]
        assert test_instance.status == SpanStatus.STARTED


def test_cli_span_to_tree() -> None:
    with patch("time.time", side_effect=[11.0, 22.0, 33.0]):
        parent_instance = CLISpan(name=TEST_NAME_1, inputs=TEST_INPUT)
        second_instance = CLISpan(name=TEST_NAME_2, parent=parent_instance)
        third_instance = CLISpan(name="process_3", parent=second_instance)
        third_instance.status = SpanStatus.ERROR
        second_instance.children = [third_instance]
        parent_instance.children = [second_instance]
        res_tree = parent_instance.to_tree()
        assert "process_1" in str(res_tree.label)
        assert PrintColor.parent_color in str(res_tree.label)
        assert "process_2" in str(res_tree.children[0].label)
        assert PrintColor.child_color in str(res_tree.children[0].label)
        assert "process_3" in str(res_tree.children[0].children[0].label)
        assert PrintColor.error_color in str(res_tree.children[0].children[0].label)


def test_dicts_to_string() -> None:
    test_instance = CLISpan(TEST_NAME_1)
    test_dict = {"k1": "v1"}
    test_dict_nested = {"k2": test_dict}
    test_dict_double_nested = {"k3": test_dict_nested}
    key_color = PrintColor.key_color
    value_color = PrintColor.faded_color
    expected_output_1 = f"[{key_color}]k1:[/{key_color}] [{value_color}]v1[/{value_color}]"
    expected_output_2 = f"[{key_color}]k2:[/{key_color}] {{\n{expected_output_1}}}"
    expected_output_3 = f"[{key_color}]k3:[/{key_color}] {{\n{expected_output_2}}}"
    result_1 = test_instance._dicts_to_string(test_dict)
    result_2 = test_instance._dicts_to_string(test_dict_nested)
    result_3 = test_instance._dicts_to_string(test_dict_double_nested)
    assert result_1.strip() == expected_output_1.strip()
    assert result_2.strip() == expected_output_2.strip()
    assert result_3.strip() == expected_output_3.strip()


def test_cli_trace_start() -> None:
    trace_handler = CLITraceHandler()
    parent_span = trace_handler.start(name=TEST_NAME_1, inputs=TEST_INPUT)
    assert trace_handler.live is not None
    assert trace_handler.live_tree is not None
    assert trace_handler.root_span is not None
    assert trace_handler.live_tree.label == f"Spans from main {TEST_NAME_1}"
    assert trace_handler.root_span.name == TEST_NAME_1
    assert trace_handler.root_span.inputs == TEST_INPUT
    assert parent_span.name == TEST_NAME_1
    assert parent_span.parent is None
    assert parent_span.start_time is not None
    assert parent_span.status == SpanStatus.STARTED

    child_span = trace_handler.start(name=TEST_NAME_2, inputs={}, current_span=parent_span)
    assert parent_span.children[0].name == TEST_NAME_2
    assert child_span.name == TEST_NAME_2
    assert child_span.parent == parent_span
    assert child_span.parent.name == TEST_NAME_1
    trace_handler.live.stop()


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
    assert child_span.outputs == outputs
    assert child_span.end_time is not None
    trace_handler.live.stop.assert_not_called()
    child_span.end.assert_called_once()

    trace_handler.stop(outputs, parent_span)

    assert parent_span.end_time is not None
    assert parent_span.status == SpanStatus.COMPLETED
    assert parent_span.outputs == outputs
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
    assert child_span.outputs == {"error": "Test exception"}
    child_span.end.assert_called_once()
    trace_handler.live.stop.assert_not_called()

    trace_handler.error(error=exception, current_span=parent_span)

    assert parent_span.status == SpanStatus.ERROR
    assert parent_span.outputs == {"error": "Test exception"}
    assert parent_span.end_time is not None
    trace_handler.live.stop.assert_called_once()

    original_live_stop()
