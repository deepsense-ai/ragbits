import pytest

from ragbits.document_search.documents.element import ImageElement, TextElement
from ragbits.document_search.ingestion.enrichers.exceptions import EnricherNotFoundError
from ragbits.document_search.ingestion.enrichers.image import ImageElementEnricher
from ragbits.document_search.ingestion.enrichers.router import ElementEnricherRouter


async def test_enricher_router() -> None:
    enricher = ImageElementEnricher()
    enricher_router = ElementEnricherRouter({ImageElement: enricher})

    assert enricher_router.get(ImageElement) is enricher


async def test_enricher_router_raises_when_no_enricher_found() -> None:
    enricher = ImageElementEnricher()
    enricher_router = ElementEnricherRouter()
    enricher_router._enrichers = {ImageElement: enricher}

    with pytest.raises(EnricherNotFoundError) as err:
        enricher_router.get(TextElement)

    assert err.value.message == f"No enricher found for the element type {TextElement}"
    assert err.value.element_type == TextElement
