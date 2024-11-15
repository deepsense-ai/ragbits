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
            self.key,
            self.text_representation,
            str(self.location),
        ]
        return str(uuid.uuid5(uuid.NAMESPACE_OID, ";".join(id_components)))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def key(self) -> str:
        """
        Get the representation of the element for embedding.

        Returns:
            The representation for embedding.
        """
        return self.text_representation

    @computed_field  # type: ignore[prop-decorator]
    @property
    @abstractmethod
    def text_representation(self) -> str:
        """
        Get the text representation of the element.

        Returns:
            The text representation.
        """

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
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
        element_type = db_entry.metadata["element_type"]
        element_cls = Element._elements_registry[element_type]
        return element_cls(**db_entry.metadata)

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
            key=self.key,
            vector=vector,
            metadata=self.model_dump(exclude={"id", "key"}),
        )


class TextElement(Element):
    """
    An object representing a text element in a document.
    """

    element_type: str = "text"
    content: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def text_representation(self) -> str:
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def text_representation(self) -> str:
        """
        Get the text representation of the element.

        Returns:
            The text representation.
        """
        return f"Description: {self.description}\nExtracted text: {self.ocr_extracted_text}"
