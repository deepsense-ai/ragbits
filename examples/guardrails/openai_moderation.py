# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
#     "openai",
# ]
# ///
import asyncio
from argparse import ArgumentParser

from ragbits.guardrails.base import GuardrailManager
from ragbits.guardrails.openai_moderation import OpenAIModerationGuardrail


async def guardrail_run(message: str) -> None:
    """
    Example of using the OpenAIModerationGuardrail. Requires the OPENAI_API_KEY environment variable to be set.
    """
    manager = GuardrailManager([OpenAIModerationGuardrail()])
    res = await manager.verify(message)
    print(res)


if __name__ == "__main__":
    args = ArgumentParser()
    args.add_argument("message", nargs="+", type=str, help="Message to validate")
    parsed_args = args.parse_args()

    asyncio.run(guardrail_run("".join(parsed_args.message)))
