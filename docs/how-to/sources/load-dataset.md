# How-To: Load dataset with sources

Ragbits provides an abstraction for handling datasets. The [`Source`][ragbits.core.sources.Source] component is designed to define interactions with any data source, such as downloading and querying.

## Supported sources

This is the list of currently supported sources by Ragbits.

| Source | URI Schema | Class |
|-|-|-|
| Azure Blob Storage | `azure://https://account_name.blob.core.windows.net/<container-name>|<blob-name>` | [`AzureBlobStorageSource`][ragbits.core.sources.AzureBlobStorageSource] |
| Google Cloud Storage | `gcs://<bucket-name>/<prefix>` | [`GCSSource`][ragbits.core.sources.GCSSource] |
| Git | `git://<https-url>|<ssh-url>` | [`GitSource`][ragbits.core.sources.GitSource] |
| Hugging Face | `hf://<dataset-path>/<split>/<row>` | [`HuggingFaceSource`][ragbits.core.sources.HuggingFaceSource] |
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

### Register custom sources

To register your custom source class update `pyproject.toml` within your project root with the following lines:

```toml
[tool.ragbits.core]
modules_to_import = ["python.path.to.custom_source"]
```

You can specify any number of modules in that list — all source classes found in those modules will be imported and registered automatically.

## Custom element

To define a new element, extend the [`Element`][ragbits.document_search.documents.element.Element] class. Here's a basic template for a custom element class:

```python
class CustomElement(Element):
    element_type: str = "custom_element"
    custom_field: str

    @computed_field
    @property
    def text_representation(self) -> str:
        return self.custom_field
```

### Register custom elements

To register your custom element classes, include their module paths in the `modules_to_import` section of your `pyproject.toml` file:

```toml
[tool.ragbits.core]
modules_to_import = [
    "python.path.to.custom_source",
    "python.path.to.custom_element",
]
```

This setup allows you to register both custom sources and custom elements in one place, making your extensions automatically available throughout the system.
