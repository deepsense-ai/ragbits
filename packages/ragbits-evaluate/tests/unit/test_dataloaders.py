from unittest.mock import Mock

from ragbits.evaluate.dataloaders import EvalPortDataLoader


async def test_evalport_data_loader_maps_standard_fields() -> None:
    loader = EvalPortDataLoader(source=Mock())

    result = await loader.map(
        [
            {
                "input": "What is RAG?",
                "expected_output": "Retrieval-augmented generation.",
                "retrieval_context": ["RAG retrieves context before generation."],
                "metadata": {"id": "case-1"},
            }
        ]
    )

    assert list(result)[0].model_dump() == {
        "question": "What is RAG?",
        "reference_answer": "Retrieval-augmented generation.",
        "reference_context": ["RAG retrieves context before generation."],
    }


def test_evalport_data_loader_uses_data_split_and_required_fields() -> None:
    loader = EvalPortDataLoader(source=Mock())

    assert loader.split == "data"
    assert loader.required_keys == {"input", "expected_output"}
