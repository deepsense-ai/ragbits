"""
Ragbits Core Example: OpenTelemetry Audit

This example demonstrates how to collect traces and metrics using Ragbits audit module with OpenTelemetry.
We run the LLM generation several times to collect telemetry data, and then export it to the OpenTelemetry collector and visualize it in Grafana.

The script exports traces to the local OTLP collector running on http://localhost:4317.
The recommended way to run it is using the official Docker image:

    ```bash
    docker run \
        --mount type=bind,src=./examples/core/audit/config/grafana/ragbits-dashboard.json,dst=/otel-lgtm/ragbits-dashboard.json \
        --mount type=bind,src=./examples/core/audit/config/grafana/grafana-dashboards.yaml,dst=/otel-lgtm/grafana/conf/provisioning/dashboards/grafana-dashboards.yaml \
        -p 3000:3000 -p 4317:4317 -p 4318:4318 --rm -ti grafana/otel-lgtm
    ```

To run the script, execute the following command:

    ```bash
    uv run examples/core/audit/otel.py
    ```

To visualize the metrics collected by Ragbits, follow these steps:

    1. Open your browser and navigate to http://localhost:3000.
    2. To check collected metrics, go to the Dashboards section and select Ragbits (make sure auto refresh is enabled).
    3. To check collected traces, go to the Drilldown/Traces section.
"""  # noqa: E501

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core[otel]",
#     "opentelemetry-sdk",
#     "opentelemetry-exporter-otlp-proto-grpc",
#     "google-auth>=2.35.0",
#     "tqdm",
# ]
# ///

import asyncio
from collections.abc import AsyncGenerator

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel
from tqdm.asyncio import tqdm

from ragbits.core.audit import set_metric_handlers, set_trace_handlers, traceable
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt

resource = Resource({SERVICE_NAME: "ragbits-example"})

# Otel tracer provider setup
span_exporter = OTLPSpanExporter("http://localhost:4317", insecure=True)
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter, max_export_batch_size=1))
trace.set_tracer_provider(tracer_provider)

# Otel meter provider setup
metric_exporter = OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True)
reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=1000)
meter_provider = MeterProvider(metric_readers=[reader], resource=resource)
metrics.set_meter_provider(meter_provider)

# Ragbits observability setup
set_trace_handlers("otel")
set_metric_handlers("otel")


class PhilosopherPromptInput(BaseModel):
    """
    Input format for the philosopher prompt.
    """

    philosopher_type: str
    question: str


class PromptOutput(BaseModel):
    """
    Output format for the philosopher prompt.
    """

    answer: str


class PhilosopherPrompt(Prompt[PhilosopherPromptInput, PromptOutput]):
    """
    The philospher prompt.
    """

    system_prompt = """
    You are an ancient {{ philosopher_type }} philosopher. Answer the user's question exhaustively.
    """
    user_prompt = """
    Question: {{ question }}
    """


class AssistantPromptInput(BaseModel):
    """
    Input format for the assistant prompt.
    """

    knowledge: list[str]
    question: str


class AssistantPrompt(Prompt[AssistantPromptInput, PromptOutput]):
    """
    The assistant prompt.
    """

    system_prompt = """
    Answer the user question based on the knowledge provided.
    """
    user_prompt = """
    Question: {{ question }}

    Knowledge:
    {% for item in knowledge %}
        {{ item }}
    {% endfor %}
    """


@traceable
async def process_request() -> None:
    """
    Process an example request.
    """
    question = "What's the meaning of life?"
    philosophers = [
        LiteLLM(model_name="gpt-4.1-2025-04-14", use_structured_output=True),
        LiteLLM(model_name="claude-3-7-sonnet-20250219", use_structured_output=True),
        LiteLLM(model_name="gemini-2.0-flash", use_structured_output=True),
    ]
    prompts = [
        PhilosopherPrompt(PhilosopherPromptInput(question=question, philosopher_type=philosopher_type))
        for philosopher_type in ["nihilist", "stoic", "existentialist"]
    ]
    responses = await asyncio.gather(*[
        llm.generate(prompt) for llm, prompt in zip(philosophers, prompts, strict=False)
    ])

    assistant = LiteLLM(model_name="o3", use_structured_output=True)
    prompt = AssistantPrompt(
        AssistantPromptInput(question=question, knowledge=[response.answer for response in responses])
    )
    async for _ in assistant.generate_streaming(prompt):
        pass


async def main() -> None:
    """
    Run the example.
    """

    async def run() -> AsyncGenerator:
        for _ in range(5):
            await process_request()
            yield

    async for _ in tqdm(run()):
        pass


if __name__ == "__main__":
    asyncio.run(main())
