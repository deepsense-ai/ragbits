import logfire

from ragbits.core.audit.metrics.otel import OtelMetricHandler


class LogfireMetricHandler(OtelMetricHandler):
    """
    Logfire metric handler.
    """

    def __init__(self, metric_prefix: str = "ragbits") -> None:
        """
        Initialize the LogfireMetricHandler instance.

        Args:
            metric_prefix: Prefix for all metric names.
        """
        logfire.configure()
        logfire.instrument_system_metrics()
        super().__init__(metric_prefix=metric_prefix)
