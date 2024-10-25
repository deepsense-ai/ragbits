import base64
import io
import os

from PIL import Image
from unstructured.documents.elements import Element as UnstructuredElement

from ragbits.core.llms.base import LLM
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import TextElement


def to_text_element(element: UnstructuredElement, document_meta: DocumentMeta) -> TextElement:
    """
    Converts unstructured element to ragbits text element

    Args:
        element: element from unstructured
        document_meta: metadata of the document

    Returns:
        text element
    """
    return TextElement(
        document_meta=document_meta,
        content=element.text,
    )


def check_required_argument(value: str | None, arg_name: str, fallback_env: str) -> str:
    """
    Checks if given environment variable is set and returns it or raises an error

    Args:
        arg_name: name of the variable
        value: optional default value
        fallback_env: name of the environment variable to get

    Raises:
        ValueError: if environment variable is not set

    Returns:
        environment variable value
    """
    if value is not None:
        return value
    if (env_value := os.getenv(fallback_env)) is None:
        raise ValueError(f"Either pass {arg_name} argument or set the {fallback_env} environment variable")
    return env_value


def extract_image_coordinates(element: UnstructuredElement) -> tuple[float, float, float, float]:
    """
    Extracts image coordinates from unstructured element
    Args:
        element: element from unstructured
    Returns:
        x of top left corner, y of top left corner, x of bottom right corner, y of bottom right corner
    """
    p1, p2, p3, p4 = element.metadata.coordinates.points  # type: ignore
    return min(p1[0], p2[0]), min(p1[1], p4[1]), max(p3[0], p4[0]), max(p2[1], p3[1])


def crop_and_convert_to_bytes(image: Image.Image, x0: float, y0: float, x1: float, y1: float) -> bytes:
    """
    Crops the image and converts to bytes
    Args:
        image: PIL image
        x0: x of top left corner
        y0: y of top left corner
        x1: x of bottom right corner
        y1: y of bottom right corner
    Returns:
        bytes of the cropped image
    """
    image = image.crop((x0, y0, x1, y1))
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return buffered.getvalue()


class ImageDescriber:
    """
    Describes images content using an LLM
    """

    DEFAULT_PROMPT = "Describe the content of the image."

    def __init__(self, llm: LLM):
        self.llm = llm

    async def get_image_description(self, image_bytes: bytes, prompt: str | None = DEFAULT_PROMPT) -> str:
        """
        Provides summary of the image (passed as bytes)

        Args:
            image_bytes: bytes of the image
            prompt: prompt to be used

        Returns:
            summary of the image
        """
        img_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # TODO make this use prompt structure from ragbits core once there is a support for images
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                    },
                ],
            }
        ]
        return await self.llm.client.call(messages, self.llm.default_options)  # type: ignore
