from dataclasses import dataclass
from typing import List, Optional, Union

try:
    import litellm

    HAVE_LITELLM = True
except ImportError:
    HAVE_LITELLM = False


from ragstack_common.prompt import ChatFormat

from ..types import NOT_GIVEN, NotGiven
from .base import LLMClient, LLMOptions
from .exceptions import LLMConnectionError, LLMResponseError, LLMStatusError


@dataclass
class LiteLLMOptions(LLMOptions):
    """
    Dataclass that represents all available LLM call options for the LiteLLM client.
    Each of them is described in the [LiteLLM documentation](https://docs.litellm.ai/docs/completion/input).
    """

    frequency_penalty: Union[Optional[float], NotGiven] = NOT_GIVEN
    max_tokens: Union[Optional[int], NotGiven] = NOT_GIVEN
    n: Union[Optional[int], NotGiven] = NOT_GIVEN
    presence_penalty: Union[Optional[float], NotGiven] = NOT_GIVEN
    seed: Union[Optional[int], NotGiven] = NOT_GIVEN
    stop: Union[Optional[Union[str, List[str]]], NotGiven] = NOT_GIVEN
    temperature: Union[Optional[float], NotGiven] = NOT_GIVEN
    top_p: Union[Optional[float], NotGiven] = NOT_GIVEN


class LiteLLMClient(LLMClient[LiteLLMOptions]):
    """
    Client for the LiteLLM that supports calls to 100+ LLMs APIs, including OpenAI, Anthropic, VertexAI,
    Hugging Face and others.
    """

    _options_cls = LiteLLMOptions

    def __init__(
        self,
        model_name: str,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
    ) -> None:
        """
        Constructs a new LiteLLMClient instance.

        Args:
            model_name: Name of the model to use.
            base_url: Base URL of the LLM API.
            api_key: API key used to authenticate with the LLM API.
            api_version: API version of the LLM API.

        Raises:
            ImportError: If the litellm package is not installed.
        """
        if not HAVE_LITELLM:
            raise ImportError("You need to install litellm package to use LiteLLM models")

        super().__init__(model_name)
        self.base_url = base_url
        self.api_key = api_key
        self.api_version = api_version

    async def call(
        self,
        conversation: ChatFormat,
        options: LiteLLMOptions,
        json_mode: bool = False,
    ) -> str:
        """
        Calls the appropriate LLM endpoint with the given prompt and options.

        Args:
            conversation: List of dicts with "role" and "content" keys, representing the chat history so far.
            options: Additional settings used by the LLM.
            json_mode: Force the response to be in JSON format.

        Returns:
            Response string from LLM.

        Raises:
            LLMConnectionError: If there is a connection error with the LLM API.
            LLMStatusError: If the LLM API returns an error status code.
            LLMResponseError: If the LLM API response is invalid.
        """
        response_format = {"type": "json_object"} if json_mode else None

        try:
            response = await litellm.acompletion(
                messages=conversation,
                model=self.model_name,
                base_url=self.base_url,
                api_key=self.api_key,
                api_version=self.api_version,
                response_format=response_format,
                **options.dict(),
            )
        except litellm.openai.APIConnectionError as exc:
            raise LLMConnectionError() from exc
        except litellm.openai.APIStatusError as exc:
            raise LLMStatusError(exc.message, exc.status_code) from exc
        except litellm.openai.APIResponseValidationError as exc:
            raise LLMResponseError() from exc

        return response.choices[0].message.content
