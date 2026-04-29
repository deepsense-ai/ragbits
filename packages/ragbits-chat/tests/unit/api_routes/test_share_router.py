from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from ragbits.chat.api_routes import build_share_router
from ragbits.chat.auth import User
from ragbits.chat.interface.types import ChatContext
from ragbits.chat.persistence.share import SQLSharePersistence
from ragbits.chat.persistence.sql import SQLHistoryPersistence
from ragbits.core.storage.connections import SQLiteConnection


@pytest.fixture
async def app_with_user(
    request: pytest.FixtureRequest,
) -> AsyncIterator[tuple[FastAPI, User, SQLHistoryPersistence, SQLSharePersistence]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    history = SQLHistoryPersistence(engine)
    share_connection = SQLiteConnection(":memory:")
    share = SQLSharePersistence(share_connection)

    user = User(user_id="alice", username="alice", email="alice@example.com")

    async def require_user(_: Request) -> User:
        return user

    app = FastAPI()
    app.include_router(build_share_router(history, share, require_user))
    try:
        yield app, user, history, share
    finally:
        await share_connection.disconnect()
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_conversations_includes_owned_and_shared(
    app_with_user: tuple[FastAPI, User, SQLHistoryPersistence, SQLSharePersistence],
) -> None:
    app, user, history, share = app_with_user

    await history.save_interaction(
        "hello",
        "hi",
        [],
        ChatContext(conversation_id="conv-owned", message_id="m1", user=user),
        1000.0,
    )
    bob = User(user_id="bob", username="bob")
    await history.save_interaction(
        "shared",
        "yes",
        [],
        ChatContext(conversation_id="conv-shared", message_id="m2", user=bob),
        2000.0,
    )
    await share.set_shares("conv-shared", "bob", ["alice"])

    with TestClient(app) as client:
        resp = client.get("/api/conversations")
        assert resp.status_code == 200
        data = resp.json()

    ids = {c["conversation_id"] for c in data}
    assert ids == {"conv-owned", "conv-shared"}

    owned = next(c for c in data if c["conversation_id"] == "conv-owned")
    shared = next(c for c in data if c["conversation_id"] == "conv-shared")
    assert owned["is_shared"] is False
    assert shared["is_shared"] is True
    assert shared["shared_by"] == "bob"


@pytest.mark.asyncio
async def test_get_conversation_denies_non_owner_non_recipient(
    app_with_user: tuple[FastAPI, User, SQLHistoryPersistence, SQLSharePersistence],
) -> None:
    app, _, history, _ = app_with_user
    other = User(user_id="carol", username="carol")
    await history.save_interaction(
        "msg",
        "resp",
        [],
        ChatContext(conversation_id="conv-x", message_id="m1", user=other),
        1000.0,
    )

    with TestClient(app) as client:
        resp = client.get("/api/conversations/conv-x")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_shares_diff(
    app_with_user: tuple[FastAPI, User, SQLHistoryPersistence, SQLSharePersistence],
) -> None:
    app, user, history, share = app_with_user
    await history.save_interaction(
        "hello",
        "hi",
        [],
        ChatContext(conversation_id="conv-1", message_id="m1", user=user),
        1000.0,
    )
    await share.set_shares("conv-1", "alice", ["bob"])

    with TestClient(app) as client:
        resp = client.put("/api/conversations/conv-1/shares", json={"recipients": ["carol"]})
        assert resp.status_code == 200
        recipients = {s["recipient"] for s in resp.json()}

    assert recipients == {"carol"}


@pytest.mark.asyncio
async def test_dismiss_share(
    app_with_user: tuple[FastAPI, User, SQLHistoryPersistence, SQLSharePersistence],
) -> None:
    app, _, _, share = app_with_user
    await share.set_shares("conv-42", "bob", ["alice"])

    with TestClient(app) as client:
        resp = client.delete("/api/shared/conv-42")
        assert resp.status_code == 204

    assert await share.can_access("conv-42", ["alice"]) is False


@pytest.mark.asyncio
async def test_delete_requires_owner(
    app_with_user: tuple[FastAPI, User, SQLHistoryPersistence, SQLSharePersistence],
) -> None:
    app, _, history, _ = app_with_user
    other = User(user_id="carol", username="carol")
    await history.save_interaction(
        "msg",
        "resp",
        [],
        ChatContext(conversation_id="conv-carol", message_id="m1", user=other),
        1000.0,
    )

    with TestClient(app) as client:
        resp = client.delete("/api/conversations/conv-carol")
        assert resp.status_code == 404
