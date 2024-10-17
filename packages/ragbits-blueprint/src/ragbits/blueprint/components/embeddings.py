import textwrap

from ragbits.blueprint.base import BlueprintComponent, BlueprintComponentType
from ragbits.blueprint.options import ChoiceOption


class EmbeddingsComponentType(BlueprintComponentType):
    """
    A component type for embeddings providers.
    """

    name = "Embeddings Provider"
    description = "will be used to create vector representations of elements and for search functionality"


class LiteLLMEmbeddingsComponent(BlueprintComponent):
    """
    LiteLLM Embeddings component.
    """

    name = "LiteLLM Embeddings"
    description = "supports most popular embeddings providers with unified API."
    options = {
        "model_name": ChoiceOption(
            message="Choose a model",
            choices={
                "text-embedding-3-small": "OpenAI text-embedding-4-small",
                "text-embedding-3-large": "OpenAI text-embedding-4-large",
            },
            allow_other=True,
        )
    }

    @classmethod
    def help(cls) -> str:
        """
        Get a help message for the component.

        Returns:
            A help message for the component.
        """
        return "For more information, visit https://docs.litellm.ai/"

    def generate_imports(self) -> list[str]:
        """
        Generate the imports for the component.

        Returns:
            A list of strings with the imports.
        """
        return ["from ragbits.core.embeddings import LiteLLMEmbeddings"]

    def generate(self) -> str:
        """
        Generate the code for the component.

        Returns:
            The code for the component.
        """
        return textwrap.dedent(
            f"""
        def get_embeddings():
            return LiteLLMEmbeddings(model="{self._selected_options["model_name"]}")
        """
        ).strip()


EmbeddingsComponentType.register(LiteLLMEmbeddingsComponent)