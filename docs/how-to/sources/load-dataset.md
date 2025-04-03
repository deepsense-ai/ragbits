# How-To: Load dataset with sources

Ragbits provides an abstraction for handling datasets. The [`Source`][ragbits.core.sources.Source] component is designed to define interactions with any data source, such as downloading and querying.

## Supported sources

This is the list of currently supported sources by Ragbits.

| Source | URI Schema | Class |
|-|-|-|
| Azure Blob Storage | `azure://https://account_name.blob.core.windows.net/<container-name>|<blob-name>` | [`AzureBlobStorageSource`][ragbits.core.sources.AzureBlobStorageSource] |
| Google Cloud Storage | `gcs://<bucket-name>/<prefix>` | [`GCSSource`][ragbits.core.sources.GCSSource] |
| Git | `git://<https-url>|<ssh-url>` | [`GitSource`][ragbits.core.sources.GitSource] |
| Hugging Face | `huggingface://<dataset-path>/<split>/<row>` | [`HuggingFaceSource`][ragbits.core.sources.HuggingFaceSource] |
| Local file | `file://<file-path>|<blob-pattern>` | [`LocalFileSource`][ragbits.core.sources.LocalFileSource] |
| Amazon S3 | `s3://<bucket-name>/<prefix>` | [`S3Source`][ragbits.core.sources.S3Source] |
| Web | `web://<https-url>` | [`WebSource`][ragbits.core.sources.WebSource] |

## Custom source

To define a new sources, extend the [`Source`][ragbits.core.sources.Source] class.

```python
from ragbits.core.sources import Source


class CustomSource(Source):
    """
    Source that downloads file from the web.
    """

    protocol: ClassVar[str] = "custom"
    source_url: str
    ...

    @property
    def id(self) -> str:
        """
        Source unique identifier.
        """
        return f"{self.protocol}:{self.source_url}"

    @classmethod
    async def from_uri(cls, uri: str) -> list[Self]:
        """
        Create source instances from a URI path.

        Args:
            uri: The URI path.

        Returns:
            The list of sources.
        """
        return [cls(...), ...]

    async def fetch(self) -> Path:
        """
        Download a file for the given url.

        Returns:
            The local path to the downloaded file.
        """
        ...
        return Path(f"/tmp/{self.source_url}")
```
