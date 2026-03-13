# How-To: Trace code execution with Ragbits

Each component of Ragbits includes built-in tracing, enabling users to collect detailed telemetry data without additional configuration. These traces provide visibility into execution flow, performance characteristics, and potential bottlenecks.

## Default tracing

By default, the SDK traces the following:

- LLM generation and streaming
- Embedder calls for text and image embeddings
- Sources data fetching
- Vector Store operations - retrieve, store, remove and list
- Document Search operations - search and ingest

## Tracing your own code

The main component of the tracing system is the trace. Traces need to be started and finished. You can create a trace in two ways:

1. Using the [`trace()`][ragbits.core.audit.traces.trace] context manager.

    ```python
    from ragbits.core.audit import trace

    def add_numbers(a: int, b: int) -> int:
        with trace(name="add_numbers", a=a, b=b) as outputs:
            outputs.result = a + b
        return outputs.result
    ```

2. Using the [`@traceable`][ragbits.core.audit.traces.traceable] decorator.

    ```python
    from ragbits.core.audit import traceable

    @traceable
    def add_numbers(a: int, b: int) -> int:
        return a + b
    ```

The current trace is tracked via a Python `contextvar`. This means that it works with concurrency automatically. During runtime traces are populated to the configured trace handleres defined via [`set_trace_handlers`][ragbits.core.audit.traces.set_trace_handlers].

## Using CLI tracer

To print traces locally in the CLI, configure [`CLITraceHandler`][ragbits.core.audit.traces.cli.CLITraceHandler]. You can enable the CLI tracer in a few ways:

1. Setting the environment variable `RAGBITS_VERBOSE=1`
2. Using the `--verbose` flag in the Ragbits CLI `uv run ragbits --verbose ...`
3. Using the `set_trace_handlers("cli")` function explicitly in your script

## Using OpenTelemetry tracer

To export traces to the OpenTelemetry collector, configure the provider and exporter, and set up the [`OtelTraceHandler`][ragbits.core.audit.traces.otel.OtelTraceHandler] using the [`set_trace_handlers`][ragbits.core.audit.traces.set_trace_handlers] method.

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from ragbits.core.audit import set_trace_handlers

resource = Resource(attributes={SERVICE_NAME: "ragbits-example"})
span_exporter = OTLPSpanExporter("http://localhost:4317", insecure=True)
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter, max_export_batch_size=1))
trace.set_tracer_provider(tracer_provider)

set_trace_handlers("otel")
```

!!! info
    This code snippet exports traces to the local OpenTelemetry collector running at <http://localhost:4317>. To visualize traces from Ragbits, open a browser and navigate to the Grafana dashboard at <http://localhost:3000>.

A full example along with a detailed installation guide is available [`here`](https://github.com/deepsense-ai/ragbits/blob/main/examples/core/audit/otel.py).

## Using Logfire tracer

To export traces to the Logfire collector, you need to generate a write token in your Logfire project settings and set it as an environment variable.

```bash
export LOGFIRE_TOKEN=<your-logfire-write-token>
```

Then set up the [`LogfireTraceHandler`][ragbits.core.audit.traces.logfire.LogfireTraceHandler] using the [`set_trace_handlers`][ragbits.core.audit.traces.set_trace_handlers] method.

```python
from ragbits.core.audit import set_trace_handlers

set_trace_handlers("logfire")
```

You will find collected traces in the Live section of the Logfire project dashboard.
A full example along with a detailed guide is available [`here`](https://github.com/deepsense-ai/ragbits/blob/main/examples/core/audit/logfire_.py).

## Using Arize Phoenix tracer

[Arize Phoenix](https://github.com/Arize-ai/phoenix) is an open-source observability platform for LLM applications. Ragbits integrates with Phoenix using OpenInference Semantic Conventions for rich AI-specific tracing.

### Installation

Install Ragbits with the Phoenix extra:

```bash
pip install "ragbits-core[phoenix]"
```

### Running the Phoenix Server

Before collecting traces, start a local Phoenix server:

```bash
pip install arize-phoenix
phoenix serve
```

The Phoenix UI will be available at <http://localhost:6006>.

### Enabling Phoenix Tracing

Set up the `PhoenixTraceHandler` using the [`set_trace_handlers`][ragbits.core.audit.traces.set_trace_handlers] method:

```python
from ragbits.core.audit import set_trace_handlers

set_trace_handlers("phoenix")
```

By default, the handler exports traces to `http://localhost:6006/v1/traces`. The handler automatically enriches LLM generation spans with OpenInference attributes like model name, prompts, and responses.

### Custom Endpoint

To use a remote Phoenix instance, configure the handler directly:

```python
from ragbits.core.audit import set_trace_handlers
from ragbits.core.audit.traces.phoenix import PhoenixTraceHandler

handler = PhoenixTraceHandler(
    endpoint="https://your-phoenix-instance.com/v1/traces",
    service_name="my-ragbits-app"
)
set_trace_handlers(handler)
```

A full example is available [`here`](https://github.com/deepsense-ai/ragbits/blob/main/examples/core/audit/phoenix.py).
