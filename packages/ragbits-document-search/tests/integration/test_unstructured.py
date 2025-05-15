from pathlib import Path

import pytest

from ragbits.core.utils.helpers import env_vars_not_set
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.ingestion.parsers.unstructured import (
    UNSTRUCTURED_API_KEY_ENV,
    UNSTRUCTURED_SERVER_URL_ENV,
    UnstructuredDocumentParser,
)


@pytest.mark.parametrize(
    "use_api",
    [
        pytest.param(
            False,
            marks=pytest.mark.skipif(True, reason="No dependencies installed"),
            id="local",
        ),
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                env_vars_not_set([UNSTRUCTURED_SERVER_URL_ENV, UNSTRUCTURED_API_KEY_ENV]),
                reason="Unstructured API environment variables not set",
            ),
            id="api",
        ),
    ],
)
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
            7,
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
async def test_unstructured_parser(use_api: bool, document_metadata: DocumentMeta, expected_num_elements: int) -> None:
    document = await document_metadata.fetch()
    parser = UnstructuredDocumentParser(use_api=use_api)

    elements = await parser.parse(document)

    assert len(elements) == expected_num_elements
