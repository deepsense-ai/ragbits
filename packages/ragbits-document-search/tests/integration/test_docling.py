from pathlib import Path

import pytest

from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.ingestion.parsers.docling import DoclingDocumentParser


@pytest.mark.parametrize(
    ("document_metadata", "expected_num_elements"),
    [
        pytest.param(
            DocumentMeta.from_literal("Name of Peppa's brother is George."),
            1,
            id="TextDocument",
        ),
        pytest.param(
            DocumentMeta.from_local_path(Path(__file__).parent.parent / "assets" / "md" / "test_file.md"),
            1,
            id="MarkdownDocument",
        ),
        pytest.param(
            DocumentMeta.from_local_path(
                Path(__file__).parent.parent / "assets" / "img" / "transformers_paper_page.png"
            ),
            6,
            id="ImageDocument",
        ),
        pytest.param(
            DocumentMeta.from_local_path(
                Path(__file__).parent.parent / "assets" / "pdf" / "transformers_paper_page.pdf"
            ),
            7,
            id="PDFDocument",
        ),
    ],
)
async def test_docling_parser(document_metadata: DocumentMeta, expected_num_elements: int) -> None:
    document = await document_metadata.fetch()
    parser = DoclingDocumentParser()

    elements = await parser.parse(document)

    assert len(elements) == expected_num_elements
