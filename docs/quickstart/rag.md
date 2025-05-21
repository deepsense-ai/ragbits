# Quickstart: Building Retrieval-Augmented Generation

Let's now go through a more advanced **question answering system** with **retrieval-augmented generation** (RAG) in Ragbits. We will use the same dataset as in [the previous example](./llms.md), but we will try to improve the performance.

Install the latest Ragbits via `pip install -U ragbits` and follow along.

## Configure environment

During development, we will use OpenAI's `gpt-4o-mini` model. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md) or [local models](../how-to/llms/use_local_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
    OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Setup retriever

...

## Evaluation

...

## Conclusions

...
