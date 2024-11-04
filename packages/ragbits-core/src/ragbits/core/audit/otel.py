from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode

from ragbits.core.audit.base import TraceHandler


class OtelTraceHandler(TraceHandler[Span]):
    """
    OpenTelemetry trace handler.
    """

    def __init__(self) -> None:
        super().__init__()
        self._tracer = trace.get_tracer("ragbits.events")

    def _format_data(self, data: dict, prefix: str | None = None) -> Any:  # noqa: ANN401
        flattened = {}

        for key, value in data.items():
            current_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                flattened.update(self._format_data(value, current_key))
            elif isinstance(value, list):
                # Handle lists - convert each element to simple type
                simple_list = []
                for item in value:
                    if isinstance(item, str | float | int | bool):
                        simple_list.append(item)
                    else:
                        simple_list.append(repr(item))
                flattened[current_key] = simple_list
            elif isinstance(value, str | float | int | bool):
                # Keep simple types as-is
                flattened[current_key] = value
            else:
                # Convert complex objects to string
                flattened[current_key] = repr(value)

        return flattened

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
            attributes = self._format_data(inputs, prefix="inputs")
            span.set_attributes(attributes)

        self._spans.get().append(span)

    def end(self, outputs: dict) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
        """
        span = self._spans.get().pop()
        attributes = self._format_data(outputs, prefix="outputs")
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
        span.set_status(StatusCode.ERROR)
        span.end()
