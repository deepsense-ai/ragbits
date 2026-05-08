import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from ragbits.chat.auth.types import User
from ragbits.chat.interface.types import ChatContext, ConversationSummaryContent, ConversationSummaryResponse
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


@pytest.mark.asyncio
async def test_list_conversations_orders_by_last_interaction(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice")
    conv_1_ctx_1 = ChatContext(conversation_id="conv-1", message_id="msg-1", user=user)
    conv_2_ctx_1 = ChatContext(conversation_id="conv-2", message_id="msg-2", user=user)
    conv_1_ctx_2 = ChatContext(conversation_id="conv-1", message_id="msg-3", user=user)

    await persistence.save_interaction("first", "resp1", [], conv_1_ctx_1, 1000.0)
    await persistence.save_interaction("second", "resp2", [], conv_2_ctx_1, 2000.0)
    await persistence.save_interaction("third", "resp3", [], conv_1_ctx_2, 3000.0)

    convos = await persistence.list_conversations("user-1")
    assert [c["id"] for c in convos] == ["conv-1", "conv-2"]


@pytest.mark.asyncio
async def test_summary_falls_back_to_first_message(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice")
    ctx1 = ChatContext(conversation_id="conv-1", message_id="msg-1", user=user)
    ctx2 = ChatContext(conversation_id="conv-1", message_id="msg-2", user=user)

    await persistence.save_interaction("first message", "resp1", [], ctx1, 1000.0)
    await persistence.save_interaction("second message", "resp2", [], ctx2, 2000.0)

    summaries = await persistence.get_conversation_summaries(["conv-1"])
    assert summaries == {"conv-1": "first message"}


@pytest.mark.asyncio
async def test_summary_prefers_conversation_summary_response(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice")
    ctx1 = ChatContext(conversation_id="conv-1", message_id="msg-1", user=user)
    ctx2 = ChatContext(conversation_id="conv-1", message_id="msg-2", user=user)

    await persistence.save_interaction("first message", "resp1", [], ctx1, 1000.0)
    summary_response = ConversationSummaryResponse(content=ConversationSummaryContent(summary="LLM summary"))
    await persistence.save_interaction("second message", "resp2", [summary_response], ctx2, 2000.0)

    summaries = await persistence.get_conversation_summaries(["conv-1"])
    assert summaries == {"conv-1": "LLM summary"}


@pytest.mark.asyncio
async def test_summary_uses_latest_conversation_summary_response(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice")
    ctx1 = ChatContext(conversation_id="conv-1", message_id="msg-1", user=user)
    ctx2 = ChatContext(conversation_id="conv-1", message_id="msg-2", user=user)

    older_summary = ConversationSummaryResponse(content=ConversationSummaryContent(summary="older"))
    newer_summary = ConversationSummaryResponse(content=ConversationSummaryContent(summary="newer"))
    await persistence.save_interaction("hi", "resp1", [older_summary], ctx1, 1000.0)
    await persistence.save_interaction("again", "resp2", [newer_summary], ctx2, 2000.0)

    summaries = await persistence.get_conversation_summaries(["conv-1"])
    assert summaries == {"conv-1": "newer"}


@pytest.mark.asyncio
async def test_summary_truncates_long_first_message(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice")
    ctx = ChatContext(conversation_id="conv-1", message_id="msg-1", user=user)
    long_message = "x" * 200

    await persistence.save_interaction(long_message, "resp", [], ctx, 1000.0)

    summaries = await persistence.get_conversation_summaries(["conv-1"])
    assert summaries["conv-1"].endswith("…")
    assert len(summaries["conv-1"]) == 81


@pytest.mark.asyncio
async def test_save_interaction_persists_summary_column(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice")
    ctx = ChatContext(conversation_id="conv-1", message_id="msg-1", user=user)
    summary_response = ConversationSummaryResponse(content=ConversationSummaryContent(summary="LLM summary"))

    await persistence.save_interaction("hi", "resp", [summary_response], ctx, 1000.0)

    convos = await persistence.list_conversations("user-1")
    assert len(convos) == 1
    assert convos[0]["summary"] == "LLM summary"


@pytest.mark.asyncio
async def test_save_interaction_does_not_overwrite_existing_summary(persistence: SQLHistoryPersistence) -> None:
    user = User(user_id="user-1", username="alice")
    ctx1 = ChatContext(conversation_id="conv-1", message_id="msg-1", user=user)
    ctx2 = ChatContext(conversation_id="conv-1", message_id="msg-2", user=user)
    summary_response = ConversationSummaryResponse(content=ConversationSummaryContent(summary="LLM summary"))

    await persistence.save_interaction("hi", "resp1", [summary_response], ctx1, 1000.0)
    await persistence.save_interaction("again", "resp2", [], ctx2, 2000.0)

    summaries = await persistence.get_conversation_summaries(["conv-1"])
    assert summaries == {"conv-1": "LLM summary"}
