import time
from enum import Enum

from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree

from ragbits.core.audit.traces.base import AttributeFormatter, TraceHandler


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
    PROMPT_COLOR = "bold blue"
    RESPONSE_COLOR = "bold green"


class CLISpan:
    """
    CLI Span represents a single operation within a trace.
    """

    prompt_keyword = "prompt"
    response_keyword = "response"

    def __init__(self, name: str, attributes: dict, parent: "CLISpan | None" = None) -> None:
        """
        Initialize the CLI Span.

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

    def render_special_attribute(
        self, special_attributes: list[str], special_color: str, keyword: str, special_keywords: list[str]
    ) -> Panel:
        """
        Renders the special attributes containing keyword so they will be displayed in one frame in console.
        If special keywords list is defined, the background color is set only for attributes with name
        finishing with special keywords.

        Args:
            special_attributes: The attributes with keyword in the name.
            special_color: The color to print attributes for.
            keyword: The keyword which attributes contain.
            special_keywords: The list of keywords attribute is finished with - for special printing

        Returns:
            The rendered panel.
        """
        key_color = PrintColor.KEY_COLOR.value
        text_color = PrintColor.TEXT_COLOR.value
        rendered_prompt_attributes: list[Panel | Text] = []
        outer_panel_title = self._extract_panel_title(special_attributes[0], keyword)
        for attr_key in special_attributes:
            attr_value = self.attributes[attr_key]
            color = None
            # special attributes related to prompts and response should be in a color frame
            if isinstance(attr_value, str) and (
                AttributeFormatter.is_special_key(curr_key=attr_key, key_list=special_keywords) or not special_keywords
            ):
                color = special_color

            if color:
                syntax = Syntax(attr_value, lexer="markdown", theme="monokai", word_wrap=True)
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

    def render_attributes(self) -> list[Text | Panel]:
        """
        Renders attributes - uses markdown for prompts.

        Returns:
            list: List of formated attribute names and values.

        """
        key_color = PrintColor.KEY_COLOR.value
        text_color = PrintColor.TEXT_COLOR.value
        attrs: list[Text | Panel] = []

        # render prompts
        prompt_attr = [k for k in self.attributes if self.prompt_keyword in k.split(".")]
        if len(prompt_attr) > 0:
            rendered_prompts = self.render_special_attribute(
                prompt_attr, PrintColor.PROMPT_COLOR.value, self.prompt_keyword, AttributeFormatter.prompt_keywords
            )

        # render model response
        response_attr = [k for k in self.attributes if self.response_keyword in k.split(".")]
        if len(response_attr) > 0:
            rendered_response = self.render_special_attribute(
                response_attr, PrintColor.RESPONSE_COLOR.value, self.response_keyword, []
            )

        rendered_prompts_done = False
        rendered_response_done = False
        for k, v in self.attributes.items():
            # add all the attributes related to the prompt
            if k in prompt_attr and not rendered_prompts_done:
                attrs.append(rendered_prompts)
                rendered_prompts_done = True
            # add all the attributes related to the response
            elif k in response_attr and not rendered_response_done:
                attrs.append(rendered_response)
                rendered_response_done = True
            # add other attributes
            elif self.prompt_keyword not in k.split(".") and self.response_keyword not in k.split("."):
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
    CLI trace handler.
    """

    def __init__(self) -> None:
        """
        Initialize the CLITraceHandler instance.
        """
        super().__init__()
        self.live = Live(auto_refresh=False, vertical_overflow="visible")

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
            self.live = Live(auto_refresh=False, vertical_overflow="visible")
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
