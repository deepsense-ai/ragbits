# Tutorial: Multi-Agent System with A2A and MCP

Let's build a multi-agent system for automated trip planning with Ragbits. In this tutorial, we'll:

1. Build Flight Finder Agent that searches and recommends available flights between destinations with tools
1. Create City Explorer Agent that uses Model-Content-Provider (MCP) to gather and synthesize city information from the internet
1. Expose these agents through Agent-to-Agent (A2A) Protocol
1. Build an orchestrator with memory management that coordinates these specialized agents to create comprehensive trip plans

Install the latest Ragbits via `pip install -U ragbits` and follow along.

## Configuring the environment

During development, we will use OpenAI's `gpt-4.1-nano` model. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md) or [local models](../how-to/llms/use_local_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
    OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Builiding the Flight Finder Agent (Tools)

We start by defying the prompt that will lead this agent


Next, we define tool

!!! warning
    Setting keep_history=False in this case is crucial as this agent shouldn't have memory - it will 

and finally let's see how does this agent behave on it's own
 

## Building the City Explorer Agent (MCP)

This time instead of tool that we've programmed our next agent will have access to the MCP tool

### Running MCP Server

We will not [build an MCP server from scratch](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#quickstart), but run already existing one - [Web Fetcher](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) and make it available to one of our agents. Please run

```bash
pip install mcp-server-fetch
```

and then

```bash
python -m mcp_server_fetch
```
After execution the program should be running without printing anything nor raising exception

### Prompt

Since MCP tool can fetch any webpage we must remember to guide the agent how to use it correctly.

## Exposing Agent Through A2A

Run servers here

## Building the Orchestrator Agent (Memory)

build this send_message tool
