import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from ragbits.conversations.history.stores.sql import (
    ChatFormat,
    Conversation,
    Message,
    SQLHistoryStore,
)

MESSAGES: ChatFormat = [
    {"role": "user", "content": "Hi"},
    {"role": "model", "content": "Hello"},
]


@pytest.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Conversation.metadata.create_all)
        await conn.run_sync(Message.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    async_session = async_sessionmaker(async_engine, expire_on_commit=False)
    return async_session


@pytest.fixture
async def history_store(async_engine: AsyncEngine) -> SQLHistoryStore:
    store = SQLHistoryStore(async_engine)
    await store.init_db()
    return store


@pytest.mark.asyncio
async def test_create_conversation(history_store: SQLHistoryStore):
    conversation_id = await history_store.create_conversation(MESSAGES)
    assert conversation_id is not None
    assert isinstance(conversation_id, str)


@pytest.mark.asyncio
async def test_fetch_conversation(history_store: SQLHistoryStore):
    MESSAGES: ChatFormat = [
        {"role": "user", "content": "Hi"},
        {"role": "model", "content": "Hello"},
    ]
    conversation_id = await history_store.create_conversation(MESSAGES)
    fetched_messages = await history_store.fetch_conversation(conversation_id)
    assert fetched_messages == MESSAGES


@pytest.mark.asyncio
async def test_update_conversation(history_store: SQLHistoryStore):
    conversation_id = await history_store.create_conversation(MESSAGES)
    new_messages: ChatFormat = [
        {"role": "user", "content": "How are you?"},
    ]
    updated_conversation_id = await history_store.update_conversation(conversation_id, new_messages)
    assert updated_conversation_id == conversation_id
    fetched_MESSAGES = await history_store.fetch_conversation(conversation_id)
    assert len(fetched_MESSAGES) == 3
    assert fetched_MESSAGES[2]["role"] == "user"
    assert fetched_MESSAGES[2]["content"] == "How are you?"


@pytest.mark.asyncio
async def test_from_config():
    config = {"sqlalchemy_engine": {"type": "AsyncEngine", "config": {"url": "sqlite+aiosqlite:///:memory:"}}}
    store = SQLHistoryStore.from_config(config)
    assert store is not None
    assert isinstance(store, SQLHistoryStore)
