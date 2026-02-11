import json

from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span

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
        span = super().start(name, inputs, current_span)

        # Check if it's an LLM generation
        if "generate" in name.lower():
            span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.LLM.value)

            if "model_name" in inputs:
                span.set_attribute(SpanAttributes.LLM_MODEL_NAME, inputs["model_name"])

            if "prompt" in inputs:
                span.set_attribute(SpanAttributes.INPUT_VALUE, str(inputs["prompt"]))

            if "options" in inputs:
                span.set_attribute(SpanAttributes.LLM_INVOCATION_PARAMETERS, str(inputs["options"]))

        return span

    def stop(self, outputs: dict, current_span: Span) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """
        if "response" in outputs:
            response = outputs["response"]
            # If response is a list of objects, serialize it
            if isinstance(response, list | dict):
                try:
                    current_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(str(response)))
                except (TypeError, ValueError):
                    current_span.set_attribute(SpanAttributes.OUTPUT_VALUE, str(response))
            else:
                current_span.set_attribute(SpanAttributes.OUTPUT_VALUE, str(response))

        super().stop(outputs, current_span)
