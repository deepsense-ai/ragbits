from pathlib import Path

import pytest

from ragbits.core.utils.config_handling import ObjectConstructionConfig
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import ImageElement, TextElement
from ragbits.document_search.ingestion.parsers.base import DocumentParser, ImageDocumentParser, TextDocumentParser
from ragbits.document_search.ingestion.parsers.exceptions import ParserDocumentNotSupportedError
from ragbits.document_search.ingestion.parsers.unstructured import UnstructuredDocumentParser


@pytest.mark.parametrize("document_type", UnstructuredDocumentParser.supported_document_types)
def test_parser_validates_supported_document_types_passes(document_type: DocumentType) -> None:
    UnstructuredDocumentParser.validate_document_type(document_type)


def test_parser_validates_supported_document_types_fails() -> None:
    with pytest.raises(ParserDocumentNotSupportedError):
        UnstructuredDocumentParser.validate_document_type(DocumentType.UNKNOWN)


@pytest.mark.parametrize(
    ("parser_type", "expected_parser"),
    [
        ("ragbits.document_search.ingestion.parsers.base:TextDocumentParser", TextDocumentParser),
        ("ragbits.document_search.ingestion.parsers.base:ImageDocumentParser", ImageDocumentParser),
        (
            "ragbits.document_search.ingestion.parsers.unstructured:UnstructuredDocumentParser",
            UnstructuredDocumentParser,
        ),
        ("TextDocumentParser", TextDocumentParser),
        ("ImageDocumentParser", ImageDocumentParser),
    ],
)
def test_parser_subclass_from_config(parser_type: str, expected_parser: type[DocumentParser]) -> None:
    config = ObjectConstructionConfig.model_validate({"type": parser_type})
    parser = DocumentParser.subclass_from_config(config)

    assert isinstance(parser, expected_parser)


async def test_text_parser_call() -> None:
    document_meta = DocumentMeta.from_local_path(Path(__file__).parent.parent / "assets" / "md" / "test_file.md")
    document = await document_meta.fetch()
    enricher = TextDocumentParser()

    elements = await enricher.parse(document)

    assert len(elements) == 1
    assert isinstance(elements[0], TextElement)
    assert elements[0].content == "# Ragbits\n\nRepository for internal experiment with our upcoming LLM framework.\n"


async def test_image_parser_call() -> None:
    document_meta = DocumentMeta.from_local_path(
        Path(__file__).parent.parent / "assets" / "img" / "transformers_paper_page.png"
    )
    document = await document_meta.fetch()
    parser = ImageDocumentParser()

    elements = await parser.parse(document)

    assert len(elements) == 1
    assert isinstance(elements[0], ImageElement)
    assert elements[0].image_bytes == document.local_path.read_bytes()
    assert elements[0].description is None
    assert elements[0].ocr_extracted_text is None


@pytest.mark.parametrize(
    "parser_type",
    [
        ImageDocumentParser,
        TextDocumentParser,
    ],
)
async def test_parser_call_fail(parser_type: type[DocumentParser]) -> None:
    document_meta = DocumentMeta.from_local_path(
        Path(__file__).parent.parent / "assets" / "pdf" / "transformers_paper_page.pdf"
    )
    document = await document_meta.fetch()
    parser = parser_type()

    with pytest.raises(ParserDocumentNotSupportedError) as exc:
        await parser.parse(document)

    assert exc.value.message == f"Document type {DocumentType.PDF.value} is not supported by the {parser_type.__name__}"
    assert exc.value.document_type == DocumentType.PDF
    assert exc.value.parser_name == parser_type.__name__
