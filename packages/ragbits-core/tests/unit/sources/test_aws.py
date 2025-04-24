from unittest.mock import patch

from sympy.testing import pytest

from ragbits.core.sources.s3 import S3Source


def test_id():
    source = S3Source(bucket_name="AA", key="bb/cc.pdf")
    expected_id = "s3:AA/bb/cc.pdf"
    assert source.id == expected_id


async def test_from_uri_one_file():
    one_file_paths = [
        "s3://bucket/path/to/file",
        "https://s3.us-west-2.amazonaws.com/bucket/path/to/file",
        "https://bucket.s3-us-west-2.amazonaws.com/path/to/file",
    ]
    for path in one_file_paths:
        result = await S3Source.from_uri(path)
        assert result == [S3Source(bucket_name="bucket", key="path/to/file")]


async def test_from_uri_with_prefix():
    good_paths = [
        "s3://bucket/path/to/files*",
        "https://s3.us-west-2.amazonaws.com/bucket/path/to/files*",
        "https://bucket.s3-us-west-2.amazonaws.com/path/to/files*",
    ]
    with patch("ragbits.core.sources.s3.S3Source.list_sources") as mock_list_sources:
        for path in good_paths:
            await S3Source.from_uri(path)
            mock_list_sources.assert_called_with(bucket_name="bucket", prefix="path/to/files")


async def test_from_uri_raises_exception():
    wrong_uris = [
        "some string",
        "https://bucket.s3.us-west-2.amazonaws.com/path/to/file**",
        "https://bucket.s3.us-west-2.amazonaws.com/path/*/file*",
        "https://some/random/address",
        "https://s3.us-west-2.amazonaws.pl/path/to/file",
        "s3://short_address",
    ]
    for uri in wrong_uris:
        with pytest.raises(ValueError):
            await S3Source.from_uri(uri)
