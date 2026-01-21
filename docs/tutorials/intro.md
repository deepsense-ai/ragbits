# Tutorial: Large Language Models Intro

Let's walk through a quick example of **basic question answering**. Specifically, let's build **a system for answering tech questions**, e.g. about Linux or iPhone apps.

Install the latest Ragbits via `pip install -U ragbits ragbits-agents` and follow along.

## Configuring the environment

During development, we will use OpenAI's `gpt-4.1-nano` model. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md) or [local models](../how-to/llms/use_local_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
    OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Defining and running Prompts

The recommended way to define a prompt in Ragbits is to create a class that inherits from the [`Prompt`][ragbits.core.prompt.prompt.Prompt] class.

```python
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

class QuestionAnswerPromptInput(BaseModel):
    question: str

class QuestionAnswerPrompt(Prompt[QuestionAnswerPromptInput, str]):
    system_prompt = """
    You are a question answering agent. Answer the question to the best of your ability.
    """
    user_prompt = """
    Question: {{ question }}
    """
```

In order to run this prompt, initilize [`LLM`][ragbits.core.llms.LLM] client and call [`generate`][ragbits.core.llms.LLM.generate] method.

```python
import asyncio

from ragbits.core.llms import LiteLLM

async def main() -> None:
    llm = LiteLLM(model_name="gpt-4.1-nano")
    prompt = QuestionAnswerPrompt(QuestionAnswerPromptInput(
        question="What are high memory and low memory on linux?",
    ))
    response = await llm.generate(prompt)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

```text
In Linux, 'high memory' and 'low memory' refer to different parts of the system's physical RAM. Low memory
typically refers to the portion of RAM that is directly accessible by the kernel and most processes, often
the first 640MB or 1GB of RAM, depending on the architecture. High memory, on the other hand, is the portion
of RAM beyond this limit, which requires special handling because it cannot be directly accessed by the kernel
using regular pointers. High memory is usually seen in systems with large amounts of RAM where the kernel can't
directly address all memory with its own address space.
```

You can further and experiment with different prompting techniques like chain-of-thought in order to elicit reasoning out of your model before it commits to the answer.

```python hl_lines="2 8"
class CoTQuestionAnswerPromptOutput(BaseModel):
    reason: str
    answer: str

class CoTQuestionAnswerPrompt(Prompt[QuestionAnswerPromptInput, CoTQuestionAnswerPromptOutput]):
    system_prompt = """
    You are a question answering agent. Answer the question to the best of your ability.
    Think step by step.
    """
    user_prompt = """
    Question: {{ question }}
    """
```

Note that we have added a schema for the response, you can use it for structured output to get more predictable results by setting `use_structured_output=True` flag.

```python hl_lines="2"
async def main() -> None:
    llm = LiteLLM(model_name="gpt-4.1-nano", use_structured_output=True)
    prompt = CoTQuestionAnswerPrompt(QuestionAnswerPromptInput(
        question="What are high memory and low memory on linux?",
    ))
    response = await llm.generate(prompt)
    print(response.answer)

if __name__ == "__main__":
    asyncio.run(main())
```

```text
High memory on Linux refers to the part of RAM above the addressable limit for a 32-bit kernel, often above 1GB
or 4GB depending on architecture, which requires special handling to access. Low memory is the portion within
the addressable range for the kernel, generally below these limits, and is directly accessible by the system.
```

!!! tip "Observe the reasoning process"
    Try printing `response.reason` to see the step-by-step reasoning the model performed. You will notice that while this chain-of-thought approach can improve answer quality, it also consumes more tokens due to the additional reasoning content - an important consideration for cost and latency.

Interestingly, asking for reasoning can make the output answer shorter in this case. Is this a good thing or a bad thing? It depends on what you need: there's no free lunch, but Ragbits gives you the tools to experiment with different strategies extremely quickly.

## Evaluating the system

Ragbits provides evalution for second layer components, such as [`DocumentSearch`][ragbits.document_search.DocumentSearch] or [`Agent`][ragbits.agents.Agent]. To run the evaluation on LLM, you must use it through the [`Agent`][ragbits.agents.Agent] object.

```python
from ragbits.agents.types import QuestionAnswerAgent

llm = LiteLLM(model_name="gpt-4.1-nano", use_structured_output=True)
responder = QuestionAnswerAgent(llm=llm, prompt=CoTQuestionAnswerPrompt)
```

To measure the quality of your Ragbits system, you need a bunch of input values, like questions for example, and a metric that can score the quality of an output from your system. Metrics vary widely. Some metrics need ground-truth labels of ideal outputs, e.g. for classification or question answering. Other metrics are self-supervised, e.g. checking faithfulness or lack of hallucination.

Let's load a dataset of questions and their ground truth answers. Since we started this tutorial with the goal of building a system for answering Tech questions, we obtained a bunch of questions and their correct answers from the [RAG-QA Arena](https://arxiv.org/abs/2407.13998) dataset.

```python
from ragbits.core.sources import WebSource
from ragbits.evaluate.dataloaders.question_answer import QuestionAnswerDataLoader

source = WebSource(url="https://huggingface.co/datasets/deepsense-ai/ragbits/resolve/main/ragqa_arena_tech_examples.jsonl")
dataloader = QuestionAnswerDataLoader(
    source=source,
    split="data[:100]",
    question_key="question",
    answer_key="response",
)
```

```python
async def main() -> None:
    dataset = await dataloader.load()
    print(dataset[0])

if __name__ == "__main__":
    asyncio.run(main())
```

```python
QuestionAnswerData(
    question="why igp is used in mpls?",
    reference_answer="An IGP exchanges routing prefixes between gateways/routers.  \nWithout a routing protocol, you'd have to configure each route on every router and you'd have no dynamic updates when routes change because of link failures. \nFuthermore, within an MPLS network, an IGP is vital for advertising the internal topology and ensuring connectivity for MP-BGP inside the network.",
    reference_context=None
)
```

What kind of metric can suit our question-answering task? There are many choices, but since the answers are long, we may ask: How well does the system response cover all key facts in the gold response? And the other way around, how well is the system response not saying things that aren't in the gold response?

That metric measures essentially an answer correctness, so let's load a [`QuestionAnswerAnswerCorrectness`][ragbits.evaluate.metrics.question_answer.QuestionAnswerAnswerCorrectness] metric from Ragbits. This metric is actually implemented as a very simple Ragbits module using whatever LLM we are working with.

```python
from ragbits.evaluate.metrics.question_answer import QuestionAnswerAnswerCorrectness

judge = LiteLLM(model_name="gpt-4.1")
metric = QuestionAnswerAnswerCorrectness(judge)
```

```python hl_lines="6-12"
from ragbits.evaluate.pipelines.question_answer import QuestionAnswerResult

async def main() -> None:
    dataset = await dataloader.load()
    response = await responder.run(QuestionAnswerPromptInput(question=dataset[0].question))
    score = await metric.compute([
        QuestionAnswerResult(
            question=dataset[0].question,
            reference_answer=dataset[0].reference_answer,
            predicted_result=response,
        )
    ])
    print(score)

if __name__ == "__main__":
    asyncio.run(main())
```

```python
{'LLM_based_answer_correctness': 1.0}
```

For evaluation, you could use the metric above in a simple loop and just average the score. But for nice parallelism and utilities, we can rely on [`Evaluator`][ragbits.evaluate.evaluator.Evaluator].

```python
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics import MetricSet
from ragbits.evaluate.pipelines.question_answer import QuestionAnswerPipeline

async def main() -> None:
    evaluator = Evaluator()
    results = await evaluator.compute(
        dataloader=dataloader,
        pipeline=QuestionAnswerPipeline(responder),
        metricset=MetricSet(metric),
    )
    print(results.metrics)

if __name__ == "__main__":
    asyncio.run(main())
```

```python
{'LLM_based_answer_correctness': 0.68}  # Your result may differ
```

## Conclusions

In this tutorial, we built a very simple LLM workflow using chain-of-thought for question answering and evaluated it on a small dataset.

Can we do better? In the next guide, we will build a retrieval-augmented generation (RAG) pipeline in Ragbits for the same task. We will see how this can boost the score substantially.
