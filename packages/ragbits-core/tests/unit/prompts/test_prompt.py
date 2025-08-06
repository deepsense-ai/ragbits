from pathlib import Path
from typing import Any

import pydantic
import pytest

from ragbits.core.prompt import Attachment, Prompt
from ragbits.core.prompt.base import BasePromptWithParser
from ragbits.core.prompt.exceptions import PromptWithAttachmentOfUnsupportedFormat, PromptWithEmptyAttachment


class _PromptInput(pydantic.BaseModel):
    """
    Input format for the TestPrompt.
    """

    theme: str
    name: str
    age: int


class _SingleAttachmentPromptInput(pydantic.BaseModel):
    """
    Single input format for the TestAttachmentPrompt.
    """

    attachment: Any


class _MultipleAttachmentPromptInput(pydantic.BaseModel):
    """
    Multiple input format for the TestAttachmentsPrompt.
    """

    attachments: list[Any]


class _PromptOutput(pydantic.BaseModel):
    """
    Output format for the TestPrompt.
    """

    song_title: str
    song_lyrics: str


def _get_image_bytes() -> Attachment:
    """Get an image attachment with bytes data."""
    image_path = Path(__file__).parent.parent.parent / "assets" / "img" / "test.png"
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    return Attachment(data=image_bytes)


def _get_image_url() -> Attachment:
    """Get an image attachment with a URL."""
    return Attachment(url="http://example.com/image.jpg")


def _get_image_url_and_mime() -> Attachment:
    """Get an image attachment with a URL and MIME type."""
    return Attachment(url="http://example.com/image", mime_type="image/jpeg")


def _get_pdf_bytes() -> Attachment:
    """Get a PDF attachment with bytes data."""
    return Attachment(data=b"%PDF-1.4\n%fake PDF content\n")


def _get_pdf_url() -> Attachment:
    """Get a PDF attachment with a URL."""
    return Attachment(url="http://example.com/document.pdf")


def _get_pdf_url_and_mime() -> Attachment:
    """Get a PDF attachment with a URL and MIME type."""
    return Attachment(url="http://example.com/document", mime_type="application/pdf")


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


def test_raises_when_unknown_user_template_variable():
    """Test that a ValueError is raised when an unknown template variable is provided."""
    with pytest.raises(ValueError):

        class TestPromptUser(Prompt[_PromptInput, str]):  # pylint: disable=unused-variable
            """A test prompt"""

            user_prompt = "Hello, {{ foo }}"


def test_raises_when_unknown_system_template_variable():
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


def test_empty_attachment():
    """Tests the prompt creation using an empty attachment"""

    class TestAttachmentPrompt(Prompt):
        user_prompt = "This should fail due to empty attachment"

    with pytest.raises(PromptWithEmptyAttachment):
        TestAttachmentPrompt(_SingleAttachmentPromptInput(attachment=Attachment()))


def test_unsupported_attachment():
    """Tests the prompt creation using an unsupported attachment format"""

    class TestAttachmentPrompt(Prompt):
        user_prompt = "This should fail due to unsupported attachment format"

    with pytest.raises(PromptWithAttachmentOfUnsupportedFormat):
        TestAttachmentPrompt(
            _SingleAttachmentPromptInput(attachment=Attachment(data=b"random data", mime_type="invalid/type"))
        )


@pytest.mark.parametrize(
    ("field_value", "image_present"),
    [
        (_get_image_bytes(), True),
        (_get_image_url(), True),
        (_get_image_url_and_mime(), True),
        ("non-attachment-object", False),
        (None, False),
    ],
)
def test_image_prompt(field_value: Attachment | str | None, image_present: bool):
    """Tests the prompt creation using an image"""

    class TestAttachmentPrompt(Prompt):
        user_prompt = "What is in this image?"

    prompt = TestAttachmentPrompt(_SingleAttachmentPromptInput(attachment=field_value))
    assert len(prompt.list_images()) == (1 if image_present else 0)


def test_image_prompt_format():
    """Tests the prompt format using an image"""

    class TestAttachmentPrompt(Prompt):
        user_prompt = "What is in this image?"

    prompt = TestAttachmentPrompt(_SingleAttachmentPromptInput(attachment=_get_image_bytes()))
    chat = prompt.chat
    assert len(chat) == 1
    assert chat[0]["role"] == "user"
    assert chat[0]["content"][0]["text"] == "What is in this image?"
    assert chat[0]["content"][1]["type"] == "image_url"


def test_image_prompt_encoding():
    """Tests whether the image has a proper encoding"""

    class TestAttachmentPrompt(Prompt):
        user_prompt = "What is in this image?"

    prompt = TestAttachmentPrompt(_SingleAttachmentPromptInput(attachment=_get_image_bytes()))
    images_list = prompt.list_images()
    assert len(images_list) == 1
    assert images_list[0].startswith("data:image/png")


@pytest.mark.parametrize(
    ("field_value", "expected_number"),
    [
        ([_get_image_bytes(), _get_image_url(), _get_image_url_and_mime()], 3),
        ([_get_image_url(), _get_image_url_and_mime(), "non-attachment-object"], 2),
        ([_get_image_bytes(), "non-attachment-object"], 1),
        (["non-attachment-object"], 0),
        ([], 0),
    ],
)
def test_images_prompt(field_value: list[Attachment | str | None], expected_number: int):
    """Tests the prompt creation using images"""

    class TestAttachmentsPrompt(Prompt):
        user_prompt = "What is in these images?"

    prompt = TestAttachmentsPrompt(_MultipleAttachmentPromptInput(attachments=field_value))
    assert len(prompt.list_images()) == expected_number


@pytest.mark.parametrize(
    ("field_value", "pdf_present"),
    [
        (_get_pdf_bytes(), True),
        (_get_pdf_url(), True),
        (_get_pdf_url_and_mime(), True),
        ("non-attachment-object", False),
        (None, False),
    ],
)
def test_pdf_prompt(field_value: Attachment | str | None, pdf_present: bool):
    """Tests the prompt creation using a PDF"""

    class TestAttachmentPrompt(Prompt):
        user_prompt = "What is in this PDF?"

    prompt = TestAttachmentPrompt(_SingleAttachmentPromptInput(attachment=field_value))
    assert len(prompt.list_pdfs()) == (1 if pdf_present else 0)


def test_pdf_prompt_format():
    """Tests the prompt format using a PDF"""

    class TestAttachmentPrompt(Prompt):
        user_prompt = "What is in this PDF?"

    prompt = TestAttachmentPrompt(_SingleAttachmentPromptInput(attachment=_get_pdf_bytes()))
    chat = prompt.chat
    assert len(chat) == 1
    assert chat[0]["role"] == "user"
    assert chat[0]["content"][0]["text"] == "What is in this PDF?"
    assert chat[0]["content"][1]["type"] == "file"


def test_pdf_prompt_encoding():
    """Tests whether the PDF has a proper encoding"""

    class TestAttachmentPrompt(Prompt):
        user_prompt = "What is in this PDF?"

    prompt = TestAttachmentPrompt(_SingleAttachmentPromptInput(attachment=_get_pdf_bytes()))
    pdf_list = prompt.list_pdfs()
    assert len(pdf_list) == 1
    assert pdf_list[0].startswith("data:application/pdf")


@pytest.mark.parametrize(
    ("field_value", "expected_number"),
    [
        ([_get_pdf_bytes(), _get_pdf_url(), _get_pdf_url_and_mime()], 3),
        ([_get_pdf_url(), _get_pdf_url_and_mime(), "non-attachment-object"], 2),
        ([_get_pdf_bytes(), "non-attachment-object"], 1),
        (["non-attachment-object"], 0),
        ([], 0),
    ],
)
def test_pdfs_prompt(field_value: list[Attachment | str | None], expected_number: int):
    """Tests the prompt creation using PDFs"""

    class TestAttachmentsPrompt(Prompt):
        user_prompt = "What is in these PDFs?"

    prompt = TestAttachmentsPrompt(_MultipleAttachmentPromptInput(attachments=field_value))
    assert len(prompt.list_pdfs()) == expected_number


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


async def test_response_parser():
    class TestPrompt(Prompt):
        user_prompt = "Hello AI"

    async def async_parser(response: str) -> str:
        return response.upper()

    def sync_parser(response: str) -> str:
        return response.lower()

    test_prompt = TestPrompt()

    resp = "Hello Human"
    test_prompt.response_parser = async_parser
    resp_async = await test_prompt.parse_response(resp)
    assert resp_async == "HELLO HUMAN"

    test_prompt.response_parser = sync_parser
    resp_sync = await test_prompt.parse_response(resp)
    assert resp_sync == "hello human"


def test_add_user_message_with_string():
    """Test adding a user message with a string content."""

    class TestPrompt(Prompt):
        user_prompt = "Hello"

    prompt = TestPrompt()
    prompt.add_user_message("Additional message")

    assert prompt.chat == [{"role": "user", "content": "Hello"}, {"role": "user", "content": "Additional message"}]


def test_add_user_message_with_input_model():
    """Test adding a user message with an input model."""

    class TestPrompt(Prompt[_PromptInput, str]):
        user_prompt = "Hello {{ name }}"

    prompt = TestPrompt(_PromptInput(name="Alice", age=30, theme="rock"))
    prompt.add_user_message(_PromptInput(name="Bob", age=25, theme="jazz"))

    assert prompt.chat == [{"role": "user", "content": "Hello Alice"}, {"role": "user", "content": "Hello Bob"}]


def test_add_user_message_with_image():
    """Test adding a user message with an image."""

    class TestAttachmentPrompt(Prompt):
        user_prompt = "What is in this image?"

    prompt = TestAttachmentPrompt(_SingleAttachmentPromptInput(attachment=_get_image_bytes()))
    prompt.add_user_message(_MultipleAttachmentPromptInput(attachments=[_get_image_bytes(), _get_pdf_bytes()]))

    assert len(prompt.chat) == 2
    assert prompt.chat[0]["role"] == "user"
    assert prompt.chat[1]["role"] == "user"
    assert len(prompt.chat[0]["content"]) == 2  # text + image
    assert len(prompt.chat[1]["content"]) == 3  # text + image + pdf


def test_add_assistant_message():
    """Test adding an assistant message."""

    class TestPrompt(Prompt[_PromptInput, _PromptOutput]):
        user_prompt = "Hello {{ name }}"

    prompt = TestPrompt(_PromptInput(name="Alice", age=30, theme="rock"))
    prompt.add_assistant_message("Assistant response")

    assert prompt.chat == [
        {"role": "user", "content": "Hello Alice"},
        {"role": "assistant", "content": "Assistant response"},
    ]


def test_add_assistant_message_with_model():
    """Test adding an assistant message with a model output."""

    class TestPrompt(Prompt[_PromptInput, _PromptOutput]):
        user_prompt = "Hello {{ name }}"

    prompt = TestPrompt(_PromptInput(name="Alice", age=30, theme="rock"))
    output = _PromptOutput(song_title="Test Song", song_lyrics="Test Lyrics")
    prompt.add_assistant_message(output)

    assert prompt.chat == [
        {"role": "user", "content": "Hello Alice"},
        {"role": "assistant", "content": output.model_dump_json()},
    ]


def test_conversation_history():
    """Test building a complete conversation history with multiple messages."""

    class TestPrompt(Prompt[_PromptInput, _PromptOutput]):
        user_prompt = "Hello {{ name }}"

    prompt = TestPrompt(_PromptInput(name="Alice", age=30, theme="rock"))
    prompt.add_user_message("How are you?")
    prompt.add_assistant_message("I'm doing well!")
    prompt.add_user_message(_PromptInput(name="Bob", age=25, theme="jazz"))
    prompt.add_assistant_message(_PromptOutput(song_title="Jazz Song", song_lyrics="Jazz lyrics"))

    assert prompt.chat == [
        {"role": "user", "content": "Hello Alice"},
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "I'm doing well!"},
        {"role": "user", "content": "Hello Bob"},
        {
            "role": "assistant",
            "content": _PromptOutput(song_title="Jazz Song", song_lyrics="Jazz lyrics").model_dump_json(),
        },
    ]


class TestBasePromptWithParser(BasePromptWithParser[str]):
    """Test implementation of BasePromptWithParser for testing add_x_message methods."""

    async def parse_response(self, response: str) -> str:  # noqa: PLR6301
        """Parse the response."""
        return response.upper()


def test_base_prompt_with_parser_add_user_message_no_history():
    """Test adding a user message when no conversation history exists."""
    prompt = TestBasePromptWithParser()

    result = prompt.add_user_message("Hello world")
    assert prompt.chat == [{"role": "user", "content": "Hello world"}]
    assert result is prompt


def test_base_prompt_with_parser_add_assistant_message_no_history():
    """Test adding an assistant message when no conversation history exists."""
    prompt = TestBasePromptWithParser()

    result = prompt.add_assistant_message("Hello there!")
    assert prompt.chat == [{"role": "assistant", "content": "Hello there!"}]
    assert result is prompt


def test_base_prompt_with_parser_add_tool_use_message_no_history():
    """Test adding tool use messages when no conversation history exists."""
    prompt = TestBasePromptWithParser()

    result = prompt.add_tool_use_message(
        id="tool_123", name="test_function", arguments={"param": "value"}, result="tool result"
    )

    assert prompt.chat[0]["role"] == "assistant"
    assert prompt.chat[0]["content"] is None
    assert "tool_calls" in prompt.chat[0]
    assert prompt.chat[0]["tool_calls"][0]["id"] == "tool_123"
    assert prompt.chat[0]["tool_calls"][0]["type"] == "function"
    assert prompt.chat[0]["tool_calls"][0]["function"]["name"] == "test_function"
    assert prompt.chat[0]["tool_calls"][0]["function"]["arguments"] == '{"param": "value"}'

    assert prompt.chat[1]["role"] == "tool"
    assert prompt.chat[1]["tool_call_id"] == "tool_123"
    assert prompt.chat[1]["content"] == "tool result"

    assert result is prompt
