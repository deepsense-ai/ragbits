import re
from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

import aiohttp
from typing_extensions import Self

from ragbits.core.sources.base import Source, get_local_storage_dir
from ragbits.core.sources.exceptions import SourceDownloadError, SourceNotFoundError


class WebSource(Source):
    """
    Source for data stored in the web.
    """

    protocol: ClassVar[str] = "web"
    url: str
    headers: dict[str, str] | None = None

    @property
    def id(self) -> str:
        """
        Get the source identifier.
        """
        return f"web:{self.url}"

    async def fetch(self) -> Path:
        """
        Download a file available in the given url.

        Returns:
            The local path to the downloaded file.

        Raises:
            SourceDownloadError: If the download failed.
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
            async with aiohttp.ClientSession() as session, session.get(self.url, headers=self.headers) as response:
                if response.ok:
                    with open(path, "wb") as f:
                        async for chunk in response.content.iter_chunked(1024):
                            f.write(chunk)
                else:
                    raise SourceDownloadError(url=self.url, code=response.status)
        except (aiohttp.ClientError, IsADirectoryError) as e:
            raise SourceNotFoundError(self.id) from e

        return path

    @classmethod
    async def list_sources(cls, url: str) -> Iterable[Self]:
        """
        List the file under the given URL.

        Args:
            url: The URL to the file.

        Returns:
            The iterable of sources from the web.
        """
        return [cls(url=url)]

    @classmethod
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """
        Create WebSource instances from a URI path.

        The supported URI formats:
        - <protocol>://<domain>/<path>/<filename>.<file_extension>

        Args:
            path: The URI path in the format described above.

        Returns:
            The iterable of sources from the web.
        """
        return [cls(url=path)]
