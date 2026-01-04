import json
from typing import TypeVar

import requests
from pydantic import BaseModel

from ragbits.agents import Agent, AgentOptions, AgentResult, ToolCallResult
from ragbits.core.llms import LiteLLM
from ragbits.core.options import Options
from ragbits.core.prompt import ChatFormat, Prompt

OptionsT = TypeVar("OptionsT", bound=Options)


class RoutingPromptInput(BaseModel):
    """Represents a routing prompt input."""

    message: str
    agents: list


class ResultsSumarizationPromptInput(BaseModel):
    """Represents a results summarization prompt input."""

    message: str
    agent_results: list


class RemoteAgentTask(BaseModel):
    """Model representing a task for a remote agent"""

    agent_url: str
    parameters: dict


class AgentOrchestrator(Agent):
    """
    Coordinates querying and aggregating responses from multiple remote agents
    using tools for routing and task execution.
    """

    def __init__(
        self,
        llm: LiteLLM,
        routing_prompt: type[Prompt[RoutingPromptInput, list[dict]]],
        results_summarization_prompt: type[Prompt[ResultsSumarizationPromptInput, list]],
        timeout: float = 20.0,
        *,
        history: ChatFormat | None = None,
        keep_history: bool = False,
        default_options: AgentOptions[OptionsT] | None = None,
    ):
        """
        Initialize the orchestrator with tools for agent coordination.

        Args:
            llm: The LLM to run the agent.
            routing_prompt: Prompt template for routing messages to agents.
            results_summarization_prompt: Prompt template for summarizing agent results.
            timeout: Timeout in seconds for the HTTP request.
            history: The history of the agent.
            keep_history: Whether to keep the history of the agent.
            default_options: The default options for the agent run.

        """
        super().__init__(
            llm=llm,
            prompt=None,
            history=history,
            keep_history=keep_history,
            tools=[self.create_agent_tasks, self.execute_agent_task, self.summarize_agent_results],
            default_options=default_options,
        )

        self._timeout = timeout

        self._routing_prompt = routing_prompt
        self._results_summarization_prompt = results_summarization_prompt

        self._remote_agents: dict[str, dict] = {}

        self._current_tasks: list[RemoteAgentTask] = []
        self._current_results: list[AgentResult] = []

    def add_remote_agent(self, host: str, port: int, protocol: str = "http") -> None:
        """
        Discovers and registers a remote agent by fetching its agent card metadata.

        Args:
            host: The hostname or IP address of the remote agent.
            port: The port on which the remote agent server is running.
            protocol: The communication protocol (http or https). Defaults to "http".
        """
        url = f"{protocol}://{host}:{port}"
        if url not in self._remote_agents:
            agent_card = requests.get(f"{url}/.well-known/agent.json", timeout=self._timeout)
            self._remote_agents[url] = agent_card.json()

    async def create_agent_tasks(self, message: str) -> str:
        """
        Creates tasks for remote agents based on the input message.

        Args:
            message: The user query to route to agents

        Returns:
            JSON string of created tasks
        """
        prompt_input = RoutingPromptInput(message=message, agents=self._list_remote_agents())
        prompt = self._routing_prompt(prompt_input)
        response = await self.llm.generate(prompt)

        tasks = json.loads(response)
        self._current_tasks = [RemoteAgentTask(**task) for task in tasks]

        return json.dumps({
            "status": "success",
            "task_count": len(self._current_tasks),
            "tasks": [task.dict() for task in self._current_tasks],
        })

    async def execute_agent_task(self, task_index: int) -> str:
        """
        Executes a specific task from the current task list.

        Args:
            task_index: Index of the task to execute

        Returns:
            JSON string of the execution result
        """
        if not self._current_tasks or task_index >= len(self._current_tasks):
            return json.dumps({"status": "error", "message": "Invalid task index"})

        task = self._current_tasks[task_index]
        result = self._execute_single_task(task.agent_url, task.parameters)
        self._current_results.append(result)

        tool_calls = None
        if result.tool_calls:
            tool_calls = [{"name": tc.name, "arguments": tc.arguments, "output": tc.result} for tc in result.tool_calls]

        return json.dumps({
            "status": "success",
            "agent_url": task.agent_url,
            "result": {"content": result.content, "metadata": result.metadata, "tool_calls": tool_calls},
        })

    async def summarize_agent_results(self, message: str) -> str:
        """
        Summarizes all collected agent results.

        Args:
            message: The original user message

        Returns:
            The summarized response
        """
        if not self._current_results:
            return "No results to summarize"

        input_data = ResultsSumarizationPromptInput(message=message, agent_results=self._current_results)
        prompt = self._results_summarization_prompt(input_data=input_data)
        return await self.llm.generate(prompt)

    def _execute_single_task(self, agent_url: str, params: dict) -> AgentResult:
        payload = {"params": params}
        raw_response = requests.post(agent_url, json=payload, timeout=self._timeout)
        raw_response.raise_for_status()

        response = raw_response.json()
        result_data = response["result"]

        return AgentResult(
            content=result_data["content"],
            metadata=result_data.get("metadata", {}),
            history=result_data["history"],
            tool_calls=[ToolCallResult(**call) for call in result_data.get("tool_calls", [])] or None,
        )

    def _list_remote_agents(self) -> list[dict]:
        """
        Lists metadata of all registered remote agents in a format suitable for routing.

        Returns:
            A list of dictionaries describing each remote agent's name, URL,
            description, and skills.
        """
        return [
            {
                "name": data.get("name"),
                "agent_url": url,
                "description": data.get("description"),
            }
            for url, data in self._remote_agents.items()
        ]
