# How-To: Use local or self-hosted LLMs
This guide explains how to set up and use local LLMs in Ragbits. It covers installation, model initialization, and configuration options.

> ℹ️ **NOTE**
>
> Local implementation is not dedicated for production. Use it only in experiments / evaluation

## Setting up and using a local models
To use local LLMs, you need to install the 'local' extra requirements:

```bash
pip install ragbits[local]
```

Local LLMs in Ragbits use [`AutoModelForCausalLM`](https://huggingface.co/docs/transformers/model_doc/auto#transformers.AutoModelForCausalLM) with `device_map="auto"`. This setting automatically fills all available space on the GPU(s) first, then the CPU, and finally the hard drive (the absolute slowest option) if there is still not enough memory. See the [Hugging Face documentation](https://huggingface.co/docs/transformers/model_doc/auto#transformers.AutoModelForCausalLM) for more details.

Using a local model is as simple as:
```python
from ragbits.core.llms.local import LocalLLM

local_llm = LocalLLM(model_name="mistral-7b")
response = local_llm.generate("Tell me a science fact.")
print(response)
```

The `model_name` parameter can be specified in several ways:
- a string representing the model ID of a pretrained model hosted on Hugging Face Hub, such as `"mistral-7b"`,
- a path to a directory containing a model, e.g., `"./my_model_directory/"`,
- a path or URL to a saved configuration JSON file, e.g., `"./my_model_directory/configuration.json"`.

### Local LLM Options

The `LocalLLMOptions` class provides a set of parameters to fine-tune the behavior of local LLMs. These options described in the [HuggingFace documentation](https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client#huggingface_hub.InferenceClient.text_generation).

Example usage:
```python
from ragbits.core.llms.local import LocalLLM, LocalLLMOptions

options = LocalLLMOptions(
    temperature=0.7,
    max_new_tokens=100,
    do_sample=True,
    top_p=0.9
)

local_llm = LocalLLM(model_name="mistral-7b", default_options=options)
response = local_llm.generate("Explain quantum mechanics in simple terms.")
print(response)
```

## Local LLM servers
Ragbits also supports local LLM servers, you can use [llama.cpp](https://github.com/ggml-org/llama.cpp), [vllm](https://docs.vllm.ai/en/latest/) or other servers that are supported by [LiteLLM](https://docs.litellm.ai/docs/providers).

### Using llama.cpp
To use llama.cpp you first need to install it. You can do this by [building the sources](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) or by [using a package manager](https://github.com/ggml-org/llama.cpp/blob/master/docs/install.md).
The next step is downloading one of the models in gguf format. You can find a list of available models [here](https://huggingface.co/models?library=gguf&sort=trending).
After that you can start the llama.cp server with the following command:
```bash
./llama-server -m <model_name>.gguf -c 2048 -t 8 --api-key <api_key>
```
> ℹ️ **NOTE**
>
> The api key is required to use on the server, LiteLLM expects it from an OpenAI client.

Now you can use the server in Ragbits:
```python
import asyncio

from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt.base import SimplePrompt


async def main() -> None:
    llm = LiteLLM(model_name="openai/local", api_key="<api_key>", base_url="http://127.0.0.1:8080")
    prompt = SimplePrompt("Tell me a joke about software developers.")
    response = await llm.generate(prompt)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
```

### Using vllm
To use vllm you first need to install it. You can do this by following the [installation instructions](https://docs.vllm.ai/en/latest/getting_started/installation/index.html).

With the vllm installed you can start the server with the following command:
```bash
vllm serve <model_name>
```
vllm will download the model if it is not already present in the cache. You can find a list of available models [here](https://docs.vllm.ai/en/latest/models/supported_models.html).

Now you can use the server in Ragbits:
```python
import asyncio

from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt.base import SimplePrompt


async def main() -> None:
    llm = LiteLLM(model_name="hosted_vllm/<model_name>", base_url="http://127.0.0.1:8000/v1")
    prompt = SimplePrompt("Tell me a joke about software developers.")
    response = await llm.generate(prompt)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
```

#### Using vllm as embedding server
To use vllm as embedding server you need to start the server with the following command (make sure model supports embedding):
```bash
vllm serve <model_name> --task embed
```

After that you can send requests the server in Ragbits:
```python
import asyncio

from ragbits.core.embeddings.litellm import LiteLLMEmbedder


async def main() -> None:
    embedder = LiteLLMEmbedder(model="hosted_vllm/<model_name>", api_base="http://127.0.0.1:8000/v1")
    embeddings = await embedder.embed_text(["Hello"])
    print(len(embeddings[0]))


if __name__ == "__main__":
    asyncio.run(main())
```