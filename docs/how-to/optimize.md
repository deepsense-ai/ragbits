# How to Autoconfigure Your Pipeline

Ragbits provides a feature that allows users to automatically configure hyperparameters for a pipeline. This functionality is agnostic to the type of optimized structure, with the only requirements being the following:

- The optimized pipeline must inherit from `ragbits.evaluate.pipelines.base.EvaluationPipeline`.
- The definition of optimized metrics must adhere to the `ragbits.evaluate.metrics.base.Metric` interface.
- These metrics should be gathered into an instance of `ragbits.evaluate.metrics.base.MetricSet`.
- An instance of a class inheriting from `ragbits.evaluate.metrics.loader.base.DataLoader` must be provided as the data source for optimization.

## Supported Parameter Types

The optimized parameters can be of the following types:

- **Continuous**
- **Ordinal**
- **Categorical**

For ordinal and continuous parameters, the values should be integers or floats. For categorical parameters, more sophisticated structures are supported, including the possibility of nested parameters of other types.

Each optimized variable should be marked with the `optimize=True` flag in the configuration.

For categorical variables, you must also provide the `choices` field, which lists all possible values to be considered during optimization. For continuous and ordinal variables, the `range` field should be specified as a two-element list defining the minimum and maximum values of interest. For continuous parameters, the elements must be floats, while for ordinal parameters, they must be integers.

## Example Usage

In this example, we will optimize a system prompt for a question-answering pipeline so that the answers contain the minimal number of tokens.

### Define the Optimized Pipeline Structure

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

### Define the Data Loader

Next, we define the data loader. We'll use Ragbits generation stack to create an artificial data loader:


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

### Define the Metrics and Run the Experiment

```python
from pprint import pp as pprint
import tiktoken
from ragbits.evaluate.optimizer import Optimizer
from ragbits.evaluate.metrics.base import Metric, MetricSet, ResultT
from omegaconf import OmegaConf


class TokenCountMetric(Metric):
    def compute(self, results: list[ResultT]) -> dict[str, float]:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = [len(encoding.encode(out.answer)) for out in results]
        return {"num_tokens": sum(num_tokens) / len(num_tokens)}


metrics = MetricSet(TokenCountMetric())

optimization_cfg = OmegaConf.create(
    {"direction": "minimize", "n_trials": 4, "max_retries_for_trial": 3}
)
optimizer = Optimizer(optimization_cfg)

optimized_params = OmegaConf.create(
    {
        "system_prompt_content": {
            "optimize": True,
            "choices": [
                "Be a friendly bot answering user questions. Be as concise as possible",
                "Be a silly bot answering user questions. Use as few tokens as possible",
                "Be informative and straight to the point",
                "Respond to user questions in as few words as possible",
            ],
        }
    }
)
configs_with_scores = optimizer.optimize(
    pipeline_class=RandomQuestionRespondPipeline,
    config_with_params=optimized_params,
    metrics=metrics,
    dataloader=dataloader,
)
pprint(configs_with_scores)
```

After executing the code, your console should display an output structure similar to this:

```json
[({'system_prompt_content': 'Be a silly bot answering user questions. Use as few tokens as possible'},
  6.0,
  {'num_tokens': 6.0}),
 ({'system_prompt_content': 'Be a silly bot answering user questions. Use as few tokens as possible'},
  10.7,
  {'num_tokens': 10.7}),
 ({'system_prompt_content': 'Be a friendly bot answering user questions. Be as concise as possible'},
  37.8,
  {'num_tokens': 37.8}),
 ({'system_prompt_content': 'Be informative and straight to the point'},
  113.2,
  {'num_tokens': 113.2})]

```

This output consists of tuples, each containing three elements:

1. The configuration used in the trial.
2. The score achieved.
3. A dictionary of detailed metrics that contribute to the score.

The tuples are ordered from the best to the worst configuration based on the score.

Please note that the details may vary between runs due to the non-deterministic nature of both the LLM and the optimization algorithm.
