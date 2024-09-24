from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.ingestion.document_processor import DocumentProcessor
from ragbits.document_search.ingestion.providers.dummy import DummyProvider


async def test_document_processor_processes_text_document_with_dummy_provider():
    providers_config = {DocumentType.TXT: DummyProvider()}
    document_processor = DocumentProcessor.from_config(providers_config)
    document_meta = DocumentMeta.create_text_document_from_literal("Name of Peppa's brother is George")

    elements = await document_processor.process(document_meta)

    assert isinstance(document_processor._providers[DocumentType.TXT], DummyProvider)
    assert len(elements) == 1
    assert elements[0].content == "Name of Peppa's brother is George"
