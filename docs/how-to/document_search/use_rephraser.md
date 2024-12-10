# How-To: Use Rephraser
`ragbits-document-search` contains a `QueryRephraser` module that could be used for creating an additional query that
improves the original user query (fixes typos, handles abbreviations etc.). Those two queries are then sent to the document search
module that can use them to find better matches.

This guide will show you how to use `QueryRephraser` and how to create your custom implementation.

## LLM rephraser usage
To use a rephraser within retrival pipeline you need to provide it during `DocumentSearch` construction. In the following example we will use
`LLMQueryRephraser` and default `QueryRephraserPrompt`.
```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM
from ragbits.document_search import DocumentSearch
from ragbits.document_search.retrieval.rephrasers.llm import LLMQueryRephraser
from ragbits.document_search.retrieval.rephrasers.prompts import QueryRephraserPrompt

async def main():
    document_search = DocumentSearch(
        query_rephraser=LLMQueryRephraser(LiteLLM("gpt-3.5-turbo"), QueryRephraserPrompt),
        ...
    )
    results = await document_search.search("<query>")

asyncio.run(main())
```

The next example will show on how to use the same rephraser as independent component:

```python
import asyncio
from ragbits.document_search.retrieval.rephrasers.llm import LLMQueryRephraser
from ragbits.document_search.retrieval.rephrasers.prompts import QueryRephraserPrompt
from ragbits.core.llms.litellm import LiteLLM


async def main():
    rephraser = LLMQueryRephraser(LiteLLM("gpt-3.5-turbo"), QueryRephraserPrompt)
    rephrased = await rephraser.rephrase("Wht tim iz id?")
    print(rephrased)

asyncio.run(main())
```
The console should print:
```text
['What time is it?']
```

To change the prompt you need to create your own class in the following way:
```python
from ragbits.core.prompt import Prompt
from ragbits.document_search.retrieval.rephrasers.llm import QueryRephraserInput

class QueryRephraserPrompt(Prompt[QueryRephraserInput, str]):
    user_prompt = "{{ query }}"
    system_prompt = ("<your_prompt>")
```
You should only change the `system_prompt` as the `user_prompt` will contain a query passed to `DocumentSearch.search()` later.

## Custom rephraser
It is possible to create a custom rephraser by extending the base class:
```python
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser

class CustomRephraser(QueryRephraser):
    async def rephrase(self, query: str) -> list[str]:
        pass
```