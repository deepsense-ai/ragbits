import pickle

from ragbits.document_search.documents.exceptions import (
    SourceConnectionError,
    SourceError,
    SourceNotFoundError,
    WebDownloadError,
)


def test_source_error_init():
    error = SourceError("Test error message")
    assert error.message == "Test error message"
    assert str(error) == "Test error message"


def test_source_error_pickle():
    original = SourceError("Test pickle message")
    pickled = pickle.dumps(original)
    unpickled = pickle.loads(pickled) # noqa: S301

    assert isinstance(unpickled, SourceError)
    assert unpickled.message == "Test pickle message"
    assert str(unpickled) == "Test pickle message"


def test_source_connection_error_init():
    error = SourceConnectionError()
    assert error.message == "Connection error."
    assert str(error) == "Connection error."


def test_source_connection_error_pickle():
    original = SourceConnectionError()
    pickled = pickle.dumps(original)
    unpickled = pickle.loads(pickled) # noqa: S301

    assert isinstance(unpickled, SourceConnectionError)
    assert unpickled.message == "Connection error."
    assert str(unpickled) == "Connection error."


def test_source_not_found_error_init():
    error = SourceNotFoundError("test-source-id")
    assert error.source_id == "test-source-id"
    assert error.message == "Source with ID test-source-id not found."
    assert str(error) == "Source with ID test-source-id not found."


def test_source_not_found_error_pickle():
    original = SourceNotFoundError("test-source-id")
    pickled = pickle.dumps(original)
    unpickled = pickle.loads(pickled) # noqa: S301

    assert isinstance(unpickled, SourceNotFoundError)
    assert unpickled.source_id == "test-source-id"
    assert unpickled.message == "Source with ID test-source-id not found."
    assert str(unpickled) == "Source with ID test-source-id not found."


def test_web_download_error_init():
    url = "https://example.com/file.pdf"
    code = 404
    error = WebDownloadError(url, code)

    assert error.url == url
    assert error.code == code
    assert error.message == f"Download of {url} failed with code {code}."
    assert str(error) == f"Download of {url} failed with code {code}."


def test_web_download_error_pickle():
    url = "https://example.com/file.pdf"
    code = 404
    original = WebDownloadError(url, code)
    pickled = pickle.dumps(original)
    unpickled = pickle.loads(pickled) # noqa: S301

    assert isinstance(unpickled, WebDownloadError)
    assert unpickled.url == url
    assert unpickled.code == code
    assert unpickled.message == f"Download of {url} failed with code {code}."
    assert str(unpickled) == f"Download of {url} failed with code {code}."
