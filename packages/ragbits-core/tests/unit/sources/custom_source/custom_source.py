from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from ragbits.core.audit import traceable
from ragbits.core.sources.base import Source


class CustomSource(Source):
    """
    An object representing a custom source.
    """

    path: Path
    protocol: ClassVar[str] = "CustomSource"

    @property
    def id(self) -> str:
        """Get unique identifier of the object in the custom source."""
        return f"cs:{self.path}"

    @traceable
    async def fetch(self) -> Path:
        """Fetch the custom source."""
        return self.path

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Sequence["CustomSource"]:
        """Custom source from URI path."""
        return [cls(path=Path(path))]
