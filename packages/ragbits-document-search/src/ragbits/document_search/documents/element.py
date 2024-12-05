import hashlib
import uuid
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, computed_field

from ragbits.core.embeddings import EmbeddingType
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

    # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        """
        Retrieve the ID of the element, primarily used to represent the element's data.

        Returns:
            str: string representing element
        """
        id_components = self.get_id_components()
        return "&".join(f"{k}={v}" for k, v in id_components.items())

    def get_id_components(self) -> dict[str, str]:
        """
        Creates a dictionary of key value pairs of id components

        Returns:
            dict: a dictionary
        """
        id_components = {
            "meta": self.document_meta.id,
            "type": self.element_type,
            "key": str(self.key),
            "text": str(self.text_representation),
            "location": str(self.location),
        }
        return id_components

    @computed_field  # type: ignore[prop-decorator]
    @property
    def key(self) -> str | None:
        """
        Get the representation of the element for embedding.

        Returns:
            The representation for embedding.
        """
        return self.text_representation

    @computed_field  # type: ignore[prop-decorator]
    @property
    @abstractmethod
    def text_representation(self) -> str | None:
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
        if "embedding_type" in db_entry.metadata:
            del db_entry.metadata["embedding_type"]
        return element_cls(**db_entry.metadata)

    def to_vector_db_entry(self, vector: list[float], embedding_type: EmbeddingType) -> VectorStoreEntry:
        """
        Create a vector database entry from the element.

        Args:
            vector: The vector.
            embedding_type: EmbeddingTypes
        Returns:
            The vector database entry
        """
        id_components = [
            self.id,
            str(embedding_type),
        ]
        vector_store_entry_id = str(uuid.uuid5(uuid.NAMESPACE_OID, ";".join(id_components)))
        metadata = self.model_dump(exclude={"id", "key"})
        metadata["embedding_type"] = str(embedding_type)
        metadata["document_meta"]["source"]["id"] = self.document_meta.source.id
        return VectorStoreEntry(id=vector_store_entry_id, key=str(self.key), vector=vector, metadata=metadata)


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
    def text_representation(self) -> str | None:
        """
        Get the text representation of the element.

        Returns:
            The text representation.
        """
        if not self.description and not self.ocr_extracted_text:
            return None
        repr = ""
        if self.description:
            repr += f"Description: {self.description}\n"
        if self.ocr_extracted_text:
            repr += f"Extracted text: {self.ocr_extracted_text}"
        return repr

    def get_id_components(self) -> dict[str, str]:
        """
        Creates a dictionary of key value pairs of id components

        Returns:
            dict: a dictionary
        """
        id_components = super().get_id_components()
        id_components["image_hash"] = hashlib.sha256(self.image_bytes).hexdigest()
        return id_components
