import asyncio
import json
from typing import Any

import typer
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import Input, Static

from ragbits.agents import Agent
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT

agents_app = typer.Typer(no_args_is_help=True)


class ChatMessage(Static):
    """A widget to display a chat message."""

    def __init__(self, content: str, is_user: bool = False, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(content, **kwargs)
        self.is_user = is_user
        if is_user:
            self.add_class("user-message")
        else:
            self.add_class("assistant-message")


class ChatApp(App):
    """A Textual app for agent chat interface."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #messages {
        height: 1fr;
        padding: 1;
        border: solid $primary;
    }

    #input-container {
        height: auto;
        min-height: 3;
        padding: 1;
        background: $surface;
        border: solid $secondary;
        dock: bottom;
    }

    .user-message {
        background: $primary 20%;
        color: $text;
        padding: 1;
        margin: 1 0;
        text-align: right;
        border-left: thick $primary;
    }

    .assistant-message {
        background: $secondary 20%;
        color: $text;
        padding: 1;
        margin: 1 0;
        text-align: left;
        border-left: thick $secondary;
    }

    #message-input {
        width: 1fr;
        background: $surface;
        color: $text;
        border: solid $accent;
    }

    #message-input:focus {
        border: thick $accent;
    }
    """

    def __init__(self, agent: Agent) -> None:
        super().__init__()
        self.agent = agent

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Vertical():
            with ScrollableContainer(id="messages"):
                for message in self.agent.history:
                    if message["role"] in ["assistant", "user"] and message["content"]:
                        yield ChatMessage(message["content"], is_user=message["role"] == "user")
            with Container(id="input-container"):
                yield Input(placeholder="Type your message... (Ctrl+C to exit)", id="message-input")

    def on_mount(self) -> None:
        """Called when app starts."""
        self.query_one("#message-input", Input).focus()

    @on(Input.Submitted, "#message-input")
    async def send_message(self, event: Input.Submitted) -> None:
        """Called when the user submits a message."""
        if not event.value.strip():
            return

        user_message = event.value

        # Add user message to chat
        messages_container = self.query_one("#messages", ScrollableContainer)
        await messages_container.mount(ChatMessage(user_message, is_user=True))

        # Clear input
        event.input.value = ""

        # Check for exit command
        if user_message.lower() == "exit":
            self.exit()
            return

        # Get agent response
        typing_message = None
        try:
            # Show typing indicator
            typing_message = ChatMessage("Assistant is typing...", is_user=False)
            typing_message.add_class("typing")
            await messages_container.mount(typing_message)
            messages_container.scroll_end(animate=False)

            # Get agent response
            result = await self.agent.run(user_message)

            # Remove typing indicator
            typing_message.remove()

            # Add assistant response
            await messages_container.mount(ChatMessage(result.content, is_user=False))

        except Exception as e:
            # Remove typing indicator if it exists
            if typing_message:
                typing_message.remove()
            await messages_container.mount(ChatMessage(f"Error: {str(e)}", is_user=False))

        # Scroll to bottom
        messages_container.scroll_end(animate=False)


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """
    app.add_typer(agents_app, name="agents", help="Commands for managing agents")


def _create_prompt_input(
    prompt: str | type[Prompt[PromptInputT, PromptOutputT]] | Prompt[PromptInputT, PromptOutputT] | None,
    payload: str | None,
) -> str | PromptInputT | None:
    if prompt is None or isinstance(prompt, str):
        return payload
    elif (
        payload
        and (isinstance(prompt, type) and issubclass(prompt, Prompt) or isinstance(prompt, Prompt))
        and prompt.input_type is not None
    ):
        loaded_payload = json.loads(payload) if payload else {}
        return prompt.input_type(**loaded_payload)
    raise ValueError("Invalid combination of prompt and payload")


@agents_app.command(name="exec")
def execute(agent_factory: str, payload: str | None = None) -> None:
    """
    Executes an agent using the specified prompt class and LLM factory.
    """
    if agent_factory is None:
        raise ValueError("`agent_factory` must be provided")
    agent: Agent = Agent.subclass_from_factory(agent_factory)

    agent_output = asyncio.run(agent.run(_create_prompt_input(agent.prompt, payload)))
    print(agent_output)


@agents_app.command()
def run(agent_factory: str, payload: str | None = None) -> None:
    """
    Executes an agent using the specified prompt class and LLM factory and enters interactive mode.
    """
    if agent_factory is None:
        raise ValueError("`agent_factory` must be provided")
    agent: Agent = Agent.subclass_from_factory(agent_factory)
    agent.keep_history = True

    asyncio.run(agent.run(_create_prompt_input(agent.prompt, payload)))
    interactive_agent: Agent = Agent(
        agent.llm,
        prompt=None,
        history=agent.history,
        keep_history=agent.keep_history,
        mcp_servers=agent.mcp_servers,
        default_options=agent.default_options,
    )
    interactive_agent.tools = agent.tools

    # Launch the chat interface
    app = ChatApp(interactive_agent)
    app.run()
