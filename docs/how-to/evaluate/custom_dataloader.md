# How to create custom DataLoader for Ragbits evaluation

Ragbits provides a base interface for data loading, `ragbits.evaluate.loaders.base.DataLoader`, designed specifically for evaluation purposes. A ready-to-use implementation, `ragbits.evaluate.loaders.hf.HFLoader`, is available for handling datasets in Hugging Face format.

To create a custom DataLoader for your specific needs, you need to implement the `load` method in a class that inherits from the `DataLoader` interface. In this example we use generation stack to create it on the fly:

```python
from ragbits.evaluate.loaders.base import DataLoader, DataT
from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt
from pydantic import BaseModel
from omegaconf import OmegaConf


class DatasetGenerationPromptInput(BaseModel):
    topic: str


class DatasetGenerationPrompt(Prompt[DatasetGenerationPromptInput]):
    system_prompt = "Be a provider of random questions on a topic specified by the user."
    user_prompt = "Generate a question about {{ topic }}"


class RandomQuestionsDataLoader(DataLoader):
    async def load(self) -> list[dict[str, str]]:
        questions = []
        llm = LiteLLM()
        for _ in range(self.config.num_questions):
            question = await llm.generate(
                DatasetGenerationPrompt(DatasetGenerationPromptInput(topic=self.config.question_topic))
            )
            questions.append({"question": question})
        return questions


dataloader_config = OmegaConf.create(
    {"num_questions": 10, "question_topic": "conspiracy theories"}
)
dataloader = RandomQuestionsDataLoader(dataloader_config)
```

**Note:** This interface is not to be confused with PyTorch's `DataLoader`, as it serves a distinct purpose within the Ragbits evaluation framework.
