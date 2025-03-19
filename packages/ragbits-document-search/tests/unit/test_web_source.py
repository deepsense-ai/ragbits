from sympy.testing import pytest

from ragbits.document_search.documents.exceptions import SourceNotFoundError
from ragbits.document_search.documents.sources.web import WebSource


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
        assert result[0] == WebSource(url=url)


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
