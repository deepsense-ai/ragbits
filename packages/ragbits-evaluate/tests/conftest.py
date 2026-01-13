def pytest_configure(config):
    """Import continuous_eval before xdist workers spawn.

    This triggers NLTK data download on the main process, preventing
    race conditions when workers try to download concurrently.
    """
    try:
        import continuous_eval.metrics.retrieval  # noqa: F401
    except Exception:
        pass
