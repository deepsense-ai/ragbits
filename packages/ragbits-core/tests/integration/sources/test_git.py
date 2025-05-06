import pytest

from ragbits.core.sources.exceptions import SourceNotFoundError
from ragbits.core.sources.git import GitSource

# A public repository that's unlikely to disappear and has a stable structure
TEST_REPO_URL = "https://github.com/psf/requests.git"
TEST_REPO_SSH_URL = "git@github.com:psf/requests.git"


async def test_git_source_fetch_file():
    """Test fetching a specific file from a git repository."""
    # Fetch the README.md file
    source = GitSource(repo_url=TEST_REPO_URL, file_path="README.md")
    path = await source.fetch()

    # Check that the path exists and is a file
    assert path.is_file()
    assert path.name == "README.md"

    # Check that the content is reasonable
    content = path.read_text()
    assert "Requests" in content  # The README should contain the name of the project


async def test_git_source_fetch_with_branch():
    """Test fetching a specific file from a branch of a git repository."""
    # Use the main branch to fetch setup.py
    source = GitSource(repo_url=TEST_REPO_URL, file_path="setup.py", branch="main")
    path = await source.fetch()

    # Check that the path exists and is a file
    assert path.is_file()
    assert path.name == "setup.py"

    # Check that the content is reasonable
    content = path.read_text()
    assert "requests" in content.lower()  # The setup.py should contain the name of the project


async def test_git_source_fetch_nested_file():
    """Test fetching a file in a subdirectory of the repository."""
    # Fetch a file from the docs directory
    source = GitSource(repo_url=TEST_REPO_URL, file_path="docs/index.rst")
    path = await source.fetch()

    # Check that the path exists and is a file
    assert path.is_file()
    assert path.name == "index.rst"
    assert path.parent.name == "docs"

    # Check that the content is reasonable
    content = path.read_text()
    assert "requests" in content.lower()  # The index should mention the project


async def test_git_source_fetch_nonexistent_file():
    """Test fetching a non-existent file from a git repository."""
    source = GitSource(repo_url=TEST_REPO_URL, file_path="nonexistent_file.txt")

    with pytest.raises(SourceNotFoundError) as exc_info:
        await source.fetch()

    assert "File nonexistent_file.txt not found in repository" in str(exc_info.value)


async def test_from_uri_with_file():
    """Test GitSource.from_uri with repository URL and file path."""
    uri = f"{TEST_REPO_URL}:README.md"
    sources = await GitSource.from_uri(uri)
    assert sources == [
        GitSource(
            repo_url=TEST_REPO_URL,
            file_path="README.md",
            branch=None,
        ),
    ]


async def test_from_uri_with_branch_and_file():
    """Test GitSource.from_uri with repository URL, branch, and file path."""
    uri = f"{TEST_REPO_URL}:main:README.md"
    sources = await GitSource.from_uri(uri)
    assert sources == [
        GitSource(
            repo_url=TEST_REPO_URL,
            file_path="README.md",
            branch="main",
        ),
    ]


async def test_list_sources_pdf_files():
    """Test GitSource.list_sources with a pattern for PDF files."""
    # The requests repo doesn't have PDF files, so this should return an empty list
    result = await GitSource.list_sources(TEST_REPO_URL, file_pattern="**/*.pdf")

    assert isinstance(result, list)
    assert len(result) == 0


async def test_list_sources_py_files():
    """Test GitSource.list_sources with a pattern for Python files."""
    # Look for Python files in the repository
    result = await GitSource.list_sources(TEST_REPO_URL, file_pattern="**/*.py")

    # Verify the results are GitSource objects for individual files
    for source in result:
        assert isinstance(source, GitSource)
        assert source.repo_url == TEST_REPO_URL
        assert source.file_path.endswith(".py")

    # setup.py should be one of the files
    setup_py_sources = [s for s in result if s.file_path == "setup.py"]
    assert len(setup_py_sources) == 1


async def test_from_uri_with_ssh():
    """Test GitSource.from_uri with SSH repository URL."""
    uri = f"{TEST_REPO_SSH_URL}:README.md"
    sources = await GitSource.from_uri(uri)
    assert sources == [
        GitSource(
            repo_url=TEST_REPO_SSH_URL,
            file_path="README.md",
            branch=None,
        ),
    ]


async def test_from_uri_with_ssh_branch():
    """Test GitSource.from_uri with SSH repository URL and branch."""
    uri = f"{TEST_REPO_SSH_URL}:main:README.md"
    sources = await GitSource.from_uri(uri)
    assert sources == [
        GitSource(
            repo_url=TEST_REPO_SSH_URL,
            file_path="README.md",
            branch="main",
        ),
    ]


@pytest.mark.skip(reason="SSH is not supported in the CI environment")
async def test_git_source_fetch_with_ssh():
    """Test fetching a specific file using SSH repository URL."""
    source = GitSource(repo_url=TEST_REPO_SSH_URL, file_path="README.md")
    path = await source.fetch()

    # Check that the path exists and is a file
    assert path.is_file()
    assert path.name == "README.md"

    # Check that the content is reasonable
    content = path.read_text()
    assert "Requests" in content  # The README should contain the name of the project
