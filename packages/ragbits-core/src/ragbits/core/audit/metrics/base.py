from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class MetricType(Enum):
    """Supported metric types."""

    HISTOGRAM = "histogram"
    COUNTER = "counter"
    GAUGE = "gauge"


@dataclass
class Metric:
    """
    Represents the metric configuration data.
    """

    name: str
    description: str
    unit: str
    type: MetricType


class LLMMetric(Enum):
    """
    LLM-related metrics that can be recorded.
    Each metric has a predefined type and is registered in the global registry.
    """

    # Histogram metrics
    PROMPT_THROUGHPUT = auto()
    TOKEN_THROUGHPUT = auto()
    INPUT_TOKENS = auto()
    TIME_TO_FIRST_TOKEN = auto()


# Global registry for all metrics by type
METRICS_REGISTRY: dict[MetricType, dict[Any, Metric]] = {
    MetricType.HISTOGRAM: {},
    MetricType.COUNTER: {},
    MetricType.GAUGE: {},
}


# Register default LLM metrics
METRICS_REGISTRY[MetricType.HISTOGRAM][LLMMetric.PROMPT_THROUGHPUT] = Metric(
    name="prompt_throughput",
    description="Tracks the response time of LLM calls in seconds",
    unit="s",
    type=MetricType.HISTOGRAM,
)
METRICS_REGISTRY[MetricType.HISTOGRAM][LLMMetric.TOKEN_THROUGHPUT] = Metric(
    name="token_throughput",
    description="Tracks tokens generated per second",
    unit="tokens/s",
    type=MetricType.HISTOGRAM,
)
METRICS_REGISTRY[MetricType.HISTOGRAM][LLMMetric.INPUT_TOKENS] = Metric(
    name="input_tokens",
    description="Tracks the number of input tokens per request",
    unit="tokens",
    type=MetricType.HISTOGRAM,
)
METRICS_REGISTRY[MetricType.HISTOGRAM][LLMMetric.TIME_TO_FIRST_TOKEN] = Metric(
    name="time_to_first_token",
    description="Tracks the time to first token in seconds",
    unit="s",
    type=MetricType.HISTOGRAM,
)


def register_metric(key: str | Enum, metric: Metric) -> None:
    """
    Register a new metric in the global registry by type.

    Args:
        key: The metric key (enum value or string)
        metric: The metric configuration
    """
    METRICS_REGISTRY[metric.type][key] = metric


def get_metric(key: str | Enum, metric_type: MetricType) -> Metric | None:
    """
    Get a metric from the registry by key and type.

    Args:
        key: The metric key (enum value or string)
        metric_type: The type of metric to retrieve

    Returns:
        The metric configuration if found, None otherwise
    """
    return METRICS_REGISTRY[metric_type].get(key)


class MetricHandler(ABC):
    """
    Base class for all metric handlers.
    """

    def __init__(self, metric_prefix: str = "ragbits") -> None:
        """
        Initialize the MetricHandler instance.

        Args:
            metric_prefix: Prefix for all metric names.
        """
        super().__init__()
        self._metric_prefix = metric_prefix
        self._metrics: dict[str, Any] = {}

    @abstractmethod
    def create_metric(
        self, name: str, unit: str = "", description: str = "", metric_type: MetricType = MetricType.HISTOGRAM
    ) -> Any:  # noqa: ANN401
        """
        Create a metric of the given type.

        Args:
            name: The metric name.
            unit: The metric unit.
            description: The metric description.
            metric_type: The type of the metric (histogram, counter, gauge).

        Returns:
            The initialized metric.
        """

    @abstractmethod
    def _record(self, metric: Any, value: int | float, attributes: dict | None = None) -> None:  # noqa: ANN401
        """
        Low-level method to record a value for a specified metric.
        This method should not be called directly, use record_metric instead.

        Args:
            metric: The metric to record.
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
        """

    def register_metric_instance(
        self, name: str, unit: str = "", description: str = "", metric_type: MetricType = MetricType.HISTOGRAM
    ) -> None:
        """
        Register a metric instance.

        Args:
            name: The metric name.
            unit: The metric unit.
            description: The metric description.
            metric_type: The type of the metric (histogram, counter, gauge).
        """
        self._metrics[name] = self.create_metric(
            name=f"{self._metric_prefix}_{name}",
            unit=unit,
            description=description,
            metric_type=metric_type,
        )

    def record_metric(
        self,
        metric_key: str | Enum,
        value: int | float,
        attributes: dict | None = None,
        metric_type: MetricType = MetricType.HISTOGRAM,
    ) -> None:
        """
        Record the value for a specified metric.

        Args:
            metric_key: The metric key (name or enum value) to record.
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
            metric_type: The type of the metric (histogram, counter, gauge).
        """
        metric_cfg = get_metric(metric_key, metric_type)
        if metric_cfg:
            metric_name = metric_cfg.name
            if metric_name not in self._metrics:
                self.register_metric_instance(
                    name=metric_name,
                    unit=metric_cfg.unit,
                    description=metric_cfg.description,
                    metric_type=metric_type,
                )
        else:
            metric_name = str(metric_key)
            if metric_name not in self._metrics:
                self.register_metric_instance(metric_name, metric_type=metric_type)
        self._record(
            metric=self._metrics[metric_name],
            value=value,
            attributes=attributes,
        )
