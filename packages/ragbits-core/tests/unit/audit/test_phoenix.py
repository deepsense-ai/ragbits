from unittest.mock import MagicMock, patch

import pytest

from ragbits.core.audit.traces.phoenix import PhoenixTraceHandler


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
