from distilabel.llms import OpenAILLM
from distilabel.pipeline import Pipeline
import asyncio
from ragbits.evaluate.dataset_generator.tasks.answer_gen_task import AnswerGenTask
from ragbits.evaluate.dataset_generator.tasks.passages_gen_task import PassagesGenTask
from ragbits.evaluate.dataset_generator.tasks.query_gen_task import QueryGenTask
from ragbits.document_search.ingestion.document_processor import DocumentProcessorRouter
from ragbits.document_search.documents.document import DocumentType, Document, DocumentMeta

from ragbits.document_search.ingestion.providers.unstructured.pdf import UnstructuredPdfProvider

from datasets import Dataset

from pathlib import Path

CORPUS_PATH = Path("corpus-path")
DATASET_HF_PATH = "dataset-hf-path"


async def main():
    router = DocumentProcessorRouter(
        providers={DocumentType.PDF: UnstructuredPdfProvider(chunking_kwargs={"max_characters": 512})}
    )
    document_meta = DocumentMeta.from_local_path(local_path=CORPUS_PATH)
    document_processor = router.get_provider(document_meta)
    elements = await document_processor.process(document_meta)
    dataset = Dataset.from_dict({
        "chunk": [node.content for node in elements if node.element_type=="text"][:2]
    })

    with Pipeline("synthetic-RAG-data") as pipeline:
        query_gen_task = QueryGenTask(
            llm=OpenAILLM(model="gpt-4o"),
        )

        answer_gen_task = AnswerGenTask(
            llm=OpenAILLM(model="gpt-4o")
        )

        passages_gen_task = PassagesGenTask(
            llm=OpenAILLM(model="gpt-4o"),
        )

        # TODO: Add I don't know answer step.

        query_gen_task >> answer_gen_task >> passages_gen_task

    distiset = pipeline.run(
        use_cache=False,
        dataset=dataset
    )
    result = distiset["default"]["train"]
    result = result.remove_columns(["distilabel_metadata", "model_name"])

    result.push_to_hub(
        DATASET_HF_PATH,
        private=False,
    )

if __name__ == "__main__":
    asyncio.run(main())


