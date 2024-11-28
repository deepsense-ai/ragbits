from pathlib import Path

import pydantic
import pytest

from ragbits.core.prompt import Prompt


class _PromptInput(pydantic.BaseModel):
    """
    Input format for the TestPrompt.
    """

    theme: str
    name: str
    age: int


class _ImagePromptInput(pydantic.BaseModel):
    """
    Input format for the TestImagePrompt.
    """

    image: bytes | str | None


class _ImagesPromptInput(pydantic.BaseModel):
    """
    List input format for the TestImagePrompt.
    """

    images: list[bytes | str]


class _PromptOutput(pydantic.BaseModel):
    """
    Output format for the TestPrompt.
    """

    song_title: str
    song_lyrics: str


def _get_image_bytes() -> bytes:
    """Get the test image as bytes."""
    with open(Path(__file__).parent.parent.parent / "test-images" / "test.png", "rb") as f:
        return f.read()


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


@pytest.mark.parametrize(
    ("field_value", "image_present"),
    [
        (_get_image_bytes(), True),
        ("http://example.com/image.jpg", True),
        (None, False),
    ],
)
def test_image_prompt(field_value: bytes | str, image_present: bool):
    """Tests the prompt creation using an image"""

    class ImagePrompt(Prompt):
        user_prompt = "What is on this image?"
        image_input_fields = ["image"]

    prompt = ImagePrompt(_ImagePromptInput(image=field_value))
    assert (len(prompt.list_images()) > 0) == image_present


@pytest.mark.parametrize(
    ("field_value", "expected_number"),
    [
        ([_get_image_bytes(), "http://example.com/image.jpg"], 2),
        (["http://example.com/image.jpg"], 1),
        ([_get_image_bytes()], 1),
        ([], 0),
    ],
)
def test_images_prompt(field_value: list[bytes | str], expected_number: int):
    """Tests the prompt creation using images"""

    class ImagesPrompt(Prompt):
        user_prompt = "What is on these images?"
        image_input_fields = ["images"]

    prompt = ImagesPrompt(_ImagesPromptInput(images=field_value))
    assert len(prompt.list_images()) == expected_number


def test_prompt_with_no_input_type():
    """Test that a prompt can be created with no input type."""

    class TestPrompt(Prompt):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt()
    assert prompt.rendered_user_prompt == "Hello"
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
    assert prompt.rendered_system_prompt == "You are a song generator for a adult named Alice."
    assert prompt.rendered_user_prompt == "Theme for the song is rock."
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


def test_defining_few_shots():
    """Test that few shots can be defined for the prompt."""

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."
        few_shots = [
            ("Theme for the song is pop.", "It's a really catchy tune."),
        ]

    prompt = TestPrompt(_PromptInput(name="John", age=15, theme="rock"))

    assert prompt.chat == [
        {"role": "system", "content": "You are a song generator for a child named John."},
        {"role": "user", "content": "Theme for the song is pop."},
        {"role": "assistant", "content": "It's a really catchy tune."},
        {"role": "user", "content": "Theme for the song is rock."},
    ]


def test_defining_few_shots_input():
    """Test that few shots can be defined with input data for the prompt."""

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."
        few_shots = [
            (_PromptInput(name="Alice", age=30, theme="pop"), "It's a really catchy tune."),
        ]

    prompt = TestPrompt(_PromptInput(name="John", age=15, theme="rock"))

    assert prompt.chat == [
        {"role": "system", "content": "You are a song generator for a child named John."},
        {"role": "user", "content": "Theme for the song is pop."},
        {"role": "assistant", "content": "It's a really catchy tune."},
        {"role": "user", "content": "Theme for the song is rock."},
    ]


def test_adding_few_shots():
    """Test that few shots can be added to the conversation."""

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."

    prompt = TestPrompt(_PromptInput(name="John", age=15, theme="rock"))
    prompt.add_few_shot("Theme for the song is pop.", "It's a really catchy tune.")

    assert prompt.chat == [
        {"role": "system", "content": "You are a song generator for a child named John."},
        {"role": "user", "content": "Theme for the song is pop."},
        {"role": "assistant", "content": "It's a really catchy tune."},
        {"role": "user", "content": "Theme for the song is rock."},
    ]


def test_adding_few_shots_input():
    """Test that few shots can be added to the conversation with input data."""

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."

    prompt = TestPrompt(_PromptInput(name="John", age=15, theme="rock"))
    prompt.add_few_shot(_PromptInput(name="Alice", age=30, theme="pop"), "It's a really catchy tune.")

    assert prompt.chat == [
        {"role": "system", "content": "You are a song generator for a child named John."},
        {"role": "user", "content": "Theme for the song is pop."},
        {"role": "assistant", "content": "It's a really catchy tune."},
        {"role": "user", "content": "Theme for the song is rock."},
    ]


def test_defining_and_adding_few_shots():
    """Test that few shots can be defined and added to the conversation."""

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."
        few_shots = [
            ("Theme for the song is pop.", "It's a really catchy tune."),
        ]

    input_model = _PromptInput(name="John", age=15, theme="rock")
    prompt = TestPrompt(input_model)
    prompt.add_few_shot(
        input_model.model_copy(update={"theme": "experimental underground jazz"}),
        "It's quite hard to dance to.",
    )

    assert prompt.chat == [
        {"role": "system", "content": "You are a song generator for a child named John."},
        {"role": "user", "content": "Theme for the song is pop."},
        {"role": "assistant", "content": "It's a really catchy tune."},
        {"role": "user", "content": "Theme for the song is experimental underground jazz."},
        {"role": "assistant", "content": "It's quite hard to dance to."},
        {"role": "user", "content": "Theme for the song is rock."},
    ]


def test_few_shot_output_pydantic_model():
    """Test that the few shot examples with output Pydantic models are rendered correctly."""

    class TestPrompt(Prompt[_PromptInput, _PromptOutput]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."
        few_shots = [
            ("Theme for the song is pop.", _PromptOutput(song_title="Pop song", song_lyrics="La la la")),
        ]

    prompt = TestPrompt(_PromptInput(name="John", age=15, theme="rock"))
    prompt.add_few_shot("Theme for the song is disco.", _PromptOutput(song_title="Disco song", song_lyrics="Boogie!"))

    assert prompt.chat == [
        {"role": "system", "content": "You are a song generator for a child named John."},
        {"role": "user", "content": "Theme for the song is pop."},
        {"role": "assistant", "content": '{"song_title":"Pop song","song_lyrics":"La la la"}'},
        {"role": "user", "content": "Theme for the song is disco."},
        {"role": "assistant", "content": '{"song_title":"Disco song","song_lyrics":"Boogie!"}'},
        {"role": "user", "content": "Theme for the song is rock."},
    ]


def test_few_shot_int_output():
    """Test that the few shot examples with boolean output are rendered correctly."""

    class GoodNameDetectorPrompt(Prompt[_PromptInput, bool]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You detect whether the name name is a good name for a song with the given theme, given the age limit.
        """
        user_prompt = "The name is {{ name }}, the theme is {{ theme }} and the age is {{ age }}."
        few_shots = [
            (_PromptInput(theme="pop", name="I love you more than my cat", age=15), True),
        ]

    prompt = GoodNameDetectorPrompt(_PromptInput(theme="country", name="My muddy boots", age=18))
    prompt.add_few_shot(_PromptInput(theme="pop", name="The blood of a demon", age=75), False)

    assert prompt.chat == [
        {
            "role": "system",
            "content": "You detect whether the name name is a good name for a song with the given theme, given the age"
            " limit.",
        },
        {"role": "user", "content": "The name is I love you more than my cat, the theme is pop and the age is 15."},
        {"role": "assistant", "content": "True"},
        {"role": "user", "content": "The name is The blood of a demon, the theme is pop and the age is 75."},
        {"role": "assistant", "content": "False"},
        {"role": "user", "content": "The name is My muddy boots, the theme is country and the age is 18."},
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
    assert prompt.rendered_user_prompt == "Hello\nWorld"


def test_output_format():
    """Test that the output format is correctly returned."""

    class TestPrompt(Prompt[_PromptInput, _PromptOutput]):  # pylint: disable=unused-variable
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt(_PromptInput(name="John", age=15, theme="pop"))
    assert prompt.output_schema() == _PromptOutput


def test_output__format_no_pydantic():
    """Test that the output model and schema are not returned when output type is not a Pydantic model."""

    class TestPrompt(Prompt[_PromptInput, str]):
        """A test prompt"""

        user_prompt = "Hello"

    prompt = TestPrompt(_PromptInput(name="John", age=15, theme="pop"))
    assert prompt.output_schema() is None


def test_to_promptfoo():
    """Test that a prompt can be converted to a promptfoo prompt."""
    promptfoo_test_config = {
        "vars": {"name": "John", "age": 25, "theme": "pop"},
    }

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."

    assert TestPrompt.to_promptfoo(promptfoo_test_config) == [
        {"role": "system", "content": "You are a song generator for a adult named John."},
        {"role": "user", "content": "Theme for the song is pop."},
    ]


def test_two_instances_do_not_share_few_shots():
    """
    Test that two instances of a prompt do not share additional messages.
    """

    class TestPrompt(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
        """A test prompt"""

        system_prompt = """
        You are a song generator for a {% if age > 18 %}adult{% else %}child{% endif %} named {{ name }}.
        """
        user_prompt = "Theme for the song is {{ theme }}."

    prompt1 = TestPrompt(_PromptInput(name="John", age=15, theme="pop"))
    prompt1.add_few_shot("Theme for the song is 80s disco.", "I can't stop dancing.")

    prompt2 = TestPrompt(_PromptInput(name="Alice", age=30, theme="rock"))
    prompt2.add_few_shot("Theme for the song is 90s pop.", "Why do I know all the words?")

    assert prompt1.chat == [
        {"role": "system", "content": "You are a song generator for a child named John."},
        {"role": "user", "content": "Theme for the song is 80s disco."},
        {"role": "assistant", "content": "I can't stop dancing."},
        {"role": "user", "content": "Theme for the song is pop."},
    ]

    assert prompt2.chat == [
        {"role": "system", "content": "You are a song generator for a adult named Alice."},
        {"role": "user", "content": "Theme for the song is 90s pop."},
        {"role": "assistant", "content": "Why do I know all the words?"},
        {"role": "user", "content": "Theme for the song is rock."},
    ]
