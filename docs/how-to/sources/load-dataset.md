# How-To: Load dataset from sources

Ragbits provides an abstraction for handling datasets. The [`Source`][ragbits.core.sources.Source] component is designed to define interactions with any data source, such as downloading and querying.

## Supported sources

This is the list of currently supported sources by Ragbits.

| Source | URI Schema | Class |
|-|-|-|
| Azure Blob Storage | `azure://https://<account-name>.blob.core.windows.net/<container-name>/<blob-name>` | [`AzureBlobStorageSource`][ragbits.core.sources.AzureBlobStorageSource] |
| Google Cloud Storage | `gcs://<bucket-name>/<prefix>` | [`GCSSource`][ragbits.core.sources.GCSSource] |
| Google Drive | `<drive-id>` | [`GoogleDriveSource`][ragbits.core.sources.GoogleDriveSource] |
| Git | `git://<https-url>|<ssh-url>` | [`GitSource`][ragbits.core.sources.GitSource] |
| Hugging Face | `hf://<dataset-path>/<split>/<row>` | [`HuggingFaceSource`][ragbits.core.sources.HuggingFaceSource] |
| Local file | `local://<file-path>|<blob-pattern>` | [`LocalFileSource`][ragbits.core.sources.LocalFileSource] |
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
        Get the source identifier.
        """
        return f"{self.protocol}:{self.source_url}"

    async def fetch(self) -> Path:
        """
        Download a file for the given url.

        Returns:
            The local path to the downloaded file.
        """
        ...
        return Path(f"/tmp/{self.source_url}")

    @classmethod
    async def list_sources(cls, source_url: str) -> Iterable[Self]:
        """
        List all sources from the given storage.

        Args:
            source_url: The source url to list sources from.

        Returns:
            The iterable of Source objects.
        """
        ...
        return [cls(...), ...]

    @classmethod
    async def from_uri(cls, uri: str) -> Iterable[Self]:
        """
        Create source instances from a URI path.

        Args:
            uri: The URI path.

        Returns:
            The iterable of Source objects matching the path pattern.
        """
        ...
        return await self.list_sources(...)
```

!!! hint
    To use a custom source via the CLI, make sure that the custom source class is registered in `pyproject.toml`. You can find information on how to do this [here](../project/custom_components.md).
