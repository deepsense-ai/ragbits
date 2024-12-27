import base64
import warnings
from functools import cached_property

import litellm

from ragbits.core.prompt.base import BasePrompt, ChatFormat

from .base import LLM
from .clients.litellm import LiteLLMClient, LiteLLMOptions


class LiteLLM(LLM[LiteLLMOptions]):
    """
    Class for interaction with any LLM supported by LiteLLM API.
    """

    options_cls = LiteLLMOptions

    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        default_options: LiteLLMOptions | None = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
        use_structured_output: bool = False,
        router: litellm.Router | None = None,
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
            use_structured_output: Whether to request a
                [structured output](https://docs.litellm.ai/docs/completion/json_mode#pass-in-json_schema)
                from the model. Default is False. Can only be combined with models that support structured output.
            router: Router to be used to [route requests](https://docs.litellm.ai/docs/routing) to different models.
        """
        super().__init__(model_name, default_options)
        self.base_url = base_url
        self.api_key = api_key
        self.api_version = api_version
        self.use_structured_output = use_structured_output
        self.router = router

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
            use_structured_output=self.use_structured_output,
            router=self.router,
        )

    def count_tokens(self, prompt: BasePrompt) -> int:
        """
        Counts tokens in the prompt.

        Args:
            prompt: Formatted prompt template with conversation and response parsing configuration.

        Returns:
            Number of tokens in the prompt.
        """
        return sum(litellm.token_counter(model=self.model_name, text=message["content"]) for message in prompt.chat)

    def _format_chat_for_llm(self, prompt: BasePrompt) -> ChatFormat:
        images = prompt.list_images()
        chat = prompt.chat
        if images:
            if not litellm.supports_vision(self.model_name):
                warnings.warn(
                    message=f"Model {self.model_name} does not support vision. Image input would be ignored",
                    category=UserWarning,
                )
                return chat
            user_message_content = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64.b64encode(im).decode('utf-8')}"
                        if isinstance(im, bytes)
                        else im,
                    },
                }
                for im in images
            ]
            last_message = chat[-1]
            if last_message["role"] == "user":
                user_message_content = [{"type": "text", "text": last_message["content"]}] + user_message_content
                chat = chat[:-1]
            chat.append({"role": "user", "content": user_message_content})
        return chat
