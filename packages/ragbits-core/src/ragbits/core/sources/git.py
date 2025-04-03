import re
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import ClassVar

with suppress(ImportError):
    import git

from ragbits.core.audit import traceable
from ragbits.core.sources.base import Source, get_local_storage_dir
from ragbits.core.sources.exceptions import SourceNotFoundError
from ragbits.core.utils.decorators import requires_dependencies

# Constants for URI parts
_REPO_AND_FILE_PARTS = 2
_MIN_PARTS_WITH_PROTOCOL = 3


class GitSource(Source):
    """
    An object representing a file in a Git repository.
    """

    repo_url: str
    file_path: str
    branch: str | None = None
    protocol: ClassVar[str] = "git"

    @property
    def id(self) -> str:
        """
        Get the source ID, which is a unique identifier of the object.

        Returns:
            The source ID.
        """
        repo_name = self.repo_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        branch_part = f":{self.branch}" if self.branch else ""

        return f"git:{repo_name}{branch_part}:{self.file_path}"

    @classmethod
    def _get_repo_dir(cls, repo_url: str, branch: str | None = None) -> Path:
        """
        Get the local directory for a Git repository.

        Args:
            repo_url: URL of the git repository.
            branch: Optional branch name.

        Returns:
            Path to the local repository directory.
        """
        local_dir = get_local_storage_dir()

        # Create a sanitized directory name based on the repo URL
        sanitized_repo = re.sub(r"[^\w.-]", "_", repo_url)
        repo_dir_name = sanitized_repo.split("/")[-1]
        if repo_dir_name.endswith(".git"):
            repo_dir_name = repo_dir_name[:-4]

        # Include branch name in the directory path if specified
        if branch:
            repo_dir_name += f"_{branch}"

        repo_dir = local_dir / "git" / repo_dir_name

        # Create parent directories
        repo_dir.parent.mkdir(parents=True, exist_ok=True)

        return repo_dir

    @classmethod
    def _ensure_repo(cls, repo_url: str, repo_dir: Path, branch: str | None = None) -> None:
        """
        Ensure the repository is cloned and up to date.

        Args:
            repo_url: URL of the git repository.
            repo_dir: Path to the local repository directory.
            branch: Optional branch name.

        Raises:
            SourceNotFoundError: If repository operations fail.
        """
        try:
            # Clone the repository if it doesn't exist
            if not repo_dir.exists():
                if branch:
                    git.Repo.clone_from(
                        repo_url,
                        str(repo_dir),
                        branch=branch,
                        depth=1,  # Use shallow clone
                        single_branch=True,  # Only fetch the specified branch
                    )
                else:
                    git.Repo.clone_from(
                        repo_url,
                        str(repo_dir),
                        depth=1,  # Use shallow clone
                    )
            else:
                # If repository exists, pull the latest changes
                repo = git.Repo(str(repo_dir))
                origin = repo.remotes.origin
                # Use shallow fetch when pulling
                origin.fetch(depth=1)
                # Reset to the latest commit
                repo.git.reset("--hard", "origin/" + (branch or repo.active_branch.name))
        except git.GitCommandError as e:
            raise SourceNotFoundError(f"Failed to clone repository: {e}") from e

    @requires_dependencies(["git"])
    @traceable
    async def fetch(self) -> Path:
        """
        Clone the Git repository and return the path to the specific file.

        Returns:
            The local path to the specific file in the cloned repository.

        Raises:
            SourceNotFoundError: If the repository cannot be cloned or the file doesn't exist.
        """
        repo_dir = self._get_repo_dir(self.repo_url, self.branch)
        self._ensure_repo(self.repo_url, repo_dir, self.branch)

        # Check if the file exists in the repository
        file_path = repo_dir / self.file_path
        if not file_path.exists() or not file_path.is_file():
            raise SourceNotFoundError(f"File {self.file_path} not found in repository")

        return file_path

    @classmethod
    @traceable
    async def list_sources(
        cls, repo_url: str, file_pattern: str = "**/*", branch: str | None = None
    ) -> list["GitSource"]:
        """
        List all files in the repository matching the pattern.

        Args:
            repo_url: URL of the git repository.
            file_pattern: The glob pattern to match files.
            branch: Optional branch name.

        Returns:
            List of GitSource objects, one for each file matching the pattern.
        """
        repo_dir = cls._get_repo_dir(repo_url, branch)
        cls._ensure_repo(repo_url, repo_dir, branch)

        # Find all files matching the pattern
        matched_files = repo_dir.glob(file_pattern)
        file_sources = []

        for file_path in matched_files:
            if file_path.is_file():
                # Convert to relative path within the repository
                relative_path = file_path.relative_to(repo_dir)
                file_sources.append(cls(repo_url=repo_url, file_path=str(relative_path), branch=branch))

        return file_sources

    @classmethod
    @traceable
    async def from_uri(cls, uri: str) -> Sequence["GitSource"]:
        """
        Create GitSource instances from a URI path.

        Supported URI formats:
        - git://https://github.com/username/repo.git:path/to/file.txt
        - git://https://github.com/username/repo.git:branch:path/to/file.txt
        - git@github.com:username/repo.git:path/to/file.txt
        - git@github.com:username/repo.git:branch:path/to/file.txt

        Args:
            uri: The URI path in the format described above.

        Returns:
            A sequence containing a GitSource instance.
        """
        # Check if URI starts with git:// protocol
        if uri.startswith("git://"):
            uri = uri[6:]  # Remove the git:// prefix

        parts = uri.split(":")
        sources = []

        if len(parts) == _REPO_AND_FILE_PARTS:
            # Repo URL and file path
            sources.append(cls(repo_url=parts[0], file_path=parts[1]))
        elif len(parts) >= _MIN_PARTS_WITH_PROTOCOL:
            # Handle SSH format (git@github.com:username/repo.git)
            if parts[0].startswith("git@"):
                repo_url = f"{parts[0]}:{parts[1]}"  # Reconstruct full SSH URL
                file_path = parts[2] if len(parts) == _MIN_PARTS_WITH_PROTOCOL else parts[3]
                branch = None if len(parts) == _MIN_PARTS_WITH_PROTOCOL else parts[2]
                sources.append(cls(repo_url=repo_url, file_path=file_path, branch=branch))
            # Handle HTTPS format
            elif parts[0] in ["http", "https"]:
                repo_url = f"{parts[0]}:{parts[1]}"
                file_path = parts[2] if len(parts) == _MIN_PARTS_WITH_PROTOCOL else parts[3]
                branch = None if len(parts) == _MIN_PARTS_WITH_PROTOCOL else parts[2]
                sources.append(cls(repo_url=repo_url, file_path=file_path, branch=branch))
            else:
                # Repo URL, branch, and file path in standard format
                sources.append(cls(repo_url=parts[0], branch=parts[1], file_path=parts[2]))

        return sources
