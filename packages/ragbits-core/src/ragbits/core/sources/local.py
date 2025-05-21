from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar

from typing_extensions import Self

from ragbits.core.audit.traces import traceable
from ragbits.core.sources.base import Source
from ragbits.core.sources.exceptions import SourceNotFoundError


class LocalFileSource(Source):
    """
    Source for data stored on the local disk.
    """

    protocol: ClassVar[str] = "local"
    path: Path

    @property
    def id(self) -> str:
        """
        Get the source identifier.
        """
        return f"local:{self.path.absolute()}"

    @traceable
    async def fetch(self) -> Path:
        """
        Fetch the source.

        Returns:
            The local path to the file.

        Raises:
            SourceNotFoundError: If the source document is not found.
        """
        if not self.path.is_file():
            raise SourceNotFoundError(source_id=self.id)
        return self.path

    @classmethod
    @traceable
    async def list_sources(cls, path: Path, file_pattern: str = "*") -> Iterable[Self]:
        """
        List all sources in the given directory, matching the file pattern.

        Args:
            path: The path to the directory.
            file_pattern: The file pattern to match.

        Returns:
            The iterable of sources from the local file system.
        """
        return [cls(path=file_path) for file_path in path.glob(file_pattern)]

    @classmethod
    @traceable
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """
        Create LocalFileSource instances from a URI path.

        The supported URI formats:
        - "**/*.txt" - all .txt files in any subdirectory
        - "*.py" - all Python files in the current directory
        - "**/*" - all files in any subdirectory
        - '?' matches exactly one character

        Args:
            path: The URI path in the format described above.

        Returns:
            The iterable of sources from the local file system.
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
