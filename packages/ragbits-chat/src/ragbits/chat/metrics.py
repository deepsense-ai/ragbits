"""
Chat-specific metrics for ragbits-chat package.

This module defines and registers metrics specific to chat functionality
with the ragbits-core metrics system.
"""

from enum import Enum

from ragbits.core.audit.metrics import register_metric
from ragbits.core.audit.metrics.base import Metric, MetricType


class ChatHistogramMetric(str, Enum):
    """
    Chat-specific histogram metrics that track distributions and durations.
    """

    # Durations and distributions
    CHAT_REQUEST_DURATION = "chat_request_duration"
    CHAT_TIME_TO_FIRST_TOKEN = "chat_time_to_first_token"  # noqa: S105
    CHAT_RESPONSE_TOKENS = "chat_response_tokens"
    CHAT_HISTORY_LENGTH = "chat_history_length"
    API_REQUEST_DURATION = "api_request_duration"
    API_STREAM_DURATION = "api_stream_duration"


class ChatCounterMetric(str, Enum):
    """
    Chat-specific counter metrics that track counts of events.
    """

    # Counters for events
    CHAT_MESSAGE_COUNT = "chat_message_count"
    CHAT_CONVERSATION_COUNT = "chat_conversation_count"
    CHAT_FEEDBACK_COUNT = "chat_feedback_count"
    CHAT_ERROR_COUNT = "chat_error_count"
    CHAT_STATE_VERIFICATION_COUNT = "chat_state_verification_count"
    API_REQUEST_COUNT = "api_request_count"
    API_ERROR_COUNT = "api_error_count"
    API_STREAM_CHUNK_COUNT = "api_stream_chunk_count"


class ChatGaugeMetric(str, Enum):
    """
    Chat-specific gauge metrics that track current values.
    Currently, no gauge metrics are defined, but this can be extended in the future.
    """

    # No gauge metrics defined yet
    pass


def _register_histogram_metrics() -> None:
    """Register all chat-specific histogram metrics with the core metrics system."""
    register_metric(
        ChatHistogramMetric.CHAT_REQUEST_DURATION,
        Metric(
            name="chat_request_duration",
            description="Tracks the total duration of chat request processing in seconds",
            unit="s",
            type=MetricType.HISTOGRAM,
        ),
    )

    register_metric(
        ChatHistogramMetric.CHAT_TIME_TO_FIRST_TOKEN,
        Metric(
            name="chat_time_to_first_token",
            description="Tracks the time taken to get the first token in chat processing",
            unit="s",
            type=MetricType.HISTOGRAM,
        ),
    )

    register_metric(
        ChatHistogramMetric.CHAT_RESPONSE_TOKENS,
        Metric(
            name="chat_response_tokens",
            description="Tracks the number of tokens in chat responses",
            unit="tokens",
            type=MetricType.HISTOGRAM,
        ),
    )

    register_metric(
        ChatHistogramMetric.CHAT_HISTORY_LENGTH,
        Metric(
            name="chat_history_length",
            description="Tracks the length of conversation history",
            unit="messages",
            type=MetricType.HISTOGRAM,
        ),
    )

    register_metric(
        ChatHistogramMetric.API_REQUEST_DURATION,
        Metric(
            name="api_request_duration",
            description="Tracks the duration of API request processing in seconds",
            unit="s",
            type=MetricType.HISTOGRAM,
        ),
    )

    register_metric(
        ChatHistogramMetric.API_STREAM_DURATION,
        Metric(
            name="api_stream_duration",
            description="Tracks the duration of streaming responses in seconds",
            unit="s",
            type=MetricType.HISTOGRAM,
        ),
    )


def _register_counter_metrics() -> None:
    """Register all chat-specific counter metrics with the core metrics system."""
    register_metric(
        ChatCounterMetric.CHAT_MESSAGE_COUNT,
        Metric(
            name="chat",
            description="Tracks the count of chat messages processed",
            unit="messages",
            type=MetricType.COUNTER,
        ),
    )

    register_metric(
        ChatCounterMetric.CHAT_CONVERSATION_COUNT,
        Metric(
            name="chat",
            description="Tracks the count of new conversations started",
            unit="conversations",
            type=MetricType.COUNTER,
        ),
    )

    register_metric(
        ChatCounterMetric.CHAT_FEEDBACK_COUNT,
        Metric(
            name="chat",
            description="Tracks the count of feedback submissions",
            unit="feedbacks",
            type=MetricType.COUNTER,
        ),
    )

    register_metric(
        ChatCounterMetric.CHAT_ERROR_COUNT,
        Metric(
            name="chat",
            description="Tracks the count of errors during chat processing",
            unit="errors",
            type=MetricType.COUNTER,
        ),
    )

    register_metric(
        ChatCounterMetric.CHAT_STATE_VERIFICATION_COUNT,
        Metric(
            name="chat_state",
            description="Tracks the count of state verifications",
            unit="verifications",
            type=MetricType.COUNTER,
        ),
    )

    register_metric(
        ChatCounterMetric.API_REQUEST_COUNT,
        Metric(
            name="api",
            description="Tracks the count of API requests by endpoint",
            unit="requests",
            type=MetricType.COUNTER,
        ),
    )

    register_metric(
        ChatCounterMetric.API_ERROR_COUNT,
        Metric(
            name="api",
            description="Tracks the count of API errors by status code",
            unit="errors",
            type=MetricType.COUNTER,
        ),
    )

    register_metric(
        ChatCounterMetric.API_STREAM_CHUNK_COUNT,
        Metric(
            name="api_stream",
            description="Tracks the number of chunks streamed per response",
            unit="chunks",
            type=MetricType.COUNTER,
        ),
    )


def _register_gauge_metrics() -> None:
    """
    Register all chat-specific gauge metrics with the core metrics system.
    Currently, no gauge metrics are defined, but this function can be extended in the future.
    """
    pass


def _register_chat_metrics() -> None:
    """
    Register all chat-specific metrics with the core metrics system.
    This includes histograms, counters, and gauges.
    """
    _register_histogram_metrics()
    _register_counter_metrics()
    _register_gauge_metrics()


# Register metrics when module is imported
_register_chat_metrics()
