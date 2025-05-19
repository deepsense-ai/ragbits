from opentelemetry.trace import Span, StatusCode, TracerProvider, get_tracer, set_span_in_context

from ragbits.core.audit.traces.base import TraceHandler, format_attributes


class OtelTraceHandler(TraceHandler[Span]):
    """
    OpenTelemetry trace handler.
    """

    def __init__(self, provider: TracerProvider | None = None) -> None:
        """
        Initialize the OtelTraceHandler instance.

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
        context = set_span_in_context(current_span) if current_span else None
        with self._tracer.start_as_current_span(name, context=context, end_on_exit=False) as span:
            attributes = format_attributes(inputs, prefix="inputs")
            span.set_attributes(attributes)
        return span

    def stop(self, outputs: dict, current_span: Span) -> None:  # noqa: PLR6301
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """
        attributes = format_attributes(outputs, prefix="outputs")
        current_span.set_attributes(attributes)
        current_span.set_status(StatusCode.OK)
        current_span.end()

    def error(self, error: Exception, current_span: Span) -> None:  # noqa: PLR6301
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """
        attributes = format_attributes({"message": str(error), **vars(error)}, prefix="error")
        current_span.set_attributes(attributes)
        current_span.set_status(StatusCode.ERROR)
        current_span.end()
