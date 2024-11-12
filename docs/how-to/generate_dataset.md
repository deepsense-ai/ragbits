# Generating a Dataset with Ragbits

Ragbits offers a convenient feature to generate artificial QA datasets for evaluating Retrieval-Augmented Generation (RAG) systems. You can choose between two different approaches:

## Available Stacks

1. **FromScratch**:
   - This option allows you to create a complete QA dataset from scratch.
   - **How it works**: You provide a list of topics, and the system automatically generates both the corpus and the QA dataset.

2. **FromCorpus**:
   - This approach uses an existing textual corpus.
   - **How it works**: You supply a pre-existing corpus, such as documents you’ve previously retrieved, and the system creates the QA dataset based on it.

## Usage Examples

Below are examples demonstrating how to use both approaches.


### From Scratch


```python
import json

from datasets import Dataset
from omegaconf import OmegaConf
from ragbits.evaluate.dataset_generator.pipeline import DatasetGenerationPipeline


def print_dataset(dataset: Dataset):
    entries = []
    for idx, (question, answer, passage) in enumerate(
        zip(dataset["question"], dataset["basic_answer"], dataset["passages"])
    ):
        entries.append(
            f"{idx}. QUESTION: {question} ANSWER: {answer} PASSAGES: {json.dumps(passage)}"
        )
    print("\r\n".join(entries))

pipeline_config = OmegaConf.create(
    {
        "input_name": "query",
        "pipeline": {
            "name": "synthetic-RAG-data",
            "tasks": [
                {
                    "type": "ragbits.evaluate.dataset_generator.tasks.corpus_generation:CorpusGenerationStep",
                    "llm": {
                        "provider_type": "ragbits.core.llms.litellm:LiteLLM",
                        "kwargs": {"model_name": "gpt-4o"},
                    },
                    "kwargs": {
                        "num_per_query": 5,
                        "prompt_class": "ragbits.evaluate.dataset_generator.prompts.corpus_generation:BasicCorpusGenerationPrompt",
                    },
                },
                {
                    "type": "ragbits.evaluate.dataset_generator.tasks.text_generation.qa:QueryGenTask",
                    "llm": {
                        "provider_type": "distilabel.llms:OpenAILLM",
                        "kwargs": {"model": "gpt-4o"},
                    },
                    "kwargs": {
                        "prompt_class": "ragbits.evaluate.dataset_generator.prompts.qa:QueryGenPrompt"
                    },
                },
                {
                    "type": "ragbits.evaluate.dataset_generator.tasks.text_generation.qa:AnswerGenTask",
                    "llm": {
                        "provider_type": "distilabel.llms:OpenAILLM",
                        "kwargs": {"model": "gpt-4o"},
                    },
                    "kwargs": {
                        "prompt_class": "ragbits.evaluate.dataset_generator.prompts.qa:BasicAnswerGenPrompt"
                    },
                },
                {
                    "type": "ragbits.evaluate.dataset_generator.tasks.text_generation.qa:PassagesGenTask",
                    "llm": {
                        "provider_type": "distilabel.llms:OpenAILLM",
                        "kwargs": {"model": "gpt-4o"},
                    },
                    "kwargs": {
                        "prompt_class": "ragbits.evaluate.dataset_generator.prompts.qa:PassagesGenPrompt"
                    },
                    "filters": [
                        "ragbits.evaluate.dataset_generator.tasks.filter.dont_know:DontKnowFilter"
                    ],
                },
            ],
        },
    }
)


topics = ["conspiracy theories", "retrival augmented generation"]
pipeline = DatasetGenerationPipeline(pipeline_config)
dataset = pipeline(topics)
print_dataset(dataset)
```

After the succesful execution your console should display output with the followig structure:

```text
0. QUESTION: Is there a theory that suggests the Earth is flat? ANSWER: Yes, the "Flat Earth" theory suggests that the Earth is a flat disc rather than a sphere. PASSAGES: ["The 'Flat Earth' theory suggests that the Earth is a flat disc rather than a sphere."]
1. QUESTION: Was the 1969 moon landing really staged by NASA? ANSWER: No, the 1969 moon landing was not staged by NASA. It was a real event where astronauts from the Apollo 11 mission landed on the moon. The conspiracy theory claiming it was staged is false. PASSAGES: ["The moon landing conspiracy theory falsely claims the 1969 moon landing was staged by NASA."]
2. QUESTION: Is the Earth really flat instead of round? ANSWER: No, the Earth is not flat. Scientific evidence overwhelmingly supports that Earth is an oblate spheroid, which means it is mostly spherical but slightly flattened at the poles and bulging at the equator. PASSAGES: ["scientific evidence overwhelmingly supports that Earth is an oblate spheroid, which means it is mostly spherical but slightly flattened at the poles and bulging at the equator"]
3. QUESTION: Who claims the moon landing was staged in 1969? ANSWER: The moon landing conspiracy theory claims it was staged by NASA in 1969. PASSAGES: ["The moon landing conspiracy theory claims it was staged by NASA in 1969."]
4. QUESTION: How does retrieval augmented generation improve accuracy? ANSWER: Retrieval augmented generation improves accuracy by combining pretrained language models with a retrieval component, allowing the model to access and incorporate relevant information from external data sources during the generation process. PASSAGES: ["Retrieval augmented generation (RAG) combines pretrained language models with a retrieval component to enhance accuracy."]
5. QUESTION: How does retrieval-augmented generation improve response accuracy and relevancy? ANSWER: Retrieval-augmented generation improves response accuracy and relevancy by combining retrieved information with language models. This approach allows the model to incorporate relevant data from external sources, which enhances its ability to generate more accurate and contextually appropriate responses. PASSAGES: ["Retrieval-augmented generation combines retrieved information with language models to improve response accuracy and relevancy."]
6. QUESTION: How does retrieval-augmented generation work to improve response accuracy? ANSWER: Retrieval-augmented generation improves response accuracy by combining information retrieval with text generation. This approach involves retrieving relevant information from a database or other sources and using that information to generate more accurate and informed responses. PASSAGES: ["Retrieval-augmented generation combines information retrieval with text generation to enhance response accuracy."]
7. QUESTION: How does retrieval augmented generation work? ANSWER: Retrieval augmented generation works by combining language models with an external information retrieval system. This approach allows the model to access and incorporate relevant data from an external source, enhancing the generation of responses or content with up-to-date or specific information it might not have inherently. PASSAGES: ["Retrieval augmented generation combines language models with external information retrieval."]
8. QUESTION: How does retrieval-augmented generation improve AI responses? ANSWER: Retrieval-augmented generation improves AI responses by combining the retrieval of relevant documents with text generation, providing enhanced context for the responses. PASSAGES: ["retrieval of relevant documents", "text generation for improved context"]
```

Please note that the results may differ among the runs due to undeterministic nature of LLM.


### From Corpus

The code would be very similar as previously - the only differences are:

* removal of first task from the tasks list in pipeline config
* change of input name from `query` to `chunk`


```python
import json

from datasets import Dataset
from omegaconf import OmegaConf
from ragbits.evaluate.dataset_generator.pipeline import DatasetGenerationPipeline

pipeline_config = OmegaConf.create(
    {
        "input_name": "chunk",
        "pipeline": {
            "name": "synthetic-RAG-data",
            "tasks": [
                {
                    "type": "ragbits.evaluate.dataset_generator.tasks.text_generation.qa:QueryGenTask",
                    "llm": {
                        "provider_type": "distilabel.llms:OpenAILLM",
                        "kwargs": {"model": "gpt-4o"},
                    },
                    "kwargs": {
                        "prompt_class": "ragbits.evaluate.dataset_generator.prompts.qa:QueryGenPrompt"
                    },
                },
                {
                    "type": "ragbits.evaluate.dataset_generator.tasks.text_generation.qa:AnswerGenTask",
                    "llm": {
                        "provider_type": "distilabel.llms:OpenAILLM",
                        "kwargs": {"model": "gpt-4o"},
                    },
                    "kwargs": {
                        "prompt_class": "ragbits.evaluate.dataset_generator.prompts.qa:BasicAnswerGenPrompt"
                    },
                },
                {
                    "type": "ragbits.evaluate.dataset_generator.tasks.text_generation.qa:PassagesGenTask",
                    "llm": {
                        "provider_type": "distilabel.llms:OpenAILLM",
                        "kwargs": {"model": "gpt-4o"},
                    },
                    "kwargs": {
                        "prompt_class": "ragbits.evaluate.dataset_generator.prompts.qa:PassagesGenPrompt"
                    },
                    "filters": [
                        "ragbits.evaluate.dataset_generator.tasks.filter.dont_know:DontKnowFilter"
                    ],
                },
            ],
        },
    }
)


def print_dataset(dataset: Dataset):
    entries = []
    for idx, (question, answer, passage) in enumerate(
        zip(dataset["question"], dataset["basic_answer"], dataset["passages"])
    ):
        entries.append(
            f"{idx}. QUESTION: {question} ANSWER: {answer} PASSAGES: {json.dumps(passage)}"
        )
    print("\r\n".join(entries))


topics = [
    "Neural networks are algorithms capable of data structure recognition",
    "Large Language Models (LLM) are trained to predict the term given the context",
    "Logistic regression is a simpliest form of neural network with no hidden neurons and output activated with sigmoid function",
]
pipeline = DatasetGenerationPipeline(pipeline_config)
dataset = pipeline(topics)
print_dataset(dataset)
```

After succesful execution you should see the following output minus the considerations mentioned in [From Scratch](#from-scratch) section:

```text
0. QUESTION: What are neural networks capable of? ANSWER: Neural networks are capable of data structure recognition. PASSAGES: ["Neural networks are algorithms capable of data structure recognition"]
1. QUESTION: What does LLM stand for? ANSWER: LLM stands for Large Language Models. PASSAGES: ["Large Language Models (LLM)"]
2. QUESTION: What's the simplest form of a neural network? ANSWER: Logistic regression is the simplest form of a neural network, with no hidden neurons and an output activated with a sigmoid function. PASSAGES: ["Logistic regression is a simpliest form of neural network with no hidden neurons and output activated with sigmoid function"]
```


