# TODO: dev script for testing the Ragbits API client. To be deleted.

from __future__ import annotations

import asyncio
from typing import Final

from ragbits.chat import (
    AsyncRagbitsChatClient,
    ChatResponseType,
    RagbitsChatClient,
)

SERVER_URL: Final[str] = "http://127.0.0.1:8000"
TEST_MESSAGE: Final[str] = "Hello from Ragbits Python client!"


def run_sync_demo() -> None:
    print("\n=== Synchronous client ===")
    client = RagbitsChatClient(SERVER_URL)
    try:
        for chunk in client.send_message(TEST_MESSAGE):
            if chunk.type is ChatResponseType.TEXT:
                print(chunk.content, end="", flush=True)
    finally:
        client.stop()
    print("\nConversation id:", client.conversation_id)

async def run_async_demo() -> None:
    print("\n=== Asynchronous client ===")
    client = AsyncRagbitsChatClient(SERVER_URL)
    try:
        async for chunk in client.send_message(TEST_MESSAGE):
            if chunk.type is ChatResponseType.TEXT:
                print(chunk.content, end="", flush=True)
    finally:
        await client.stop()
        await client.aclose()
    print("\nConversation id:", client.conversation_id)

if __name__ == "__main__":
    run_sync_demo()
    asyncio.run(run_async_demo())
    print("\nAll done! ✅") 