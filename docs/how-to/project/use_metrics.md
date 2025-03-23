# How-To: Track metrics with Ragbits

This guide will walk you through setting up metric tracking with Ragbits using the OpenTelemetry stack. By following these steps, you can collect, visualize, and analyze metrics in a centralized monitoring system.

## Set up the OpenTelemetry backend

To track metrics, you need a backend to receive, store, and visualize the data. We recommend using the [`grafana/otel-lgtm`](https://hub.docker.com/r/grafana/otel-lgtm) Docker image, which provides a complete OpenTelemetry stack in a single container, eliminating the need to configure and manage multiple services separately. This includes **OpenTelemetry collector**, **Prometheus** and **Grafana**. For more details on how to get started and leverage this tool, check out [the official Grafana blog post](https://grafana.com/blog/2024/03/13/an-opentelemetry-backend-in-a-docker-image-introducing-grafana/otel-lgtm/).

Run the following command to start the backend:

```bash
docker run -p 3000:3000 -p 4317:4317 -p 4318:4318 --rm -ti grafana/otel-lgtm
```

It may take a minute for the container to start up. When startup is complete, the container will print the following line to the console:

```bash
The OpenTelemetry collector and the Grafana LGTM stack are up and running.
```

## Configure OpenTelemetry in Ragbits

Before recording metrics, you need to configure OpenTelemetry and set up the metric handler in Ragbits. This ensures that all tracked data is properly processed and exported.

To send collected metrics to the OpenTelemetry collector, configure the provider and set up an exporter in your application:

```python
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from ragbits.core.audit import set_metric_handler

resource = Resource(attributes={SERVICE_NAME: "ragbits"})
exporter = OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True)
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
provider = MeterProvider(metric_readers=[reader], resource=resource)
metrics.set_meter_provider(provider)

set_metric_handler(metrics.get_meter("ragbits"))
```

This configuration enables centralized metric collection and integration with monitoring systems.

## Start Tracking Metrics

Once the OpenTelemetry backend and Ragbits are configured, you can start tracking metrics in your application. Ragbits will automatically send the collected metrics to the OpenTelemetry collector, which will then store them in Prometheus and make them available for visualization in Grafana.

## Metrics Tracked by Ragbits

Ragbits automatically tracks the following metrics during LLM interactions: the time taken to process a prompt and receive a response (`prompt_throughput`), the number of input tokens sent to the LLM (`input_tokens`), the number of tokens processed per second (`token_throughput`) and the time taken (in seconds) to receive the first token in a streaming response (`time_to_first_token`).

Each metric is tagged with the following **labels** (attributes) for better filtering and analysis: the class name of the prompt being processed (`promp`) and the name of the LLM being used (`model`).

## Visualize Metrics in Grafana

To visualize the metrics collected by Ragbits, follow these steps:

1. Open your browser and navigate to http://localhost:3000.
2. Use the default credentials to log in (username: `admin`, password: `admin`).
3. Once logged in, you can either navigate to the Explore section to query and visualize metrics directly or create a new dashboard to build custom visualizations tailored to your needs.