from sympy.testing import pytest

from ragbits.document_search.documents.exceptions import SourceNotFoundError
from ragbits.document_search.documents.sources.http import HttpSource


def test_id():
    source = HttpSource(url="http://example.com/file.pdf")
    expected_id = "web:http://example.com/file.pdf"
    assert source.id == expected_id


async def test_from_uri_one_file():
    file_uris = [
        "http://www.without-secure-protocol.com/file.pdf",
        "https://www.with-secure-protocol.com/file.pdf",
        "https://www.longer-path.com/longer/path/to/file.pdf",
        "https://www.with-parameters.com/file.pdf?param1=value1&param2=value2",
        "https://www.with-fragment.com/file.pdf#fragment",
        "https://without-www.com/file.pdf",
        "http://www.domain-only.com",
    ]

    for uri in file_uris:
        result = await HttpSource.from_uri(uri)
        assert result[0] == HttpSource(url=uri)


async def test_invalid_url_raises_exception():
    wrong_uris = [
        "some string",
        "https://www.url with spaces.com/path/to/file",
        "www.without-protocol.com/path/to/file",
        "http://www.domain-only-with-slash.com/",
    ]

    for uri in wrong_uris:
        with pytest.raises(SourceNotFoundError):
            await HttpSource(url=uri).fetch()
