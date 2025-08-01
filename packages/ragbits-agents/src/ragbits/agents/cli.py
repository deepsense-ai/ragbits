import asyncio
import json
from collections.abc import Generator
from typing import Any

import typer
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Input, Label, Static

from ragbits.agents import Agent
from ragbits.core.llms.base import Usage
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


class UsagePanel(Vertical):
    """A widget to display token usage information."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.prompt_tokens = Label("Prompt Tokens: 0")
        self.completion_tokens = Label("Completion Tokens: 0")
        self.total_tokens = Label("Total Tokens: 0")
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._total_tokens = 0

    def compose(self) -> Generator[Label]:
        """Composes Usage Panel"""
        yield Label("Usage", classes="usage-header")
        yield self.prompt_tokens
        yield self.completion_tokens
        yield self.total_tokens

    def update_usage(self, usage: Usage) -> None:
        """Update the displayed usage information."""
        self._prompt_tokens += usage.prompt_tokens
        self._completion_tokens += usage.completion_tokens
        self._total_tokens += usage.total_tokens
        self.prompt_tokens.update(f"Prompt Tokens: {self._prompt_tokens}")
        self.completion_tokens.update(f"Completion Tokens: {self._completion_tokens}")
        self.total_tokens.update(f"Total Tokens: {self._total_tokens}")


class StreamingChatMessage(Static):
    """A widget to display a streaming chat message that can be updated in real-time."""

    def __init__(self, initial_content: str = "", is_user: bool = False, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(initial_content, **kwargs)
        self.is_user = is_user
        self.content_buffer = initial_content
        self.typing_animation_active = False
        self.typing_dots_count = 0
        if is_user:
            self.add_class("user-message")
        else:
            self.add_class("assistant-message")

    def start_typing_animation(self) -> None:
        """Start the typing animation with dots."""
        self.typing_animation_active = True
        self.typing_dots_count = 0
        self._animate_typing()

    def stop_typing_animation(self) -> None:
        """Stop the typing animation."""
        self.typing_animation_active = False

    def _animate_typing(self) -> None:
        """Animate typing dots."""
        if not self.typing_animation_active:
            return

        self.typing_dots_count = (self.typing_dots_count % 3) + 1
        dots = "." * self.typing_dots_count
        self.update(f"{dots}")

        self.set_timer(0.5, self._animate_typing)

    def append_content(self, new_content: str) -> None:
        """Append new content to the message and update the display."""
        if self.typing_animation_active:
            self.stop_typing_animation()
            self.content_buffer = ""

        self.content_buffer += new_content
        self.update(self.content_buffer)

    def set_content(self, content: str) -> None:
        """Set the complete content of the message."""
        if self.typing_animation_active:
            self.stop_typing_animation()

        self.content_buffer = content
        self.update(self.content_buffer)


class ChatApp(App):
    """A Textual app for agent chat interface."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #messages {
        width: 1fr;
        height: 100%;
        padding: 1;
        border: solid $primary;
    }

    #usage-panel {
        width: 40;
        height: 100%;
        padding: 1;
        border: solid $secondary;
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

    .usage-header {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, agent: Agent) -> None:
        super().__init__()
        self.agent = agent
        self.initial_payload = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Vertical():
            with Horizontal(id="main-container"):
                with ScrollableContainer(id="messages"):
                    for message in self.agent.history:
                        if message["role"] in ["assistant", "user"] and message["content"]:
                            yield ChatMessage(message["content"], is_user=message["role"] == "user")
                yield UsagePanel(id="usage-panel")
            with Container(id="input-container"):
                yield Input(placeholder="Type your message... (Ctrl+q to exit)", id="message-input")

    async def on_mount(self) -> None:
        """Called when app starts."""
        self.query_one("#message-input", Input).focus()

        if hasattr(self, "initial_payload") and self.initial_payload is not None:
            self.call_after_refresh(self._schedule_initial_payload)

    def _schedule_initial_payload(self) -> None:
        """Schedule the initial payload processing without blocking the UI."""
        asyncio.create_task(self._process_initial_payload())

    async def _process_initial_payload(self) -> None:
        """Process the initial payload in the background after the UI is loaded."""
        await asyncio.sleep(0.1)

        messages_container = self.query_one("#messages", ScrollableContainer)

        streaming_message = None
        try:
            stream = self.agent.run_streaming(self.initial_payload)
            initial_chat_message = False
            is_first_message = True
            async for chunk in stream:
                if self.initial_payload and not initial_chat_message:
                    initial_user_message = (
                        self.agent.prompt.rendered_user_prompt if self.agent.prompt else self.initial_payload
                    )
                    await messages_container.mount(ChatMessage(initial_user_message, is_user=True))
                    initial_chat_message = True
                if is_first_message:
                    streaming_message = StreamingChatMessage("", is_user=False)
                    await messages_container.mount(streaming_message)
                    messages_container.scroll_end(animate=False)
                    streaming_message.start_typing_animation()
                    is_first_message = False
                if isinstance(chunk, str):
                    streaming_message.append_content(chunk)
                    messages_container.scroll_end(animate=False)

            if stream.usage:
                self.query_one(UsagePanel).update_usage(stream.usage)

        except Exception as e:
            if streaming_message:
                await streaming_message.remove()
            await messages_container.mount(ChatMessage(f"Error: {str(e)}", is_user=False))

        messages_container.scroll_end(animate=False)

    @on(Input.Submitted, "#message-input")
    async def send_message(self, event: Input.Submitted) -> None:
        """Called when the user submits a message."""
        if not event.value.strip():
            return

        user_message = event.value

        messages_container = self.query_one("#messages", ScrollableContainer)
        await messages_container.mount(ChatMessage(user_message, is_user=True))

        event.input.value = ""

        if user_message.lower() == "exit":
            self.exit()
            return

        streaming_message = None
        try:
            streaming_message = StreamingChatMessage("", is_user=False)
            await messages_container.mount(streaming_message)
            messages_container.scroll_end(animate=False)

            stream = self.agent.run_streaming(user_message)
            streaming_message.start_typing_animation()

            async for chunk in stream:
                if isinstance(chunk, str):
                    streaming_message.append_content(chunk)
                    messages_container.scroll_end(animate=False)

            if stream.usage:
                self.query_one(UsagePanel).update_usage(stream.usage)

        except Exception as e:
            if streaming_message:
                await streaming_message.remove()
            await messages_container.mount(ChatMessage(f"Error: {str(e)}", is_user=False))

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

    app = ChatApp(agent)

    if payload is not None:
        app.initial_payload = _create_prompt_input(agent.prompt, payload)

    app.run()
