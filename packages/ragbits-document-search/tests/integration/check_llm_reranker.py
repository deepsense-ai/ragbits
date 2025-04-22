import asyncio
import os
from pathlib import Path

import arxiv

from ragbits.core.llms import LiteLLM
from ragbits.core.sources import LocalFileSource
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import TextElement
from ragbits.document_search.retrieval.rerankers.llm_reranker import LLMReranker

API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-3.5-turbo"
QUERY = "how do bi-encoders work for sentence embeddings"

##### getting docs
print("Finding docs")
search = arxiv.Search(query=QUERY, max_results=20, sort_by=arxiv.SortCriterion.Relevance)

result_list = []

for result in search.results():
    result_dict = {}

    result_dict.update({"title": result.title})
    result_dict.update({"summary": result.summary})

    # Taking the first url provided
    result_dict.update({"article_url": [x.href for x in result.links][0]})
    result_dict.update({"pdf_url": [x.href for x in result.links][1]})
    result_list.append(result_dict)

print("Results amount: ", len(result_list))
print("first result: ", result_list[0])

#### change texts to TextElements sequence
print("changing search results to text elements list")
elements_list = []
for x in result_list:
    content = x["title"] + ": " + x["summary"]
    document_meta = DocumentMeta(document_type=DocumentType.TXT, source=LocalFileSource(path=Path(x["pdf_url"])))
    element = TextElement(content=content, document_meta=document_meta)
    elements_list.append(element)
elements_seq = [elements_list]

#### reranking
print("RERANK STARTS")
litellm = LiteLLM(model_name=OPENAI_MODEL)
reranker = LLMReranker(litellm)

res = asyncio.run(reranker.rerank(elements=elements_seq, query=QUERY))
print(len(res))
print(res[0])
