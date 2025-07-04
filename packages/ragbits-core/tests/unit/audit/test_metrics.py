from unittest.mock import MagicMock

import pytest

from ragbits.core.audit.metrics import record_metric, set_metric_handlers
from ragbits.core.audit.metrics.base import MetricHandler, MetricType


class MockMetricHandler(MetricHandler):
    @classmethod
    def create_metric(
        cls, name: str, unit: str = "", description: str = "", metric_type: MetricType = MetricType.HISTOGRAM
    ) -> MagicMock:
        mock = MagicMock()
        mock.name = name
        mock.unit = unit
        mock.description = description
        mock.type = metric_type
        return mock

    def _record(self, metric: MagicMock, value: int | float, attributes: dict | None = None) -> None:
        # Implementation for tests
        pass


@pytest.fixture
def mock_handler() -> MockMetricHandler:
    handler = MockMetricHandler()
    set_metric_handlers(handler)
    return handler


def test_record_metric_with_default(mock_handler: MockMetricHandler) -> None:
    metric = MagicMock()
    mock_handler.create_metric = MagicMock(return_value=metric)  # type: ignore
    mock_handler._record = MagicMock()  # type: ignore

    record_metric("test_metric", 1, metric_type=MetricType.HISTOGRAM)

    mock_handler.create_metric.assert_called_once_with(
        name="ragbits_test_metric",
        unit="",
        description="",
        metric_type=MetricType.HISTOGRAM,
    )
    mock_handler._record.assert_called_once_with(metric=metric, value=1, attributes={})


def test_record_metric_with_registration(mock_handler: MockMetricHandler) -> None:
    metric = MagicMock()
    mock_handler.create_metric = MagicMock(return_value=metric)  # type: ignore
    mock_handler._record = MagicMock()  # type: ignore

    mock_handler.register_metric_instance(
        name="test_metric", unit="test_unit", description="test_description", metric_type=MetricType.COUNTER
    )
    record_metric("test_metric", 1, metric_type=MetricType.COUNTER)

    mock_handler.create_metric.assert_called_once_with(
        name="ragbits_test_metric",
        unit="test_unit",
        description="test_description",
        metric_type=MetricType.COUNTER,
    )
    mock_handler._record.assert_called_once_with(metric=metric, value=1, attributes={})
