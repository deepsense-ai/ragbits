from ragbits.chat.api_routes.share_access import normalize_identifier, recipient_identifiers
from ragbits.chat.auth import User


def test_normalize_identifier_lowercases_and_trims() -> None:
    assert normalize_identifier("  Alice  ") == "alice"
    assert normalize_identifier("Bob@Example.com") == "bob@example.com"


def test_normalize_identifier_returns_none_for_empty() -> None:
    assert normalize_identifier(None) is None
    assert normalize_identifier("") is None
    assert normalize_identifier("   ") is None


def test_recipient_identifiers_collects_all_fields() -> None:
    user = User(user_id="U1", username="Alice", email="Alice@Example.com")

    ids = recipient_identifiers(user)

    assert ids == ["u1", "alice", "alice@example.com"]


def test_recipient_identifiers_deduplicates() -> None:
    user = User(user_id="alice", username="alice", email="alice@example.com")

    ids = recipient_identifiers(user)

    assert ids == ["alice", "alice@example.com"]


def test_recipient_identifiers_skips_none_fields() -> None:
    user = User(user_id="alice", username="alice")

    ids = recipient_identifiers(user)

    assert ids == ["alice"]
