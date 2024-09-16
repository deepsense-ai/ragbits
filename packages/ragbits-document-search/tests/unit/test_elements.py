from ragbits_document_search.documents.document import DocumentType
from ragbits_document_search.documents.element import Element
from ragbits_document_search.vector_store.base import VectorDBEntry


def test_resolving_element_type():
    class MyElement(Element):
        element_type: str = "custom_element"
        foo: str

        def get_key(self) -> str:
            return self.foo + self.foo

    element = Element.from_vector_db_entry(
        db_entry=VectorDBEntry(
            key="key",
            vector=[0.1, 0.2],
            metadata={
                "element_type": "custom_element",
                "foo": "bar",
                "document": {"document_type": "txt", "source": {"source_type": "local_file", "path": "/example/path"}},
            },
        )
    )

    assert isinstance(element, MyElement)
    assert element.foo == "bar"
    assert element.get_key() == "barbar"
    assert element.document.document_type == DocumentType.TXT
    assert element.document.source.source_type == "local_file"
