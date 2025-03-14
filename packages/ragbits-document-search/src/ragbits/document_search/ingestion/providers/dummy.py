from collections.abc import Sequence

from ragbits.document_search.documents.document import (
    DocumentMeta,
    DocumentType,
    TextDocument,
)
from ragbits.document_search.documents.element import Element, ImageElement, IntermediateElement, TextElement
from ragbits.document_search.ingestion.providers.base import BaseProvider


class DummyProvider(BaseProvider):
    """
    This is a mock provider that returns a TextElement with the content of the document.
    It should be used for testing purposes only.
    """

    SUPPORTED_DOCUMENT_TYPES = {DocumentType.TXT, DocumentType.MD}

    async def process(self, document_meta: DocumentMeta) -> list[Element | IntermediateElement]:
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


class DummyImageProvider(BaseProvider):
    """
    This is a simple provider that returns an ImageElement with the content of the image
    and empty text metadata.
    """

    SUPPORTED_DOCUMENT_TYPES = {DocumentType.JPG, DocumentType.PNG}

    async def process(self, document_meta: DocumentMeta) -> Sequence[Element | IntermediateElement]:
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
                description="",
                ocr_extracted_text="",
                image_bytes=image_bytes,
                document_meta=document_meta,
            )
        ]
