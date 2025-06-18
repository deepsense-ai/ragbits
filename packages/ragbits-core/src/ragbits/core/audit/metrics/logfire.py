import logfire
from opentelemetry.metrics import MeterProvider

from ragbits.core.audit.metrics.otel import OtelMetricHandler


class LogfireMetricHandler(OtelMetricHandler):
    """
    Logfire metric handler.
    """

    def __init__(self, provider: MeterProvider | None = None, metric_prefix: str = "ragbits") -> None:
        """
        Initialize the LogfireMetricHandler instance.

        Args:
            provider: The meter provider to use.
            metric_prefix: Prefix for all metric names.
        """
        logfire.configure()
        logfire.instrument_system_metrics()
        super().__init__(provider=provider, metric_prefix=metric_prefix)
