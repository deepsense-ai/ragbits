import uuid
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, computed_field

from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.document_search.documents.document import DocumentMeta


class ElementLocation(BaseModel):
    """
    An object representing position of chunk within document.
    """

    page_number: int | None = None
    coordinates: dict | None = None


class Element(BaseModel, ABC):
    """
    An object representing an element in a document.
    """

    element_type: str
    document_meta: DocumentMeta
    location: ElementLocation | None = None

    _elements_registry: ClassVar[dict[str, type["Element"]]] = {}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        """
        Get the ID of the element. The id is primarly used as a key in the vector store.
        The current representation is a UUID5 hash of various element metadata, including
        its contents and location where it was sourced from.

        Returns:
            The ID in the form of a UUID5 hash.
        """
        id_components = [
            self.document_meta.id,
            self.element_type,
            self.get_text_for_embedding(),
            self.get_text_representation(),
            str(self.location),
        ]

        return str(uuid.uuid5(uuid.NAMESPACE_OID, ";".join(id_components)))

    def get_text_for_embedding(self) -> str:
        """
        Get the text representation of the element for embedding.

        Returns:
            The text representation for embedding.
        """
        return self.get_text_representation()

    @abstractmethod
    def get_text_representation(self) -> str:
        """
        Get the text representation of the element.

        Returns:
            The text representation.
        """

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:  # pylint: disable=unused-argument #noqa: ANN401
        element_type_default = cls.model_fields["element_type"].default

        if element_type_default is None:
            raise ValueError("Element type must be defined")

        Element._elements_registry[element_type_default] = cls

    @classmethod
    def from_vector_db_entry(cls, db_entry: VectorStoreEntry) -> "Element":
        """
        Create an element from a vector database entry.

        Args:
            db_entry: The vector database entry.

        Returns:
            The element.
        """
        meta = db_entry.metadata
        element_type = meta["element_type"]
        element_cls = Element._elements_registry[element_type]

        return element_cls(**meta)

    def to_vector_db_entry(self, vector: list[float]) -> VectorStoreEntry:
        """
        Create a vector database entry from the element.

        Args:
            vector: The vector.

        Returns:
            The vector database entry
        """
        return VectorStoreEntry(
            id=self.id,
            vector=vector,
            content=self.get_text_for_embedding(),
            metadata=self.model_dump(),
        )


class TextElement(Element):
    """
    An object representing a text element in a document.
    """

    element_type: str = "text"
    content: str

    def get_text_representation(self) -> str:
        """
        Get the text representation of the element.

        Returns:
            The text representation.
        """
        return self.content


class ImageElement(Element):
    """
    An object representing an image element in a document.
    """

    element_type: str = "image"
    description: str
    ocr_extracted_text: str
    image_bytes: bytes

    def get_text_representation(self) -> str:
        """
        Get the text representation of the element.

        Returns:
            The text representation.
        """
        return f"Description: {self.description}\nExtracted text: {self.ocr_extracted_text}"
