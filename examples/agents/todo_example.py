#!/usr/bin/env python3
"""Simplified Hiking Trip Planning Agent - Process Under Hood, Stream Final Summary."""

import asyncio
import json
import os

from pydantic import BaseModel

from ragbits.agents.todo_agent import TodoAgent
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt.prompt import Prompt


class HikingPlanInput(BaseModel):
    """Simplified input for hiking trip planning."""

    location: str
    duration_days: int
    group_size: int
    skill_level: str
    season: str
    preferences: str


class PlanningPrompt(Prompt[HikingPlanInput]):
    """Unified prompt for all hiking planning tasks."""

    system_prompt = """
    You are an expert hiking guide with 15+ years of experience. You create comprehensive,
    actionable hiking trip plans by working through planning tasks systematically.

    Always prioritize safety while maximizing the adventure experience.
    Provide specific recommendations with real names, locations, costs, and practical details.
    """

    user_prompt = """
    Plan a {{ duration_days }}-day hiking trip for {{ group_size }} {{ skill_level }} hikers
    in {{ location }} during {{ season }}.

    Preferences: {{ preferences }}

    Complete this specific planning task with detailed, actionable recommendations.
    """

class SummaryInput(BaseModel):
    """Input for summary generation with task results."""

    location: str
    duration_days: int
    group_size: int
    skill_level: str
    season: str
    preferences: str
    task_results: str  # Compiled task results


class TaskGenerationPrompt(Prompt[HikingPlanInput]):
    """Prompt for AI to generate planning tasks."""

    system_prompt = """
    You are an expert hiking trip planner. Create a JSON array of planning tasks.

    IMPORTANT: Return ONLY the JSON array, no other text or explanations.

    Create 3-5 specific planning tasks. Each task should be actionable and focused.

    Example response:
    ["Research trail routes and difficulty levels", "Find accommodation near trailheads",
     "Analyze weather and gear needs"]
    """

    user_prompt = """
    Create planning tasks for:
    - {{ duration_days }}-day hiking trip in {{ location }}
    - {{ group_size }} {{ skill_level }} hikers
    - Season: {{ season }}
    - Preferences: {{ preferences }}

    Return only the JSON array of task descriptions.
    """


class SummaryPrompt(Prompt[SummaryInput]):
    """Prompt for creating final comprehensive summary."""

    system_prompt = """
    You are an expert hiking guide creating a comprehensive trip plan summary.
    Based on your planning analysis, create a complete, actionable hiking trip plan
    that covers all essential aspects of the adventure.

    Structure your response clearly with specific recommendations and practical details.
    """

    user_prompt = """
    Create a comprehensive hiking trip plan based on the completed research:

    TRIP DETAILS:
    - {{ duration_days }}-day trip in {{ location }}
    - {{ group_size }} {{ skill_level }} hikers
    - Season: {{ season }}
    - Preferences: {{ preferences }}

    COMPLETED RESEARCH:
    {{ task_results }}

    Based on this research, provide a complete plan...
    """


def clear_console() -> None:
    """Clear the console screen."""
    os.system("clear" if os.name == "posix" else "cls")  # noqa: S605


def display_task_list(agent: TodoAgent, title: str = "Planning Progress") -> None:
    """Display current task list with visual status indicators."""
    clear_console()
    print("🏔️  AI Hiking Trip Planner")
    print("=" * 50)
    print(f"\n📋 {title}")
    print("─" * 30)

    for task in agent.tasks:
        if task.status.value == "pending":
            status_icon = "⏳"
        elif task.status.value == "in-progress":
            status_icon = "🔄"
        else:  # done
            status_icon = "✅"

        print(f"  {status_icon} {task.description}")

    print(f"\n📊 Progress: {len(agent.done_tasks)}/{len(agent.tasks)} completed")


async def smart_hiking_planner() -> None:
    """Smart hiking planner that processes tasks under the hood and streams final summary."""
    llm = LiteLLM(model_name="gpt-4o-mini")

    clear_console()
    print("🏔️  Smart AI Hiking Trip Planner")
    print("=" * 50)

    # Trip configuration
    trip_input = HikingPlanInput(
        location="Tatra Mountains - Poland",
        duration_days=1,
        group_size=2,
        skill_level="intermediate",
        season="late September/early October",
        preferences="scenic views, no longer than 15km, no crowds, avoid Morskie Oko/Giewont/Kasprowy Wierch",
    )

    print("\n📋 Trip Configuration:")
    print(f"  📍 Location: {trip_input.location}")
    print(f"  📅 Duration: {trip_input.duration_days} day(s)")
    print(f"  👥 Group: {trip_input.group_size} {trip_input.skill_level} hikers")
    print(f"  🌤️  Season: {trip_input.season}")
    print(f"  ⭐ Preferences: {trip_input.preferences}")

    await asyncio.sleep(2)

    # AI creates planning tasks
    print("\n🤖 AI analyzing trip requirements and generating tasks...")

    # Create task generation agent
    task_generator = TodoAgent(llm=llm, prompt=TaskGenerationPrompt)

    # Generate tasks with AI
    task_response = await task_generator.run(trip_input)

    # Parse AI-generated tasks with robust error handling
    try:
        # Extract response content - AgentResult has .content attribute
        if hasattr(task_response, "content"):
            response_content = task_response.content.strip()
        else:
            response_content = str(task_response).strip()

        # Multiple strategies to extract JSON
        import re

        # Strategy 1: Try direct JSON parsing
        try:
            planning_tasks = json.loads(response_content)
        except json.JSONDecodeError:
            # Strategy 2: Extract JSON array from text
            json_patterns = [
                r"\[(?:[^[\]]*(?:\[[^\]]*\])*)*\]",  # Complex nested array pattern
                r"\[.*?\]",  # Simple array pattern
            ]

            planning_tasks = None
            for pattern in json_patterns:
                json_match = re.search(pattern, response_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        planning_tasks = json.loads(json_str)
                        break
                    except json.JSONDecodeError:
                        continue

            if planning_tasks is None:
                raise ValueError("No valid JSON array found in response") from None

        # Validate it's a list of strings
        if not isinstance(planning_tasks, list):
            raise ValueError(f"Expected list, got {type(planning_tasks)}")

        if not all(isinstance(task, str) for task in planning_tasks):
            raise ValueError("All tasks must be strings")

        if len(planning_tasks) == 0:
            raise ValueError("No tasks generated")

    except Exception as e:
        print(f"⚠️  AI task generation failed ({e}), using fallback tasks...")
        planning_tasks = [
            "Research optimal trail routes and scenic viewpoints",
            "Find accommodation close to trailheads",
            "Analyze weather conditions and gear requirements",
            "Plan daily schedule with sunrise/sunset times",
            "Research post-hike activities and relaxation spots",
        ]

    # Create planning agent
    planning_agent = TodoAgent(llm=llm, prompt=PlanningPrompt, keep_history=True)
    planning_agent.create_todo_list(planning_tasks)

    await asyncio.sleep(1)
    display_task_list(planning_agent, "AI-Generated Planning Tasks")
    await asyncio.sleep(2)

    print("\n🚀 Processing tasks under the hood...")
    await asyncio.sleep(1)

    # Process all tasks and capture results
    task_results = []
    for task in planning_agent.tasks:
        # Show current progress
        planning_agent.mark_task(task.id, "in-progress")
        display_task_list(planning_agent, f"Processing: {task.description[:40]}...")

        # Process task with AI and CAPTURE results
        task_result = await planning_agent.run(trip_input)
        task_results.append({
            "task": task.description,
            "result": task_result.content if hasattr(task_result, 'content') else str(task_result)
        })

        # Mark as completed
        planning_agent.mark_task(task.id, "done")
        await asyncio.sleep(1)

    # Show all tasks completed
    display_task_list(planning_agent, "All Planning Tasks Completed!")
    await asyncio.sleep(2)

    # Compile task results
    compiled_results = "\n\n".join([
        f"TASK: {result['task']}\nRESULT: {result['result']}"
        for result in task_results
    ])

    # Create summary input with all task results
    summary_input = SummaryInput(
        location=trip_input.location,
        duration_days=trip_input.duration_days,
        group_size=trip_input.group_size,
        skill_level=trip_input.skill_level,
        season=trip_input.season,
        preferences=trip_input.preferences,
        task_results=compiled_results
    )

    # Generate and stream comprehensive summary
    print("\n🎯 Generating comprehensive trip plan...")
    print("🤖 AI compiling all research into actionable plan...")
    await asyncio.sleep(2)

    # Summary agent now has access to all task research!
    summary_agent = TodoAgent(llm=llm, prompt=SummaryPrompt)

    # Clear screen for final summary
    clear_console()
    print(f"{'='*60}")
    print("🏔️  COMPLETE HIKING TRIP PLAN")
    print(f"{'='*60}")
    print()

    # Stream the comprehensive summary
    streaming_result = summary_agent.run_streaming(summary_input)

    async for chunk in streaming_result:
        if isinstance(chunk, str):
            print(chunk, end="", flush=True)

    print(f"\n\n{'='*60}")
    print("✅ Trip planning completed!")
    print(f"📊 Agent processed {len(planning_agent.tasks)} planning tasks")
    print("🎉 Ready for your adventure!")


async def main() -> None:
    """Run the smart hiking planner."""
    print("🚀 Smart AI Hiking Trip Planner")
    print("AI processes planning tasks under the hood, then streams comprehensive plan")
    print("\nPress Ctrl+C to exit...")
    await asyncio.sleep(3)

    try:
        await smart_hiking_planner()
        print("\n✨ Planning completed successfully!")

    except KeyboardInterrupt:
        print("\n👋 Planning interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure OPENAI_API_KEY is set")


if __name__ == "__main__":
    asyncio.run(main())
