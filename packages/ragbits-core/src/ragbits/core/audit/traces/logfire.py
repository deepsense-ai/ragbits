import logfire
from opentelemetry.trace import TracerProvider

from ragbits.core.audit.traces.otel import OtelTraceHandler


class LogfireTraceHandler(OtelTraceHandler):
    """
    Logfire trace handler.
    """

    def __init__(self, provider: TracerProvider | None = None) -> None:
        """
        Initialize the LogfireTraceHandler instance.

        Args:
            provider: The tracer provider to use.
        """
        logfire.configure()
        super().__init__(provider=provider)
