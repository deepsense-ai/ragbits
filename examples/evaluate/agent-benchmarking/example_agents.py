"""
Agent definitions for benchmarking examples.

Each agent is encapsulated in a class and instances are
declared at the bottom so they can be imported via the CLI helper
`import_agent_from_path` using file path forms, e.g.:

  - file path:    "examples/evaluate/agent-benchmarking/example_agents.py:gaia_agent"

Todo-augmented variants are exported as `<name>_todo_agent` and wrap the base
agent with the `TodoAgent` orchestrator.
"""

from collections.abc import Callable
from typing import Any, cast

from ragbits.agents import Agent, AgentOptions, AgentResult
from ragbits.agents.tool import ToolCallResult
from ragbits.agents.tools.openai import get_web_search_tool
from ragbits.agents.tools.planning import ToDoPlanner, TodoResult
from ragbits.core.llms import LiteLLM
from ragbits.core.llms.base import LLMClientOptionsT, Usage
from ragbits.core.prompt.base import BasePrompt


class TodoAgent(Agent[LLMClientOptionsT, None, str]):
    """
    Agent wrapper that uses TodoOrchestrator to optionally decompose a query
    into tasks and aggregate a final answer, while remaining compatible with
    existing EvaluationPipelines that expect an Agent.
    """

    def __init__(self, agent: Agent[LLMClientOptionsT, None, str], domain_context: str = "") -> None:
        super().__init__(
            llm=agent.llm,
            prompt=agent.prompt,
            history=agent.history,
            keep_history=False,
            mcp_servers=agent.mcp_servers,
            default_options=cast(AgentOptions[LLMClientOptionsT] | None, agent.default_options),
        )
        self._inner_agent = agent
        self._domain_context = domain_context
        self._orchestrator = ToDoPlanner(domain_context=domain_context)

    def __getattr__(self, name: str) -> object:
        """Proxy missing attributes to the wrapped inner agent."""
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return getattr(self._inner_agent, name)

    async def run(
        self,
        input: str | None = None,
        *_: Any,
        **__: Any,
    ) -> AgentResult[str]:
        """Run the orchestrated flow and return a single final answer."""
        query = input or ""

        # Accumulate outputs from the orchestrated workflow
        final_text: str = ""
        tool_calls: list[ToolCallResult] | None = None
        total_usage: Usage = Usage()
        last_prompt: BasePrompt | None = None

        tasks_created = False
        num_tasks = 0
        in_final_summary = False
        final_summary_only: str = ""

        async for item in self._orchestrator.run_todo_workflow_streaming(self._inner_agent, query):
            match item:
                case str():
                    final_text += item
                    if in_final_summary:
                        final_summary_only += item
                case ToolCallResult():
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append(item)
                case Usage():
                    total_usage += item
                case BasePrompt():
                    last_prompt = item
                case TodoResult():
                    if item.type == "final_summary_start":
                        in_final_summary = True
                        final_summary_only = ""
                    elif item.type == "final_summary_end":
                        in_final_summary = False
                case _:
                    # Inspect orchestrator internal state to populate metadata
                    tasks_created = len(self._orchestrator.todo_list.tasks) > 0
                    num_tasks = len(self._orchestrator.todo_list.tasks)

        # Compose metadata with TODO info
        complexity = "COMPLEX" if tasks_created else "SIMPLE"
        todo_meta: dict[str, Any] = {
            "was_decomposed": bool(tasks_created),
            "complexity_classification": complexity,
            "num_tasks": int(num_tasks),
            "domain_context": self._domain_context,
        }

        # Build result compatible with existing pipelines
        history = last_prompt.chat if last_prompt is not None else []

        # If we had tasks and generated a final summary, use that; otherwise use all text
        content_to_return = final_summary_only.strip() if final_summary_only else final_text.strip()
        return AgentResult(
            content=content_to_return,
            metadata={"todo": todo_meta},
            tool_calls=tool_calls,
            history=history,
            usage=total_usage,
        )


class AgentHumanEval:
    """Factory for the HumanEval base agent."""

    @staticmethod
    def build_system_prompt() -> str:
        """Return the system prompt for HumanEval."""
        return "\n".join(
            [
                "You are an expert Python engineer.",
                "Implement exactly one function that solves the problem.",
                "Output ONLY the function as plain Python (no markdown). Include necessary imports.",
                "Do not include explanations or comments.",
            ]
        )

    @classmethod
    def build(cls) -> Agent:
        """Build the HumanEval agent and attach code sanitization callable."""
        agent: Agent = Agent(
            llm=LiteLLM("gpt-4.1-mini"),
            prompt=cls.build_system_prompt(),
            tools=[],
            default_options=AgentOptions(max_turns=30),
        )
        agent.code_sanitize_fn = cls.sanitize_code  # type: ignore[attr-defined]
        return agent

    @staticmethod
    def sanitize_code(text: str) -> str:
        """Remove markdown fences and keep only Python function text returned by the model."""
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if "```" in cleaned:
            start = cleaned.find("```")
            end = cleaned.find("```", start + 3)
            if end != -1:
                inside = cleaned[start + 3 : end].lstrip()
                if "\n" in inside:
                    first, rest = inside.split("\n", 1)
                    cleaned = rest if first.strip().lower().startswith("python") else inside
                else:
                    cleaned = inside
        return cleaned.strip()


class AgentHotpot:
    """Factory for the HotpotQA base agent."""

    @staticmethod
    def build_system_prompt() -> str:
        """Return the system prompt for HotpotQA."""
        return (
            "You are a helpful assistant. Use the provided context to answer.\n"
            "Respond on a single line as: 'Answer: <final answer>'.\n"
            "- If yes/no, respond 'Answer: yes' or 'Answer: no'.\n"
            "- If a name or title is required, provide only that after 'Answer:'.\n"
            "- Do not add any extra text beyond the Answer line.\n"
            "Keep the answer concise."
        )

    @classmethod
    def build(cls) -> Agent:
        """Build the HotpotQA agent and attach parsing helpers."""
        agent: Agent = Agent(
            llm=LiteLLM("gpt-4.1-mini"),
            prompt=cls.build_system_prompt(),
            tools=[],
            default_options=AgentOptions(max_turns=5),
        )
        agent.parse_final_answer = cls.parse_final_answer  # type: ignore[attr-defined]
        agent.question_generation_prompt_fn = cls.build_question_generation_prompt  # type: ignore[attr-defined]
        return agent

    @staticmethod
    def parse_final_answer(text: str) -> str:
        """Extract and normalize the final answer from model text output."""
        marker = "Answer:"
        idx = text.rfind(marker)
        if idx == -1:
            return text.strip()
        candidate = text[idx + len(marker) :].strip()
        if candidate.startswith("<") and candidate.endswith(">"):
            candidate = candidate[1:-1].strip()
        return candidate

    @staticmethod
    def build_question_generation_prompt(original_question: str, accumulated_context: str) -> str:
        """Construct the next-hop question prompt for multi-hop retrieval."""
        return (
            f"Original question: {original_question}\n\n"
            f"Context so far: \n{accumulated_context}\n\n"
            "Write ONE new, specific search question that fills the key missing info.\n"
            "Do not repeat known facts. Return ONLY the question."
        )


class AgentGAIA:
    """Factory for the GAIA base agent with extra tools."""

    @staticmethod
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    @staticmethod
    def subtract(a: int, b: int) -> int:
        """Subtract two integers."""
        return a - b

    @staticmethod
    def multiply(a: int, b: int) -> int:
        """Multiply two integers."""
        return a * b

    @staticmethod
    def divide(a: int, b: int) -> float:
        """Divide two integers as float."""
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b

    @staticmethod
    def modulus(a: int, b: int) -> int:
        """Compute remainder a % b."""
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a % b

    @classmethod
    def get_extra_instruction_tpl(cls) -> str:
        """Return tool usage instruction template."""
        return (
            "Tools (use when needed):\n"
            "- add(a, b), subtract(a, b), multiply(a, b), divide(a, b), modulus(a, b)\n"
            "- web_search -> OpenAI websearch tool\n"
        )

    @classmethod
    def build_system_prompt(cls) -> str:
        """Return the GAIA system prompt with tool instructions."""
        gaia_prompt = (
            "You are a general AI assistant. Provide a concise solution and finish with:\n"
            "FINAL ANSWER: [your final answer].\n"
            "Rules for FINAL ANSWER: use digits for numbers (no units unless requested);\n"
            "prefer few words for strings; for lists, return a comma-separated list."
        )
        return "\n".join([gaia_prompt, cls.get_extra_instruction_tpl()])

    @classmethod
    def build_tools(cls) -> list[Callable[..., Any]]:
        """Return the callable toolset used by the GAIA agent."""
        tools: list[Callable[..., Any]] = [
            cls.add,
            cls.subtract,
            cls.multiply,
            cls.divide,
            cls.modulus,
            cast(Callable[..., Any], get_web_search_tool(model_name="gpt-4.1-mini")),
        ]
        return tools

    @classmethod
    def build(cls) -> Agent:
        """Build the GAIA agent and attach final-answer parser."""
        agent: Agent = Agent(
            llm=LiteLLM("gpt-4.1-mini"),
            prompt=cls.build_system_prompt(),
            tools=cls.build_tools(),
            default_options=AgentOptions(max_turns=30),
        )
        agent.parse_final_answer = cls.parse_final_answer  # type: ignore[attr-defined]
        return agent

    @staticmethod
    def parse_final_answer(text: str) -> str:
        """Extract the FINAL ANSWER segment from model output."""
        marker = "FINAL ANSWER:"
        idx = text.rfind(marker)
        if idx == -1:
            return text.strip()
        candidate = text[idx + len(marker) :].strip()
        if candidate.startswith("[") and candidate.endswith("]"):
            candidate = candidate[1:-1].strip()
        return candidate


# Export agent instances for import
humaneval_agent: Agent = AgentHumanEval.build()
humaneval_todo_agent: Agent = TodoAgent(agent=humaneval_agent, domain_context="python engineer")

hotpot_agent: Agent = AgentHotpot.build()
hotpot_todo_agent: Agent = TodoAgent(agent=hotpot_agent, domain_context="research QA")

gaia_agent: Agent = AgentGAIA.build()
gaia_todo_agent: Agent = TodoAgent(agent=gaia_agent, domain_context="general AI assistant")
