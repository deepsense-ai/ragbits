import logfire

from ragbits.core.audit.traces.otel import OtelTraceHandler


class LogfireTraceHandler(OtelTraceHandler):
    """
    Logfire trace handler.
    """

    def __init__(self) -> None:
        """
        Initialize the LogfireTraceHandler instance.
        """
        logfire.configure()
        super().__init__()
