"""CLI commands for managing and running agents."""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import typer

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents._main import AgentResult
from ragbits.core.llms.base import Reasoning

agents_app = typer.Typer(help="Commands for managing agents")


def import_agent_from_path(agent_path: str) -> Agent:
    """
    Import an agent from a module path.

    Args:
        agent_path: Path in format 'module.path:agent_variable' or 'path/to/file.py:agent_variable'

    Returns:
        The imported agent instance

    Raises:
        ValueError: If the path format is invalid
        ImportError: If the module cannot be imported
        AttributeError: If the agent variable is not found
    """
    if ":" not in agent_path:
        raise ValueError(
            f"Invalid agent path format: {agent_path}. "
            f"Expected 'module.path:agent_variable' or 'path/to/file.py:agent_variable'"
        )

    module_path, agent_name = agent_path.split(":", 1)

    # Check if it's a file path
    if module_path.endswith(".py") and (Path(module_path).exists() or "/" in module_path or "\\" in module_path):
        # Import from file
        file_path = Path(module_path).resolve()
        if not file_path.exists():
            raise ImportError(f"Agent file not found: {file_path}")

        spec = importlib.util.spec_from_file_location("agent_module", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["agent_module"] = module
        spec.loader.exec_module(module)
    else:
        # Import from module name
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Cannot import module {module_path}: {e}") from e

    # Get the agent instance
    try:
        agent = getattr(module, agent_name)
    except AttributeError as e:
        raise AttributeError(f"Agent '{agent_name}' not found in module {module_path}") from e

    if not isinstance(agent, Agent):
        raise TypeError(f"'{agent_name}' is not an Agent instance, got {type(agent)}")

    return agent


def format_agent_metadata(agent: Agent) -> dict[str, Any]:
    """
    Extract and format agent metadata for display.

    Args:
        agent: The agent instance

    Returns:
        Dictionary containing formatted agent metadata
    """
    metadata = {
        "llm": {
            "model": getattr(agent.llm, "model_name", "Unknown"),
            "type": agent.llm.__class__.__name__,
        },
        "prompt": {
            "type": type(agent.prompt).__name__ if agent.prompt else "None",
            "has_system_prompt": hasattr(agent.prompt, "system_prompt") if agent.prompt else False,
        },
        "tools": {
            "count": len(agent.tools),
            "names": [tool.name for tool in agent.tools],
        },
        "mcp_servers": {
            "count": len(agent.mcp_servers),
            "types": [server.__class__.__name__ for server in agent.mcp_servers],
        },
        "history": {
            "enabled": agent.keep_history,
            "length": len(agent.history),
        },
    }

    return metadata


def run_interactive_agent(agent: Agent, agent_path: str) -> None:
    """
    Run the interactive TUI for the given agent.

    Args:
        agent: The agent instance to run interactively
        agent_path: The path used to import the agent (for display)
    """
    try:
        # Import textual components here to avoid dependency issues
        from textual import on
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical, VerticalScroll
        from textual.reactive import reactive
        from textual.widgets import (
            Button,
            Footer,
            Header,
            Input,
            LoadingIndicator,
            Log,
            Static,
            TabbedContent,
            TabPane,
            TextArea,
        )

        class AgentChatApp(App):
            """Interactive TUI application for chatting with ragbits agents."""

            CSS = """
            Screen {
                layout: vertical;
            }

            .chat-container {
                height: 1fr;
                border: solid $primary;
                margin: 1;
            }

            .input-container {
                height: auto;
                margin: 1;
            }

            .metadata-container {
                height: 1fr;
                border: solid $secondary;
                margin: 1;
            }

            .tools-log {
                height: 1fr;
                border: solid $accent;
            }

            .system-prompt {
                height: 1fr;
                border: solid $warning;
            }

            Input {
                margin: 1 0;
            }

            Button {
                margin: 0 1;
            }

            .controls {
                height: auto;
                margin: 1;
            }

            LoadingIndicator {
                height: 1;
                margin: 0 1;
            }
            """

            TITLE = "Ragbits Agent Interactive CLI"

            agent_path: reactive[str] = reactive("")
            current_conversation: reactive[list[dict[str, str]]] = reactive([])

            def __init__(self, agent: Agent, agent_path: str) -> None:
                super().__init__()
                self.agent = agent
                self.agent_path = agent_path
                self.metadata = format_agent_metadata(agent)

            def compose(self) -> ComposeResult:
                """Compose the app UI."""
                yield Header(show_clock=True)

                with TabbedContent(initial="chat"):
                    with TabPane("Chat", id="chat"):
                        yield Vertical(
                            Log(id="chat_log", classes="chat-container"),
                            LoadingIndicator(id="loading_indicator"),
                            Horizontal(
                                Input(placeholder="Type your message...", id="chat_input"),
                                Button("Send", variant="primary", id="send_button"),
                                classes="input-container",
                            ),
                            classes="chat-tab",
                        )

                    with TabPane("Agent Info", id="agent_info"):
                        yield VerticalScroll(
                            Static(self._format_agent_info(), id="agent_metadata"),
                            classes="metadata-container",
                        )

                    with TabPane("Tools Log", id="tools"):
                        yield Log(id="tools_log", classes="tools-log")

                    with TabPane("System Prompt", id="system_prompt"):
                        yield TextArea(
                            text=self._get_system_prompt(),
                            read_only=True,
                            id="system_prompt_area",
                            classes="system-prompt",
                        )

                with Horizontal(classes="controls"):
                    yield Button("Clear Chat", variant="warning", id="clear_button")
                    yield Button("Quit", variant="error", id="quit_button")

                yield Footer()

            def on_mount(self) -> None:
                """Handle app mount event."""
                chat_log = self.query_one("#chat_log", Log)
                chat_log.write_line(f"🤖 Agent loaded: {self.agent_path}")
                chat_log.write_line("💬 Type a message and press Enter or click Send to start chatting!")
                chat_log.write_line("💡 Tip: Type '/exit' to quit the interactive session")

                # Hide loading indicator initially
                loading = self.query_one("#loading_indicator", LoadingIndicator)
                loading.display = False

                # Focus on input
                self.query_one("#chat_input", Input).focus()

            @on(Input.Submitted, "#chat_input")
            @on(Button.Pressed, "#send_button")
            def handle_send_message(self, event: Input.Submitted | Button.Pressed) -> None:
                """Handle sending a message to the agent."""
                import asyncio

                chat_input = self.query_one("#chat_input", Input)
                message = chat_input.value.strip()

                if not message:
                    return

                # Clear input
                chat_input.value = ""

                # Check for /exit command
                if message.lower() == "/exit":
                    chat_log = self.query_one("#chat_log", Log)
                    chat_log.write_line("👋 Goodbye! Exiting...")
                    self.exit()
                    return

                # Add user message to chat
                chat_log = self.query_one("#chat_log", Log)
                chat_log.write_line(f"👤 You: {message}")

                # Run agent asynchronously
                asyncio.create_task(self._run_agent(message))

            @on(Button.Pressed, "#clear_button")
            def handle_clear_chat(self) -> None:
                """Clear the chat history."""
                chat_log = self.query_one("#chat_log", Log)
                chat_log.clear()
                chat_log.write_line("🤖 Chat cleared. Start a new conversation!")

                # Clear agent history if enabled
                if self.agent.keep_history:
                    self.agent.history = []

            @on(Button.Pressed, "#quit_button")
            def handle_quit(self) -> None:
                """Quit the application."""
                self.exit()

            async def _run_agent(self, message: str) -> None:
                """Run the agent with the provided message."""
                chat_log = self.query_one("#chat_log", Log)
                tools_log = self.query_one("#tools_log", Log)
                loading = self.query_one("#loading_indicator", LoadingIndicator)

                try:
                    # Show loading indicator while agent is thinking
                    loading.display = True
                    tools_log.write_line(f"🔧 Tool calls for message '{message[:50]}...':")

                    first_response = True
                    in_reasoning_mode = False
                    agent_results = self.agent.run_streaming(message)

                    async for result in agent_results:
                        match result:
                            case Reasoning():
                                if not in_reasoning_mode:
                                    loading.display = False
                                    chat_log.write(
                                        "\n🧠⚡ Thinking...: " if first_response else "\n\n🧠⚡ Thinking Further...: "
                                    )
                                    in_reasoning_mode = True
                                    first_response = False
                                chat_log.write(str(result))

                            case str():
                                if in_reasoning_mode or first_response:
                                    if in_reasoning_mode:
                                        chat_log.write("\n\n🤖 Agent: ")
                                        in_reasoning_mode = False
                                    else:  # first output (no reasoning before)
                                        loading.display = False
                                        chat_log.write("\n🤖 Agent: ")
                                    first_response = False
                                chat_log.write(result)

                            case ToolCallResult():
                                tools_log.write_line(f"  • {result.name}({result.arguments}) → {result.result}")

                    total_usage = agent_results.usage
                    if first_response:
                        loading.display = False
                        chat_log.write("\n🤖 Agent: (No response)")

                    usage_text = (
                        f"📊 Usage: {total_usage.prompt_tokens}+"
                        f"{total_usage.completion_tokens}={total_usage.total_tokens} tokens"
                    )
                    chat_log.write_line(usage_text)

                except Exception as e:
                    # Always hide loading indicator on error
                    loading.display = False
                    chat_log.write_line(f"❌ Error: {e}")
                    tools_log.write_line(f"❌ Error running agent: {e}")

            def _format_agent_info(self) -> str:
                """Format agent metadata for display."""
                info = f"""🤖 Agent Information

        📍 Agent Path: {self.agent_path}

        🧠 LLM Configuration:
          • Model: {self.metadata['llm']['model']}
          • Type: {self.metadata['llm']['type']}

        📝 Prompt Configuration:
          • Type: {self.metadata['prompt']['type']}
          • Has System Prompt: {self.metadata['prompt']['has_system_prompt']}

        🔧 Tools:
          • Count: {self.metadata['tools']['count']}
          • Names: {', '.join(self.metadata['tools']['names']) if self.metadata['tools']['names'] else 'None'}

        🌐 MCP Servers:
          • Count: {self.metadata['mcp_servers']['count']}
          • Types: {', '.join(self.metadata['mcp_servers']['types'])
                     if self.metadata['mcp_servers']['types'] else 'None'}

        💾 History:
          • Enabled: {self.metadata['history']['enabled']}
          • Current Length: {self.metadata['history']['length']}
        """
                return info

            def _get_system_prompt(self) -> str:
                """Get the system prompt text."""
                if not self.agent.prompt:
                    return "No system prompt configured"

                if isinstance(self.agent.prompt, str):
                    return self.agent.prompt

                if hasattr(self.agent.prompt, "system_prompt"):
                    return self.agent.prompt.system_prompt or "No system prompt found in prompt class"

                return f"Prompt type: {type(self.agent.prompt).__name__} (cannot extract system prompt text)"

        app = AgentChatApp(agent, agent_path)
        app.run()

    except ImportError as e:
        typer.echo(
            "❌ Error: textual is required for interactive mode. Install with 'pip install ragbits-agents[cli]'",
            err=True,
        )
        typer.echo(f"Details: {e}")
        raise typer.Exit(1) from e


@agents_app.command()
def run(
    agent_path: str = typer.Argument(
        help="Path to agent in format 'module.path:agent_variable' (e.g., 'examples.city_explorer:agent')"
    ),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", "-i", help="Run in interactive mode with TUI"
    ),
) -> None:
    """
    Run an agent interactively or in batch mode.

    AGENT_PATH should be in format 'module.path:agent_variable'
    Example: 'examples.city_explorer:city_explorer_agent'
    """
    try:
        agent = import_agent_from_path(agent_path)

        if interactive:
            run_interactive_agent(agent, agent_path)
        else:
            typer.echo(f"Running agent {agent_path} in batch mode (not implemented yet)")

    except Exception as e:
        typer.echo(f"Error running agent: {e}", err=True)
        raise typer.Exit(1) from e


@agents_app.command(name="exec")
def execute_agent(
    agent_path: str = typer.Argument(help="Path to agent in format 'module.path:agent_variable'"),
    input_text: str = typer.Argument(help="Input text to send to the agent"),
) -> None:
    """
    Execute a single input against an agent and return the result.

    This runs the agent once with the provided input and outputs the result.
    """
    import asyncio

    try:
        agent = import_agent_from_path(agent_path)

        typer.echo(f"🤖 Running agent: {agent_path}")
        typer.echo(f"💬 Input: {input_text}")
        typer.echo("⏳ Processing...")

        # Run the agent
        async def run_single() -> AgentResult[Any]:
            agent_result = await agent.run(input_text)
            return agent_result

        result = asyncio.run(run_single())

        typer.echo("\n✅ Response:")
        typer.echo(result.content)

        if result.tool_calls:
            typer.echo(f"\n🔧 Tools used: {len(result.tool_calls)}")
            for tool_call in result.tool_calls:
                typer.echo(f"  • {tool_call.name}: {tool_call.result}")

        if result.usage.total_tokens > 0:
            usage_text = (
                f"\n📊 Token usage: {result.usage.prompt_tokens}+"
                f"{result.usage.completion_tokens}={result.usage.total_tokens}"
            )
            typer.echo(usage_text)

    except Exception as e:
        typer.echo(f"❌ Error executing agent: {e}", err=True)
        raise typer.Exit(1) from e


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the agents package.

    Args:
        app: The Typer object to register the commands with.
    """
    app.add_typer(agents_app, name="agents", help="Commands for managing and running agents")
