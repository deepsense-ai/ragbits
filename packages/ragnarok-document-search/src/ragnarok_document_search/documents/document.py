import tempfile
from enum import Enum
from pathlib import Path
from typing import Union

from pydantic import BaseModel, Field
from ragnarok_document_search.documents.sources import LocalFileSource


class DocumentType(str, Enum):
    """Types of documents that can be stored."""

    MD = "md"
    TXT = "txt"


class DocumentMeta(BaseModel):
    """
    An object representing a document metadata.
    """

    document_type: DocumentType
    source: Union[LocalFileSource] = Field(..., discriminator="source_type")

    @property
    def id(self) -> str:
        """
        Get the document ID.

        Returns:
            The document ID.
        """
        return self.source.get_id()

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


class Document(DocumentMeta):
    """
    An object representing a document which is downloaded and stored locally.
    """

    local_path: Path

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
        new_obj = {"local_path": local_path, **document_meta.model_dump()}

        if document_meta.document_type in [DocumentType.MD, DocumentType.TXT]:
            return TextDocument.model_validate(new_obj)
        return cls.model_validate(new_obj)


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
