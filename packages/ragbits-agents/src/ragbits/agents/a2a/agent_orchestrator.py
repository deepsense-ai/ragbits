import json

import requests

from ragbits.agents import AgentResult, ToolCallResult
from ragbits.agents.a2a.routing_prompt import RoutingPrompt, RoutingPromptInput
from ragbits.agents.a2a.summarize_results_prompt import SummarizeAgentResultsInput, SummarizeAgentResultsPrompt
from ragbits.core.llms import LiteLLM


class AgentOrchestrator:
    """
    Coordinates querying and aggregating responses from multiple remote agents
    using an LLM-driven routing and summarization approach.
    """

    def __init__(self, llm: LiteLLM, timeout: float = 20.0):
        """
        Initializes the orchestrator with the given LLM.

        Args:
            llm: The LLM instance.
            timeout: Timeout in seconds for the HTTP request.
        """
        self._llm = llm
        self._timeout = timeout
        self._remote_agents: dict = {}

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

    async def _create_tasks(self, message: str) -> list[dict]:
        """
        Generates a list of tasks by routing the input message to appropriate remote agents.

        Args:
            message: The user query or request to route.

        Returns:
            A list of task dictionaries specifying agent URLs and parameters,
            parsed from the routing prompt's structured output.
        """
        prompt_input = RoutingPromptInput(message=message, agents=self._list_remote_agents())
        prompt = RoutingPrompt(prompt_input)
        response = await self._llm.generate(prompt)
        return json.loads(response)

    def _run_task(self, agent_url: str, params: dict) -> AgentResult:
        """
        Executes a single task by sending a request to the specified remote agent.

        Args:
            agent_url: The base URL of the remote agent.
            params: Parameters to send to the remote agent.

        Returns:
            The agent's structured response including content,
            metadata, and optional tool call results.
        """
        payload = {"params": params}
        raw_response = requests.post(agent_url, json=payload, timeout=self._timeout)
        raw_response.raise_for_status()

        response = raw_response.json()
        result_data = response["result"]
        content = result_data["content"]
        metadata = result_data.get("metadata", {})
        tool_calls_data = result_data.get("tool_calls", [])

        tool_calls = (
            [
                ToolCallResult(name=call["name"], arguments=call["arguments"], output=call["output"])
                for call in tool_calls_data
            ]
            if tool_calls_data
            else None
        )

        return AgentResult[str](content=content, metadata=metadata, tool_calls=tool_calls)

    def _run_tasks(self, tasks: list[dict]) -> list[AgentResult[str]]:
        """
        Executes multiple tasks sequentially by invoking the corresponding remote agents.

        Args:
            tasks: A list of task dictionaries each containing 'agent_url' and 'parameters'.

        Returns:
            A list of results returned from each invoked agent.
        """
        results = [self._run_task(task["agent_url"], task["parameters"]) for task in tasks]

        return results

    def _list_remote_agents(self) -> list[dict]:
        """
        Lists metadata of all registered remote agents in a format suitable for routing.

        Returns:
            A list of dictionaries describing each remote agent's name, URL,
            description, and skills.
        """
        agent_list = []
        for url, data in self._remote_agents.items():
            agent_info = {
                "name": data.get("name"),
                "agent_url": url,
                "description": data.get("description"),
                "skills": [
                    {"id": skill.get("id"), "name": skill.get("name"), "description": skill.get("description")}
                    for skill in data.get("skills", [])
                ],
            }
            agent_list.append(agent_info)
        return agent_list

    async def run(self, message: str) -> str:
        """
        Runs the full orchestration pipeline for a given message:
        1. Routes the message to relevant agents and generates tasks.
        2. Executes all tasks and collects their results.
        3. Summarizes the aggregated results into a final response using the LLM.

        Args:
            message: The user query or input message.

        Returns:
            The final summarized response generated by the LLM.
        """
        tasks = await self._create_tasks(message=message)
        results = self._run_tasks(tasks)

        input_data = SummarizeAgentResultsInput(message=message, agent_results=results)
        prompt = SummarizeAgentResultsPrompt(input_data=input_data)
        response = await self._llm.generate(prompt)
        return response
