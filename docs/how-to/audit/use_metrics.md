# How-To: Track metrics with Ragbits

Similar to [traces](./use_tracing.md), Ragbits also collects metrics. These metrics offer insight into system performance, resource usage, and operational health, allowing users to monitor and optimize their workflows effectively.

## Default metrics

By default, the SDK tracks only histogram metrics for LLMs:

- `input_tokens`: the number of input tokens sent to the model
- `prompt_throughput`the time taken to process a prompt and receive a response
- `token_throughput`: the number of tokens processed per second
- `time_to_first_token`: the time taken (in seconds) to receive the first token in a streaming response

!!! info
    For now Ragbits support only histogram metrics, in the future we plan to extend the API for counter and gauge metrics.

## Collecting custom metrics

The Histogram metric is particularly useful when you want to measure the distribution of a set of values.

You can use this metric for measuring things like:

- The duration of a request.
- The size of a file.
- The number of items in a list.

To create a histogram metric, use the [`create_histogram`][ragbits.core.audit.metrics.create_histogram] function.

```python
from ragbits.core.audit import create_histogram, record

request_duration = create_histogram(
    name="request_duration",
    unit="ms",
    description="Duration of requests",
)

for duration in [10, 20, 30, 40, 50]:
    record(request_duration, duration)
```

## Using OpenTelemetry meter

To export metrics to the OpenTelemetry collector, configure the provider and exporter, and set up the [`OtelMetricHandler`][ragbits.core.audit.metrics.otel.OtelMetricHandler] using the [`set_metric_handlers`][ragbits.core.audit.metrics.set_metric_handlers] method.

```python
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from ragbits.core.audit import set_metric_handlers

resource = Resource(attributes={SERVICE_NAME: "ragbits-example"})
metric_exporter = OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=1000)
metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader], resource=resource))

set_metric_handlers("otel")
```

!!! info
    This code snippet exports metrics to the local OpenTelemetry collector running at <http://localhost:4317>. To visualize metrics from Ragbits, open a browser and navigate to the Grafana dashboard at <http://localhost:3000>.

A full example along with a detailed installation guide is available [`here`](https://github.com/deepsense-ai/ragbits/blob/main/examples/core/audit/otel.py).

## Using Logfire meter

To export metrics to the Logfire collector, you need to generate a write token in your Logfire project settings and set it as an environment variable.

```bash
export LOGFIRE_TOKEN=<your-logfire-write-token>
```

Create a new project dashboard based on the "Basic System Metrics (Logfire)" template. This template includes pre-configured panels for visualizing system metrics.

Then set up the [`LogfireMetricHandler`][ragbits.core.audit.metrics.logfire.LogfireMetricHandler] using the [`set_metric_handlers`][ragbits.core.audit.metrics.set_metric_handlers] method.

```python
from ragbits.core.audit import set_metric_handlers

set_metric_handlers("logfire")
```

You will find collected metrics in the dashboard you created before.
A full example along with a detailed guide is available [`here`](https://github.com/deepsense-ai/ragbits/blob/main/examples/core/audit/logfire_.py).
