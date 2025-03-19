import re
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

with suppress(ImportError):
    import aiohttp

from ragbits.core.utils.decorators import requires_dependencies
from ragbits.document_search.documents.exceptions import SourceNotFoundError, WebDownloadError
from ragbits.document_search.documents.sources import Source
from ragbits.document_search.documents.sources.base import get_local_storage_dir


class WebSource(Source):
    """
    An object representing a Web dataset source.
    """

    url: str
    protocol: ClassVar[str] = "https"

    @property
    def id(self) -> str:
        """
        Get the source ID, which is an unique identifier of the object.
        """
        return f"web:{self.url}"

    @requires_dependencies(["aiohttp"])
    async def fetch(self) -> Path:
        """
        Download a file available in the given url.

        Returns:
            Path: The local path to the downloaded file.

        Raises:
            WebDownloadError: If the download failed.
            SourceNotFoundError: If the URL is invalid.
        """
        parsed_url = urlparse(self.url)
        url_path, file_name = ("/" + parsed_url.netloc + parsed_url.path).rsplit("/", 1)
        normalized_url_path = re.sub(r"\W", "_", url_path) + file_name
        domain_name = parsed_url.netloc

        local_dir = get_local_storage_dir()
        container_local_dir = local_dir / domain_name
        container_local_dir.mkdir(parents=True, exist_ok=True)
        path = container_local_dir / normalized_url_path

        try:
            async with aiohttp.ClientSession() as session, session.get(self.url) as response:
                if response.ok:
                    with open(path, "wb") as f:
                        async for chunk in response.content.iter_chunked(1024):
                            f.write(chunk)
                else:
                    raise WebDownloadError(url=self.url, code=response.status)
        except (aiohttp.ClientError, IsADirectoryError) as e:
            raise SourceNotFoundError(self.id) from e

        return path

    @classmethod
    async def list_sources(cls, url: str) -> Sequence["WebSource"]:
        """
        List the file under the given URL.

        Arguments:
            url: The URL to the file.

        Returns:
            Sequence: The Sequence with Web source.
        """
        return [cls(url=url)]

    @classmethod
    async def from_uri(cls, uri: str) -> Sequence["WebSource"]:
        """
        Create WebSource instances from a URI path.
        The supported uri format is:
        <protocol>://<domain>/<path>/<filename>.<file_extension>

        Args:
            uri: The URI path. Needs to include the protocol.

        Returns:
            A sequence containing a WebSource instance.
        """
        return [cls(url=uri)]
