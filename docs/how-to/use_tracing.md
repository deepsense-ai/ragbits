# How to use tracing in ragbits
Ragbits offers two trace handlers opentelemetry and cli
to use one of the suppoorted tracehandler you need tyo import
from ragbits.core.audit import traceable and use @traceble for the code you want to be rtaced




## CLI Trace Handler
launch with 
- environmental variable export RAGBITS_VERBOSE=1

- --verbose option
audit.set_trace_handlers("cli")
from ragbits.core import audit
from ragbits.core.audit import traceable
audit.set_trace_handlers("cli")
@traceable
def add_numbers(a: int, b: int) -> int:
    if a % 2 == 0:
        return add_numbers(a + 1, b)
    return a + b


## Open Telemetry

audit.set_trace_handlers("otel")
The script exports traces to the local OTLP collector running on `http://localhost:4317`. To visualize the traces,
you can use Jeager. The recommended way to run it is using the official Docker image:

    1. Run Jaeger Docker container:

        ```bash
        docker run -d --rm --name jaeger \
            -p 16686:16686 \
            -p 4317:4317 \
            jaegertracing/all-in-one:1.62.0
        ```

    2. Open the Jaeger UI in your browser:

        ```
        http://localhost:16686
        ```
"""
    


@traceable
from ragbits.core.audit import traceable

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from ragbits.core import audit


provider = TracerProvider(resource=Resource({SERVICE_NAME: "ragbits"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter("http://localhost:4317", insecure=True)))
trace.set_tracer_provider(provider)

audit.set_trace_handlers("otel")

see example: example/otel.py