import time
from enum import Enum

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree

from ragbits.core.audit.base import AttributeFormatter, TraceHandler


class SpanStatus(Enum):
    """
    SpanStatus represents the status of the span.
    """

    ERROR = "ERROR"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"


class PrintColor(str, Enum):
    """
    SpanPrintColor represents the color of font for printing the span related information to the console.
    """

    RUNNING_COLOR = "bold blue"
    END_COLOR = "bold green"
    ERROR_COLOR = "bold red"
    TEXT_COLOR = "grey50"
    KEY_COLOR = "plum4"
    SYSTEM_PROMPT_COLOR = "blue3"
    USER_PROMPT_COLOR = "dark_blue"
    RESPONSE_PROMPT_COLOR = "dark_green"


class CLISpan:
    """
    CLI Span represents a single operation within a trace.
    """

    prompt_keyword = "prompt"
    response_keyword = "response"

    def __init__(self, name: str, attributes: dict, parent: "CLISpan | None" = None) -> None:
        """
        Constructs a new CLI Span.

        Args:
            name: The name of the span.
            attributes: The attributes of the span.
            parent: the parent of initiated span.
        """
        self.name = name
        self.parent = parent
        self.attributes = attributes
        self.start_time = time.perf_counter()
        self.end_time: float | None = None
        self.status = SpanStatus.STARTED
        self.tree = Tree("")
        if self.parent is not None:
            self.parent.tree.add(self.tree)

    def update(self) -> None:
        """
        Updates tree label based on span state.
        """
        elapsed = f": {(self.end_time - self.start_time):.3f}s" if self.end_time else " ..."
        color = {
            SpanStatus.ERROR: PrintColor.ERROR_COLOR,
            SpanStatus.STARTED: PrintColor.RUNNING_COLOR,
            SpanStatus.COMPLETED: PrintColor.END_COLOR,
        }[self.status].value

        text_color = PrintColor.TEXT_COLOR.value
        name = f"[{color}]{self.name}[/{color}][{text_color}]{elapsed}[/{text_color}]"

        attrs = self.render_attributes()

        if len(attrs) > 0:
            self.tree.label = Group(name, *attrs)
        else:
            self.tree.label = name

    @staticmethod
    def _extract_panel_title(string: str, keyword: str) -> str:
        parts = string.strip().split(".")
        try:
            index = parts.index(keyword)
        except ValueError:
            return string
        return ".".join(parts[: index + 1])

    def render_prompt(self, prompt_attributes: list[str]) -> Panel:
        """
        Renders the attributes related to prompt so they will be displayed in one frame in console.

        Args:
            prompt_attributes: The attributes with 'prompt' in the name.

        Returns:
            The rendered panel.
        """
        key_color = PrintColor.KEY_COLOR.value
        text_color = PrintColor.TEXT_COLOR.value
        rendered_prompt_attributes: list[Panel | Text] = []
        outer_panel_title = self._extract_panel_title(prompt_attributes[0], self.prompt_keyword)
        for attr_key in prompt_attributes:
            attr_value = self.attributes[attr_key]
            color = None
            if isinstance(attr_value, str):
                if AttributeFormatter.is_special_key(
                    curr_key=attr_key, key_list=AttributeFormatter.system_prompt_keywords
                ):
                    color = PrintColor.SYSTEM_PROMPT_COLOR.value
                elif AttributeFormatter.is_special_key(
                    curr_key=attr_key, key_list=AttributeFormatter.user_prompt_keywords
                ):
                    color = PrintColor.USER_PROMPT_COLOR.value
            if color:
                syntax = Syntax(attr_value, lexer="markdown", theme="monokai", word_wrap=True, background_color=color)
                panel = Panel(
                    syntax, title=f"[{key_color}]{attr_key}[/{key_color}]", title_align="left", border_style=color
                )
                rendered_prompt_attributes.append(panel)
            else:
                rendered_prompt_attributes.append(
                    Text.from_markup(
                        f"[{key_color}]{attr_key}:[/{key_color}] [{text_color}]{str(attr_value)}[/{text_color}]"
                    )
                )
        inner_group = Group(*rendered_prompt_attributes)
        outer_panel = Panel(inner_group, title=f"[{key_color}]{outer_panel_title}[/{key_color}]", title_align="left")
        return outer_panel

    def render_response(self, response_attributes: list[str]) -> Panel:
        """
        Renders the attributes related to response so they will be displayed in one frame in console.

        Args:
            response_attributes: The attributes with 'prompt' in the name.

        Returns:
            The rendered panel.
        """
        key_color = PrintColor.KEY_COLOR.value
        text_color = PrintColor.TEXT_COLOR.value
        rendered_response_attributes: list[Panel | Text] = []
        outer_panel_title = self._extract_panel_title(response_attributes[0], self.response_keyword)
        for attr_key in response_attributes:
            attr_value = self.attributes[attr_key]
            if isinstance(attr_value, str):
                color = PrintColor.RESPONSE_PROMPT_COLOR.value
                syntax = Syntax(attr_value, lexer="markdown", theme="monokai", word_wrap=True, background_color=color)
                panel = Panel(
                    syntax, title=f"[{key_color}]{attr_key}[/{key_color}]", title_align="left", border_style=color
                )
                rendered_response_attributes.append(panel)
            else:
                rendered_response_attributes.append(
                    Text.from_markup(
                        f"[{key_color}]{attr_key}:[/{key_color}] [{text_color}]{str(attr_value)}[/{text_color}]"
                    )
                )

        inner_group = Group(*rendered_response_attributes)
        outer_panel = Panel(inner_group, title=f"[{key_color}]{outer_panel_title}[/{key_color}]", title_align="left")
        return outer_panel

    def render_attributes(self) -> list[Text | Panel]:
        """
        Renders attributes - uses markdown for prompts.

        Returns:
            list: List of formated attribute names and values.

        """
        key_color = PrintColor.KEY_COLOR.value
        text_color = PrintColor.TEXT_COLOR.value
        attrs: list[Text | Panel] = []
        prompt_attr = [k for k in self.attributes if self.prompt_keyword in k.split(".")]
        if len(prompt_attr) > 0:
            new_attr = self.render_prompt(prompt_attr)
            attrs.append(new_attr)
        response_attr = [k for k in self.attributes if self.response_keyword in k.split(".")]
        if len(response_attr) > 0:
            new_attr = self.render_response(response_attr)
            attrs.append(new_attr)
        for k, v in self.attributes.items():
            if self.prompt_keyword not in k.split(".") and self.response_keyword not in k.split("."):
                attrs.append(Text.from_markup(f"[{key_color}]{k}:[/{key_color}] [{text_color}]{str(v)}[/{text_color}]"))
        return attrs

    def end(self) -> None:
        """
        Sets the current time as the span's end time.
        The span's end time is the wall time at which the operation finished.
        Only the first call to `end` should modify the span, further calls are ignored.
        """
        if self.end_time is None:
            self.end_time = time.perf_counter()


class CLITraceHandler(TraceHandler[CLISpan]):
    """
    CLITraceHandler class for all trace handlers.
    """

    def __init__(self) -> None:
        super().__init__()
        self.live = Live(auto_refresh=False)

    def start(self, name: str, inputs: dict, current_span: CLISpan | None = None) -> CLISpan:
        """
        Log input data at the beginning of the trace.

        Args:
            name: The name of the trace.
            inputs: The input data.
            current_span: The current trace span.

        Returns:
            The updated current trace span.
        """
        formatter = AttributeFormatter(data=inputs, prefix="inputs")
        formatter.process_attributes()
        attributes = formatter.flattened

        span = CLISpan(
            name=name,
            attributes=attributes,
            parent=current_span,
        )
        if current_span is None:
            self.live = Live(auto_refresh=False)
            self.live.start()
            self.tree = span.tree

        span.update()
        self.live.update(self.tree, refresh=True)

        return span

    def stop(self, outputs: dict, current_span: CLISpan) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """
        formatter = AttributeFormatter(data=outputs, prefix="outputs")
        formatter.process_attributes()
        attributes = formatter.flattened
        current_span.attributes.update(attributes)
        current_span.status = SpanStatus.COMPLETED
        current_span.end()

        current_span.update()
        self.live.update(self.tree, refresh=True)

        if current_span.parent is None:
            self.live.stop()

    def error(self, error: Exception, current_span: CLISpan) -> None:
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """
        formatter = AttributeFormatter({"message": str(error), **vars(error)}, prefix="error")
        formatter.process_attributes()
        attributes = formatter.flattened
        current_span.attributes.update(attributes)
        current_span.status = SpanStatus.ERROR
        current_span.end()

        current_span.update()
        self.live.update(self.tree, refresh=True)

        if current_span.parent is None:
            self.live.stop()
