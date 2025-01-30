import asyncio

from rich import print as pprint

from ragbits.conversations.piepline.pipeline import ConversationPiepline
from ragbits.core.llms.litellm import LiteLLM


async def main() -> None:
    """
    Example of using convcrsation pipeline
    """
    llm = LiteLLM("gpt-4o")
    pipeline = ConversationPiepline(llm)

    question = "What is my favorite fruit?"
    result = await pipeline.run(question)
    pprint("[b][blue]The user asked:[/blue][b]")
    pprint(question)
    print()

    pprint("[b][blue]The LLM generated the following response:[/blue][b]\n")
    async for response in result.output_stream:
        pprint(response, end="", flush=True)

    pprint("\n\n[b][blue]The plugin metadata is:[/blue][b]\n")
    pprint(result.plugin_metadata)


if __name__ == "__main__":
    asyncio.run(main())
