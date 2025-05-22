# Quickstart: Working with Large Language Models

Let's walk through a quick example of **basic question answering**. Specifically, let's build **a system for answering tech questions**, e.g. about Linux or iPhone apps.

Install the latest Ragbits via `pip install -U ragbits` and follow along.

## Configure environment

During development, we will use OpenAI's `gpt-4o-mini` model. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md) or [local models](../how-to/llms/use_local_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
    OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Exploring Ragbits components

...

## Evaluation

...

## Conclusions

So far, we built a very simple LLM workflow for question answering and evaluated it on a small dataset.

Can we do better? In the next guide, we will build a retrieval-augmented generation (RAG) pipeline in Ragbits for the same task. We'll see how this can boost the score substantially, then we'll use Ragbits optimizer to tune the retrieval parameters, raising our scores even more.
