"""Terminal conversation between the ragbits hotel booking agent and a simulated user."""

from __future__ import annotations

import argparse
import asyncio
import signal
import subprocess
import time
from itertools import zip_longest
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from config import config
from fixtures.hotel.hotel_chat import HotelChat

from ragbits.evaluate.agent_simulation import load_personalities, load_scenarios, run_duet

HOTEL_API_DIR = Path(__file__).resolve().parent / "fixtures" / "hotel-api"
SERVER_HEALTHCHECK_URL = "http://localhost:8000/openapi.json"
SERVER_START_TIMEOUT = 30.0
SERVER_POLL_INTERVAL = 0.5


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Two-agent terminal chat (ragbits hotel agent + simulated user)")
    parser.add_argument(
        "--scenario-ids",
        type=int,
        nargs="+",
        required=True,
        help="Scenario IDs (1-based indices). Pass one or more values separated by space.",
    )
    parser.add_argument("--scenarios-file", type=str, default="scenarios.json", help="Path to scenarios file")
    parser.add_argument(
        "--personality-ids",
        type=int,
        nargs="*",
        help=(
            "Personality IDs (1-based indices, optional). Provide zero or more values. "
            "If fewer IDs are provided than scenarios, missing entries will be treated as None."
        ),
    )
    parser.add_argument(
        "--personalities-file", type=str, default="personalities.json", help="Path to personalities file"
    )
    parser.add_argument(
        "--max-turns-scenario", type=int, default=15, help="Max number of conversation turns for the entire scenario"
    )
    parser.add_argument("--max-turns-task", type=int, default=4, help="Max number of conversation turns per task")
    parser.add_argument("--log-file", type=str, default="duet_conversations.log", help="Path to log file")
    parser.add_argument("--agent-model-name", type=str, help="Override agent LLM model name")
    parser.add_argument("--sim-user-model-name", type=str, help="Override simulated user LLM model name")
    parser.add_argument("--checker-model-name", type=str, help="Override goal checker LLM model name")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
        help="Number of run_coroutines to run concurrently (batch size for async execution).",
    )
    return parser.parse_args()


def _populate_database(process_ids: list[int]) -> None:
    cmd = [
        "uv",
        "run",
        "python",
        "populate_db.py",
        "--ids",
        *map(str, process_ids),
    ]
    subprocess.run(cmd, cwd=HOTEL_API_DIR, check=True)  # noqa: S603


def _start_uvicorn() -> subprocess.Popen[bytes]:
    cmd = ["uv", "run", "uvicorn", "app:app", "--reload", "--port", "8000"]
    return subprocess.Popen(cmd, cwd=HOTEL_API_DIR)  # noqa: S603


def _wait_for_server(timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(SERVER_HEALTHCHECK_URL, timeout=2):  # noqa: S310
                return
        except URLError:
            time.sleep(SERVER_POLL_INTERVAL)
    raise RuntimeError(f"Timed out waiting for hotel API at {SERVER_HEALTHCHECK_URL}")


def _stop_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _clear_database() -> None:
    cmd = [
        "uv",
        "run",
        "python",
        "clear_db.py",
    ]
    subprocess.run(cmd, cwd=HOTEL_API_DIR, check=True, text=True, input="yes\n")  # noqa: S603


def main() -> None:
    """Main entry point for the duet CLI application."""
    args = parse_args()

    # Load scenarios list and validate requested IDs
    scenarios = load_scenarios(args.scenarios_file)
    if any(sid < 1 or sid > len(scenarios) for sid in args.scenario_ids):
        raise ValueError(f"One or more scenario IDs out of range. Available: 1-{len(scenarios)}")

    # Load personalities if any were provided at all (we'll pick per-pair below)
    personalities = None
    if args.personality_ids:
        personalities = load_personalities(args.personalities_file)
        if any(pid < 1 or pid > len(personalities) for pid in args.personality_ids):
            raise ValueError(f"One or more personality IDs out of range. Available: 1-{len(personalities)}")

    # Hotel-specific message prefix
    message_prefix = (
        "[STYLE]\nAnswer helpfully and clearly. "
        "Provide specific details when available (hotel names, room types, prices, dates). "
        "If information is unavailable, explain why briefly.\n\n"
    )
    # Prepare list of (scenario, personality_id) pairs, filling missing personality ids with None
    # Create pairing between the selected scenario ids and provided personality ids
    pairs = list(zip_longest(args.scenario_ids, args.personality_ids or [], fillvalue=None))

    async def _run_pair(process_id: int, scenario_id: int, personality_id: int | None) -> None:
        # Resolve scenario
        scenario = scenarios[scenario_id - 1]

        # Resolve personality for this pair if an id was supplied; otherwise leave None
        personality = None
        if personality_id is not None and personalities is not None:
            personality = personalities[personality_id - 1]

        # Create HotelChat for this process id
        hotel_chat = HotelChat(args.agent_model_name or config.llm_model, config.openai_api_key, process_id)

        # Use a per-process log file suffix to avoid conflicts when running concurrently
        log_file = f"{args.log_file}.pid{process_id}_s{scenario_id}_p{personality_id}" if args.log_file else None

        await run_duet(
            scenario=scenario,
            chat=hotel_chat,
            max_turns_scenario=args.max_turns_scenario,
            max_turns_task=args.max_turns_task,
            log_file=log_file,
            agent_model_name=args.agent_model_name,
            sim_user_model_name=args.sim_user_model_name,
            checker_model_name=args.checker_model_name,
            default_model=config.llm_model,
            api_key=config.openai_api_key,
            user_message_prefix=message_prefix,
            personality=personality,
        )

    async def _run_all(batches: list[tuple[int, int | None]], batch_size: int) -> None:
        # Semaphore to limit concurrency
        sem = asyncio.Semaphore(batch_size)

        async def _bounded_run(process_id: int, scenario_id: int, personality_id: int | None) -> None:
            async with sem:
                await _run_pair(process_id, scenario_id, personality_id)

        # Spawn tasks and wait for them
        tasks = [
            asyncio.create_task(_bounded_run(idx, s_id, p_id)) for idx, (s_id, p_id) in enumerate(batches, start=1)
        ]
        await asyncio.gather(*tasks)

    process_ids = list(range(1, len(pairs) + 1))
    if not process_ids:
        raise ValueError("At least one scenario id must be provided.")

    _populate_database(process_ids)

    server_process: subprocess.Popen[bytes] | None = None
    try:
        server_process = _start_uvicorn()
        _wait_for_server(SERVER_START_TIMEOUT)

        # Run all selected pairs with the requested concurrency
        asyncio.run(_run_all(pairs, args.batch_size))
    finally:
        if server_process is not None:
            _stop_process(server_process)
        _clear_database()


if __name__ == "__main__":
    main()
