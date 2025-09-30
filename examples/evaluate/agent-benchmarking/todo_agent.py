from __future__ import annotations

from typing import Any, cast

from ragbits.agents import Agent, AgentOptions, AgentResult
from ragbits.agents.tool import ToolCallResult
from ragbits.agents.tools.todo import TodoOrchestrator
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

    async def run(
        self,
        input: str | None = None,
        *_: Any,
        **__: Any,
    ) -> AgentResult[str]:
        """Run the orchestrated flow and return a single final answer."""
        query = input or ""

        orchestrator = TodoOrchestrator(domain_context=self._domain_context)

        # Accumulate outputs from the orchestrated workflow
        final_text: str = ""
        tool_calls: list[ToolCallResult] | None = None
        total_usage: Usage = Usage()
        last_prompt: BasePrompt | None = None

        tasks_created = False
        num_tasks = 0

        async for item in orchestrator.run_todo_workflow_streaming(self._inner_agent, query):
            match item:
                case str():
                    final_text += item
                case ToolCallResult():
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append(item)
                case Usage():
                    total_usage += item
                case BasePrompt():
                    last_prompt = item
                case _:
                    # Inspect orchestrator internal state to populate metadata
                    tasks_created = len(orchestrator.todo_list.tasks) > 0
                    num_tasks = len(orchestrator.todo_list.tasks)

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

        return AgentResult(
            content=final_text.strip(),
            metadata={"todo": todo_meta},
            tool_calls=tool_calls,
            history=history,
            usage=total_usage,
        )
