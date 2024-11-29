# How to create custom Evaluation Pipeline for Ragbits evaluation

Ragbits provides a ready-to-use evaluation pipeline for document search, implemented within the `ragbits.evaluate.document_search.DocumentSearchPipeline` module.

To create a custom evaluation pipeline for your specific use case, you need to implement the `__call__` method as part of the `ragbits.evaluate.pipelines.base.EvaluationPipeline` interface.


Please find the example here:

```python
from dataclasses import dataclass
from ragbits.evaluate.pipelines.base import EvaluationResult, EvaluationPipeline
from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt
from pydantic import BaseModel


@dataclass
class RandomQuestionPipelineResult(EvaluationResult):
    answer: str


class QuestionRespondPromptInput(BaseModel):
    system_prompt_content: str
    question: str


class QuestionRespondPrompt(Prompt[QuestionRespondPromptInput]):
    system_prompt = "{{ system_prompt_content }}"
    user_prompt = "{{ question }}"


class RandomQuestionRespondPipeline(EvaluationPipeline):
    async def __call__(self, data: dict[str, str]) -> RandomQuestionPipelineResult:
        llm = LiteLLM()
        input_prompt = QuestionRespondPrompt(
            QuestionRespondPromptInput(
                system_prompt_content=self.config.system_prompt_content,
                question=data["question"],
            )
        )
        answer = await llm.generate(prompt=input_prompt)
        return RandomQuestionPipelineResult(answer=answer)
```
