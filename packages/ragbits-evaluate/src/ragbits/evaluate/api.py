"""EvalAPI - FastAPI server for evaluation UI."""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from ragbits.chat.interface import ChatInterface
from ragbits.evaluate.agent_simulation.models import Personality, Scenario, SimulationConfig
from ragbits.evaluate.agent_simulation.results import SimulationResult, SimulationStatus
from ragbits.evaluate.agent_simulation.scenarios import ScenarioFile, load_personalities, load_scenario_file
from ragbits.evaluate.api_types import (
    EvalConfigResponse,
    PersonasListResponse,
    PersonaSummary,
    ResultsListResponse,
    RunEvaluationRequest,
    RunStartResponse,
    ScenarioDetail,
    ScenarioFileSummary,
    ScenarioSummary,
    SimulationRunsListResponse,
    TaskDetail,
)
from ragbits.evaluate.execution_manager import ExecutionManager, create_progress_callback

if TYPE_CHECKING:
    from ragbits.evaluate.stores.base import EvalReportStore

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
        response_adapters: list = None,
        simulation_config: SimulationConfig | None = None,
        store: EvalReportStore | None = None,
    ) -> None:
        """Initialize the EvalAPI.

        Args:
            chat_factory: Factory function that creates ChatInterface instances,
                         or a string path in format "module:function".
            scenarios_dir: Directory containing scenario JSON files.
            results_dir: Directory for storing evaluation results (used if store is not provided).
            cors_origins: List of allowed CORS origins.
            ui_build_dir: Path to custom UI build directory.
            response_adapters: List of response adapters for processing chat responses.
            simulation_config: Default SimulationConfig for running evaluations.
                Can be overridden per-run via API request.
            store: Storage backend for evaluation results. If not provided,
                uses FileEvalReportStore with results_dir.
        """
        self.chat_factory = self._load_chat_factory(chat_factory)
        self.scenarios_dir = Path(scenarios_dir)
        self.results_dir = Path(results_dir)
        self.dist_dir = self._resolve_ui_build_dir(ui_build_dir)
        self.cors_origins = cors_origins or []
        self.response_adapters = response_adapters
        self.simulation_config = simulation_config or SimulationConfig()

        # Ensure directories exist
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)

        # Initialize execution manager with store or default to file-based
        if store is not None:
            self.execution_manager = ExecutionManager(store=store)
        else:
            self.results_dir.mkdir(parents=True, exist_ok=True)
            self.execution_manager = ExecutionManager(store=self.results_dir)

        # Cache for loaded scenarios and scenario files
        self._scenarios_cache: dict[str, Scenario] | None = None
        self._scenario_files_cache: list[ScenarioFile] | None = None
        # Cache for loaded personas
        self._personas_cache: dict[str, Personality] | None = None

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
            # Load scenarios and personas on startup
            self._load_all_scenarios()
            self._load_all_personas()
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
        self._setup_health_routes()
        self._setup_config_routes()
        self._setup_scenario_routes()
        self._setup_execution_routes()
        self._setup_persona_routes()
        self._setup_results_routes()
        self._setup_ui_routes()

    def _setup_health_routes(self) -> None:
        """Setup health check endpoints."""

        @self.app.get("/api/health", response_class=JSONResponse)
        async def health() -> JSONResponse:
            """Basic liveness check - returns OK if the server is running."""
            return JSONResponse(content={"status": "ok"})

        @self.app.get("/api/ready", response_class=JSONResponse)
        async def ready() -> JSONResponse:
            """Readiness check - verifies the API is ready to handle requests."""
            checks = {
                "scenarios_loaded": self._scenarios_cache is not None,
                "personas_loaded": self._personas_cache is not None,
                "scenarios_dir_exists": self.scenarios_dir.exists(),
                "results_dir_exists": self.results_dir.exists(),
            }
            all_ready = all(checks.values())
            return JSONResponse(
                content={
                    "status": "ready" if all_ready else "not_ready",
                    "checks": checks,
                },
                status_code=status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    def _setup_config_routes(self) -> None:
        """Setup configuration endpoints."""

        @self.app.get("/api/eval/config", response_class=JSONResponse)
        async def get_config() -> JSONResponse:
            """Get evaluation configuration with available scenarios."""
            scenarios = self._get_scenarios()
            scenario_files = self._get_scenario_files()
            response = EvalConfigResponse(
                available_scenarios=[
                    ScenarioSummary(name=s.name, num_tasks=len(s.tasks), group=s.group) for s in scenarios.values()
                ],
                scenario_files=[
                    ScenarioFileSummary(
                        filename=sf.filename,
                        group=sf.group,
                        scenarios=[
                            ScenarioSummary(name=s.name, num_tasks=len(s.tasks), group=s.group)
                            for s in sf.scenarios
                        ],
                    )
                    for sf in scenario_files
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
                        checkers=t.checkers,
                        checker_mode=t.checker_mode,
                    )
                    for t in scenario.tasks
                ],
                group=scenario.group,
            )
            return JSONResponse(content=detail.model_dump())

        @self.app.post("/api/eval/scenarios/reload", response_class=JSONResponse)
        async def reload_scenarios() -> JSONResponse:
            """Reload scenarios from disk."""
            self._scenarios_cache = None
            self._scenario_files_cache = None
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
            """Start an evaluation run with one or more scenarios.

            If personas are provided, creates a matrix run: each scenario × each persona.
            """
            scenarios = self._get_scenarios()

            # Validate all requested scenarios exist
            missing = [name for name in request.scenario_names if name not in scenarios]
            if missing:
                raise HTTPException(status_code=404, detail=f"Scenarios not found: {missing}")

            # Validate personas exist if provided
            if request.personas:
                missing_personas = [p for p in request.personas if p not in scenarios]
                if missing_personas:
                    raise HTTPException(status_code=404, detail=f"Personas not found: {missing_personas}")

            # Generate run ID and create progress queue
            run_id = ExecutionManager.generate_run_id()

            # Determine personas to use (None means single run without persona)
            personas_to_run: list[str | None] = request.personas if request.personas else [None]

            # Build list of scenario runs (scenarios × personas matrix)
            scenario_run_names = []
            for scenario_name in request.scenario_names:
                for persona in personas_to_run:
                    # Create unique name for tracking
                    run_name = f"{scenario_name}:{persona}" if persona else scenario_name
                    scenario_run_names.append(run_name)

            self.execution_manager.create_run(run_id, scenario_run_names)

            # Start execution tasks for each scenario × persona combination
            base_config = request.config.model_dump()
            for scenario_name in request.scenario_names:
                scenario = scenarios[scenario_name]
                for persona in personas_to_run:
                    config_with_persona = {**base_config, "persona": persona}
                    asyncio.create_task(
                        self._run_scenario(run_id, scenario, config_with_persona, persona),
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

        @self.app.get("/api/eval/progress/{run_id}/buffer/{scenario_run_id}", response_class=JSONResponse)
        async def get_scenario_buffer(run_id: str, scenario_run_id: str) -> JSONResponse:
            """Get buffered events for a scenario run.

            This allows fetching all events that occurred before subscribing to SSE,
            enabling late subscribers to catch up on scenario history.
            """
            if not self.execution_manager.is_run_active(run_id):
                raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found or completed")

            events = self.execution_manager.get_scenario_run_buffer(run_id, scenario_run_id)
            return JSONResponse(content={"events": [e.model_dump(mode="json") for e in events]})

    def _setup_persona_routes(self) -> None:
        """Setup persona management and testing endpoints."""

        @self.app.get("/api/eval/personas", response_class=JSONResponse)
        async def list_personas() -> JSONResponse:
            """List all available personas."""
            personas = self._get_personas()
            response = PersonasListResponse(
                personas=[
                    PersonaSummary(name=p.name, description=p.description)
                    for p in personas.values()
                ],
                total=len(personas),
            )
            return JSONResponse(content=response.model_dump())

        @self.app.get("/api/eval/personas/{persona_name}", response_class=JSONResponse)
        async def get_persona(persona_name: str) -> JSONResponse:
            """Get full persona details."""
            persona = self._get_persona(persona_name)
            if not persona:
                raise HTTPException(status_code=404, detail=f"Persona '{persona_name}' not found")
            return JSONResponse(
                content=PersonaSummary(name=persona.name, description=persona.description).model_dump()
            )

        @self.app.post("/api/eval/personas/reload", response_class=JSONResponse)
        async def reload_personas() -> JSONResponse:
            """Reload personas from disk."""
            self._personas_cache = None
            self._load_all_personas()
            personas = self._get_personas()
            return JSONResponse(
                content={
                    "status": "reloaded",
                    "count": len(personas),
                }
            )

    def _setup_results_routes(self) -> None:
        """Setup results management endpoints."""

        @self.app.get("/api/eval/runs", response_class=JSONResponse)
        async def list_runs(limit: int = 50, offset: int = 0) -> JSONResponse:
            """List simulation runs (batch runs grouped by run_id)."""
            runs, total = await self.execution_manager.list_runs(limit=limit, offset=offset)
            response = SimulationRunsListResponse(runs=runs, total=total)
            return JSONResponse(content=response.model_dump(mode="json"))

        @self.app.get("/api/eval/runs/{run_id}", response_class=JSONResponse)
        async def get_run(run_id: str) -> JSONResponse:
            """Get full details for a simulation run."""
            run = await self.execution_manager.get_run(run_id)
            if not run:
                raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
            return JSONResponse(content=run.model_dump(mode="json"))

        @self.app.get("/api/eval/results", response_class=JSONResponse)
        async def list_results(limit: int = 50, offset: int = 0) -> JSONResponse:
            """List completed evaluation results."""
            results, total = await self.execution_manager.list_results(limit=limit, offset=offset)
            response = ResultsListResponse(results=results, total=total)
            return JSONResponse(content=response.model_dump(mode="json"))

        @self.app.get("/api/eval/results/{result_id}", response_class=JSONResponse)
        async def get_result(result_id: str) -> JSONResponse:
            """Get full evaluation result with conversation details."""
            result = await self.execution_manager.load_result(result_id)
            if not result:
                raise HTTPException(status_code=404, detail=f"Result '{result_id}' not found")
            return JSONResponse(content=result.to_dict())

        @self.app.delete("/api/eval/results/{result_id}", response_class=JSONResponse)
        async def delete_result(result_id: str) -> JSONResponse:
            """Delete an evaluation result."""
            if await self.execution_manager.delete_result(result_id):
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
        request_config: dict[str, Any],
        persona: str | None = None,
    ) -> None:
        """Run a single scenario and emit progress updates."""
        from ragbits.evaluate.agent_simulation.conversation import run_simulation

        # Create unique run name for scenario+persona combination
        run_name = f"{scenario.name}:{persona}" if persona else scenario.name

        # Register the scenario run to get a unique ID and enable event buffering
        scenario_run_id = self.execution_manager.register_scenario_run(run_id, run_name)
        callback = create_progress_callback(
            run_id, scenario_run_id, scenario.name, self.execution_manager, persona=persona
        )

        # Get personality from cache if persona is specified
        personality: Personality | None = self._get_persona(persona) if persona else None

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

            # Merge request config with default simulation config
            # Request values override defaults (excluding 'persona' which is handled separately)
            config = self.simulation_config.model_copy(
                update={k: v for k, v in request_config.items() if v is not None and k != "persona"}
            )

            # Run the simulation with progress callback and personality
            result = await run_simulation(
                scenario=scenario,
                chat=chat,
                config=config,
                personality=personality,
                progress_callback=callback,
            )

            # Save result
            result_id = await self.execution_manager.save_result(run_id, scenario_run_id, scenario.name, result)

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
            await self.execution_manager.save_result(run_id, scenario_run_id, scenario.name, failed_result)

            await callback("error", error=str(e))

    def _load_all_scenarios(self) -> None:
        """Load all scenarios from the scenarios directory."""
        self._scenarios_cache = {}
        self._scenario_files_cache = []

        for json_file in self.scenarios_dir.glob("*.json"):
            try:
                scenario_file = load_scenario_file(str(json_file))
                self._scenario_files_cache.append(scenario_file)
                for scenario in scenario_file.scenarios:
                    self._scenarios_cache[scenario.name] = scenario
                logger.info(f"Loaded {len(scenario_file.scenarios)} scenarios from {json_file}")
            except Exception as e:
                logger.warning(f"Failed to load scenarios from {json_file}: {e}")

        logger.info(f"Total scenarios loaded: {len(self._scenarios_cache)}")

    def _get_scenarios(self) -> dict[str, Scenario]:
        """Get cached scenarios, loading if necessary."""
        if self._scenarios_cache is None:
            self._load_all_scenarios()
        return self._scenarios_cache or {}

    def _get_scenario_files(self) -> list[ScenarioFile]:
        """Get cached scenario files, loading if necessary."""
        if self._scenario_files_cache is None:
            self._load_all_scenarios()
        return self._scenario_files_cache or []

    def _load_all_personas(self) -> None:
        """Load all personas from the scenarios directory."""
        self._personas_cache = {}

        # Try to find personas file (with fallback to old name)
        personas_file = self.scenarios_dir / "personas.json"
        if not personas_file.exists():
            personas_file = self.scenarios_dir / "personalities.json"

        if personas_file.exists():
            try:
                personas = load_personalities(str(personas_file))
                for persona in personas:
                    self._personas_cache[persona.name] = persona
                logger.info(f"Loaded {len(personas)} personas from {personas_file}")
            except Exception as e:
                logger.warning(f"Failed to load personas from {personas_file}: {e}")
        else:
            logger.info("No personas file found")

    def _get_personas(self) -> dict[str, Personality]:
        """Get cached personas, loading if necessary."""
        if self._personas_cache is None:
            self._load_all_personas()
        return self._personas_cache or {}

    def _get_persona(self, name: str) -> Personality | None:
        """Get a specific persona by name."""
        return self._get_personas().get(name)

    @staticmethod
    def _resolve_ui_build_dir(ui_build_dir: str | None) -> Path:
        """Resolve the UI build directory path.

        Priority:
        1. Custom path if provided
        2. Eval-specific ui-build directory if exists
        3. Fallback to ragbits-chat ui-build directory

        Args:
            ui_build_dir: Optional custom UI build directory path.

        Returns:
            Path to the UI build directory.
        """
        if ui_build_dir:
            return Path(ui_build_dir)

        # Try eval-specific ui-build first
        eval_ui_dir = Path(__file__).parent / "ui-build"
        if eval_ui_dir.exists():
            return eval_ui_dir

        # Fallback to ragbits-chat ui-build
        import ragbits.chat.api as chat_api

        return Path(chat_api.__file__).parent / "ui-build"

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
