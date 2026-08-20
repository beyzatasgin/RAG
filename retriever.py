"""Küçük eğitim veri seti için NumPy full-scan semantic/hybrid retrieval."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from retrieval_utils import cosine_similarity, hybrid_score, keyword_score
from storage import Storage, StorageDataError, validate_vector


@dataclass(frozen=True)
class RetrievalResult:
    source: str
    chunk_index: int
    content: str
    semantic_score: float
    keyword_score: float
    combined_score: float


class RetrievalConfigurationError(ValueError):
    pass


class Retriever:
    def __init__(self, storage: Storage, client: Any, model_alias: str) -> None:
        self.storage = storage
        self.client = client
        self.model_alias = model_alias

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        min_score: float | None = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> list[RetrievalResult]:
        if not isinstance(query, str) or not query.strip():
            raise RetrievalConfigurationError("Query boş olmamalıdır.")
        if not isinstance(top_k, int) or top_k <= 0:
            raise RetrievalConfigurationError("top_k pozitif olmalıdır.")
        if min_score is not None and not math.isfinite(min_score):
            raise RetrievalConfigurationError("min_score finite olmalıdır.")

        rows = self.storage.load_chunks_with_embeddings()
        if not rows:
            return []
        aliases = {str(row["model_alias"]) for row in rows}
        dimensions = {int(row["dimensions"]) for row in rows}
        if len(aliases) != 1 or len(dimensions) != 1:
            raise StorageDataError("DB karışık model alias veya dimension içeriyor.")
        stored_alias = next(iter(aliases))
        stored_dimensions = next(iter(dimensions))
        if stored_alias != self.model_alias:
            raise RetrievalConfigurationError(
                f"Query modeli '{self.model_alias}', DB modeli '{stored_alias}' ile uyuşmuyor."
            )

        query_result = self.client.generate_embedding(query)
        query_vector = validate_vector(
            query_result.data[0].embedding, stored_dimensions
        )
        results: list[RetrievalResult] = []
        for row in rows:
            semantic = cosine_similarity(query_vector, row["vector"])
            keyword = keyword_score(query, str(row["content"]))
            combined = hybrid_score(
                semantic,
                keyword,
                semantic_weight=semantic_weight,
                keyword_weight=keyword_weight,
            )
            result = RetrievalResult(
                source=str(row["source"]),
                chunk_index=int(row["chunk_index"]),
                content=str(row["content"]),
                semantic_score=semantic,
                keyword_score=keyword,
                combined_score=combined,
            )
            if min_score is None or combined >= min_score:
                results.append(result)

        results.sort(
            key=lambda item: (
                -item.combined_score,
                item.source.casefold(),
                item.source,
                item.chunk_index,
            )
        )
        return results[:top_k]
