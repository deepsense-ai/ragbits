from docling.chunking import HierarchicalChunker
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import AcceleratorOptions, EasyOcrOptions, PdfPipelineOptions, PipelineOptions
from docling.document_converter import (
    DocumentConverter,
    ExcelFormatOption,
    HTMLFormatOption,
    MarkdownFormatOption,
    PdfFormatOption,
    PowerpointFormatOption,
    WordFormatOption,
)
from docling_core.types.doc import DocItem, DoclingDocument

from ragbits.document_search.documents.document import Document, DocumentType
from ragbits.document_search.documents.element import Element, ElementLocation, ImageElement, TextElement
from ragbits.document_search.ingestion.parsers import DocumentParser


class DoclingDocumentParser(DocumentParser):
    """
    Parser that uses the Docling to process the documents.
    """

    supported_document_types = {
        DocumentType.DOCX,
        DocumentType.PPTX,
        DocumentType.XLSX,
        DocumentType.MD,
        DocumentType.PNG,
        DocumentType.JPG,
        DocumentType.HTML,
        DocumentType.TXT,
        DocumentType.PDF,
    }

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

        Raises:
            ConversionError: If converting the document to the Docling format fails.
        """
        accelerator_options = AcceleratorOptions(num_threads=self.num_threads)
        pipeline_options = PipelineOptions(accelerator_options=accelerator_options)
        pdf_pipeline_options = PdfPipelineOptions(
            images_scale=2,
            generate_page_images=True,
            ocr_options=EasyOcrOptions(),
            accelerator_options=accelerator_options,
        )
        converter = DocumentConverter(
            format_options={
                InputFormat.XLSX: ExcelFormatOption(pipeline_options=pipeline_options),
                InputFormat.DOCX: WordFormatOption(pipeline_options=pipeline_options),
                InputFormat.PPTX: PowerpointFormatOption(pipeline_options=pipeline_options),
                InputFormat.HTML: HTMLFormatOption(pipeline_options=pipeline_options),
                InputFormat.MD: MarkdownFormatOption(pipeline_options=pipeline_options),
                InputFormat.IMAGE: PdfFormatOption(pipeline_options=pdf_pipeline_options),
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_pipeline_options),
            },
        )
        # For txt files, temporarily rename to .md extension. Docling doesn't support text files natively.
        if document.metadata.document_type == DocumentType.TXT:
            original_suffix = document.local_path.suffix
            document.local_path = document.local_path.rename(document.local_path.with_suffix(".md"))

        partitioned_document = converter.convert(document.local_path).document

        # Convert back to the original file.
        if document.metadata.document_type == DocumentType.TXT:
            document.local_path = document.local_path.rename(document.local_path.with_suffix(original_suffix))

        return partitioned_document

    def _chunk(self, partitioned_document: DoclingDocument, document: Document) -> list[Element]:
        """
        Chunk the partitioned document.

        Args:
            partitioned_document: The partitioned document by Docling.
            document: The document to parse.

        Returns:
            The list of chunked elements.
        """
        chunker = HierarchicalChunker()
        text_elements: list[Element] = [
            TextElement(
                document_meta=document.metadata,
                location=self._extract_element_location(chunk.meta.doc_items[0]),  # type: ignore
                content=chunk.text,
            )
            for chunk in chunker.chunk(partitioned_document)
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
