from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from ragbits.core.audit import traceable
from ragbits.document_search.documents.exceptions import SourceNotFoundError
from ragbits.document_search.documents.sources import Source


class LocalFileSource(Source):
    """
    An object representing a local file source.
    """

    path: Path
    protocol: ClassVar[str] = "file"

    @property
    def id(self) -> str:
        """
        Get unique identifier of the object in the source.

        Returns:
            Unique identifier.
        """
        return f"local_file:{self.path.absolute()}"

    @traceable
    async def fetch(self) -> Path:
        """
        Fetch the source.

        Returns:
            The local path to the object fetched from the source.

        Raises:
            SourceNotFoundError: If the source document is not found.
        """
        if not self.path.is_file():
            raise SourceNotFoundError(source_id=self.id)
        return self.path

    @classmethod
    @traceable
    def list_sources(cls, path: Path, file_pattern: str = "*") -> list["LocalFileSource"]:
        """
        List all sources in the given directory, matching the file pattern.

        Args:
            path: The path to the directory.
            file_pattern: The file pattern to match.

        Returns:
            List of source objects.
        """
        return [cls(path=file_path) for file_path in path.glob(file_pattern)]

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Sequence["LocalFileSource"]:
        """Create LocalFileSource instances from a URI path.

        Supports full glob patterns via Path.glob:
        - "**/*.txt" - all .txt files in any subdirectory
        - "*.py" - all Python files in the current directory
        - "**/*" - all files in any subdirectory
        - '?' matches exactly one character

        Args:
            path: The path part of the URI (after file://). Pattern support depends on source type.

        Returns:
            A sequence of LocalFileSource objects
        """
        path_obj: Path = Path(path)
        base_path, pattern = cls._split_path_and_pattern(path=path_obj)
        if base_path.is_file():
            return [cls(path=base_path)]
        if not pattern:
            return []
        return [cls(path=f) for f in base_path.glob(pattern) if f.is_file()]

    @staticmethod
    def _split_path_and_pattern(path: Path) -> tuple[Path, str]:
        parts = path.parts
        # Find the first part containing '*' or '?'
        for i, part in enumerate(parts):
            if "*" in part or "?" in part:
                base_path = Path(*parts[:i])
                pattern = str(Path(*parts[i:]))
                return base_path, pattern
        return path, ""
