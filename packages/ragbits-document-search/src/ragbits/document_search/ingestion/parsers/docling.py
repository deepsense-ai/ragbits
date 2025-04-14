from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import AcceleratorOptions, EasyOcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import DocItem, DoclingDocument

from ragbits.document_search.documents.document import Document, DocumentType
from ragbits.document_search.documents.element import Element, ElementLocation, ImageElement, TextElement
from ragbits.document_search.ingestion.parsers import DocumentParser


class DoclingDocumentParser(DocumentParser):
    """
    Parser that uses the Docling to process the documents.
    """

    # NOTE: For now this parser supports only PDF files
    supported_document_types = {DocumentType.PDF}

    def __init__(self, ignore_images: bool = False, num_threads: int = 1) -> None:
        """
        Initialize the DoclingDocumentParser instance.

        Args:
            ignore_images: If True images will be skipped.
            num_threads: The number of threads for parsing parallelism on CPU.
        """
        self.ignore_images = ignore_images
        self.num_threads = num_threads

    async def parse(self, document: Document) -> list[Element]:
        """
        Parse the document using the Docling API.

        Args:
            document: The document to parse.

        Returns:
            The list of elements extracted from the document.
        """
        self.validate_document_type(document.metadata.document_type)
        partitioned_document = await self._partition(document)
        return self._chunk(partitioned_document, document)

    async def _partition(self, document: Document) -> DoclingDocument:
        """
        Partition the document.

        Args:
            document: The document to parse.

        Returns:
            The docling document.
        """
        pipeline_options = PdfPipelineOptions(
            images_scale=2,
            generate_page_images=True,
            ocr_options=EasyOcrOptions(),
            accelerator_options=AcceleratorOptions(num_threads=self.num_threads),
        )
        # TODO: Check pipeline options for other document types
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            },
        )
        return converter.convert(document.local_path).document

    def _chunk(self, partitioned_document: DoclingDocument, document: Document) -> list[Element]:
        """
        Chunk the partitioned document.

        Args:
            partitioned_document: The partitioned document by Docling.
            document: The document to parse.

        Returns:
            The list of chunked elements.
        """
        text_elements: list[Element] = [
            TextElement(
                document_meta=document.metadata,
                location=self._extract_element_location(element),
                content=element.text,
            )
            for element in partitioned_document.texts
        ]

        if self.ignore_images:
            return text_elements

        return text_elements + [
            ImageElement(
                document_meta=document.metadata,
                location=self._extract_element_location(element),
                image_bytes=image_bytes,
                ocr_extracted_text=element.caption_text(partitioned_document),
            )
            for element in partitioned_document.pictures
            if (image := element.get_image(partitioned_document)) and (image_bytes := image._repr_jpeg_())
        ]

    @staticmethod
    def _extract_element_location(element: DocItem) -> ElementLocation:
        """
        Convert docling element to element location.

        Args:
            element: The element from docling.

        Returns:
            The element location.
        """
        metadata = element.prov[0].model_dump() if element.prov else {}
        return ElementLocation(
            page_number=metadata.get("page_no"),
        )
