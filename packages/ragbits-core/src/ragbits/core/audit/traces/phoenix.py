from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from ragbits.core.audit.traces.otel import OtelTraceHandler


class PhoenixTraceHandler(OtelTraceHandler):
    """
    Phoenix trace handler.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:6006/v1/traces",
        service_name: str = "ragbits-phoenix",
    ) -> None:
        """
        Initialize the PhoenixTraceHandler instance.

        Args:
            endpoint: The Phoenix endpoint.
            service_name: The service name.
        """
        resource = Resource(attributes={SERVICE_NAME: service_name})
        span_exporter = OTLPSpanExporter(endpoint=endpoint)
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)
        super().__init__(provider=tracer_provider)
