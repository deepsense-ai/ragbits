from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy

from ragbits.conversations.history.store import ConversationHistoryStore


@pytest.fixture
def store():
    engine_mock = MagicMock(spec=sqlalchemy.Engine)
    return ConversationHistoryStore(engine_mock)


def test_generate_conversation_id(store: ConversationHistoryStore):
    messages = [{"role": "user", "content": "Hello"}]
    id = store.generate_conversation_id(messages)
    assert isinstance(id, str)
    assert len(id) == 64


def test_create_conversation(store: ConversationHistoryStore):
    with patch.object(store.sqlalchemy_engine, "connect") as mock_connect:
        mock_connection = mock_connect.return_value.__enter__.return_value
        mock_connection.execute.return_value.fetchone.return_value = None

        id = store.create_conversation([{"role": "user", "content": "Hello"}])
        assert isinstance(id, str)
        mock_connection.execute.assert_called()
        mock_connection.commit.assert_called_once()


def test_fetch_conversation(store: ConversationHistoryStore):
    with patch.object(store.sqlalchemy_engine, "connect") as mock_connect:
        mock_connection = mock_connect.return_value.__enter__.return_value
        mock_connection.execute.return_value.fetchall.return_value = [
            MagicMock(role="user", content="Hi"),
            MagicMock(role="model", content="Hello"),
        ]

        messages = store.fetch_conversation("id")
        assert messages == [{"role": "user", "content": "Hi"}, {"role": "model", "content": "Hello"}]


def test_update_conversation(store: ConversationHistoryStore):
    with patch.object(store.sqlalchemy_engine, "connect") as mock_connect:
        mock_connection = mock_connect.return_value.__enter__.return_value

        store.update_conversation("id", [{"role": "user", "content": "How are you?"}])
        mock_connection.execute.assert_called()
        mock_connection.commit.assert_called_once()
