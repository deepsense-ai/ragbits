from pydantic import computed_field

from ragbits.core.vector_stores.base import VectorStoreEntry
from ragbits.document_search.documents.document import DocumentType
from ragbits.document_search.documents.element import Element


def test_resolving_element_type() -> None:
    class MyElement(Element):
        element_type: str = "custom_element"
        foo: str

        @computed_field  # type: ignore[prop-decorator]
        @property
        def text_representation(self) -> str:
            return self.foo + self.foo

    element = Element.from_vector_db_entry(
        db_entry=VectorStoreEntry(
            id="test id",
            key="test content",
            vector=[0.1, 0.2],
            metadata={
                "element_type": "custom_element",
                "foo": "bar",
                "document_meta": {
                    "document_type": "txt",
                    "source": {"source_type": "local_file_source", "path": "/example/path"},
                },
            },
        )
    )

    assert isinstance(element, MyElement)
    assert element.foo == "bar"
    assert element.key == "barbar"
    assert element.text_representation == "barbar"
    assert element.document_meta.document_type == DocumentType.TXT
    assert element.document_meta.source.source_type == "local_file_source"
