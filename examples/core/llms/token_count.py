"""
Ragbits Core Example: Preflight token count

This example shows how to estimate prompt token count locally with
``LLM.count_tokens`` before calling the API. OpenAI uses tiktoken when
available; only user-visible text segments are counted from multimodal
messages (image and other non-text parts are skipped).

To run the script, execute the following command:

    ```bash
    uv run examples/core/llms/token_count.py
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
from ragbits.core.prompt.base import SimplePrompt


async def main() -> None:
    """
    Run the example.
    """
    llm = OpenAILLM(model_name="gpt-4o-mini")

    plain = SimplePrompt("Summarize ragbits in one sentence.")
    estimated = llm.count_tokens(plain)
    print(f"Estimated prompt tokens (plain text): {estimated}")

    multimodal = SimplePrompt(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image briefly."},
                    {"type": "image_url", "image_url": {"url": "https://example.com/photo.png"}},
                ],
            }
        ]
    )
    multimodal_estimated = llm.count_tokens(multimodal)
    print(f"Estimated prompt tokens (multimodal, text only): {multimodal_estimated}")

    result = await llm.generate_with_metadata(plain)
    if result.usage is None:
        print("No usage metadata returned by the provider for this call.")
        return

    print(f"Actual prompt tokens from API: {result.usage.prompt_tokens}")
    print(f"Difference (API - estimate): {result.usage.prompt_tokens - estimated}")


if __name__ == "__main__":
    asyncio.run(main())
