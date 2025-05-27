from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Generic, TypeVar

HistogramT = TypeVar("HistogramT")


@dataclass
class Metric:
    """
    Represents the metric configuration data.
    """

    name: str
    description: str
    unit: str


class HistogramMetric(Enum):
    """
    Histogram metric types that can be recorded.
    """

    PROMPT_THROUGHPUT = auto()
    TOKEN_THROUGHPUT = auto()
    INPUT_TOKENS = auto()
    TIME_TO_FIRST_TOKEN = auto()

    # Chat Interface Metrics
    CHAT_REQUEST_DURATION = auto()
    CHAT_RESPONSE_TOKENS = auto()
    CHAT_HISTORY_LENGTH = auto()
    CHAT_MESSAGE_COUNT = auto()
    CHAT_CONVERSATION_COUNT = auto()
    CHAT_FEEDBACK_COUNT = auto()
    CHAT_ERROR_COUNT = auto()
    CHAT_STATE_VERIFICATION_COUNT = auto()

    # API Metrics
    API_REQUEST_DURATION = auto()
    API_REQUEST_COUNT = auto()
    API_ERROR_COUNT = auto()
    API_STREAM_DURATION = auto()
    API_STREAM_CHUNK_COUNT = auto()


HISTOGRAM_METRICS = {
    HistogramMetric.PROMPT_THROUGHPUT: Metric(
        name="prompt_throughput",
        description="Tracks the response time of LLM calls in seconds",
        unit="s",
    ),
    HistogramMetric.TOKEN_THROUGHPUT: Metric(
        name="token_throughput",
        description="Tracks tokens generated per second",
        unit="tokens/s",
    ),
    HistogramMetric.INPUT_TOKENS: Metric(
        name="input_tokens",
        description="Tracks the number of input tokens per request",
        unit="tokens",
    ),
    HistogramMetric.TIME_TO_FIRST_TOKEN: Metric(
        name="time_to_first_token",
        description="Tracks the time to first token in seconds",
        unit="s",
    ),
    # Chat Interface Metrics
    HistogramMetric.CHAT_REQUEST_DURATION: Metric(
        name="chat_request_duration",
        description="Tracks the total duration of chat request processing in seconds",
        unit="s",
    ),
    HistogramMetric.CHAT_RESPONSE_TOKENS: Metric(
        name="chat_response_tokens",
        description="Tracks the number of tokens in chat responses",
        unit="tokens",
    ),
    HistogramMetric.CHAT_HISTORY_LENGTH: Metric(
        name="chat_history_length",
        description="Tracks the length of conversation history",
        unit="messages",
    ),
    HistogramMetric.CHAT_MESSAGE_COUNT: Metric(
        name="chat_message_count",
        description="Tracks the count of chat messages processed",
        unit="messages",
    ),
    HistogramMetric.CHAT_CONVERSATION_COUNT: Metric(
        name="chat_conversation_count",
        description="Tracks the count of new conversations started",
        unit="conversations",
    ),
    HistogramMetric.CHAT_FEEDBACK_COUNT: Metric(
        name="chat_feedback_count",
        description="Tracks the count of feedback submissions",
        unit="feedback",
    ),
    HistogramMetric.CHAT_ERROR_COUNT: Metric(
        name="chat_error_count",
        description="Tracks the count of errors during chat processing",
        unit="errors",
    ),
    HistogramMetric.CHAT_STATE_VERIFICATION_COUNT: Metric(
        name="chat_state_verification_count",
        description="Tracks the count of state verifications",
        unit="verifications",
    ),
    # API Metrics
    HistogramMetric.API_REQUEST_DURATION: Metric(
        name="api_request_duration",
        description="Tracks the duration of API request processing in seconds",
        unit="s",
    ),
    HistogramMetric.API_REQUEST_COUNT: Metric(
        name="api_request_count",
        description="Tracks the count of API requests by endpoint",
        unit="requests",
    ),
    HistogramMetric.API_ERROR_COUNT: Metric(
        name="api_error_count",
        description="Tracks the count of API errors by status code",
        unit="errors",
    ),
    HistogramMetric.API_STREAM_DURATION: Metric(
        name="api_stream_duration",
        description="Tracks the duration of streaming responses in seconds",
        unit="s",
    ),
    HistogramMetric.API_STREAM_CHUNK_COUNT: Metric(
        name="api_stream_chunk_count",
        description="Tracks the number of chunks streamed per response",
        unit="chunks",
    ),
}


class MetricHandler(Generic[HistogramT], ABC):
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
        self._histogram_metrics: dict[str, HistogramT] = {}

    @abstractmethod
    def create_histogram(self, name: str, unit: str = "", description: str = "") -> HistogramT:
        """
        Create a histogram metric.

        Args:
            name: The histogram metric name.
            unit: The histogram metric unit.
            description: The histogram metric description.

        Returns:
            The initialized histogram metric.
        """

    @abstractmethod
    def record(self, metric: HistogramT, value: int | float, attributes: dict | None = None) -> None:
        """
        Record the value for a specified histogram metric.

        Args:
            metric: The histogram metric to record.
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
        """

    def register_histogram(self, name: str, unit: str = "", description: str = "") -> None:
        """
        Register a histogram metric.

        Args:
            name: The histogram metric name.
            unit: The histogram metric unit.
            description: The histogram metric description.

        Returns:
            The registered histogram metric.
        """
        self._histogram_metrics[name] = self.create_histogram(
            name=f"{self._metric_prefix}_{name}",
            unit=unit,
            description=description,
        )

    def record_histogram(
        self, metric: HistogramMetric | str, value: int | float, attributes: dict | None = None
    ) -> None:
        """
        Record the value for a specified histogram metric.

        Args:
            metric: The histogram metric name to record.
            value: The value to record for the metric.
            attributes: Additional metadata for the metric.
        """
        if histogram_metric := HISTOGRAM_METRICS.get(metric):  # type: ignore
            metric_name = histogram_metric.name
            if metric_name not in self._histogram_metrics:
                self.register_histogram(
                    name=metric_name,
                    unit=histogram_metric.unit,
                    description=histogram_metric.description,
                )
        else:
            metric_name = str(metric)
            if metric_name not in self._histogram_metrics:
                self.register_histogram(metric_name)

        self.record(
            metric=self._histogram_metrics[metric_name],
            value=value,
            attributes=attributes,
        )
