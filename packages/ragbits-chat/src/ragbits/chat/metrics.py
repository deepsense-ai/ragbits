"""
Chat-specific metrics for ragbits-chat package.

This module defines and registers metrics specific to chat functionality
with the ragbits-core metrics system.
"""

from enum import Enum

from ragbits.core.audit.metrics import register_histogram_metric
from ragbits.core.audit.metrics.base import Metric


class ChatMetric(str, Enum):
    """
    Chat-specific histogram metrics that can be recorded.
    """

    # Chat Interface Metrics
    CHAT_REQUEST_DURATION = "chat_request_duration"
    CHAT_TIME_TO_FIRST_TOKEN = "chat_time_to_first_token"  # noqa: S105
    CHAT_RESPONSE_TOKENS = "chat_response_tokens"
    CHAT_HISTORY_LENGTH = "chat_history_length"
    CHAT_MESSAGE_COUNT = "chat_message_count"
    CHAT_CONVERSATION_COUNT = "chat_conversation_count"
    CHAT_FEEDBACK_COUNT = "chat_feedback_count"
    CHAT_ERROR_COUNT = "chat_error_count"
    CHAT_STATE_VERIFICATION_COUNT = "chat_state_verification_count"

    # API Metrics
    API_REQUEST_DURATION = "api_request_duration"
    API_REQUEST_COUNT = "api_request_count"
    API_ERROR_COUNT = "api_error_count"
    API_STREAM_DURATION = "api_stream_duration"
    API_STREAM_CHUNK_COUNT = "api_stream_chunk_count"


def _register_chat_metrics() -> None:
    """Register all chat-specific metrics with the core metrics system."""
    # Chat Interface Metrics
    register_histogram_metric(
        ChatMetric.CHAT_REQUEST_DURATION,
        Metric(
            name="chat_request_duration",
            description="Tracks the total duration of chat request processing in seconds",
            unit="s",
        ),
    )

    register_histogram_metric(
        ChatMetric.CHAT_TIME_TO_FIRST_TOKEN,
        Metric(
            name="chat_time_to_first_token",
            description="Tracks the time taken to get the first token in chat processing",
            unit="s",
        ),
    )

    register_histogram_metric(
        ChatMetric.CHAT_RESPONSE_TOKENS,
        Metric(
            name="chat_response_tokens",
            description="Tracks the number of tokens in chat responses",
            unit="tokens",
        ),
    )

    register_histogram_metric(
        ChatMetric.CHAT_HISTORY_LENGTH,
        Metric(
            name="chat_history_length",
            description="Tracks the length of conversation history",
            unit="messages",
        ),
    )

    register_histogram_metric(
        ChatMetric.CHAT_MESSAGE_COUNT,
        Metric(
            name="chat_message_count",
            description="Tracks the count of chat messages processed",
            unit="messages",
        ),
    )

    register_histogram_metric(
        ChatMetric.CHAT_CONVERSATION_COUNT,
        Metric(
            name="chat_conversation_count",
            description="Tracks the count of new conversations started",
            unit="conversations",
        ),
    )

    register_histogram_metric(
        ChatMetric.CHAT_FEEDBACK_COUNT,
        Metric(
            name="chat_feedback_count",
            description="Tracks the count of feedback submissions",
            unit="feedback",
        ),
    )

    register_histogram_metric(
        ChatMetric.CHAT_ERROR_COUNT,
        Metric(
            name="chat_error_count",
            description="Tracks the count of errors during chat processing",
            unit="errors",
        ),
    )

    register_histogram_metric(
        ChatMetric.CHAT_STATE_VERIFICATION_COUNT,
        Metric(
            name="chat_state_verification_count",
            description="Tracks the count of state verifications",
            unit="verifications",
        ),
    )

    # API Metrics
    register_histogram_metric(
        ChatMetric.API_REQUEST_DURATION,
        Metric(
            name="api_request_duration",
            description="Tracks the duration of API request processing in seconds",
            unit="s",
        ),
    )

    register_histogram_metric(
        ChatMetric.API_REQUEST_COUNT,
        Metric(
            name="api_request_count",
            description="Tracks the count of API requests by endpoint",
            unit="requests",
        ),
    )

    register_histogram_metric(
        ChatMetric.API_ERROR_COUNT,
        Metric(
            name="api_error_count",
            description="Tracks the count of API errors by status code",
            unit="errors",
        ),
    )

    register_histogram_metric(
        ChatMetric.API_STREAM_DURATION,
        Metric(
            name="api_stream_duration",
            description="Tracks the duration of streaming responses in seconds",
            unit="s",
        ),
    )

    register_histogram_metric(
        ChatMetric.API_STREAM_CHUNK_COUNT,
        Metric(
            name="api_stream_chunk_count",
            description="Tracks the number of chunks streamed per response",
            unit="chunks",
        ),
    )


# Register metrics when module is imported
_register_chat_metrics()
