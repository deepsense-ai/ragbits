"""
Ragbits Core Example: Local LLM with Ollama via LiteLLM

This example demonstrates how to use LiteLLM to connect to a model hosted locally by Ollama.
Before running, make sure Ollama is installed and the model is available:

    ```bash
    ollama pull llama3.2
    ollama serve
    ```

To run the script, execute the following command:

    ```bash
    uv run examples/core/llms/ollama.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
# ]
# ///

import asyncio

from ragbits.core.llms import LiteLLM

OLLAMA_API_BASE = "http://localhost:11434"
OLLAMA_MODEL = "ollama/llama3.2"


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM(model_name=OLLAMA_MODEL, api_base=OLLAMA_API_BASE)
    response = await llm.generate("What is the capital of Poland?")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
