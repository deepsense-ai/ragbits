import hashlib
import uuid
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, computed_field

from ragbits.core.utils.pydantic import SerializableBytes
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
    score: float | None = None

    _elements_registry: ClassVar[dict[str, type["Element"]]] = {}

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

    @property
    def image_representation(self) -> bytes | None:
        """
        Get the image representation of the element.

        Returns:
            The image representation.
        """
        return None

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        element_type_default = cls.model_fields["element_type"].default
        if element_type_default is None:
            raise ValueError("Element type must be defined")
        Element._elements_registry[element_type_default] = cls

    @classmethod
    def from_vector_db_entry(cls, db_entry: VectorStoreEntry, score: float | None = None) -> "Element":
        """
        Create an element from a vector database entry.

        Args:
            db_entry: The vector database entry.
            score: The score of the element retrieved from the vector database or reranker.

        Returns:
            The element.
        """
        element_type = db_entry.metadata["element_type"]
        element_cls = Element._elements_registry[element_type]
        if "embedding_type" in db_entry.metadata:
            del db_entry.metadata["embedding_type"]

        element = element_cls(**db_entry.metadata)
        element.score = score
        return element

    def to_vector_db_entry(self) -> VectorStoreEntry:
        """
        Create a vector database entry from the element.

        Returns:
            The vector database entry
        """
        id_components = [
            self.id,
        ]
        vector_store_entry_id = uuid.uuid5(uuid.NAMESPACE_OID, ";".join(id_components))
        metadata = self.model_dump(exclude={"id", "key"})
        metadata["document_meta"]["source"]["id"] = self.document_meta.source.id

        return VectorStoreEntry(
            id=vector_store_entry_id, text=self.key, image_bytes=self.image_representation, metadata=metadata
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
    image_bytes: SerializableBytes
    description: str | None = None
    ocr_extracted_text: str | None = None

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

    @property
    def image_representation(self) -> bytes:
        """
        Get the image representation of the element.

        Returns:
            The image representation.
        """
        return self.image_bytes

    def get_id_components(self) -> dict[str, str]:
        """
        Creates a dictionary of key value pairs of id components

        Returns:
            dict: a dictionary
        """
        id_components = super().get_id_components()
        id_components["image_hash"] = hashlib.sha256(self.image_bytes).hexdigest()
        return id_components
