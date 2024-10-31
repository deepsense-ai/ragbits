from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode
from ragbits.core.audit.base import TraceHandler


class OtelTraceHandler(TraceHandler):
    """
    OpenTelemetry trace handler.
    """

    def __init__(self) -> None:
        self._tracer = trace.get_tracer("ragbits.events")

    async def on_start(self, **inputs: Any) -> None:
        with self._tracer.start_as_current_span("request", end_on_exit=False) as span:
            for key, value in inputs.items():
                span.set_attribute(key, value)

    async def on_end(self, **outputs: Any) -> None:
        span = trace.get_current_span()
        for key, value in outputs.items():
            span.set_attribute(key, value)
        span.set_status(StatusCode.OK)
        span.end()

    async def on_error(self, error: Exception) -> None:
        print("on_error", error)
