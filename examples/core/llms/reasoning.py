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
#     "ragbits-core",
# ]
# ///

import asyncio

from ragbits.core.llms import LiteLLM, LiteLLMOptions


async def main() -> None:
    """
    Run the example.
    """
    options = LiteLLMOptions(reasoning_effort="medium")
    model = LiteLLM(model_name="claude-3-7-sonnet-20250219", default_options=options)
    response = await model.generate_with_metadata(
        "Do you like Jazz?",
    )
    print(f"reasoning: {response.reasoning}")

    options = LiteLLMOptions(thinking={"type": "enabled", "budget_tokens": 1024})
    model = LiteLLM(model_name="claude-3-7-sonnet-20250219", default_options=options)
    response = await model.generate_with_metadata(
        "Do you like Jazz?",
    )
    print(f"reasoning: {response.reasoning}")


if __name__ == "__main__":
    asyncio.run(main())
