"""Base class for evaluation report storage backends."""

from abc import ABC, abstractmethod
from typing import ClassVar

from ragbits.evaluate import stores as stores_module
from ragbits.evaluate.agent_simulation.results import ResponseChunk, SimulationResult
from ragbits.evaluate.api_types import ResultSummary, SimulationRunDetail, SimulationRunSummary


class EvalReportStore(ABC):
    """Abstract base class for evaluation report storage.

    Provides a pluggable interface for storing and retrieving evaluation results.
    Implementations can use file-based storage, SQLite, PostgreSQL, or other backends.
    """

    default_module: ClassVar = stores_module
    configuration_key: ClassVar = "eval_report_store"

    @abstractmethod
    async def save_result(
        self,
        run_id: str,
        scenario_run_id: str,
        scenario_name: str,
        result: SimulationResult,
        buffered_chunks: list[ResponseChunk] | None = None,
    ) -> str:
        """Save a simulation result.

        Args:
            run_id: Run identifier for grouping multiple scenarios.
            scenario_run_id: Unique identifier for this scenario run.
            scenario_name: Name of the scenario.
            result: The simulation result to save.
            buffered_chunks: Optional response chunks from the event buffer.

        Returns:
            Result ID for later retrieval.
        """

    @abstractmethod
    async def load_result(self, result_id: str) -> SimulationResult | None:
        """Load a simulation result by ID.

        Args:
            result_id: Result identifier.

        Returns:
            SimulationResult if found, None otherwise.
        """

    @abstractmethod
    async def delete_result(self, result_id: str) -> bool:
        """Delete a simulation result.

        Args:
            result_id: Result identifier.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    async def list_results(self, limit: int = 50, offset: int = 0) -> tuple[list[ResultSummary], int]:
        """List evaluation results with pagination.

        Args:
            limit: Maximum number of results to return.
            offset: Number of results to skip.

        Returns:
            Tuple of (results list, total count).
        """

    @abstractmethod
    async def list_runs(self, limit: int = 50, offset: int = 0) -> tuple[list[SimulationRunSummary], int]:
        """List simulation runs (batch runs grouped by run_id).

        Args:
            limit: Maximum number of runs to return.
            offset: Number of runs to skip.

        Returns:
            Tuple of (runs list, total count).
        """

    @abstractmethod
    async def get_run(self, run_id: str) -> SimulationRunDetail | None:
        """Get full details for a simulation run.

        Args:
            run_id: Run identifier.

        Returns:
            SimulationRunDetail if found, None otherwise.
        """
