from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode, TracerProvider
from opentelemetry.util.types import AttributeValue

from ragbits.core.audit.base import TraceHandler


class OtelTraceHandler(TraceHandler[Span]):
    """
    OpenTelemetry trace handler.
    """

    def __init__(self, provider: TracerProvider | None = None) -> None:
        """
        Constructs a new OtelTraceHandler instance.

        Args:
            provider: The tracer provider to use.
        """
        super().__init__()
        self._tracer = trace.get_tracer(instrumenting_module_name=__name__, tracer_provider=provider)

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
        context = trace.set_span_in_context(current_span) if current_span else None

        with self._tracer.start_as_current_span(name, context=context, end_on_exit=False) as span:
            attributes = _format_attributes(inputs, prefix="inputs")
            span.set_attributes(attributes)

        return span

    def stop(self, outputs: dict, current_span: Span) -> None:  # noqa: PLR6301
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """
        attributes = _format_attributes(outputs, prefix="outputs")
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
        attributes = _format_attributes(vars(error), prefix="error")
        current_span.set_attributes(attributes)
        current_span.set_status(StatusCode.ERROR)
        current_span.end()


def _format_attributes(data: dict, prefix: str | None = None) -> dict[str, AttributeValue]:
    """
    Format attributes for OpenTelemetry.

    Args:
        data: The data to format.
        prefix: The prefix to use for the keys.

    Returns:
        The formatted attributes.
    """
    flattened = {}

    for key, value in data.items():
        current_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            flattened.update(_format_attributes(value, current_key))
        elif isinstance(value, list | tuple):
            flattened[current_key] = [
                item if isinstance(item, str | float | int | bool) else repr(item)
                for item in value  # type: ignore
            ]
        elif isinstance(value, str | float | int | bool):
            flattened[current_key] = value
        else:
            flattened[current_key] = repr(value)

    return flattened
