from pathlib import Path

import pytest

from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import Element, ImageElement
from ragbits.document_search.ingestion.enrichers.exceptions import EnricherElementNotSupportedError
from ragbits.document_search.ingestion.enrichers.image import ImageDescriberPrompt, ImageElementEnricher


@pytest.fixture
def llm() -> LiteLLM:
    default_options = LiteLLMOptions(mock_response='{"description": "response"}')
    return LiteLLM(model_name="gpt-4o", default_options=default_options)


@pytest.fixture
def image_bytes() -> bytes:
    with open(Path(__file__).parent.parent / "test.png", "rb") as f:
        return f.read()


@pytest.fixture
def image_element(image_bytes: bytes) -> ImageElement:
    return ImageElement(
        document_meta=DocumentMeta.create_text_document_from_literal(""),
        image_bytes=image_bytes,
        ocr_extracted_text="ocr text",
    )


def test_enricher_validates_supported_element_types_passes() -> None:
    ImageElementEnricher.validate_element_type(ImageElement)


def test_enricher_validates_supported_document_types_fails() -> None:
    class CustomElement(Element):
        pass

    with pytest.raises(EnricherElementNotSupportedError):
        ImageElementEnricher.validate_element_type(CustomElement)  # type: ignore


async def test_process(llm: LiteLLM, image_element: ImageElement):
    enricher = ImageElementEnricher(llm=llm)
    results = await enricher.enrich([image_element])

    assert len(results) == 1
    assert isinstance(results[0], ImageElement)
    assert results[0].description == "response"
    assert results[0].image_bytes == image_element.image_bytes
    assert results[0].ocr_extracted_text == image_element.ocr_extracted_text


def test_from_config():
    config = {
        "llm": {
            "type": "LiteLLM",
            "prompt": "ragbits.document_search.ingestion.enrichers.image:ImageDescriberPrompt",
        }
    }

    enricher = ImageElementEnricher.from_config(config)

    assert isinstance(enricher, ImageElementEnricher)
    assert isinstance(enricher._llm, LiteLLM)
    assert enricher._prompt == ImageDescriberPrompt
