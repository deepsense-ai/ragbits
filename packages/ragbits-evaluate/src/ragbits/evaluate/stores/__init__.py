"""Evaluation report storage backends.

This module provides pluggable storage backends for evaluation reports.
The default is FileEvalReportStore which maintains backward compatibility
with the existing file-based approach.

Example usage:
    from ragbits.evaluate.stores import FileEvalReportStore, KVEvalReportStore

    # File-based storage (default)
    store = FileEvalReportStore(results_dir="./eval_results")

    # KV-based storage using PostgreSQL (recommended for production)
    from ragbits.core.storage.connections import PostgresConnection
    from ragbits.core.storage.kv_store import PostgresKVStore

    conn = PostgresConnection(host="localhost", database="mydb")
    kv = PostgresKVStore(connection=conn, table_name="eval_results")
    store = KVEvalReportStore(kv_store=kv)
"""

from ragbits.evaluate.stores.base import EvalReportStore
from ragbits.evaluate.stores.file import FileEvalReportStore

__all__ = [
    "EvalReportStore",
    "FileEvalReportStore",
]

# KV store is optional (requires ragbits-core with storage extras)
try:
    from ragbits.evaluate.stores.kv import KVEvalReportStore  # noqa: F401

    __all__.append("KVEvalReportStore")
except ImportError:
    pass
