import tempfile
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import filetype
from pydantic import BaseModel
from typing_extensions import deprecated

from ragbits.core.sources.base import Source, SourceDiscriminator
from ragbits.core.sources.local import LocalFileSource


class DocumentType(str, Enum):
    """
    Document types that can be parsed.
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
    JSON = "json"
    JSONL = "jsonl"
    XML = "xml"
    JPG = "jpg"
    PNG = "png"

    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value: object) -> Any:  # noqa: ANN401
        """
        Return WILDCARD if the value is not found in the enum.
        """
        return cls.UNKNOWN


class DocumentMeta(BaseModel):
    """
    An object representing a document metadata.
    """

    document_type: DocumentType
    source: Annotated[Source, SourceDiscriminator()]

    @property
    def id(self) -> str:
        """
        Get the document ID.

        Returns:
            The document ID.
        """
        return self.source.id

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
    @deprecated("Use from_literal() instead")
    def create_text_document_from_literal(cls, content: str) -> "DocumentMeta":
        """
        Create a text document from a literal content. This method is deprecated, use from_literal() instead.

        Args:
            content: The content of the document.

        Returns:
            The document metadata.
        """
        return cls.from_literal(content)

    @classmethod
    def from_literal(cls, content: str) -> "DocumentMeta":
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
            document_type=cls._infer_document_type(local_path),
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
            document_type=cls._infer_document_type(path),
            source=source,
        )

    @staticmethod
    def _infer_document_type(path: Path) -> DocumentType:
        """
        Infer the document type by checking the file signature. Use the file extension as a fallback.

        Args:
            path: The path to the file.

        Returns:
            The inferred document type.
        """
        if kind := filetype.guess(path):
            return DocumentType(kind.extension)
        return DocumentType(path.suffix[1:])


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
