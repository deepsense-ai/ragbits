from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from ragbits.core.vector_store.base import VectorDBEntry
from ragbits.document_search.documents.document import DocumentMeta


class Element(BaseModel, ABC):
    """
    An object representing an element in a document.
    """

    element_type: str
    document_meta: DocumentMeta

    _elements_registry: ClassVar[dict[str, type["Element"]]] = {}

    @abstractmethod
    def get_key(self) -> str:
        """
        Get the key of the element which will be used to generate the vector.

        Returns:
            The key.
        """

    @classmethod
    def __pydantic_init_subclass__(cls) -> None:  # pylint: disable=unused-argument
        element_type_default = cls.model_fields["element_type"].default

        if element_type_default is None:
            raise ValueError("Element type must be defined")

        Element._elements_registry[element_type_default] = cls

    @classmethod
    def from_vector_db_entry(cls, db_entry: VectorDBEntry) -> "Element":
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

    def to_vector_db_entry(self, vector: list[float]) -> VectorDBEntry:
        """
        Create a vector database entry from the element.

        Args:
            vector: The vector.

        Returns:
            The vector database entry
        """
        return VectorDBEntry(
            key=self.get_key(),
            vector=vector,
            metadata=self.model_dump(),
        )


class TextElement(Element):
    """
    An object representing a text element in a document.
    """

    element_type: str = "text"
    content: str

    def get_key(self) -> str:
        """
        Get the key of the element which will be used to generate the vector.

        Returns:
            The key.
        """
        return self.content
