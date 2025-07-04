# How-To: Track metrics with Ragbits

Similar to [traces](./use_tracing.md), Ragbits also collects metrics. These metrics offer insight into system performance, resource usage, and operational health, allowing users to monitor and optimize their workflows effectively.

## Default metrics

By default, the SDK tracks histogram metrics for LLMs:

- `input_tokens`: the number of input tokens sent to the model
- `prompt_throughput`: the time taken to process a prompt and receive a response
- `token_throughput`: the number of tokens processed per second
- `time_to_first_token`: the time taken (in seconds) to receive the first token in a streaming response

## Supported metric types

Ragbits supports three types of metrics:

1. **Histogram metrics**: For tracking the distribution of values (like durations, sizes)
2. **Counter metrics**: For tracking counts of events (like requests, errors)
3. **Gauge metrics**: For tracking current values that can increase or decrease (like memory usage)

## Registering custom metrics

To register a custom metric, use the [`register_metric`][ragbits.core.audit.metrics.register_metric] function:

```python
from enum import Enum
from ragbits.core.audit.metrics import register_metric
from ragbits.core.audit.metrics.base import Metric, MetricType

# You can define metrics as enums for type safety
class MyHistogramMetrics(str, Enum):
    REQUEST_DURATION = "request_duration"

class MyCounterMetrics(str, Enum):
    REQUEST_COUNT = "request_count"

# Register a histogram metric
register_metric(
    MyHistogramMetrics.REQUEST_DURATION,
    Metric(
        name="request_duration",
        description="Duration of requests in milliseconds",
        unit="ms",
        type=MetricType.HISTOGRAM,
    ),
)

# Register a counter metric
register_metric(
    MyCounterMetrics.REQUEST_COUNT,
    Metric(
        name="request_count",
        description="Number of requests processed",
        unit="requests",
        type=MetricType.COUNTER,
    ),
)
```

## Recording metrics

To record metric values, use the [`record_metric`][ragbits.core.audit.metrics.record_metric] function:

```python
from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import MetricType

# Record a histogram value
record_metric(
    MyHistogramMetrics.REQUEST_DURATION,
    150,  # 150ms duration
    metric_type=MetricType.HISTOGRAM,
    endpoint="/api/search"  # Additional attributes
)

# Record a counter increment
record_metric(
    MyCounterMetrics.REQUEST_COUNT,
    1,  # Increment by 1
    metric_type=MetricType.COUNTER,
    endpoint="/api/search",
    status_code=200
)
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
