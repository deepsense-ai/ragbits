"""
Agent definitions for benchmarking examples.

Each agent is encapsulated in a class and instances are
declared at the bottom so they can be imported via the CLI helper
`import_agent_from_path` using file path forms, e.g.:

  - file path:    "examples/evaluate/agent-benchmarking/example_agents.py:gaia_agent"

Planning-augmented variants are exported as `<name>_planning_agent` and include
planning tools that allow the agent to break down complex tasks.
"""

from collections.abc import Callable
from typing import Any, cast

from ragbits.agents import Agent, AgentOptions
from ragbits.agents.tools.openai import get_web_search_tool
from ragbits.agents.tools.planning import PlanningState, create_planning_tools
from ragbits.core.llms import LiteLLM


def build_planning_agent(
    base_prompt: str,
    tools: list[Callable[..., Any]] | None = None,
    max_turns: int = 50,
) -> Agent:
    """
    Build an agent with planning capabilities.

    Args:
        base_prompt: The base system prompt for the agent.
        tools: Additional tools to provide to the agent.
        max_turns: Maximum number of turns for the agent.

    Returns:
        Agent with planning tools included.
    """
    planning_prompt = f"""{base_prompt}

For complex requests, use your planning tools:
1. Use create_plan to break down the task into subtasks
2. Use get_current_task to see what to work on
3. Complete each task, then use complete_task with a summary
4. Continue until all tasks are done

For simple questions, answer directly."""

    planning_state = PlanningState()
    all_tools: list[Callable[..., Any]] = list(tools or [])
    all_tools.extend(create_planning_tools(planning_state))

    return Agent(
        llm=LiteLLM("gpt-4.1-mini"),
        prompt=planning_prompt,
        tools=all_tools,
        default_options=AgentOptions(max_turns=max_turns),
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
humaneval_planning_agent: Agent = build_planning_agent(
    base_prompt=AgentHumanEval.build_system_prompt(),
    max_turns=30,
)

hotpot_agent: Agent = AgentHotpot.build()
hotpot_planning_agent: Agent = build_planning_agent(
    base_prompt=AgentHotpot.build_system_prompt(),
    max_turns=30,
)

gaia_agent: Agent = AgentGAIA.build()
gaia_planning_agent: Agent = build_planning_agent(
    base_prompt=AgentGAIA.build_system_prompt(),
    tools=AgentGAIA.build_tools(),
    max_turns=50,
)
