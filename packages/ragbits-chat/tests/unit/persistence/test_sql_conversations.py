import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from ragbits.chat.auth.types import User
from ragbits.chat.interface.types import ChatContext
from ragbits.chat.persistence.sql import SQLHistoryPersistence


@pytest.fixture
async def persistence() -> SQLHistoryPersistence:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    return SQLHistoryPersistence(engine)


@pytest.mark.asyncio
async def test_save_interaction_stores_user_id(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice", email="alice@example.com")
    context = ChatContext(conversation_id="conv-1", message_id="msg-1", user=user)

    await persistence.save_interaction("Hello", "Hi", [], context, 1000.0)

    owner = await persistence.get_conversation_owner("conv-1")
    assert owner == "user-1"


@pytest.mark.asyncio
async def test_list_conversations_returns_owned(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice")
    ctx1 = ChatContext(conversation_id="conv-1", message_id="msg-1", user=user)
    ctx2 = ChatContext(conversation_id="conv-2", message_id="msg-2", user=user)

    await persistence.save_interaction("msg1", "resp1", [], ctx1, 1000.0)
    await persistence.save_interaction("msg2", "resp2", [], ctx2, 2000.0)

    convos = await persistence.list_conversations("user-1")
    ids = {c["id"] for c in convos}

    assert ids == {"conv-1", "conv-2"}


@pytest.mark.asyncio
async def test_list_conversations_excludes_other_users(persistence: SQLHistoryPersistence) -> None:
    alice = User(user_id="alice", username="alice")
    bob = User(user_id="bob", username="bob")

    ctx_a = ChatContext(conversation_id="conv-a", message_id="m1", user=alice)
    ctx_b = ChatContext(conversation_id="conv-b", message_id="m2", user=bob)
    await persistence.save_interaction("a", "b", [], ctx_a, 1000.0)
    await persistence.save_interaction("c", "d", [], ctx_b, 2000.0)

    alice_convos = await persistence.list_conversations("alice")
    assert len(alice_convos) == 1
    assert alice_convos[0]["id"] == "conv-a"


@pytest.mark.asyncio
async def test_get_conversation_owner_not_found(persistence: SQLHistoryPersistence) -> None:
    owner = await persistence.get_conversation_owner("nonexistent")
    assert owner is None


@pytest.mark.asyncio
async def test_list_conversations_respects_limit(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice")
    for i in range(5):
        ctx = ChatContext(conversation_id=f"conv-{i}", message_id=f"msg-{i}", user=user)
        await persistence.save_interaction(f"msg{i}", f"resp{i}", [], ctx, float(1000 + i))

    convos = await persistence.list_conversations("user-1", limit=3)
    assert len(convos) == 3
