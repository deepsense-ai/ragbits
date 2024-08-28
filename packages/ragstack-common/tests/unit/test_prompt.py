import pydantic
import pytest

from ragstack_common.prompt import Prompt


class _PromptInput(pydantic.BaseModel):
    """
    Input format for the TestPrompt.
    """

    theme: str
    name: str
    age: int


class _PromptOutput(pydantic.BaseModel):
    """
    Output format for the TestPrompt.
    """

    song_title: str
    song_lyrics: str


def test_raises_when_no_user_message():
    """Test that a ValueError is raised when no user message is provided."""
    with pytest.raises(ValueError):

        class TestPrompt(Prompt):  # pylint: disable=unused-variable
            """A test prompt"""


def test_raises_when_user_variable_with_no_input():
    """Test that a ValueError is raised when a user template variable is provided but no input model."""
    with pytest.raises(ValueError):

        class TestPromptUser(Prompt):  # pylint: disable=unused-variable
            """A test prompt"""

            user_prompt = "Hello, {{ name }}"


def test_raises_when_system_variable_with_no_input():
    """Test that a ValueError is raised when a system template variable is provided but no input model."""
    with pytest.raises(ValueError):

        class TestPromptSystem(Prompt):  # pylint: disable=unused-variable
            """A test prompt"""

            user_prompt = "Hello"
            system_prompt = "Hello, {{ name }}"


def test_raises_when_unknow_user_template_variable():
    """Test that a ValueError is raised when an unknown template variable is provided."""
    with pytest.raises(ValueError):

        class TestPromptUser(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
            """A test prompt"""

            user_prompt = "Hello, {{ foo }}"


def test_raises_when_unknow_system_template_variable():
    """Test that a ValueError is raised when an unknown template variable is provided."""
    with pytest.raises(ValueError):

        class TestPromptSystem(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
            """A test prompt"""

            user_prompt = "Hello"
            system_prompt = "Hello, {{ foo }}"


def test_raises_when_unknown_template_variable_in_condition():
    """Test that a ValueError is raised when an unknown template variable is used in a condition."""
    with pytest.raises(ValueError):

        class TestPromptSystem(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
            """A test prompt"""

            user_prompt = "Hello"
            system_prompt = "{% if foo %}Hello{% endif %}"


def test_raises_when_no_input_data():
    """Test that a ValueError is raised when input type is specified but no input data is provided."""

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    with pytest.raises(ValueError):
        TestPrompt()


def test_prompt_with_no_input_type():
    """Test that a prompt can be created with no input type."""

    class TestPrompt(Prompt):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt()
    assert prompt.user_message == "Hello"
    assert prompt.chat == [{"role": "user", "content": "Hello"}]


def test_prompt_with_input_type():
    """Test that a prompt can be created with an input type."""

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."

    prompt = TestPrompt(_PromptInput(name="Alice", age=30, theme="rock"))
    assert prompt.system_message == "You are a song generator for a adult named Alice."
    assert prompt.user_message == "Theme for the song is rock."
    assert prompt.chat == [
        {"role": "system", "content": "You are a song generator for a adult named Alice."},
        {"role": "user", "content": "Theme for the song is rock."},
    ]


def test_input_type_must_be_pydantic_model():
    """Test that an error is raised when the input type is not a Pydantic model."""
    with pytest.raises(AssertionError):

        class TestPrompt(Prompt[str, str]):  # type: ignore # pylint: disable=unused-variable
            """A test prompt"""

            user_prompt = "Hello"


def test_adding_messages():
    """Test that messages can be added to the conversation."""

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."

    prompt = TestPrompt(_PromptInput(name="John", age=15, theme="pop"))
    prompt.add_assistant_message("It's a really catchy tune.").add_user_message("I like it.")

    assert prompt.chat == [
        {"role": "system", "content": "You are a song generator for a child named John."},
        {"role": "user", "content": "Theme for the song is pop."},
        {"role": "assistant", "content": "It's a really catchy tune."},
        {"role": "user", "content": "I like it."},
    ]


def test_prompt_with_new_lines():
    """Test that prompts with new lines are rendered correctly."""

    class TestPrompt(Prompt):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = """
        Hello
        World
        """

    prompt = TestPrompt()
    assert prompt.user_message == "Hello\nWorld"


def test_output_format():
    """Test that the output format is correctly returned."""

    class TestPrompt(Prompt[_PromptInput, _PromptOutput]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt(_PromptInput(name="John", age=15, theme="pop"))
    assert prompt.output_schema() == {
        "title": "_PromptOutput",
        "description": "Output format for the TestPrompt.",
        "type": "object",
        "properties": {
            "song_title": {"title": "Song Title", "type": "string"},
            "song_lyrics": {"title": "Song Lyrics", "type": "string"},
        },
        "required": ["song_title", "song_lyrics"],
    }
