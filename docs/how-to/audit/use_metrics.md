# How-To: Track metrics with Ragbits

Similar to [traces](./use_tracing.md), Ragbits also collects metrics. These metrics offer insight into system performance, resource usage, and operational health, allowing users to monitor and optimize their workflows effectively.

## Default metrics

By default, the SDK tracks the following:

- `input_tokens`: the number of input tokens sent to the LLM
- `prompt_throughput`the time taken to process a prompt and receive a response
- `token_throughput`: the number of tokens processed per second
- `time_to_first_token`: the time taken (in seconds) to receive the first token in a streaming response

## Collecting custom metrics

...

```python
...
```

## Using OpenTelemetry meter

To export metrics to the OpenTelemetry collector, configure the provider and exporter, and set up the `OtelMetricHandler` using the `set_metric_handlers("otel")` method.

```python
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from ragbits.core.audit import set_metric_handlers

resource = Resource(attributes={SERVICE_NAME: "ragbits"})
exporter = OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True)
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
provider = MeterProvider(metric_readers=[reader], resource=resource)
metrics.set_meter_provider(provider)

set_metric_handlers("otel")
```

!!! info
    This code snippet exports metrics to the local OpenTelemetry collector running at <http://localhost:4317>. To visualize metrics from Ragbits, open a browser and navigate to the Grafana dashboard at <http://localhost:3000>.

A full example along with a detailed installation guide is available [`here`](https://github.com/deepsense-ai/ragbits/blob/main/examples/document-search/otel.py).
