# Quickstart: Building Retrieval-Augmented Generation

Let's walk through a quick example of basic question answering with and without retrieval-augmented generation (RAG) in Ragbits. Specifically, let's build a system for answering Tech questions, e.g. about Linux or iPhone apps.

Install the latest Ragbits via `pip install -U ragbits` and follow along.

## Configure Ragbits environment

Let's tell Ragbits that we will use OpenAI's `gpt-4o-mini` in our modules. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md) or [local models](../how-to/llms/use_local_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
    OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).
