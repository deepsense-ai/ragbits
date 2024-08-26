from functools import cached_property
from typing import Optional

try:
    import litellm

    HAVE_LITELLM = True
except ImportError:
    HAVE_LITELLM = False

from ragstack_common.prompt import Prompt

from .base import LLM
from .clients.litellm import LiteLLMClient, LiteLLMOptions


class LiteLLM(LLM[LiteLLMOptions]):
    """
    Class for interaction with any LLM supported by LiteLLM API.
    """

    _options_cls = LiteLLMOptions

    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        default_options: Optional[LiteLLMOptions] = None,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
    ) -> None:
        """
        Constructs a new LiteLLM instance.

        Args:
            model_name: Name of the [LiteLLM supported model](https://docs.litellm.ai/docs/providers) to be used.\
                Default is "gpt-3.5-turbo".
            default_options: Default options to be used.
            base_url: Base URL of the LLM API.
            api_key: API key to be used. API key to be used. If not specified, an environment variable will be used,
                for more information, follow the instructions for your specific vendor in the\
                [LiteLLM documentation](https://docs.litellm.ai/docs/providers).
            api_version: API version to be used. If not specified, the default version will be used.

        Raises:
            ImportError: If the litellm package is not installed.
        """
        if not HAVE_LITELLM:
            raise ImportError("You need to install litellm package to use LiteLLM models")

        super().__init__(model_name, default_options)
        self.base_url = base_url
        self.api_key = api_key
        self.api_version = api_version

    @cached_property
    def client(self) -> LiteLLMClient:
        """
        Client for the LLM.
        """
        return LiteLLMClient(
            model_name=self.model_name,
            base_url=self.base_url,
            api_key=self.api_key,
            api_version=self.api_version,
        )

    def count_tokens(self, prompt: Prompt) -> int:
        """
        Counts tokens in the prompt.

        Args:
            prompt: Formatted prompt template with conversation and response parsing configuration.

        Returns:
            Number of tokens in the prompt.
        """
        return sum(litellm.token_counter(model=self.model_name, text=message["content"]) for message in prompt.chat)
