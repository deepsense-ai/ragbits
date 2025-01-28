# How to use tracing in ragbits

Ragbits provides two options for trace handling: [**OpenTelemetry**](https://www.ibm.com/products/instana/opentelemetry)
and **CLI**.
To use either of these trace handlers, you need to import the traceable decorator from ragbits.core.audit
and apply it (@traceable) to the code you wish to trace.

You can enable the desired trace handler in your script using the following method:
```audit.set_trace_handlers(trace_handler_name)```

Here, trace_handler_name should be set to:

- `"cli"` for the CLI trace handler, which prints the processing tree to the console

- `"otel"` for the OpenTelemetry trace handler.

Keep in mind that you can use both methods in one script. Below are examples of how to configure and use each handler.

## CLI Trace Handler
You can enable the CLI trace handler in one of the following ways:

1. **Using an environment variable**:
   Set the `RAGBITS_VERBOSE` environment variable to `1`.
   Example:
```bash
export RAGBITS_VERBOSE=1
```
2. **Using the `--verbose flag`**:
   Add the --verbose option to your command.
   Example:
```bash
uv run ragbits --verbose vector-store --factory-path PATH_TO_FACTORY list
```
3. **Programmatically inside the python script**:
   Use the audit.set_trace_handlers("cli") method to explicitly set the CLI trace handler.
   Example:
```python
from ragbits.core import audit
from ragbits.core.audit import traceable


audit.set_trace_handlers("cli")
@traceable
def add_numbers(a: int, b: int) -> int:
    if a % 2 == 0:
        return add_numbers(a + 1, b)
    if a % 3 == 0:
        return add_numbers(a + 2, b)
    return a + b


if __name__ == "__main__":
    add_numbers(2, 2)
```
These options allow you to easily enable trace handling for debugging or monitoring purposes.

## OpenTelemetry Trace Handler
To export traces to an OpenTelemetry collector, configure the OpenTelemetry provider
and set the trace handler to `"otel"` (`audit.set_trace_handlers("otel")`). Here's an example script:

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from ragbits.core import audit
from ragbits.core.audit import traceable

provider = TracerProvider(resource=Resource({SERVICE_NAME: "ragbits"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter("http://localhost:4317", insecure=True)))
trace.set_tracer_provider(provider)

audit.set_trace_handlers("otel")

@traceable
def add_numbers(a: int, b: int) -> int:
    if a % 2 == 0:
        return add_numbers(a + 1, b)
    if a % 3 == 0:
        return add_numbers(a + 2, b)
    return a + b

if __name__ == "__main__":
    add_numbers(2, 2)
```
This script exports traces to a local OTLP collector running at http://localhost:4317.

### Visualizing Traces with Jaeger
To visualize traces exported by the OpenTelemetry handler, you can use Jaeger.
Follow these steps to set up Jaeger:

1. **Run Jaeger Docker container**:
```bash
docker run -d --rm --name jaeger \
    -p 16686:16686 \
    -p 4317:4317 \
    jaegertracing/all-in-one:1.62.0
```
2. **Open the Jaeger UI in your browser**:

```
http://localhost:16686
```
To check the OpenTelemetry trace handler you can also run our example:  ```examples/document-search/otel.py```
