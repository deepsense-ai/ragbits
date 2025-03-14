from pathlib import Path

import pytest

from ragbits.core.llms.litellm import LiteLLM, LiteLLMOptions
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import ImageElement, IntermediateImageElement
from ragbits.document_search.ingestion.intermediate_handlers.images import ImageIntermediateHandler, _ImagePrompt


@pytest.fixture
def llm() -> LiteLLM:
    options = LiteLLMOptions(mock_response="response")
    llm = LiteLLM(model_name="gpt-4o", api_key="key", default_options=options)
    return llm


@pytest.fixture
def image_bytes() -> bytes:
    with open(Path(__file__).parent.parent / "test.png", "rb") as f:
        return f.read()


@pytest.fixture
def intermediate_image_element(image_bytes: bytes) -> IntermediateImageElement:
    return IntermediateImageElement(
        document_meta=DocumentMeta.create_text_document_from_literal(""),
        image_bytes=image_bytes,
        ocr_extracted_text="ocr text",
    )


@pytest.mark.asyncio
async def test_process(llm: LiteLLM, intermediate_image_element: IntermediateImageElement):
    handler = ImageIntermediateHandler(llm=llm)
    results = await handler.process([intermediate_image_element])

    assert len(results) == 1
    assert isinstance(results[0], ImageElement)
    assert results[0].description == "response"
    assert results[0].image_bytes == intermediate_image_element.image_bytes
    assert results[0].ocr_extracted_text == intermediate_image_element.ocr_extracted_text


def test_from_config():
    config = {
        "llm": {
            "type": "LiteLLM",
            "prompt": "ragbits.document_search.ingestion.intermediate_handlers.images:_ImagePrompt",
        }
    }

    handler = ImageIntermediateHandler.from_config(config)

    assert isinstance(handler, ImageIntermediateHandler)
    assert isinstance(handler._llm, LiteLLM)
    assert handler._prompt == _ImagePrompt
