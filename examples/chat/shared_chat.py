r"""
Ragbits Chat Example: Conversation Sharing

This example demonstrates how to enable conversation sharing between authenticated
users by wiring `SQLSharePersistence` into `RagbitsAPI` alongside
`SQLHistoryPersistence`.

By default it uses SQLite for both stores so the example runs with no external
dependencies. Set ``USE_POSTGRES=1`` (and the optional ``PG_*`` env vars) to
point share persistence at a Postgres instance instead, e.g.:

    ```bash
    docker run --rm -d --name ragbits-pg \
      -e POSTGRES_USER=ragbits -e POSTGRES_PASSWORD=ragbits \
      -e POSTGRES_DB=ragbits -p 5432:5432 postgres:16
    USE_POSTGRES=1 uv run examples/chat/shared_chat.py
    ```

To run the script, execute the following command:

    ```bash
    uv run examples/chat/shared_chat.py
    ```

Log in as `alice` / `alice123` and `bob` / `bob123` in two browser windows to try it.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat[sql]",
#     "ragbits-core[sqlite,postgres]",
# ]
# ///

import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from ragbits.chat.api import RagbitsAPI
from ragbits.chat.auth.backends import ListAuthenticationBackend
from ragbits.chat.auth.session_store import InMemorySessionStore
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.chat.persistence.share import SQLSharePersistence
from ragbits.chat.persistence.sql import SQLHistoryPersistence
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import ChatFormat
from ragbits.core.storage.connections import PostgresConnection, SQLiteConnection

DB_FILE = Path(tempfile.gettempdir()) / "ragbits_shared_chat.db"
SHARES_DB_FILE = Path(tempfile.gettempdir()) / "ragbits_shared_chat_shares.db"


class SharedChat(ChatInterface):
    """An example ChatInterface with SQLite history so conversations can be shared."""

    conversation_history = True

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")
        self.history_persistence = SQLHistoryPersistence(create_async_engine(f"sqlite+aiosqlite:///{DB_FILE}"))

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Stream a reply from the LLM; persisted history is owned by `context.user`."""
        async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
            yield self.create_text_response(chunk)


def get_auth_backend() -> ListAuthenticationBackend:
    """Factory for a simple username/password backend with two demo users."""
    users = [
        {
            "user_id": "alice",
            "username": "alice",
            "password": "alice123",
            "email": "alice@example.com",
            "full_name": "Alice",
            "roles": ["user"],
        },
        {
            "user_id": "bob",
            "username": "bob",
            "password": "bob123",
            "email": "bob@example.com",
            "full_name": "Bob",
            "roles": ["user"],
        },
    ]
    return ListAuthenticationBackend(users=users, session_store=InMemorySessionStore())


def get_share_persistence() -> SQLSharePersistence:
    """Factory for a SharePersistence backed by `ragbits.core.storage`.

    Defaults to a local SQLite file. Set ``USE_POSTGRES=1`` (with optional
    ``PG_*`` overrides) to use a PostgreSQL connection instead.
    """
    if os.environ.get("USE_POSTGRES"):
        connection = PostgresConnection(
            host=os.environ.get("PG_HOST", "localhost"),
            port=int(os.environ.get("PG_PORT", "5432")),
            database=os.environ.get("PG_DB", "ragbits"),
            user=os.environ.get("PG_USER", "ragbits"),
            password=os.environ.get("PG_PASS", "ragbits"),
        )
        return SQLSharePersistence(connection)
    return SQLSharePersistence(SQLiteConnection(SHARES_DB_FILE))


if __name__ == "__main__":
    RagbitsAPI(
        SharedChat,
        auth_backend=get_auth_backend(),
        share_persistence=get_share_persistence(),
    ).run()
