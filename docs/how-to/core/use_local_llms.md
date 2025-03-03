# How to use local LLMs with Ragbits
This guide explains how to set up and use local LLMs in Ragbits. It covers installation, model initialization, and configuration options.

## Setting up and using a local models
To use a local LLMs, you need to install the 'local' extra requirements:

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