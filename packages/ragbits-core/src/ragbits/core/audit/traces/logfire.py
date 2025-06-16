from opentelemetry.trace import Span, StatusCode, TracerProvider, get_tracer, set_span_in_context

from ragbits.core.audit.traces.base import TraceHandler, format_attributes


class LogfireTraceHandler(TraceHandler[Span]):
    """
    Logfire trace handler.
    """

    def __init__(self, provider: TracerProvider | None = None) -> None:
        """
        Initialize the LogfireTraceHandler instance.

        Args:
            provider: The tracer provider to use.
        """
        super().__init__()
        self._tracer = get_tracer(instrumenting_module_name=__name__, tracer_provider=provider)

    def start(self, name: str, inputs: dict, current_span: Span | None = None) -> Span:
        """
        Log input data at the beginning of the trace.

        Args:
            name: The name of the trace.
            inputs: The input data.
            current_span: The current trace span.

        Returns:
            The updated current trace span.
        """
        pass

    def stop(self, outputs: dict, current_span: Span) -> None:  # noqa: PLR6301
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """
        pass

    def error(self, error: Exception, current_span: Span) -> None:  # noqa: PLR6301
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """
        pass
