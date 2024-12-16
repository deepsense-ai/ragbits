from ragbits.core.embeddings.local import LocalEmbeddingsOptions

if __name__ == "__main__":
    extra_kwargs = {"model_name": "bert-base"}
    local_embedding_options = LocalEmbeddingsOptions(**extra_kwargs)  # type: ignore

    second_local_embedding_options = LocalEmbeddingsOptions(batch_size=10, something=20)  # type: ignore

    merged = local_embedding_options | second_local_embedding_options

    print(merged.dict())
    print(merged)
