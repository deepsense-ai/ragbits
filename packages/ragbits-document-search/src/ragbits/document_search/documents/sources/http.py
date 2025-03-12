from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlparse

with suppress(ImportError):
    import aiohttp
    import validators

from ragbits.core.utils.decorators import requires_dependencies
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.documents.sources.base import get_local_storage_dir

HTTP_STATUS_OK = 200


class HttpSource(Source):
    """
    An object representing an HTTP dataset source.
    """

    url: str

    @property
    def id(self) -> str:
        """
        Get the source ID, which is the full url to the file.
        """
        return self.url

    @requires_dependencies(["aiohttp"])
    async def fetch(self) -> Path:
        """
        Download a file available in the given url.

        Returns:
            Path: The local path to the downloaded file.

        Raises:
            ValueError: If the download fails.
        """
        parsed_url = urlparse(self.url)
        domain_name = parsed_url.netloc
        normalized_url_path = parsed_url.path.replace("/", "_")

        local_dir = get_local_storage_dir()
        container_local_dir = local_dir / domain_name
        container_local_dir.mkdir(parents=True, exist_ok=True)
        path = container_local_dir / normalized_url_path

        async with aiohttp.ClientSession() as session, session.get(self.url) as response:
            if response.status == HTTP_STATUS_OK:
                with open(path, "wb") as f:
                    async for chunk in response.content.iter_chunked(1024):
                        f.write(chunk)
            else:
                raise ValueError(f"Failed to download {self.url}. Response code: {response.status}")

        return path

    @classmethod
    @requires_dependencies(["validators"])
    async def from_uri(cls, url: str) -> Sequence["HttpSource"]:
        """
        Create HttpSource instances from a URI path.
        The supported url format is:
        <protocol>://<domain>/<path>

        Args:
            url: The URI path.

        Returns:
            A sequence containing a HttpSource instance.

        Raises:
            ValueError: If the url has invalid format

        """
        if not validators.url(url):
            raise ValueError(f"Invalid URL: {url}")

        return [cls(url=url)]
