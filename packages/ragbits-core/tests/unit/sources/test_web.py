from unittest.mock import MagicMock, patch

import pytest

from ragbits.core.sources.exceptions import SourceNotFoundError
from ragbits.core.sources.web import WebSource


def test_id():
    source = WebSource(url="http://example.com/file.pdf")
    expected_id = "web:http://example.com/file.pdf"
    assert source.id == expected_id


async def test_from_uri_one_file():
    file_urls = [
        "http://www.without-secure-protocol.com/file.pdf",
        "https://www.with-secure-protocol.com/file.pdf",
        "https://www.longer-path.com/longer/path/to/file.pdf",
        "https://www.with-parameters.com/file.pdf?param1=value1&param2=value2",
        "https://www.with-fragment.com/file.pdf#fragment",
        "https://without-www.com/file.pdf",
        "http://www.domain-only.com",
    ]

    for url in file_urls:
        result = await WebSource.from_uri(url)
        assert result == [WebSource(url=url)]


async def test_invalid_url_raises_exception():
    wrong_urls = [
        "some string",
        "https://www.url with spaces.com/path/to/file",
        "www.without-protocol.com/path/to/file",
        "http://www.domain-only-with-slash.com/",
    ]

    for url in wrong_urls:
        with pytest.raises(SourceNotFoundError):
            await WebSource(url=url).fetch()


@patch("ragbits.core.sources.web.aiohttp.ClientSession")
async def test_url_and_headers_are_passed_correctly(client_session_mock: MagicMock) -> None:
    session_mock = MagicMock()
    get_mock = MagicMock()
    expected_url = "http://example.com"
    expected_headers = {"header1": "value1"}

    source = WebSource(url=expected_url, headers=expected_headers)
    client_session_mock.return_value.__aenter__.return_value = session_mock
    session_mock.get.return_value.__aenter__.return_value = get_mock
    get_mock.content.iter_chunked.return_value.__aiter__.return_value = [b"test data"]

    await source.fetch()

    assert session_mock.get.call_args.args[0] == expected_url
    assert session_mock.get.call_args.kwargs["headers"] == expected_headers


@patch("ragbits.core.sources.web.aiohttp.ClientSession")
async def test_passed_headers_are_none_by_default(client_session_mock: MagicMock) -> None:
    session_mock = MagicMock()
    get_mock = MagicMock()
    expected_url = "http://example.com"

    source = WebSource(url=expected_url)
    client_session_mock.return_value.__aenter__.return_value = session_mock
    session_mock.get.return_value.__aenter__.return_value = get_mock
    get_mock.content.iter_chunked.return_value.__aiter__.return_value = [b"test data"]

    await source.fetch()

    assert session_mock.get.call_args.args[0] == expected_url
    assert session_mock.get.call_args.kwargs["headers"] is None
