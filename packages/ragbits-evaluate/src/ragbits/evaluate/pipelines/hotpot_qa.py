import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from typing_extensions import Self

from ragbits.agents import Agent
from ragbits.core.llms.base import LLM, LLMClientOptionsT, LLMResponseWithMetadata, Usage
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.evaluate.pipelines.base import EvaluationData, EvaluationPipeline, EvaluationResult


class HotpotQAData(EvaluationData):
    """
    Represents a single HotpotQA example.
    """

    id: str
    question: str
    reference_answer: str
    qtype: str
    level: str
    reference_context: list[str]


@dataclass
class HotpotQAResult(EvaluationResult):
    """
    Represents the result of evaluating a single HotpotQA example.
    """

    id: str
    predicted_result: str
    reference_answer: str
    question: str
    qtype: str
    level: str
    predicted_parsed: str | None = None
    reference_normalized: str | None = None
    em_value: float = 0.0
    f1_value: float = 0.0


class HotpotQAPipeline(
    EvaluationPipeline[
        Agent[LLMClientOptionsT, None, str] | LLM[LLMClientOptionsT],
        HotpotQAData,
        HotpotQAResult,
    ]
):
    """
    HotpotQA evaluation pipeline with simple RAG ingestion per batch and multi-hop retrieval.
    """

    def __init__(
        self,
        evaluation_target: Agent[LLMClientOptionsT, None, str] | LLM[LLMClientOptionsT],
        *,
        retriever: DocumentSearch,
        hops: int = 3,
        per_example_log_file: Path | None = None,
        extended_logs: bool = False,
        parse_answer_fn: Callable[[str], str] | None = None,
        question_generation_prompt_fn: Callable[[str, str], str] | None = None,
        retrieval_k: int = 3,
        element_max_chars: int = 500,
        hop_context_max_chars: int = 1200,
    ) -> None:
        super().__init__(evaluation_target=evaluation_target)
        self.retriever = retriever
        self.hops = max(1, min(hops, 5))
        self.per_example_log_file = per_example_log_file
        self.extended_logs = extended_logs
        self.parse_answer_fn = parse_answer_fn
        self.question_generation_prompt_fn = question_generation_prompt_fn
        self.retrieval_k = max(1, int(retrieval_k))
        self.element_max_chars = max(50, int(element_max_chars))
        self.hop_context_max_chars = max(100, int(hop_context_max_chars))
        self._init_log_file()

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """Create pipeline from config.
        Attempts Agent first, falls back to raw LLM construction.
        """
        if "evaluation_target" not in config:
            try:
                config["evaluation_target"] = Agent.from_config(config)
            except Exception:
                config["evaluation_target"] = LLM.from_config(config)
        config["retriever"] = DocumentSearch.from_config(config["document_search"])
        config["hops"] = int(config.get("hops", 3))
        config["retrieval_k"] = int(config.get("retrieval_k", 3))
        config["element_max_chars"] = int(config.get("element_max_chars", 500))
        config["hop_context_max_chars"] = int(config.get("hop_context_max_chars", 1200))
        return super().from_config(config)

    async def _ingest_documents(self, data: Iterable[HotpotQAData]) -> None:
        """Ingest all documents from the data."""
        documents: list[DocumentMeta] = []
        for row in data:
            for content in row.reference_context:
                documents.append(DocumentMeta.from_literal(content))
        await self.retriever.ingest(documents)

    async def _perform_multihop_retrieval(self, example: HotpotQAData) -> tuple[str, list[dict]]:
        """Perform multi-hop retrieval and return accumulated context and hop logs."""
        accumulated_context: list[str] = []
        hop_logs: list[dict] = []
        last_query = example.question
        for hop_idx in range(self.hops):
            elements = await self.retriever.search(last_query)
            text_parts: list[str] = []
            consumed = 0
            for element in elements[: self.retrieval_k]:
                content = getattr(element, "content", "") if hasattr(element, "content") else ""
                if isinstance(content, str) and content:
                    snippet = content.strip().replace("\n\n", "\n")[: self.element_max_chars]
                    budget = max(0, self.hop_context_max_chars - consumed)
                    take = snippet[:budget]
                    if take:
                        text_parts.append(take)
                        consumed += len(take)
                    if consumed >= self.hop_context_max_chars:
                        break
            hop_text = "\n\n".join(text_parts)
            hop_logs.append({"hop": hop_idx + 1, "question": last_query, "retrieved": hop_text})
            if hop_text:
                accumulated_context.append(hop_text)
                # generate a new question for the next hop
                if hop_idx < self.hops - 1:
                    last_query = await self._generate_next_question(
                        original_question=example.question,
                        accumulated_context="\n\n".join(accumulated_context),
                    )
            else:
                break
        return "\n\n".join(accumulated_context), hop_logs

    async def _answer_with_retrieval(self, example: HotpotQAData) -> tuple[str, Usage, list, list[dict], dict]:
        """Answer a question with multi-hop retrieval."""
        full_context, hop_logs = await self._perform_multihop_retrieval(example)
        prompt_input = example.question if not full_context else f"{example.question}\n\nContext:\n{full_context}"

        if self.extended_logs:
            content, dbg = await self._generate_with_debug(prompt_input)
            usage = cast(Usage, (dbg or {}).get("usage") or Usage())
            tool_calls = cast(list, (dbg or {}).get("tool_calls") or [])
            metadata = cast(dict, (dbg or {}).get("metadata") or {})
        else:
            content, usage, tool_calls = await self._generate_answer(prompt_input)
            metadata = {}

        return str(content), usage, tool_calls, hop_logs, metadata

    async def __call__(self, data: Iterable[HotpotQAData]) -> Iterable[HotpotQAResult]:
        """Ingest contexts, perform multi-hop retrieval, and answer HotpotQA questions."""
        data_list = list(data)
        await self._ingest_documents(data_list)

        results: list[HotpotQAResult] = []
        for row in data_list:
            try:
                predicted_text, usage, tool_calls, hop_logs, metadata = await self._answer_with_retrieval(row)
            except Exception:
                predicted_text = ""
                usage = Usage()
                tool_calls = []
                hop_logs = []
                metadata = {}
            predicted_extracted = self._parse_answer(predicted_text)
            ref_norm = self._normalize(row.reference_answer)

            # Compute normalized fields and sample metrics once
            em = 1.0 if self._normalize(predicted_extracted) == ref_norm else 0.0
            f1 = self._f1(self._normalize(predicted_extracted), ref_norm)

            result = HotpotQAResult(
                id=row.id,
                predicted_result=predicted_text,
                reference_answer=row.reference_answer,
                question=row.question,
                qtype=row.qtype,
                level=row.level,
                predicted_parsed=self._normalize(predicted_extracted),
                reference_normalized=ref_norm,
                em_value=float(em),
                f1_value=float(f1),
            )
            results.append(result)

            ext_log_str = None
            if self.extended_logs:
                ext_log_str = json.dumps(
                    [
                        {
                            "usage": usage,
                            "tool_calls": tool_calls,
                            "hops": hop_logs,
                            "metadata": metadata,
                        }
                    ],
                    ensure_ascii=False,
                    default=str,
                )
            self._log_example(
                row=row,
                predicted_text=predicted_text,
                predicted_extracted=predicted_extracted,
                em=result.em_value,
                f1=result.f1_value,
                extended_log=ext_log_str,
            )

        return results

    def _init_log_file(self) -> None:
        """Ensure the per-example log file exists if logging is enabled."""
        if self.per_example_log_file is None:
            return
        self.per_example_log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.per_example_log_file, "w", encoding="utf-8") as _:
            pass

    def _log_example(
        self,
        *,
        row: HotpotQAData,
        predicted_text: str,
        predicted_extracted: str,
        em: float,
        f1: float,
        extended_log: str | None = None,
    ) -> None:
        """Append a single NDJSON record for debugging if enabled."""
        if self.per_example_log_file is None:
            return
        record: dict[str, object] = {
            "id": row.id,
            "question": row.question,
            "reference": row.reference_answer,
            "predicted": predicted_text,
            "predicted_extracted": predicted_extracted,
            "type": row.qtype,
            "level": row.level,
            "em": float(em),
            "f1": float(f1),
        }
        record["extended_debug_logging"] = extended_log or "[]"
        with open(self.per_example_log_file, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _parse_answer(self, text: str) -> str:
        """Optionally parse final answer from text using provided function.
        If no parser provided, returns the original text.
        """
        if self.parse_answer_fn is None:
            return text
        try:
            return self.parse_answer_fn(text)
        except Exception as exc:
            import logging as _logging

            _logging.getLogger(__name__).debug("Answer parse error: %s", exc)
            return text

    async def _generate_answer(self, prompt: str) -> tuple[str, Usage, list]:
        """Generate final answer from Agent or raw LLM and capture usage and tool calls."""
        target = self.evaluation_target
        if isinstance(target, Agent):
            res = await target.run(prompt)
            return str(res.content), res.usage, (res.tool_calls or [])

        resp = cast(LLMResponseWithMetadata[str], await target.generate_with_metadata(prompt))
        return str(resp.content), (resp.usage or Usage()), []

    async def _generate_with_debug(self, prompt: str) -> tuple[str, dict | None]:
        """Generate answer and capture tool/history/usage for logging (as raw content)."""
        target = self.evaluation_target
        if isinstance(target, Agent):
            res = await target.run(prompt)
            dbg = {
                "history": res.history,
                "tool_calls": res.tool_calls,
                "usage": res.usage,
                "metadata": res.metadata,
            }
            return str(res.content), dbg
        resp = await target.generate(prompt)
        return str(resp), None

    async def _generate_next_question(self, original_question: str, accumulated_context: str) -> str:
        """Generate a new follow-up question based on the original question and accumulated context."""
        if self.question_generation_prompt_fn is None:
            # default: simple concatenation
            return f"{original_question}\n\nContext so far:\n{accumulated_context}"

        question_generation_prompt = self.question_generation_prompt_fn(original_question, accumulated_context)

        target = self.evaluation_target
        if isinstance(target, Agent):
            resp = await target.llm.generate(question_generation_prompt)
            return str(resp).strip()
        resp = await target.generate(question_generation_prompt)
        return str(resp).strip()

    @staticmethod
    def _normalize(text: str) -> str:
        """Basic normalization for answer equality checks: lowercase, strip spaces."""
        return "".join(ch.lower() for ch in (text or "").strip() if not ch.isspace())

    @staticmethod
    def _f1(prediction: str, ground_truth: str) -> float:
        import re as _re
        from collections import Counter as _Counter

        def tokens(value: str) -> list[str]:
            value = (value or "").lower()
            value = _re.sub(r"[^a-z0-9\s]", " ", value)
            value = _re.sub(r"\b(a|an|the)\b", " ", value)
            value = _re.sub(r"\s+", " ", value).strip()
            return value.split()

        pred_tokens = tokens(prediction)
        gt_tokens = tokens(ground_truth)
        if not pred_tokens and not gt_tokens:
            return 1.0
        if not pred_tokens or not gt_tokens:
            return 0.0

        pred_counts = _Counter(pred_tokens)
        gt_counts = _Counter(gt_tokens)
        common = sum((pred_counts & gt_counts).values())
        if common == 0:
            return 0.0

        precision = common / len(pred_tokens)
        recall = common / len(gt_tokens)
        return 2 * precision * recall / (precision + recall)
