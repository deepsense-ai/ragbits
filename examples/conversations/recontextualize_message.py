"""
Ragbits Conversations Example: Recontextualize Last Message

This example demonstrates how to use the `StandaloneMessageCompressor` compressor to recontextualize
the last message in a conversation history.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-conversations",
# ]
# ///

import asyncio

from ragbits.conversations.history.compressors.llm import StandaloneMessageCompressor
from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import ChatFormat

# Example conversation history
conversation: ChatFormat = [
    {"role": "user", "content": "Who's working on Friday?"},
    {"role": "assistant", "content": "Jim"},
    {"role": "user", "content": "Where is he based?"},
    {"role": "assistant", "content": "At our California Head Office"},
    {"role": "user", "content": "Is he a senior staff member?"},
    {"role": "assistant", "content": "Yes, he's a senior manager"},
    {"role": "user", "content": "What's his phone number (including the prefix for his state)?"},
]


async def main() -> None:
    """
    Main function to demonstrate the StandaloneMessageCompressor compressor.
    """
    # Initialize the LiteLLM client
    llm = LiteLLM("gpt-4o")

    # Initialize the StandaloneMessageCompressor compressor
    compressor = StandaloneMessageCompressor(llm, history_len=10)

    # Compress the conversation history
    recontextualized_message = await compressor.compress(conversation)

    # Print the recontextualized message
    print("Recontextualized Message:")
    print(recontextualized_message)


if __name__ == "__main__":
    asyncio.run(main())
