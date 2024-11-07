from distilabel.llms import OpenAILLM
from distilabel.pipeline import Pipeline
import asyncio
from ragbits.evaluate.dataset_generator.tasks.text_generation.qa import AnswerGenTask, PassagesGenTask, QueryGenTask
from ragbits.evaluate.dataset_generator.tasks.filter.dont_know import DontKnowFilter


from datasets import Dataset

from pathlib import Path

CORPUS_PATH = Path("osha3192.pdf")
DATASET_HF_PATH = "osho"


async def main():
    # router = DocumentProcessorRouter(
    #     providers={DocumentType.PDF: UnstructuredPdfProvider(chunking_kwargs={"max_characters": 512})}
    # )
    # document_meta = DocumentMeta.from_local_path(local_path=CORPUS_PATH)
    # document_processor = router.get_provider(document_meta)
    # elements = await document_processor.process(document_meta)
    FACTOIDS = ["Neural networks are algorithms capable of recognition and processing the data structure", "Warsaw is capital of Poland", "Ambafatima"]
    dataset = Dataset.from_dict({
        "chunk": FACTOIDS
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

        dont_know_filter = DontKnowFilter(task=answer_gen_task)


        query_gen_task >> answer_gen_task  >> passages_gen_task >> dont_know_filter

    distiset = pipeline.run(
        use_cache=False,
        dataset=dataset
    )
    result = distiset["default"]["train"]
    result = result.remove_columns(["distilabel_metadata", "model_name"])

    breakpoint()
    result.push_to_hub(
        DATASET_HF_PATH,
        private=False,
    )

if __name__ == "__main__":
    asyncio.run(main())


