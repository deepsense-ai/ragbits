from pydantic import computed_field

from ragbits.document_search.documents.element import Element


class CustomElement(Element):
    element_type: str = "custom_element"
    custom_field: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def text_representation(self) -> str:
        return self.custom_field
