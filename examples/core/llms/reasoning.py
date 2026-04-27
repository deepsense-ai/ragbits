"""
Ragbits Core Example: Reasoning with LLM

This example demonstrates how to use reasoning with LLM.

To run the script, execute the following command:

    ```bash
    uv run examples/core/llms/reasoning.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core[anthropic]",
# ]
# ///

import asyncio

from ragbits.core.llms import AnthropicLLM, AnthropicLLMOptions


async def main() -> None:
    """
    Run the example.
    """
    options = AnthropicLLMOptions(thinking={"type": "enabled", "budget_tokens": 1024})
    model = AnthropicLLM(model_name="claude-haiku-4-5-20251001", default_options=options)
    response = await model.generate_with_metadata(
        "Do you like Jazz?",
    )
    print(f"reasoning: {response.reasoning}")

    options = AnthropicLLMOptions(thinking={"type": "enabled", "budget_tokens": 1024})
    model = AnthropicLLM(model_name="claude-haiku-4-5-20251001", default_options=options)
    response = await model.generate_with_metadata(
        "Do you like Jazz?",
    )
    print(f"reasoning: {response.reasoning}")


if __name__ == "__main__":
    asyncio.run(main())
