from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar

from typing_extensions import Self

from ragbits.core.audit.traces import traceable
from ragbits.core.sources.base import Source


class CustomCliSource(Source):
    """
    An object representing a custom source for CLI testing.
    """

    path: Path
    protocol: ClassVar[str] = "custom_cli_protocol"

    @property
    def id(self) -> str:
        """Get unique identifier of the object in the custom CLI source."""
        return f"custom_cli_source:{self.path}"

    @traceable
    async def fetch(self) -> Path:
        """Fetch the custom CLI source."""
        return self.path

    @classmethod
    async def list_sources(cls, path: str) -> Iterable[Self]:
        """List all sources from the Custom LCI source."""
        return [cls(path=Path(path))]

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """Custom CLI source from URI path."""
        return [cls(path=Path(path))]
