from typing import Any

from ragbits.core.audit.metrics.otel import OtelMetricHandler


class LangfuseMetricHandler(OtelMetricHandler):
    """
    Langfuse metric handler.

    Note: Langfuse's OpenTelemetry integration currently focuses on traces/spans.
    This handler provides API consistency with LangfuseTraceHandler but uses the
    default OpenTelemetry metric infrastructure. To export metrics to a backend,
    configure an OTEL metric exporter separately.
    """

    def __init__(self, metric_prefix: str = "ragbits", *args: Any, **kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """
        Initialize the LangfuseMetricHandler instance.

        Args:
            metric_prefix: Prefix for all metric names.
            *args: Additional arguments (unused, for API consistency).
            **kwargs: Additional keyword arguments (unused, for API consistency).
        """
        super().__init__(metric_prefix=metric_prefix)
