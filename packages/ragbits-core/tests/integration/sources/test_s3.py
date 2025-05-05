from collections.abc import Generator

import boto3
import pytest
from moto import mock_s3

from ragbits.core.sources.s3 import S3Source

TEST_BUCKET = "test-bucket"
TEST_KEY = "test-file.txt"
TEST_CONTENT = "Hello, this is a test file!"
TEST_REGION = "us-east-1"


@pytest.fixture
def s3_mock() -> Generator[boto3.client, None, None]:
    """Create a mock S3 environment."""
    with mock_s3():
        s3 = boto3.client("s3", region_name=TEST_REGION)
        s3.create_bucket(Bucket=TEST_BUCKET)
        s3.put_object(Bucket=TEST_BUCKET, Key=TEST_KEY, Body=TEST_CONTENT)
        yield s3


async def test_s3_source_fetch(s3_mock: boto3.client):
    """Test fetching a file from S3."""
    source = S3Source(bucket_name=TEST_BUCKET, key=TEST_KEY)
    path = await source.fetch()

    assert path.is_file()
    assert path.read_text() == TEST_CONTENT


async def test_s3_source_fetch_not_found(s3_mock: boto3.client):
    """Test fetching a non-existent file from S3."""
    source = S3Source(bucket_name=TEST_BUCKET, key="non-existent.txt")

    with pytest.raises(FileNotFoundError) as exc:
        await source.fetch()

    assert "The object does not exist" in str(exc.value)


async def test_s3_source_list_sources(s3_mock: boto3.client):
    """Test listing sources from S3."""
    s3_mock.put_object(Bucket=TEST_BUCKET, Key="folder1/file1.txt", Body="test1")
    s3_mock.put_object(Bucket=TEST_BUCKET, Key="folder1/file2.txt", Body="test2")

    sources = await S3Source.list_sources(bucket_name=TEST_BUCKET, prefix="folder1/")
    assert sources == [
        S3Source(bucket_name="test-bucket", key="folder1/file1.txt"),
        S3Source(bucket_name="test-bucket", key="folder1/file2.txt"),
    ]


async def test_s3_source_from_uri():
    """Test creating S3Source from URI."""
    # Test s3:// URI
    sources = await S3Source.from_uri(f"s3://{TEST_BUCKET}/{TEST_KEY}")
    assert sources == [S3Source(bucket_name=TEST_BUCKET, key=TEST_KEY)]

    # Test https:// URI
    sources = await S3Source.from_uri(f"https://{TEST_BUCKET}.s3.amazonaws.com/{TEST_KEY}")
    assert sources == [S3Source(bucket_name=TEST_BUCKET, key=TEST_KEY)]

    # Test wildcard pattern
    with pytest.raises(ValueError) as exc:
        await S3Source.from_uri(f"s3://{TEST_BUCKET}/**/file.txt")
    assert "only supports '*' at the end of path" in str(exc.value)

    # Test invalid URI
    with pytest.raises(ValueError) as exc:
        await S3Source.from_uri("invalid-uri")
    assert "Invalid AWS Source URI format" in str(exc.value)
