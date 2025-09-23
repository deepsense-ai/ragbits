"""Todo list management tool for agents."""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Callable


class TaskStatus(str, Enum):
    """Task status options."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class Task:
    """Simple task representation."""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    order: int = 0
    summary: str | None = None
    full_response: str | None = None


@dataclass
class TodoList:
    """Simple todo list for one agent run."""
    tasks: list[Task] = field(default_factory=list)
    current_index: int = 0

    def get_current_task(self) -> Task | None:
        """Get current task to work on."""
        if self.current_index < len(self.tasks):
            return self.tasks[self.current_index]
        return None

    def advance_to_next(self):
        """Move to next task."""
        self.current_index += 1

    def create_tasks(self, task_descriptions: list[str]) -> dict[str, Any]:
        """Create tasks from descriptions."""
        if not task_descriptions:
            raise ValueError("Tasks required for create action")

        # Clear existing tasks
        self.tasks.clear()
        self.current_index = 0

        for i, desc in enumerate(task_descriptions):
            task = Task(
                id=str(uuid.uuid4()),
                description=desc.strip(),
                order=i
            )
            self.tasks.append(task)

        return {
            "action": "create",
            "tasks": [{"id": t.id, "description": t.description, "order": t.order} for t in self.tasks],
            "total_count": len(self.tasks),
            "message": f"Created {len(task_descriptions)} tasks"
        }

    def get_current(self) -> dict[str, Any]:
        """Get current task information."""
        current = self.get_current_task()
        if not current:
            return {
                "action": "get_current",
                "current_task": None,
                "all_completed": True,
                "message": "All tasks completed!"
            }

        return {
            "action": "get_current",
            "current_task": {"id": current.id, "description": current.description, "status": current.status.value},
            "progress": f"{self.current_index + 1}/{len(self.tasks)}",
            "all_completed": False,
            "message": f"Current task: {current.description}"
        }

    def start_current_task(self) -> dict[str, Any]:
        """Start the current task."""
        current = self.get_current_task()
        if not current:
            raise ValueError("No current task to start")

        current.status = TaskStatus.IN_PROGRESS
        return {
            "action": "start_task",
            "task": {"id": current.id, "description": current.description, "status": current.status.value},
            "message": f"Started task: {current.description}"
        }

    def complete_current_task(self, summary: str) -> dict[str, Any]:
        """Complete the current task with summary."""
        if not summary:
            raise ValueError("Summary required for complete_task")

        current = self.get_current_task()
        if not current:
            raise ValueError("No current task to complete")

        if current.status != TaskStatus.IN_PROGRESS:
            raise ValueError("Task must be started before completing")

        current.status = TaskStatus.COMPLETED
        current.summary = summary.strip()
        self.advance_to_next()

        next_task = self.get_current_task()
        completed_count = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)

        return {
            "action": "complete_task",
            "completed_task": {"id": current.id, "description": current.description, "summary": current.summary},
            "next_task": {"id": next_task.id, "description": next_task.description} if next_task else None,
            "progress": f"{completed_count}/{len(self.tasks)}",
            "all_completed": next_task is None,
            "message": f"Completed: {current.description}"
        }

    def get_completed_context(self) -> str:
        """Get context from all completed tasks."""
        completed_tasks = [t for t in self.tasks if t.status == TaskStatus.COMPLETED]
        if not completed_tasks:
            return "No previous tasks completed yet."

        context_parts = []
        for i, task in enumerate(completed_tasks, 1):
            context_parts.append(f"{i}. {task.description}: {task.summary or 'Completed'}")

        return "Previous completed tasks:\n" + "\n".join(context_parts)


@dataclass
class TodoOrchestrator:
    """High-level orchestrator for managing todo workflow with context passing."""
    todo_list: TodoList = field(default_factory=TodoList)
    domain_context: str = ""

    def __init__(self, domain_context: str = ""):
        """
        Initialize TodoOrchestrator with domain-specific prompts.

        Args:
            domain_context: Additional context about the domain (e.g., "hiking guide", "software architect", etc.)
        """
        self.todo_list = TodoList()
        self.domain_context = domain_context

    async def run_todo_workflow_streaming(self, agent, initial_query: str):
        """
        Run complete todo workflow with streaming responses.

        Yields:
            Various response types: str, ToolCall, ToolResult, dict (status updates)
        """
        yield {"type": "status", "message": "🚀 Starting todo workflow..."}

        # Step 1: Analyze complexity and create tasks if needed
        yield {"type": "status", "message": "🔍 Analyzing query complexity..."}

        tasks = await self._create_tasks_simple(agent, initial_query)

        if not tasks:
            # Query is simple - answer directly without task breakdown
            yield {"type": "status", "message": "💡 Simple query detected - providing direct answer..."}

            # Create a focused prompt for direct answering
            direct_prompt = f"""
            Answer this query directly and comprehensively:

            "{initial_query}"

            {f"Context: You are working as a {self.domain_context}." if self.domain_context else ""}

            Provide a clear, complete answer without unnecessary complexity.
            """

            # Stream the direct answer
            async for response in agent.run_streaming(direct_prompt):
                if isinstance(response, str):
                    yield response
                else:
                    yield response  # Pass through tool calls, etc.

            yield {"type": "status", "message": "\n🎯 Direct answer completed!"}
            return

        # Complex query - proceed with task breakdown
        yield {"type": "status", "message": f"📋 Complex query - created {len(tasks)} tasks:"}
        for i, task in enumerate(tasks, 1):
            yield {"type": "task_list", "task_number": i, "task_description": task}

        # Step 2: Execute each task with context from previous tasks
        task_summaries = []

        while True:
            current_task_info = self.todo_list.get_current()
            if current_task_info["all_completed"]:
                break

            current_task = current_task_info["current_task"]
            yield {"type": "task_summary_start", "message": f"\n🔧 Task {current_task_info['progress']}: {current_task['description']}\n"}

            # Get context from previous completed tasks
            context = self.todo_list.get_completed_context()

            # Execute single task with focused context and stream summary
            async for response in self._execute_single_task_focused(agent, current_task, context, initial_query):
                yield response

            # Get the completed task summary
            completed_tasks = [t for t in self.todo_list.tasks if t.status == TaskStatus.COMPLETED]
            if completed_tasks:
                latest_summary = completed_tasks[-1].summary
                task_summaries.append(latest_summary)
                yield {"type": "task_completed", "message": "\n✅ Task completed\n"}

        # Step 3: Generate comprehensive final summary with streaming
        yield {"type": "status", "message": "📝 Generating comprehensive final summary..."}
        yield {"type": "final_summary_start", "message": f"\n📊 COMPREHENSIVE {self.domain_context.upper()} SUMMARY:\n" + "=" * 60 + "\n"}

        async for response in self._generate_comprehensive_summary_streaming(agent, initial_query, task_summaries):
            yield response

        yield {"type": "final_summary_end", "message": "\n" + "=" * 60}
        yield {"type": "status", "message": "🎉 All tasks completed!"}


    async def _analyze_query_complexity(self, agent, query: str) -> bool:
        """
        Analyze if the query requires task breakdown or can be answered directly.
        Returns True if complex (needs tasks), False if simple (direct answer).
        """
        complexity_prompt = f"""
        Analyze this query and determine if it requires a multi-step breakdown or can be answered directly.

        Query: "{query}"

        Consider these factors:
        - Simple factual questions (What is...? Who is...? When did...?) = SIMPLE
        - Yes/No questions = SIMPLE
        - Single concept explanations = SIMPLE
        - Questions requiring research, planning, or multiple steps = COMPLEX
        - Questions asking for comprehensive analysis, comparisons, or detailed guides = COMPLEX
        - Questions with multiple parts or requiring extensive information = COMPLEX

        Respond with ONLY one word: "SIMPLE" or "COMPLEX"
        """

        agent_result = await agent.run(complexity_prompt)
        response = agent_result.content.strip().upper()

        # Default to COMPLEX if we can't determine (safer approach)
        return response != "SIMPLE"

    async def _create_tasks_simple(self, agent, initial_query: str) -> list[str]:
        """Create tasks based on initial query - simple, non-streaming."""

        # First, analyze if the query actually needs task breakdown
        is_complex = await self._analyze_query_complexity(agent, initial_query)

        if not is_complex:
            # Query is simple enough to answer directly - return empty task list
            return []

        task_creation_prompt = f"""
        Based on this query: "{initial_query}"

        Create 3-5 specific, actionable tasks that will comprehensively address this query.
        Each task should be clear and focused on one specific aspect.

        {f"Context: You are working as a {self.domain_context}." if self.domain_context else ""}

        CRITICAL: Respond with ONLY a Python list of task descriptions, nothing else:
        ["Task 1: Specific description", "Task 2: Specific description", "Task 3: Specific description"]
        """

        agent_result = await agent.run(task_creation_prompt)
        response = agent_result.content

        # Parse tasks from the response
        tasks = self._parse_tasks_from_response(response)
        if tasks:
            self.todo_list.create_tasks(tasks)
            return tasks

        return []

    async def _execute_single_task_focused(self, agent, current_task: dict, context: str, original_query: str):
        """Execute a single task with focused context - stream only essential info."""

        task_prompt = f"""
        You are working on ONE SPECIFIC TASK as part of a larger workflow.

        ORIGINAL QUERY: {original_query}

        YOUR CURRENT TASK: {current_task['description']}

        CONTEXT FROM PREVIOUS TASKS:
        {context}

        CRITICAL INSTRUCTIONS:
        1. Focus EXCLUSIVELY on your current task - do not overlap with other tasks
        2. Use previous context to avoid repetition but DO NOT duplicate their work
        3. Be comprehensive but stay within your task scope
        4. End with: TASK SUMMARY: [2-3 sentence summary]

        Complete ONLY your assigned task now.
        """

        # Mark task as started
        self.todo_list.start_current_task()

        full_response = ""
        last_summary_length = 0

        # Stream the task execution but only show summary parts
        async for response in agent.run_streaming(task_prompt):
            if isinstance(response, str):
                full_response += response
                # Only stream text that comes after "TASK SUMMARY:" marker
                if "TASK SUMMARY:" in full_response:
                    summary_start = full_response.find("TASK SUMMARY:") + len("TASK SUMMARY:")
                    summary_text = full_response[summary_start:].strip()
                    if summary_text and len(summary_text) > last_summary_length:
                        # Stream only new characters
                        new_chars = summary_text[last_summary_length:]
                        if new_chars:
                            yield new_chars
                            last_summary_length = len(summary_text)
            else:
                yield response  # Pass through tool calls, etc.

        # Extract final summary and complete task
        summary = self._extract_summary_from_response(full_response)

        # Store the full response for final summary generation
        current_task_obj = self.todo_list.get_current_task()
        if current_task_obj:
            current_task_obj.full_response = full_response

        self.todo_list.complete_current_task(summary)

    async def _generate_comprehensive_summary_streaming(self, agent, original_query: str, task_summaries: list[str]):
        """Generate a comprehensive final summary with streaming."""

        # Get full responses from completed tasks
        full_responses = []
        for task in self.todo_list.tasks:
            if task.status == TaskStatus.COMPLETED and hasattr(task, 'full_response'):
                full_responses.append(f"**{task.description}**:\n{task.full_response}")

        # Create domain-specific summary instructions
        domain_instructions = ""
        if self.domain_context:
            domain_instructions = f"Format as a comprehensive {self.domain_context} response that someone could use to address their needs."
        else:
            domain_instructions = "Format as a comprehensive, well-structured response."

        summary_prompt = f"""
        You need to create a comprehensive final summary for this query: "{original_query}"

        Here are the detailed results from all completed tasks:

        {chr(10).join(full_responses)}

        Create a comprehensive, well-structured final summary that:
        1. Directly answers the original query
        2. Combines all the detailed information from the tasks
        3. Organizes information logically and coherently
        4. Provides actionable recommendations
        5. Is complete and self-contained

        {domain_instructions}
        """

        # Stream the comprehensive summary generation
        async for response in agent.run_streaming(summary_prompt):
            if isinstance(response, str):
                yield response  # Stream each character as it comes
            else:
                yield response  # Pass through tool calls, etc.

    def _parse_tasks_from_response(self, response: str) -> list[str]:
        """Parse task list from agent response."""
        try:
            import ast

            # The prompt asks for ONLY a Python list, so try direct parsing first
            response = response.strip()

            # Try to parse the entire response as a Python literal
            try:
                tasks = ast.literal_eval(response)
                if isinstance(tasks, list) and all(isinstance(t, str) for t in tasks):
                    return tasks
            except (ValueError, SyntaxError):
                pass

            # Fallback: Look for the first list in the response
            import re
            list_pattern = r'\[.*?\]'
            match = re.search(list_pattern, response, re.DOTALL)
            if match:
                try:
                    tasks = ast.literal_eval(match.group())
                    if isinstance(tasks, list) and all(isinstance(t, str) for t in tasks):
                        return tasks
                except (ValueError, SyntaxError):
                    pass

            print(f"Could not parse tasks from response: {response[:200]}...")

        except Exception as e:
            print(f"Failed to parse tasks: {e}")

        return []

    def _extract_summary_from_response(self, response: str) -> str:
        """Extract task summary from agent response."""
        summary_marker = "TASK SUMMARY:"
        if summary_marker in response:
            parts = response.split(summary_marker)
            summary = parts[-1].strip()
            # Clean up the summary (remove extra formatting)
            summary = summary.replace('\n', ' ').strip()
            return summary
        else:
            # Fallback: use last paragraph as summary
            paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
            if paragraphs:
                summary = paragraphs[-1]
                # Limit length and clean up
                if len(summary) > 300:
                    summary = summary[:300] + "..."
                return summary
            return "Task completed"