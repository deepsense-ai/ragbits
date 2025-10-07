## TodoOrchestrator — !!!mock-up tutorial!!!

Short and pragmatic guide to orchestrating task execution with a Todo-oriented agent.

---

### Why TodoOrchestrator?

- **Motivation**: make complex, multi-step tasks explicit, auditable, and re-runnable.
- **What it is**: a lightweight orchestration layer over your agent tools for planning and progress tracking.
- **Benefits**: clarity of intent, measurable progress, easier debugging, better eval scores via structured decomposition.

#### Workflow overview

<graph of TodoOrchestrator workflow goes here>

- **Input**: user goal -> agent -> TodoOrchestrator
- **Plan**: generate todos -> order/prioritize -> attach tools
- **Execute**: dispatch steps -> record artifacts -> update status
- **Review**: summarize -> retry failed steps -> export audit

---

### Prerequisites

- Python env managed by `uv`.
- LLM provider configured (e.g., environment variables) and network access where needed.
- `huggingface_cli` account login with access to relevant datasets (i.e. GAIA)
- Example files referenced in this tutorial:
  - `packages/ragbits-agents/src/ragbits/agents/tools/todo.py`
  - `examples/agents/todo_tools_example.py`
  - Evaluations: `examples/evaluate/agent-benchmarking/run_gaia.py`, `run_hotpot.py`, `run_humaneval.py`

---

### 1) Set up an agent (baseline)

Minimal agent wiring using TodoOrchestrator as a tool provider.

```python
# mock-up code (baseline agent)
from ragbits.agents import Agent
from ragbits.agents.tools.todo import TodoOrchestrator

agent = Agent(
    llm="gpt-xyz",
    tools=[tool_1, tool_2],
)

result = agent.run("Execute Task XYZ.")
```

Notes:
- Will keep this as a baseline: no todo manager yet, minimal defaults, some tools.

---

### 2) Baseline evaluation setup (measure accuracy)

We’ll run three complementary benchmarks to measure multi-step reasoning and tooling:

- **GAIA**: generalist agent tasks with tool-use and basic reasoning.
- **HotpotQA**: multi-hop question answering assessing and complex reasoning and information retrieval.
- **HumanEval**: code generation with function-level correctness (pass@k).

Run baseline (mock commands):

```bash
uv run python examples/evaluate/agent-benchmarking/run_gaia.py --agent baseline # or sth like this
uv run python examples/evaluate/agent-benchmarking/run_hotpot.py --agent baseline # might be full code snippets
uv run python examples/evaluate/agent-benchmarking/run_humaneval.py --agent baseline
```

Mock results snapshot (baseline):

<table of baseline metrics (accuracy, F1, pass@1) goes here>

---

### 3) Apply TodoOrchestrator

Plug in a concrete todo manager for persistence, progress tracking, and retries.

```python
# mock-up code!!!
from ragbits.agents.tools.todo import TodoOrchestrator

todo_orchestrator = TodoOrchestrator(domain_context="<some context here>")


# Similar flow as before
```

UI/Console mock-up:

    <screenshot of todo list goes here>

---

### 4) Re-run evaluation (expected improvement)

Re-run the same suites with orchestration.

```bash
uv run python examples/evaluate/agent-benchmarking/run_gaia.py --agent todo_orchestrated # or sth like this
uv run python examples/evaluate/agent-benchmarking/run_hotpot.py --agent todo_orchestrated # might be full code snippets
uv run python examples/evaluate/agent-benchmarking/run_humaneval.py --agent todo_orchestrated
```

Mock results snapshot (after orchestration):

<table comparing baseline vs orchestrated metrics goes here>

<bar chart of gains in GAIA/HotpotQA/HumanEval goes here>

Key expected gains (mock):
- **GAIA**: +XXX% task success via [argument here].
- **HotpotQA**: +XXX% F1 through [argument here].
- **HumanEval**: +XXX% pass@1K with [some argument here].

---

### 5) MOCK-UP Operational tips

- **Auditability**: export run logs and todo timelines for regression analysis.
- **Backoff**: configure retries for unreliable tools.
- **Safety**: restrict tool scopes and validate step outputs.

---

### 6) References & examples

- Tooling: `packages/ragbits-agents/src/ragbits/agents/tools/todo.py`
- Complete example: `examples/agents/todo_tools_example.py`
- Evaluations:
  - GAIA: `examples/evaluate/agent-benchmarking/run_gaia.py`
  - HotpotQA: `examples/evaluate/agent-benchmarking/run_hotpot.py`
  - HumanEval: `examples/evaluate/agent-benchmarking/run_humaneval.py`

Related tutorials:
- Agents tutorial: `https://ragbits.deepsense.ai/stable/tutorials/agents/`
- RAG tutorial: `https://ragbits.deepsense.ai/stable/tutorials/rag/`
- Chat tutorial: `https://ragbits.deepsense.ai/stable/tutorials/chat/`

---

### Appendix (copy-paste mocks)

```bash

# run the agent example (mock)
uv run python examples/agents/todo_tools_example.py
```

<sequence diagram of planning -> execution -> audit export or sth goes here>
