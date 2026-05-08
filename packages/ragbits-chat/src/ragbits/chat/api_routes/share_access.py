"""Helpers used by the conversation-sharing API.

Kept in its own module so it can be unit-tested without bringing up the whole
FastAPI application.
"""

from __future__ import annotations

from ragbits.chat.auth import User


def normalize_identifier(identifier: str | None) -> str | None:
    """Return the canonical (lowercased, trimmed) form of ``identifier``.

    Returns ``None`` when the input is empty after trimming.
    """
    if identifier is None:
        return None
    normalized = identifier.strip().lower()
    return normalized or None


def recipient_identifiers(user: User) -> list[str]:
    """Return all identifiers a user can be addressed by when sharing.

    A user may be addressed by user_id, username, or email. The persistence
    layer stores recipients lowercased, so we mirror that here. Duplicates
    are removed while preserving order.
    """
    ids: list[str] = []
    seen: set[str] = set()
    for raw in (user.user_id, user.username, user.email):
        normalized = normalize_identifier(raw)
        if normalized and normalized not in seen:
            seen.add(normalized)
            ids.append(normalized)
    return ids
