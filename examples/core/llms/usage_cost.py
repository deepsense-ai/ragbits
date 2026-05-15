"""
Ragbits Core Example: Token usage and estimated cost

This example shows how to read prompt and completion token counts from an LLM
response and the estimated USD cost computed from those counts. Direct API
clients (OpenAI, Anthropic, Gemini) use bundled public list prices; actual
invoices may differ.

To run the script, execute the following command:

    ```bash
    uv run examples/core/llms/usage_cost.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core[openai]",
# ]
# ///

import asyncio

from ragbits.core.llms import OpenAILLM


async def main() -> None:
    """
    Run the example.
    """
    llm = OpenAILLM(model_name="gpt-4o-mini")
    result = await llm.generate_with_metadata("Reply with exactly one word: hello or hi.")

    if result.usage is None:
        print("No usage metadata returned by the provider for this call.")
        return

    print(f"Model: {result.usage.requests[0].model}")
    print(f"Prompt tokens: {result.usage.prompt_tokens}")
    print(f"Completion tokens: {result.usage.completion_tokens}")
    print(f"Total tokens: {result.usage.total_tokens}")
    print(f"Estimated cost (USD): {result.usage.estimated_cost:.6f}")

    manual = llm.get_estimated_cost(prompt_tokens=10_000, completion_tokens=500)
    print(f"Manual estimate for 10k prompt / 500 completion tokens: ${manual:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
