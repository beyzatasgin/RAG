"""Model ve veritabanından bağımsız retrieval hesaplamaları."""

from collections.abc import Sequence
import math

import numpy as np


def cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """İki eş boyutlu vektörün cosine similarity değerini hesaplar."""
    v1 = np.asarray(vec1, dtype=np.float64)
    v2 = np.asarray(vec2, dtype=np.float64)

    if v1.ndim != 1 or v2.ndim != 1:
        raise ValueError("Vektörler tek boyutlu olmalıdır.")
    if v1.size == 0 or v2.size == 0:
        raise ValueError("Vektörler boş olmamalıdır.")
    if v1.shape != v2.shape:
        raise ValueError("Vektörlerin boyutları aynı olmalıdır.")
    if not np.all(np.isfinite(v1)) or not np.all(np.isfinite(v2)):
        raise ValueError("Vektörler yalnızca sonlu sayılar içermelidir.")

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0

    result = np.dot(v1, v2) / (norm1 * norm2)
    return float(np.clip(result, -1.0, 1.0))


def keyword_score(query: str, content: str) -> float:
    """Benzersiz sorgu kelimelerinin substring eşleşme oranını döndürür.

    Tekrarlanan sorgu kelimeleri bir kez değerlendirilir. Boş sorgu veya
    boş içerik için skor sıfırdır.
    """
    query_words = set(query.lower().split())
    if not query_words or not content:
        return 0.0

    content_lower = content.lower()
    matches = sum(1 for word in query_words if word in content_lower)
    return matches / len(query_words)


def hybrid_score(
    semantic_score: float,
    keyword_match_score: float,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> float:
    """Toplamı 1 olan ağırlıklarla iki sonlu skoru birleştirir."""
    scores = (semantic_score, keyword_match_score)
    if not all(math.isfinite(score) for score in scores):
        raise ValueError("Semantic ve keyword skorları sonlu olmalıdır.")

    weights = (semantic_weight, keyword_weight)
    if not all(math.isfinite(weight) and 0 <= weight <= 1 for weight in weights):
        raise ValueError("Hibrit skor ağırlıkları 0 ile 1 arasında olmalıdır.")
    if not math.isclose(sum(weights), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("Hibrit skor ağırlıklarının toplamı 1 olmalıdır.")

    return semantic_weight * semantic_score + keyword_weight * keyword_match_score
