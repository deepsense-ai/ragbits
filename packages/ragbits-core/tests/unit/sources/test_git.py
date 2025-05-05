from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ragbits.core.sources.exceptions import SourceNotFoundError
from ragbits.core.sources.git import GitSource


def test_id():
    """Test the ID property for GitSource"""
    # Test basic case
    source = GitSource(repo_url="https://github.com/user/repo.git", file_path="README.md")
    assert source.id == "git:repo/README.md"

    # Test with branch
    source = GitSource(repo_url="https://github.com/user/repo.git", file_path="README.md", branch="main")
    assert source.id == "git:repo/main/README.md"

    # Test with deeper file path
    source = GitSource(repo_url="https://github.com/user/repo.git", file_path="docs/index.md", branch="main")
    assert source.id == "git:repo/main/docs/index.md"

    # Test without .git extension
    source = GitSource(repo_url="https://github.com/user/repo", file_path="README.md")
    assert source.id == "git:repo/README.md"

    # Test with trailing slash
    source = GitSource(repo_url="https://github.com/user/repo/", file_path="README.md")
    assert source.id == "git:repo/README.md"


async def test_from_uri():
    """Test creating GitSource instances from URI"""
    # Test with repo URL and file path
    result = await GitSource.from_uri("https://github.com/user/repo.git:README.md")
    assert result == [
        GitSource(
            repo_url="https://github.com/user/repo.git",
            branch=None,
            file_path="README.md",
        )
    ]

    # Test with repo URL, branch, and file path
    result = await GitSource.from_uri("https://github.com/user/repo.git:main:README.md")
    assert result == [
        GitSource(
            repo_url="https://github.com/user/repo.git",
            branch="main",
            file_path="README.md",
        )
    ]

    # Test with deep file path
    result = await GitSource.from_uri("https://github.com/user/repo.git:main:docs/api/index.md")
    assert result == [
        GitSource(
            repo_url="https://github.com/user/repo.git",
            branch="main",
            file_path="docs/api/index.md",
        )
    ]

    # Test with SSH format and file path
    result = await GitSource.from_uri("git@github.com:user/repo.git:README.md")
    assert result == [
        GitSource(
            repo_url="git@github.com:user/repo.git",
            branch=None,
            file_path="README.md",
        )
    ]

    # # Test with SSH format, branch, and file path
    result = await GitSource.from_uri("git@github.com:user/repo.git:main:README.md")
    assert result == [
        GitSource(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            file_path="README.md",
        )
    ]

    # Test with SSH format and deep file path
    result = await GitSource.from_uri("git@github.com:user/repo.git:main:docs/api/index.md")
    assert result == [
        GitSource(
            repo_url="git@github.com:user/repo.git",
            branch="main",
            file_path="docs/api/index.md",
        )
    ]


@patch("ragbits.core.sources.git.git")
async def test_fetch_new_repository(git_mock: MagicMock):
    """Test fetching a file from a new git repository"""
    # Setup mocks
    repo_mock = MagicMock()
    git_mock.Repo.clone_from.return_value = repo_mock
    git_mock.GitCommandError = Exception

    # Create source and fetch
    source = GitSource(repo_url="https://github.com/user/repo.git", file_path="README.md")

    # Mock Path.exists to return False for repo but True for file
    with (
        patch("pathlib.Path.exists", side_effect=[False, True]),
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.mkdir"),
    ):
        result = await source.fetch()

    # Verify clone was called with correct arguments
    git_mock.Repo.clone_from.assert_called_once()
    call_args = git_mock.Repo.clone_from.call_args.args
    assert call_args[0] == "https://github.com/user/repo.git"
    assert isinstance(call_args[1], str)

    # Verify result is a Path
    assert isinstance(result, Path)


@patch("ragbits.core.sources.git.git")
async def test_fetch_existing_repository(git_mock: MagicMock):
    """Test fetching a file from an existing git repository"""
    # Setup mocks
    repo_mock = MagicMock()
    origin_mock = MagicMock()
    active_branch_mock = MagicMock()
    active_branch_mock.name = "main"
    repo_mock.remotes.origin = origin_mock
    repo_mock.active_branch = active_branch_mock
    git_mock.Repo.return_value = repo_mock
    git_mock.GitCommandError = Exception

    # Create source and fetch
    source = GitSource(repo_url="https://github.com/user/repo.git", file_path="README.md")

    # Mock Path.exists to return True for both repo and file
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.mkdir"),
    ):
        result = await source.fetch()

    # Verify Repo was initialized with the correct path
    git_mock.Repo.assert_called_once()
    # Verify fetch was called with depth=1
    origin_mock.fetch.assert_called_once_with(depth=1)
    # Verify reset was called
    repo_mock.git.reset.assert_called_once_with("--hard", "origin/main")

    # Verify result is a Path
    assert isinstance(result, Path)


@patch("ragbits.core.sources.git.git")
async def test_fetch_with_branch(git_mock: MagicMock):
    """Test fetching a file from a repository with a specific branch"""
    # Setup mocks
    repo_mock = MagicMock()
    git_mock.Repo.clone_from.return_value = repo_mock
    git_mock.GitCommandError = Exception

    # Create source and fetch
    source = GitSource(repo_url="https://github.com/user/repo.git", file_path="README.md", branch="dev")

    # Mock Path.exists to return False for repo but True for file
    with (
        patch("pathlib.Path.exists", side_effect=[False, True]),
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.mkdir"),
    ):
        result = await source.fetch()

    # Verify clone was called with correct arguments including branch
    git_mock.Repo.clone_from.assert_called_once()
    call_args = git_mock.Repo.clone_from.call_args
    assert call_args.args[0] == "https://github.com/user/repo.git"
    assert isinstance(call_args.args[1], str)
    assert call_args.kwargs["branch"] == "dev"

    # Verify result is a Path
    assert isinstance(result, Path)


@patch("ragbits.core.sources.git.git")
async def test_fetch_file_not_found(git_mock: MagicMock):
    """Test fetching a file that doesn't exist in the repository"""
    # Setup mocks
    repo_mock = MagicMock()
    git_mock.Repo.clone_from.return_value = repo_mock
    git_mock.GitCommandError = Exception

    # Create source and fetch
    source = GitSource(repo_url="https://github.com/user/repo.git", file_path="non_existent.md")

    # Mock Path.exists to return False for the file
    with (
        patch("pathlib.Path.exists", side_effect=[False, False]),
        patch("pathlib.Path.mkdir"),
        pytest.raises(SourceNotFoundError) as exc_info,
    ):
        await source.fetch()

    # Verify error message
    assert "File non_existent.md not found in repository" in str(exc_info.value)


@patch("ragbits.core.sources.git.git")
async def test_fetch_not_a_file(git_mock: MagicMock):
    """Test fetching a path that isn't a file in the repository"""
    # Setup mocks
    repo_mock = MagicMock()
    git_mock.Repo.clone_from.return_value = repo_mock
    git_mock.GitCommandError = Exception

    # Create source and fetch
    source = GitSource(repo_url="https://github.com/user/repo.git", file_path="docs")

    # Mock Path.exists to return True for path but is_file returns False
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_file", return_value=False),
        patch("pathlib.Path.mkdir"),
        pytest.raises(SourceNotFoundError) as exc_info,
    ):
        await source.fetch()

    # Verify error message
    assert "File docs not found in repository" in str(exc_info.value)


@patch("ragbits.core.sources.git.git")
async def test_fetch_clone_error(git_mock: MagicMock):
    """Test handling of git command errors during clone"""
    # Setup mocks
    git_command_error = Exception("Git clone failed")
    git_mock.Repo.clone_from.side_effect = git_command_error
    git_mock.GitCommandError = Exception

    # Create source and fetch
    source = GitSource(repo_url="https://github.com/user/repo.git", file_path="README.md")

    # Mock Path.exists to return False for the repo
    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("pathlib.Path.mkdir"),
        pytest.raises(SourceNotFoundError) as exc_info,
    ):
        await source.fetch()

    # Verify error message
    assert "Failed to clone repository" in str(exc_info.value)


@patch("ragbits.core.sources.git.git")
async def test_list_sources(git_mock: MagicMock):
    """Test listing files from a git repository"""
    # Setup mocks
    repo_mock = MagicMock()
    git_mock.Repo.clone_from.return_value = repo_mock
    git_mock.GitCommandError = Exception

    # Mock file paths matching the pattern
    mock_files = [
        Path("/mock/repo/file1.pdf"),
        Path("/mock/repo/docs/file2.pdf"),
        Path("/mock/repo/docs/subfolder"),  # This is a directory, not a file
    ]

    # Mock Path.exists to return False for repo (new clone)
    # Mock Path.glob to return our mock files
    # Mock Path.is_file to return True for files, False for directories
    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.glob", return_value=mock_files),
        patch("pathlib.Path.is_file", side_effect=[True, True, False]),
        patch("pathlib.Path.relative_to", side_effect=[Path("file1.pdf"), Path("docs/file2.pdf")]),
    ):
        result = await GitSource.list_sources(repo_url="https://github.com/user/repo.git", file_pattern="**/*.pdf")

    # Verify result
    assert result == [
        GitSource(
            repo_url="https://github.com/user/repo.git",
            file_path="file1.pdf",
        ),
        GitSource(
            repo_url="https://github.com/user/repo.git",
            file_path="docs/file2.pdf",
        ),
    ]
    assert all(isinstance(source, GitSource) for source in result)
