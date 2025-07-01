from typing import Any

import logfire

from ragbits.core.audit.metrics.otel import OtelMetricHandler


class LogfireMetricHandler(OtelMetricHandler):
    """
    Logfire metric handler.
    """

    def __init__(self, metric_prefix: str = "ragbits", *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """
        Initialize the LogfireMetricHandler instance.
        """
        logfire.configure(*args, **kwargs)
        logfire.instrument_system_metrics()
        super().__init__(metric_prefix=metric_prefix)
