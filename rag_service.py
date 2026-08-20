"""Grounded retrieval-and-generation orchestration for the local RAG app."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Any

from chat_utils import ChatResponseError, collect_streaming_answer, configure_generation
from citations import validate_citations
from prompt_builder import (
    DEFAULT_CONTEXT_BUDGET,
    NO_INFORMATION_ANSWER,
    PromptBuildError,
    build_prompt,
)
from retriever import RetrievalResult


class RagServiceError(RuntimeError):
    """Base error for a user-facing RAG operation."""


class RagRetrievalError(RagServiceError):
    """Retrieval failed."""


class RagGenerationError(RagServiceError):
    """Prompt construction or local generation failed."""


@dataclass(frozen=True)
class RagSource:
    label: str
    source: str
    chunk_index: int
    semantic_score: float
    combined_score: float


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    sources: tuple[RagSource, ...]
    retrieved_count: int
    used_context_count: int
    insufficient_context: bool
    valid_citations: tuple[str, ...] = ()
    unknown_citations: tuple[str, ...] = ()

    @property
    def has_valid_inline_citation(self) -> bool:
        """Whether the model answer contains at least one allowed source label."""

        return bool(self.valid_citations)


class RagService:
    """Coordinate a retriever and a Foundry Local streaming chat client."""

    def __init__(self, retriever: Any | None = None, chat_client: Any | None = None):
        self.retriever = retriever
        self.chat_client = chat_client

    def retrieve(
        self, question: str, *, top_k: int = 3, min_score: float | None = None
    ) -> list[RetrievalResult]:
        if not question.strip():
            raise ValueError("Soru boş olamaz.")
        if self.retriever is None:
            raise RagRetrievalError("Retriever yapılandırılmadı.")
        try:
            return list(
                self.retriever.search(question, top_k=top_k, min_score=min_score)
            )
        except Exception as exc:
            raise RagRetrievalError("Doküman araması başarısız oldu.") from exc

    def generate_from_results(
        self,
        question: str,
        results: Sequence[RetrievalResult],
        *,
        context_budget: int = DEFAULT_CONTEXT_BUDGET,
        max_output_tokens: int = 192,
    ) -> RagAnswer:
        if not question.strip():
            raise ValueError("Soru boş olamaz.")
        if not results:
            return RagAnswer(
                answer=NO_INFORMATION_ANSWER,
                sources=(),
                retrieved_count=0,
                used_context_count=0,
                insufficient_context=True,
            )
        if self.chat_client is None:
            raise RagGenerationError("Chat istemcisi yapılandırılmadı.")

        unique_results: list[RetrievalResult] = []
        seen: set[tuple[str, int]] = set()
        for result in results:
            key = (result.source, result.chunk_index)
            if key not in seen:
                unique_results.append(result)
                seen.add(key)

        try:
            prompt = build_prompt(
                question,
                unique_results,
                context_budget=context_budget,
                max_output_tokens=max_output_tokens,
            )
            configure_generation(
                self.chat_client,
                max_tokens=max_output_tokens,
                temperature=0.0,
                completions=1,
            )
            answer = collect_streaming_answer(self.chat_client, prompt.messages)
        except (PromptBuildError, ChatResponseError) as exc:
            raise RagGenerationError(str(exc)) from exc
        except Exception as exc:
            raise RagGenerationError("Foundry Local cevap üretimi başarısız oldu.") from exc

        labels = tuple(item.label for item in prompt.contexts)
        citation_status = validate_citations(answer, labels)
        sources = tuple(
            RagSource(
                label=item.label,
                source=item.result.source,
                chunk_index=item.result.chunk_index,
                semantic_score=item.result.semantic_score,
                combined_score=item.result.combined_score,
            )
            for item in prompt.contexts
        )
        return RagAnswer(
            answer=answer,
            sources=sources,
            retrieved_count=len(results),
            used_context_count=len(prompt.contexts),
            insufficient_context=False,
            valid_citations=citation_status.valid,
            unknown_citations=citation_status.unknown,
        )

    def answer(
        self,
        question: str,
        *,
        top_k: int = 3,
        min_score: float | None = None,
        context_budget: int = DEFAULT_CONTEXT_BUDGET,
        max_output_tokens: int = 192,
    ) -> RagAnswer:
        results = self.retrieve(question, top_k=top_k, min_score=min_score)
        return self.generate_from_results(
            question,
            results,
            context_budget=context_budget,
            max_output_tokens=max_output_tokens,
        )
