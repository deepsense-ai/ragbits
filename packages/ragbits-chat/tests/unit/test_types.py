"""Unit tests for chat interface types."""

import pytest
from pydantic import ValidationError

from ragbits.chat.interface.types import ChatContext


@pytest.mark.parametrize("timezone", ["Europe/Warsaw", "America/New_York", "UTC", "Asia/Tokyo"])
def test_valid_timezone(timezone: str) -> None:
    """Test ChatContext accepts valid IANA timezones."""
    ctx = ChatContext(timezone=timezone)
    assert ctx.timezone == timezone


@pytest.mark.parametrize("timezone", ["Invalid/Timezone", "Europe/Warsow", "Not/A/Timezone"])
def test_invalid_timezone(timezone: str) -> None:
    """Test ChatContext rejects invalid timezones."""
    with pytest.raises(ValidationError, match="Invalid timezone"):
        ChatContext(timezone=timezone)


def test_none_timezone() -> None:
    """Test ChatContext with None timezone (default)."""
    ctx = ChatContext()
    assert ctx.timezone is None
