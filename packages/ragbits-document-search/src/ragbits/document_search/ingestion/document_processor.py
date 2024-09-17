"""
TODO: This module is mocked. To be deleted and replaced with a real implementation.
"""

from typing import List

from ragbits.document_search.documents.document import DocumentMeta, TextDocument
from ragbits.document_search.documents.element import Element, TextElement


class DocumentProcessor:
    """
    A class with an implementation of Document Processor, allowing to process documents.

    TODO: probably this one should be replaced with something more generic,
          allowing for passing different processors for different document types.
    """

    async def process(self, document_meta: DocumentMeta) -> List[Element]:
        """
        Process the document.

        Args:
            document_meta: The document to process.

        Returns:
            The processed elements.
        """
        document = await document_meta.fetch()

        if isinstance(document, TextDocument):
            # for now just return the whole document as a single element
            return [TextElement(document=document_meta, content=document.content)]

        return []
