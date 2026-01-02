from unittest.mock import MagicMock, patch

import pytest

<<<<<<< HEAD
trace_module = pytest.importorskip("openinference.semconv.trace")
OpenInferenceSpanKindValues = trace_module.OpenInferenceSpanKindValues
SpanAttributes = trace_module.SpanAttributes

from ragbits.core.audit.traces.phoenix import PhoenixTraceHandler  # noqa: E402
=======
from ragbits.core.audit.traces.phoenix import PhoenixTraceHandler
>>>>>>> 2477c2433 (feat: add Arize Phoenix tracing integration)


@pytest.fixture
def mock_otel_exporter():
    with patch("ragbits.core.audit.traces.phoenix.OTLPSpanExporter") as mock:
        yield mock


@pytest.fixture
def mock_tracer_provider():
    with patch("ragbits.core.audit.traces.phoenix.TracerProvider") as mock:
        yield mock


@pytest.fixture
def mock_batch_span_processor():
    with patch("ragbits.core.audit.traces.phoenix.BatchSpanProcessor") as mock:
        yield mock


@pytest.fixture
def mock_set_tracer_provider():
    with patch("ragbits.core.audit.traces.phoenix.trace.set_tracer_provider") as mock:
        yield mock


def test_phoenix_trace_handler_init(
    mock_otel_exporter: MagicMock,
    mock_tracer_provider: MagicMock,
    mock_batch_span_processor: MagicMock,
    mock_set_tracer_provider: MagicMock,
) -> None:
    handler = PhoenixTraceHandler()

    assert isinstance(handler, PhoenixTraceHandler)
    mock_otel_exporter.assert_called_once_with(endpoint="http://localhost:6006/v1/traces")
    mock_tracer_provider.assert_called_once()
    mock_batch_span_processor.assert_called_once()
    mock_set_tracer_provider.assert_called_once()


def test_phoenix_trace_handler_init_custom_endpoint(
    mock_otel_exporter: MagicMock,
    mock_tracer_provider: MagicMock,
    mock_batch_span_processor: MagicMock,
    mock_set_tracer_provider: MagicMock,
) -> None:
    custom_endpoint = "http://custom-phoenix:6006/v1/traces"
    handler = PhoenixTraceHandler(endpoint=custom_endpoint)

    assert isinstance(handler, PhoenixTraceHandler)
    mock_otel_exporter.assert_called_once_with(endpoint=custom_endpoint)
<<<<<<< HEAD


def test_start_llm_span(
    mock_otel_exporter: MagicMock,
    mock_tracer_provider: MagicMock,
    mock_batch_span_processor: MagicMock,
    mock_set_tracer_provider: MagicMock,
) -> None:
    handler = PhoenixTraceHandler()
    span_mock = MagicMock()

    with patch("ragbits.core.audit.traces.otel.OtelTraceHandler.start", return_value=span_mock) as mock_super_start:
        inputs = {"model_name": "gpt-4", "prompt": "hello", "options": {"temperature": 0.5}}
        handler.start("generate", inputs)

        mock_super_start.assert_called_once()
        span_mock.set_attribute.assert_any_call(
            SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value
        )
        span_mock.set_attribute.assert_any_call(SpanAttributes.LLM_MODEL_NAME, "gpt-4")
        span_mock.set_attribute.assert_any_call(SpanAttributes.INPUT_VALUE, "hello")
        span_mock.set_attribute.assert_any_call(SpanAttributes.LLM_INVOCATION_PARAMETERS, "{'temperature': 0.5}")


def test_stop_llm_span(
    mock_otel_exporter: MagicMock,
    mock_tracer_provider: MagicMock,
    mock_batch_span_processor: MagicMock,
    mock_set_tracer_provider: MagicMock,
) -> None:
    handler = PhoenixTraceHandler()
    span_mock = MagicMock()

    with patch("ragbits.core.audit.traces.otel.OtelTraceHandler.stop") as mock_super_stop:
        outputs = {"response": "world"}
        handler.stop(outputs, span_mock)

        mock_super_stop.assert_called_once()
        span_mock.set_attribute.assert_any_call(SpanAttributes.OUTPUT_VALUE, "world")
=======
>>>>>>> 2477c2433 (feat: add Arize Phoenix tracing integration)
