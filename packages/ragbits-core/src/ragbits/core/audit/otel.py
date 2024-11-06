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

    def start(self, name: str, inputs: dict) -> None:
        """
        Log input data at the start of the trace.

        Args:
            name: The name of the trace.
            inputs: The input data.
        """
        self._spans.set(self._spans.get()[:])
        context = trace.set_span_in_context(self._spans.get()[-1]) if self._spans.get() else None

        with self._tracer.start_as_current_span(name, context=context, end_on_exit=False) as span:
            attributes = _format_attributes(inputs, prefix="inputs")
            span.set_attributes(attributes)

        self._spans.get().append(span)

    def end(self, outputs: dict) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
        """
        span = self._spans.get().pop()
        attributes = _format_attributes(outputs, prefix="outputs")
        span.set_attributes(attributes)
        span.set_status(StatusCode.OK)
        span.end()

    def error(self, error: Exception) -> None:
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
        """
        span = self._spans.get().pop()
        attributes = _format_attributes(vars(error), prefix="error")
        span.set_attributes(attributes)
        span.set_status(StatusCode.ERROR)
        span.end()


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
