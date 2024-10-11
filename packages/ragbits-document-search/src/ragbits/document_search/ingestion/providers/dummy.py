from ragbits.document_search.documents.document import (
    DocumentMeta,
    DocumentType,
    TextDocument,
)
from ragbits.document_search.documents.element import Element, TextElement
from ragbits.document_search.ingestion.providers.base import BaseProvider


class DummyProvider(BaseProvider):
    """This is a mock provider that returns a TextElement with the content of the document.
    It should be used for testing purposes only.

    TODO: Remove this provider after the implementation of the real providers.
    """

    SUPPORTED_DOCUMENT_TYPES = {DocumentType.TXT}

    async def process(self, document_meta: DocumentMeta) -> list[Element]:
        """Process the text document.

        Args:
            document_meta: The document to process.

        Returns:
            List with a single TextElement containing the content of the document.
        """
        self.validate_document_type(document_meta.document_type)

        document = await document_meta.fetch()
        if isinstance(document, TextDocument):
            return [TextElement(content=document.content, document_meta=document_meta)]
        return []
