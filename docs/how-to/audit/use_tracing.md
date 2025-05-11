# How-To: Trace code execution with Ragbits

Each component of Ragbits includes built-in tracing, enabling users to collect detailed telemetry data without additional configuration. These traces provide visibility into execution flow, performance characteristics, and potential bottlenecks.

## Default tracing

By default, the SDK traces the following:

- LLM generation and streaming
- Embedder calls for text and image embeddings
- Vector Store operations: `retrieve()`, `store()`, `remove()` and `list()`
- Sources data fetching
- Document Search operations: `search()` and `ingest()`

## Tracing your own code

The main component of the tracing system is the trace. Traces need to be started and finished. You can create a trace in two ways:

1. Using the `trace()` context manager.

    ```python
    from ragbits.core.audit import trace

    def add_numbers(a: int, b: int) -> int:
        with trace(name="add_numbers", a=a, b=b) as outputs:
            outputs.result = a + b
        return outputs.result
    ```

2. Using the `@traceable` decorator.

    ```python
    from ragbits.core.audit import traceable

    @traceable
    def add_numbers(a: int, b: int) -> int:
        return a + b
    ```

The current trace is tracked via a Python `contextvar`. This means that it works with concurrency automatically. During runtime traces are populated to the configured trace handleres defined via `set_trace_handlers(...)`.

## Using CLI tracer

To print traces locally in the CLI, configure `CLITraceHandler`. You can enable the CLI tracer in a few ways:

1. Setting the environment variable `RAGBITS_VERBOSE=1`
2. Using the `--verbose` flag in the Ragbits CLI `uv run ragbits --verbose ...`
3. Using the `set_trace_handlers("cli")` function explicitly in your script

## Using OpenTelemetry tracer

To export traces to the OpenTelemetry collector, configure the provider and exporter, and set up the `OtelTraceHandler` using the `set_trace_handlers` method.

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from ragbits.core.audit import set_trace_handlers

provider = TracerProvider(resource=Resource({SERVICE_NAME: "ragbits"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter("http://localhost:4317", insecure=True)))
trace.set_tracer_provider(provider)

set_trace_handlers("otel")
```

!!! info
    This code snippet exports traces to the local OpenTelemetry collector running at <http://localhost:4317>. To visualize traces from Ragbits, open a browser and navigate to the Grafana dashboard at <http://localhost:3000>.

A full example along with a detailed installation guide is available [`here`](https://github.com/deepsense-ai/ragbits/blob/main/examples/document-search/otel.py).
