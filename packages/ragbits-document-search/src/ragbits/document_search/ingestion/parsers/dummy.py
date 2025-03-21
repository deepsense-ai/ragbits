from ragbits.document_search.documents.document import (
    DocumentMeta,
    DocumentType,
    TextDocument,
)
from ragbits.document_search.documents.element import Element, ImageElement, TextElement
from ragbits.document_search.ingestion.parsers.base import DocumentParser


class DummyProvider(DocumentParser):
    """
    This is a mock provider that returns a TextElement with the content of the document.
    It should be used for testing purposes only.
    """

    supported_document_types = {DocumentType.TXT, DocumentType.MD}

    async def parse(self, document_meta: DocumentMeta) -> list[Element]:
        """
        Process the text document.

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


class DummyImageProvider(DocumentParser):
    """
    This is a simple provider that returns an ImageElement with the content of the image
    and empty text metadata.
    """

    supported_document_types = {DocumentType.JPG, DocumentType.PNG}

    async def parse(self, document_meta: DocumentMeta) -> list[Element]:
        """
        Process the image document.

        Args:
            document_meta: The document to process.

        Returns:
            List with a single ImageElement containing the content of the image.
        """
        self.validate_document_type(document_meta.document_type)

        document = await document_meta.fetch()
        image_path = document.local_path
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        return [
            ImageElement(
                image_bytes=image_bytes,
                document_meta=document_meta,
            )
        ]
