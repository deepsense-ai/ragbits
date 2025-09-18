"""Example demonstrating the new single tool-based todo functionality."""

import asyncio

from ragbits.agents import Agent, AgentOptions, ToolCallResult, get_todo_instruction_tpl, todo_manager
from ragbits.core.llms import LiteLLM, ToolCall


async def main():
    """Demonstrate the new single tool-based todo approach with streaming and logging."""

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
        """ + get_todo_instruction_tpl(task_range=(3, 5), enforce_workflow=True),
        tools=[todo_manager],
        default_options=AgentOptions(max_turns=30)
    )

    print("=== Enhanced Todo Workflow Example ===\n")
    print("🚀 Hiking trip planning with systematic workflow:\n")

    # Simpler query to reduce complexity
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
                    print(f"\n🔧 [TOOL] {action.upper()}", end="", flush=True)

                    if action == "create":
                        tasks = response.arguments.get("tasks", [])
                        tasks_count = len(tasks)
                        print(f" - Creating {tasks_count} tasks", flush=True)
                        for i, task in enumerate(tasks, 1):
                            print(f"   {i}. {task}")

            case ToolCallResult():
                if response.name == "todo_manager":
                    result = response.result
                    action = result.get("action", "unknown")

                    if action == "create":
                        total = result.get('total_count', 0)
                        print(f" ✅ {total} tasks created successfully", flush=True)
                        current_task = result.get("current_task")
                        if current_task:
                            print(f"📋 Next: {current_task['description']}")
                    elif action == "update":
                        task = result.get("task", {})
                        task_desc = task.get("description", "Unknown task")[:50]
                        new_status = task.get("status", "unknown")
                        print(f" ✅ Status changed to '{new_status}'", flush=True)
                        print(f"📋 Task: {task_desc}{'...' if len(task.get('description', '')) > 50 else ''}")
                    elif action == "complete_with_summary":
                        progress = result.get("progress", "unknown")
                        all_done = result.get("all_completed", False)
                        completed_task = result.get("completed_task", {})
                        task_desc = completed_task.get("description", "Unknown task")

                        if all_done:
                            print(f" ✅ FINAL TASK COMPLETED! Progress: {progress}", flush=True)
                            print(f"🎉 All tasks finished! Preparing final summary...")
                        else:
                            print(f" ✅ Task completed. Progress: {progress}", flush=True)
                            next_task = result.get("next_task")
                            if next_task:
                                print(f"📋 Next: {next_task['description']}")
                    elif action == "get_final_summary":
                        total_completed = result.get("total_completed", 0)
                        print(f" ✅ Final summary ready ({total_completed} tasks)", flush=True)
                        print("📄 Complete results below:")
                    elif action == "get_current":
                        current_task = result.get("current_task")
                        all_completed = result.get("all_completed", False)
                        if all_completed:
                            print(f" ✅ All tasks completed!", flush=True)
                        elif current_task:
                            print(f" ✅ Current task identified", flush=True)
                            print(f"📋 Current: {current_task['description']}")
                        else:
                            print(f" ✅ No current task", flush=True)
                    elif action == "get":
                        progress = result.get("progress", "unknown")
                        print(f" ✅ Task overview retrieved (Progress: {progress})", flush=True)
                    else:
                        print(f" ✅ {action} completed", flush=True)

    print("\n\n" + "="*50)
    print("🎉 Systematic hiking trip planning completed!")


if __name__ == "__main__":
    asyncio.run(main())