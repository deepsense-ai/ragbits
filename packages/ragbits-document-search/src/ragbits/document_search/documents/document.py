import tempfile
from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel

from ragbits.document_search.documents.sources import LocalFileSource, Source, SourceDiscriminator


class DocumentType(str, Enum):
    """
    Types of documents that can be stored.
    """

    MD = "md"
    TXT = "txt"
    PDF = "pdf"
    CSV = "csv"
    DOC = "doc"
    DOCX = "docx"
    HTML = "html"
    EPUB = "epub"
    XLSX = "xlsx"
    XLS = "xls"
    ORG = "org"
    ODT = "odt"
    PPT = "ppt"
    PPTX = "pptx"
    RST = "rst"
    RTF = "rtf"
    TSV = "tsv"
    XML = "xml"
    JPG = "jpg"
    PNG = "png"

    UNKNOWN = "unknown"


class DocumentLocation(BaseModel):
    """
    An object representing position of chunk within document
    """

    page_number: int | None = None
    coordinates: dict | None = None


class DocumentMeta(BaseModel):
    """
    An object representing a document metadata.
    """

    document_type: DocumentType
    source: Annotated[Source, SourceDiscriminator()]
    location: DocumentLocation | None = None

    @property
    def id(self) -> str:
        """
        Get the document ID.

        Returns:
            The document ID.
        """
        return self.source.id

    def add_location_metadata(self, provider_metadata: dict) -> None:
        """
        Add metadata retrived by provider to document metadata.

        Args:
            provider_metadata: metadata retrived by provider or null.

        """
        page_number = provider_metadata.get("page_number")
        coordinates = provider_metadata.get("coordinates")
        self.location = DocumentLocation(page_number=page_number, coordinates=coordinates)

    async def fetch(self) -> "Document":
        """
        This method fetches the document from source (potentially remote) and creates an object to interface with it.
        Based on the document type, it will return a different object.

        Returns:
            The document.
        """
        local_path = await self.source.fetch()
        return Document.from_document_meta(self, local_path)

    @classmethod
    def create_text_document_from_literal(cls, content: str) -> "DocumentMeta":
        """
        Create a text document from a literal content.

        Args:
            content: The content of the document.

        Returns:
            The document metadata.
        """
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(content.encode())

        return cls(
            document_type=DocumentType.TXT,
            source=LocalFileSource(path=Path(temp_file.name)),
        )

    @classmethod
    def from_local_path(cls, local_path: Path) -> "DocumentMeta":
        """
        Create a document metadata from a local path.

        Args:
            local_path: The local path to the document.

        Returns:
            The document metadata.
        """
        return cls(
            document_type=DocumentType(local_path.suffix[1:]),
            source=LocalFileSource(path=local_path),
        )

    @classmethod
    async def from_source(cls, source: Source) -> "DocumentMeta":
        """
        Create a document metadata from a source.

        Args:
            source: The source from which the document is fetched.

        Returns:
            The document metadata.
        """
        path = await source.fetch()

        return cls(
            document_type=DocumentType(path.suffix[1:]),
            source=source,
        )


class Document(BaseModel):
    """
    An object representing a document which is downloaded and stored locally.
    """

    local_path: Path
    metadata: DocumentMeta

    @classmethod
    def from_document_meta(cls, document_meta: DocumentMeta, local_path: Path) -> "Document":
        """
        Create a document from a document metadata.
        Based on the document type, it will return a different object.

        Args:
            document_meta: The document metadata.
            local_path: The local path to the document.

        Returns:
            The document.
        """
        if document_meta.document_type in [DocumentType.MD, DocumentType.TXT]:
            return TextDocument(local_path=local_path, metadata=document_meta)
        return cls(local_path=local_path, metadata=document_meta)


class TextDocument(Document):
    """
    An object representing a text document.
    """

    @property
    def content(self) -> str:
        """
        Get the content of the document.

        Returns:
            The content of the document.
        """
        return self.local_path.read_text()
