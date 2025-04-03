from ragbits.core.sources.exceptions import (
    SourceConnectionError,
    SourceDownloadError,
    SourceError,
    SourceNotFoundError,
)


def test_source_error_init():
    error = SourceError("Test error message")
    assert error.message == "Test error message"
    assert str(error) == "Test error message"


def test_source_connection_error_init():
    error = SourceConnectionError()
    assert error.message == "Connection error."
    assert str(error) == "Connection error."


def test_source_not_found_error_init():
    error = SourceNotFoundError("test-source-id")
    assert error.source_id == "test-source-id"
    assert error.message == "Source with ID test-source-id not found."
    assert str(error) == "Source with ID test-source-id not found."


def test_web_download_error_init():
    url = "https://example.com/file.pdf"
    code = 404
    error = SourceDownloadError(url, code)

    assert error.url == url
    assert error.code == code
    assert error.message == f"Download of {url} failed with code {code}."
    assert str(error) == f"Download of {url} failed with code {code}."
