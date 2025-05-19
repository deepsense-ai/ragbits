from unittest.mock import MagicMock

import pytest

from ragbits.core.audit.metrics import create_histogram, record, set_metric_handlers
from ragbits.core.audit.metrics.base import MetricHandler


class MockMetricHandler(MetricHandler[MagicMock]):
    def create_histogram(self, name: str, unit: str = "", description: str = "") -> MagicMock:  # noqa: PLR6301
        return MagicMock()

    def record(self, metric: MagicMock, value: int | float, attributes: dict | None = None) -> None: ...


@pytest.fixture
def mock_handler() -> MockMetricHandler:
    handler = MockMetricHandler()
    set_metric_handlers(handler)
    return handler


def test_record_with_default_create_histogram(mock_handler: MockMetricHandler) -> None:
    metric = MagicMock()
    mock_handler.create_histogram = MagicMock(return_value=metric)  # type: ignore
    mock_handler.record = MagicMock()  # type: ignore

    record("test_metric", 1)

    mock_handler.create_histogram.assert_called_once_with(
        name="ragbits_test_metric",
        unit="",
        description="",
    )
    mock_handler.record.assert_called_once_with(metric=metric, value=1, attributes={})


def test_record_with_create_histogram(mock_handler: MockMetricHandler) -> None:
    metric = MagicMock()
    mock_handler.create_histogram = MagicMock(return_value=metric)  # type: ignore
    mock_handler.record = MagicMock()  # type: ignore

    metric_name = create_histogram(name="test_metric", unit="test_unit", description="test_description")
    record(metric_name, 1)

    mock_handler.create_histogram.assert_called_once_with(
        name="ragbits_test_metric",
        unit="test_unit",
        description="test_description",
    )
    mock_handler.record.assert_called_once_with(metric=metric, value=1, attributes={})
