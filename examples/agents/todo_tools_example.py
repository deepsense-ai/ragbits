"""Example demonstrating the new instance-based todo functionality."""

import asyncio

from ragbits.agents import Agent, AgentOptions
from ragbits.agents.tools.todo import TodoList, create_todo_manager, get_todo_instruction_tpl
from ragbits.core.llms import LiteLLM, ToolCall


async def main():
    """Demonstrate the new instance-based todo approach with streaming and logging."""

    # Create a dedicated TodoList instance for this agent
    my_todo_list = TodoList()
    my_todo_manager = create_todo_manager(my_todo_list)

    # Create an agent with higher turn limit and todo capabilities
    my_agent = Agent(
        llm=LiteLLM("gpt-4o-mini"),
        prompt="""
        You are an expert hiking guide. You can either answer questions or
        create a comprehensive, detailed hiking trip plan.

        WORKFLOW:
        1. If query is complex you have access to todo_manager tool to create a todo list with specific tasks
        2. If query is simple question, you work without todo_manager tool, just answer the question
        3. If you use todo_manager tool, you must follow the todo workflow below

        For hiking plans include:
        - Specific route names, distances, elevation gain
        - Detailed gear recommendations with quantities
        - Transportation details with times, costs, parking info
        - Weather considerations and backup plans
        - Safety information and emergency contacts
        """ + get_todo_instruction_tpl(task_range=(3, 5)),
        tools=[my_todo_manager],  # Use the instance-specific todo manager
        default_options=AgentOptions(max_turns=30)
    )

    query = "Plan a 1-day hiking trip for 2 people in Tatra Mountains, Poland. Focus on scenic routes under 15km, avoiding crowds."
    # query = "How long is hike to Giewont from Kuźnice?"
    # query = "Is it difficult to finish Orla Perć? Would you recommend me to go there if I've never been in mountains before?"

    stream = my_agent.run_streaming(query)

    async for response in stream:
        match response:
            case str():
                if response.strip():
                    print(response, end="", flush=True)

            case ToolCall():
                if response.name == "todo_manager":
                    action = response.arguments.get("action", "unknown")

                    if action == "create":
                        print("=== Enhanced Todo Workflow Example ===\n")
                        print("🚀 Hiking trip planning with systematic workflow:\n")

                        tasks = response.arguments.get("tasks", [])
                        tasks_count = len(tasks)
                        print(f" - Creating {tasks_count} tasks", flush=True)
                        for i, task in enumerate(tasks, 1):
                            print(f"   {i}. {task}")

    print("\n\n" + "="*50)
    print("🎉 Systematic hiking trip planning completed!")


if __name__ == "__main__":
    asyncio.run(main())