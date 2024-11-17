import asyncio
from dataclasses import dataclass, field, replace
from typing import Any

try:
    import gradio as gr

    HAS_GRADIO = True
except ImportError:
    HAS_GRADIO = False

import jinja2
from pydantic import BaseModel
from rich.console import Console

from ragbits.core.config import core_config
from ragbits.core.llms import LLM
from ragbits.core.llms.base import LLMType
from ragbits.core.llms.factory import get_llm_from_factory
from ragbits.core.prompt import Prompt
from ragbits.core.prompt.discovery import PromptDiscovery


@dataclass(frozen=True)
class PromptState:
    """
    Class to store the current state of the application.

    This class holds various data structures used throughout the application's lifecycle.

    Attributes:
        prompts (list): A list containing discovered prompts.
        rendered_prompt (Prompt): The most recently rendered Prompt instance.
        llm (LLM): The LLM instance to be used for generating responses.
    """

    prompts: list = field(default_factory=list)
    rendered_prompt: Prompt | None = None
    llm: LLM | None = None


def render_prompt(index: int, system_prompt: str, user_prompt: str, state: PromptState, *args: Any) -> PromptState:  # noqa: ANN401
    """
    Renders a prompt based on the provided key, system prompt, user prompt, and input variables.

    This function constructs a Prompt object using the prompt constructor and input constructor
    associated with the given key. It then updates the current prompt in the application state.

    Args:
        index (int): The index of the prompt to render in the prompts state.
        system_prompt (str): The system prompt template for the prompt.
        user_prompt (str): The user prompt template for the prompt.
        state (PromptState): The application state object.
        args (tuple): A tuple of input values for the prompt.

    Returns:
        PromptState: The updated application state object.
    """
    prompt_class = state.prompts[index]
    prompt_class.system_prompt_template = jinja2.Template(system_prompt)
    prompt_class.user_prompt_template = jinja2.Template(user_prompt)

    input_type = prompt_class.input_type
    input_fields = get_input_type_fields(input_type)
    variables = {field["field_name"]: value for field, value in zip(input_fields, args, strict=False)}
    input_data = input_type(**variables) if input_type is not None else None
    prompt_object = prompt_class(input_data=input_data)
    state = replace(state, rendered_prompt=prompt_object)

    return state


def list_prompt_choices(state: PromptState) -> list[tuple[str, int]]:
    """
    Returns a list of prompt choices based on the discovered prompts.

    This function generates a list of tuples containing the names of discovered prompts and their
    corresponding indices.

    Args:
        state (PromptState): The application state object.

    Returns:
        list[tuple[str, int]]: A list of tuples containing prompt names and their indices.
    """
    return [(prompt.__name__, idx) for idx, prompt in enumerate(state.prompts)]


def send_prompt_to_llm(state: PromptState) -> str:
    """
    Sends the current prompt to the LLM and returns the response.

    This function creates a LiteLLM client using the LLM model name and API key stored in the
    application state. It then calls the LLM client to generate a response based on the current prompt.

    Args:
        state (PromptState): The application state object.

    Returns:
        str: The response generated by the LLM.

    Raises:
        ValueError: If the LLM model is not configured.
    """
    assert state.rendered_prompt is not None, "Prompt has not been rendered yet."  # noqa: S101

    if state.llm is None:
        raise ValueError("LLM model is not configured.")

    try:
        response = asyncio.run(state.llm.generate_raw(prompt=state.rendered_prompt))
    except Exception as e:  # pylint: disable=broad-except
        response = str(e)

    return response # type: ignore


def get_input_type_fields(obj: BaseModel | None) -> list[dict]:
    """
    Retrieves the field names and default values from the input type of a prompt.

    This function inspects the input type object associated with a prompt and extracts information
    about its fields, including their names and default values.

    Args:
        obj (BaseModel): The input type object of the prompt.

    Returns:
        list[dict]: A list of dictionaries, each containing a field name and its default value.
    """
    if obj is None:
        return []
    return [
        {"field_name": k, "field_default_value": v["schema"].get("default", None)}
        for (k, v) in obj.__pydantic_core_schema__["schema"]["fields"].items()
    ]


def lab_app(  # pylint: disable=missing-param-doc
    file_pattern: str = core_config.prompt_path_pattern,
    llm_factory: str | None = core_config.default_llm_factories[LLMType.TEXT],
) -> None:
    """
    Launches the interactive application for listing, rendering, and testing prompts
    defined within the current project.
    """
    if not HAS_GRADIO:
        Console(stderr=True).print(
            "To use Prompt Lab, you need the Gradio library. Please install it using the following command:\n"
            r"[b]pip install ragbits-core\[lab][/b]"
        )
        return

    prompts = PromptDiscovery(file_pattern=file_pattern).discover()

    if not prompts:
        Console(stderr=True).print(
            f"""No prompts were found for the given file pattern: [b]{file_pattern}[/b].

Please make sure that you are executing the command from the correct directory \
or provide a custom file pattern using the [b]--file-pattern[/b] flag."""
        )
        return

    with gr.Blocks() as gr_app:
        prompts_state = gr.State(
            PromptState(
                prompts=list(prompts),
                llm=get_llm_from_factory(llm_factory) if llm_factory else None,
            )
        )

        prompt_selection_dropdown = gr.Dropdown(
            choices=list_prompt_choices(prompts_state.value),
            value=0,
            label="Select Prompt",
        )

        @gr.render(inputs=[prompt_selection_dropdown, prompts_state])
        def show_split(index: int, state: gr.State) -> None:
            prompt = state.prompts[index]
            list_of_vars = []
            with gr.Row():
                with gr.Column(scale=1), gr.Tab("Inputs"):
                    input_fields: list = get_input_type_fields(prompt.input_type)
                    for entry in input_fields:
                        with gr.Row():
                            var = gr.Textbox(
                                label=entry["field_name"],
                                value=entry["field_default_value"],
                                interactive=True,
                            )
                            list_of_vars.append(var)

                    render_prompt_button = gr.Button(value="Render prompts")

                with gr.Column(scale=4), gr.Tab("Prompt"):
                    with gr.Row():
                        with gr.Column():
                            prompt_details_system_prompt = gr.Textbox(
                                label="System Prompt",
                                value=prompt.system_prompt,
                                interactive=True,
                            )

                        with gr.Column():
                            rendered_system_prompt = (
                                state.rendered_prompt.rendered_system_prompt if state.rendered_prompt else ""
                            )
                            gr.Textbox(
                                label="Rendered System Prompt",
                                value=rendered_system_prompt,
                                interactive=False,
                            )

                    with gr.Row():
                        with gr.Column():
                            prompt_details_user_prompt = gr.Textbox(
                                label="User Prompt",
                                value=prompt.user_prompt,
                                interactive=True,
                            )

                        with gr.Column():
                            rendered_user_prompt = (
                                state.rendered_prompt.rendered_user_prompt if state.rendered_prompt else ""
                            )
                            gr.Textbox(
                                label="Rendered User Prompt",
                                value=rendered_user_prompt,
                                interactive=False,
                            )

            llm_enabled = state.llm is not None
            prompt_ready = state.rendered_prompt is not None
            llm_request_button = gr.Button(
                value="Send to LLM",
                interactive=llm_enabled and prompt_ready,
            )
            gr.Markdown(
                "To enable this button set an LLM factory function in CLI options or your pyproject.toml",
                visible=not llm_enabled,
            )
            gr.Markdown(
                "To enable this button, render a prompt first.",
                visible=llm_enabled and not prompt_ready,
            )
            llm_prompt_response = gr.Textbox(lines=10, label="LLM response")

            render_prompt_button.click(
                render_prompt,
                [
                    prompt_selection_dropdown,
                    prompt_details_system_prompt,
                    prompt_details_user_prompt,
                    prompts_state,
                    *list_of_vars,
                ],
                [prompts_state],
            )
            llm_request_button.click(send_prompt_to_llm, prompts_state, llm_prompt_response)

    gr_app.launch()
