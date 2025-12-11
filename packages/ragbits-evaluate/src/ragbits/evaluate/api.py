"""EvalAPI - FastAPI server for evaluation UI."""

import asyncio
import importlib
import json
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from ragbits.chat.interface import ChatInterface
from ragbits.evaluate.agent_simulation.models import Scenario
from ragbits.evaluate.agent_simulation.results import SimulationResult, SimulationStatus
from ragbits.evaluate.agent_simulation.scenarios import load_scenarios
from ragbits.evaluate.api_types import (
    EvalConfigResponse,
    ResultsListResponse,
    RunEvaluationRequest,
    RunStartResponse,
    ScenarioDetail,
    ScenarioSummary,
    TaskDetail,
)
from ragbits.evaluate.execution_manager import ExecutionManager, create_progress_callback

logger = logging.getLogger(__name__)


class EvalAPI:
    """FastAPI server for evaluation UI with scenario management and parallel execution."""

    def __init__(
        self,
        chat_factory: Callable[[], ChatInterface] | str,
        scenarios_dir: str = "./scenarios",
        results_dir: str = "./eval_results",
        cors_origins: list[str] | None = None,
        ui_build_dir: str | None = None,
    ) -> None:
        """Initialize the EvalAPI.

        Args:
            chat_factory: Factory function that creates ChatInterface instances,
                         or a string path in format "module:function".
            scenarios_dir: Directory containing scenario JSON files.
            results_dir: Directory for storing evaluation results.
            cors_origins: List of allowed CORS origins.
            ui_build_dir: Path to custom UI build directory.
        """
        self.chat_factory = self._load_chat_factory(chat_factory)
        self.scenarios_dir = Path(scenarios_dir)
        self.results_dir = Path(results_dir)
        self.dist_dir = Path(ui_build_dir) if ui_build_dir else Path(__file__).parent / "ui-build"
        self.cors_origins = cors_origins or []

        # Ensure directories exist
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Initialize execution manager
        self.execution_manager = ExecutionManager(self.results_dir)

        # Cache for loaded scenarios
        self._scenarios_cache: dict[str, Scenario] | None = None

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
            # Load scenarios on startup
            self._load_all_scenarios()
            yield

        self.app = FastAPI(lifespan=lifespan, title="Ragbits Evaluation API")

        self.configure_app()
        self.setup_routes()
        self.setup_exception_handlers()

    def configure_app(self) -> None:
        """Configure middleware, CORS, and static files."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Mount static files if directory exists
        assets_dir = self.dist_dir / "assets"
        if assets_dir.exists():
            self.app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    def setup_exception_handlers(self) -> None:
        """Setup custom exception handlers."""

        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
            logger.error(f"Validation error: {exc}")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": exc.errors(), "body": exc.body},
            )

    def setup_routes(self) -> None:
        """Define API routes."""
        self._setup_config_routes()
        self._setup_scenario_routes()
        self._setup_execution_routes()
        self._setup_results_routes()
        self._setup_ui_routes()

    def _setup_config_routes(self) -> None:
        """Setup configuration endpoints."""

        @self.app.get("/api/eval/config", response_class=JSONResponse)
        async def get_config() -> JSONResponse:
            """Get evaluation configuration with available scenarios."""
            scenarios = self._get_scenarios()
            response = EvalConfigResponse(
                available_scenarios=[
                    ScenarioSummary(name=s.name, num_tasks=len(s.tasks)) for s in scenarios.values()
                ],
                scenarios_dir=str(self.scenarios_dir),
            )
            return JSONResponse(content=response.model_dump())

    def _setup_scenario_routes(self) -> None:
        """Setup scenario management endpoints."""

        @self.app.get("/api/eval/scenarios/{scenario_name}", response_class=JSONResponse)
        async def get_scenario(scenario_name: str) -> JSONResponse:
            """Get full scenario details for viewing/editing."""
            scenarios = self._get_scenarios()
            scenario = scenarios.get(scenario_name)
            if not scenario:
                raise HTTPException(status_code=404, detail=f"Scenario '{scenario_name}' not found")

            detail = ScenarioDetail(
                name=scenario.name,
                tasks=[
                    TaskDetail(
                        task=t.task,
                        expected_result=t.expected_result,
                        expected_tools=t.expected_tools,
                    )
                    for t in scenario.tasks
                ],
            )
            return JSONResponse(content=detail.model_dump())

        @self.app.post("/api/eval/scenarios/reload", response_class=JSONResponse)
        async def reload_scenarios() -> JSONResponse:
            """Reload scenarios from disk."""
            self._scenarios_cache = None
            self._load_all_scenarios()
            scenarios = self._get_scenarios()
            return JSONResponse(
                content={
                    "status": "reloaded",
                    "count": len(scenarios),
                }
            )

    def _setup_execution_routes(self) -> None:
        """Setup evaluation execution endpoints."""

        @self.app.post("/api/eval/run", response_class=JSONResponse)
        async def run_evaluation(request: RunEvaluationRequest) -> JSONResponse:
            """Start an evaluation run with one or more scenarios."""
            scenarios = self._get_scenarios()

            # Validate all requested scenarios exist
            missing = [name for name in request.scenario_names if name not in scenarios]
            if missing:
                raise HTTPException(status_code=404, detail=f"Scenarios not found: {missing}")

            # Generate run ID and create progress queue
            run_id = ExecutionManager.generate_run_id()
            self.execution_manager.create_run(run_id, request.scenario_names)

            # Start execution tasks for each scenario
            for scenario_name in request.scenario_names:
                scenario = scenarios[scenario_name]
                asyncio.create_task(
                    self._run_scenario(run_id, scenario, request.config.model_dump()),
                )

            response = RunStartResponse(run_id=run_id, scenarios=request.scenario_names)
            return JSONResponse(content=response.model_dump())

        @self.app.get("/api/eval/progress/{run_id}")
        async def stream_progress(run_id: str) -> StreamingResponse:
            """Stream progress updates for a running evaluation."""
            if not self.execution_manager.is_run_active(run_id):
                raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found or completed")

            return StreamingResponse(
                self._progress_generator(run_id),
                media_type="text/event-stream",
            )

    def _setup_results_routes(self) -> None:
        """Setup results management endpoints."""

        @self.app.get("/api/eval/results", response_class=JSONResponse)
        async def list_results(limit: int = 50, offset: int = 0) -> JSONResponse:
            """List completed evaluation results."""
            results, total = self.execution_manager.list_results(limit=limit, offset=offset)
            response = ResultsListResponse(results=results, total=total)
            return JSONResponse(content=response.model_dump(mode="json"))

        @self.app.get("/api/eval/results/{result_id}", response_class=JSONResponse)
        async def get_result(result_id: str) -> JSONResponse:
            """Get full evaluation result with conversation details."""
            result = self.execution_manager.load_result(result_id)
            if not result:
                raise HTTPException(status_code=404, detail=f"Result '{result_id}' not found")
            return JSONResponse(content=result.to_dict())

        @self.app.delete("/api/eval/results/{result_id}", response_class=JSONResponse)
        async def delete_result(result_id: str) -> JSONResponse:
            """Delete an evaluation result."""
            if self.execution_manager.delete_result(result_id):
                return JSONResponse(content={"status": "deleted"})
            raise HTTPException(status_code=404, detail=f"Result '{result_id}' not found")

    def _setup_ui_routes(self) -> None:
        """Setup UI serving endpoints."""

        @self.app.get("/{full_path:path}", response_class=HTMLResponse)
        async def serve_ui(full_path: str = "") -> HTMLResponse:
            """Serve the evaluation UI."""
            index_file = self.dist_dir / "eval.html"
            if not index_file.exists():
                # Fall back to index.html if eval.html doesn't exist
                index_file = self.dist_dir / "index.html"
            if not index_file.exists():
                raise HTTPException(status_code=404, detail="UI not built")
            with open(str(index_file)) as file:
                return HTMLResponse(content=file.read())

    async def _progress_generator(self, run_id: str) -> AsyncGenerator[str, None]:
        """Generate SSE events for progress updates."""
        async for update in self.execution_manager.stream_progress(run_id):
            data = json.dumps(update.model_dump(mode="json"))
            yield f"data: {data}\n\n"

    async def _run_scenario(
        self,
        run_id: str,
        scenario: Scenario,
        config: dict[str, Any],
    ) -> None:
        """Run a single scenario and emit progress updates."""
        from ragbits.evaluate.agent_simulation.conversation import run_simulation

        callback = create_progress_callback(run_id, scenario.name, self.execution_manager)

        try:
            # Emit starting status
            await callback(
                "status",
                status=SimulationStatus.RUNNING,
                current_turn=0,
                current_task_index=0,
                current_task=scenario.tasks[0].task if scenario.tasks else None,
            )

            # Create a new ChatInterface instance for this scenario
            chat = self.chat_factory()
            await chat.setup()

            # Run the simulation with progress callback
            result = await run_simulation(
                scenario=scenario,
                chat=chat,
                max_turns_scenario=config.get("max_turns_scenario", 15),
                max_turns_task=config.get("max_turns_task", 4),
                sim_user_model_name=config.get("sim_user_model_name"),
                checker_model_name=config.get("checker_model_name"),
                default_model=config.get("default_model", "gpt-4o-mini"),
                progress_callback=callback,
            )

            # Save result
            result_id = self.execution_manager.save_result(run_id, scenario.name, result)

            # Emit completion
            await callback(
                "complete",
                result_id=result_id,
                status=result.status,
                success_rate=result.metrics.success_rate if result.metrics else 0.0,
                total_turns=result.metrics.total_turns if result.metrics else 0,
                total_tasks=result.metrics.total_tasks if result.metrics else 0,
                tasks_completed=result.metrics.tasks_completed if result.metrics else 0,
            )

        except Exception as e:
            logger.exception(f"Error running scenario {scenario.name}")
            # Save failed result
            failed_result = SimulationResult(
                scenario_name=scenario.name,
                start_time=self.execution_manager._active_runs.get(run_id, {}).get(
                    "start_time", __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                ),
                status=SimulationStatus.FAILED,
                error=str(e),
            )
            result_id = self.execution_manager.save_result(run_id, scenario.name, failed_result)

            await callback("error", error=str(e))

    def _load_all_scenarios(self) -> None:
        """Load all scenarios from the scenarios directory."""
        self._scenarios_cache = {}

        for json_file in self.scenarios_dir.glob("*.json"):
            try:
                scenarios = load_scenarios(str(json_file))
                for scenario in scenarios:
                    self._scenarios_cache[scenario.name] = scenario
                logger.info(f"Loaded {len(scenarios)} scenarios from {json_file}")
            except Exception as e:
                logger.warning(f"Failed to load scenarios from {json_file}: {e}")

        logger.info(f"Total scenarios loaded: {len(self._scenarios_cache)}")

    def _get_scenarios(self) -> dict[str, Scenario]:
        """Get cached scenarios, loading if necessary."""
        if self._scenarios_cache is None:
            self._load_all_scenarios()
        return self._scenarios_cache or {}

    @staticmethod
    def _load_chat_factory(factory: Callable[[], ChatInterface] | str) -> Callable[[], ChatInterface]:
        """Load chat factory from callable or string path.

        Args:
            factory: Factory function or string path in format "module:function".

        Returns:
            Callable that creates ChatInterface instances.
        """
        if isinstance(factory, str):
            module_path, obj_name = factory.split(":")
            logger.info(f"Loading chat factory from {module_path}:{obj_name}")
            module = importlib.import_module(module_path)
            factory_func = getattr(module, obj_name)
            if not callable(factory_func):
                raise TypeError(f"{obj_name} is not callable")
            return factory_func
        return factory

    def run(self, host: str = "127.0.0.1", port: int = 8001) -> None:
        """Start the API server.

        Args:
            host: Host to bind to.
            port: Port to bind to.
        """
        uvicorn.run(self.app, host=host, port=port)
