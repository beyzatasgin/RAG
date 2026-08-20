"""Foundry Local embedding modelini güvenli, varsayılan-offline çalıştır."""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Sequence
from typing import Any, Callable

import numpy as np

from foundry_runtime import FoundryRuntime, FoundryRuntimeConfig


SENTENCES = [
    "Python programlama dili çok kullanışlıdır.",
    "Python yazılım geliştirmede popüler bir dil.",
    "Bugün hava çok güzel ve güneşli.",
    "Yapay zeka ve makine öğrenmesi geleceği şekillendiriyor.",
]
QUERY = "Python ile kod yazmayı seviyorum."


def cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """İki vektör arasındaki cosine benzerliğini hesapla."""
    first = np.asarray(vec1, dtype=float)
    second = np.asarray(vec2, dtype=float)
    denominator = np.linalg.norm(first) * np.linalg.norm(second)
    if denominator == 0:
        raise ValueError("Cosine similarity sıfır vektörle hesaplanamaz.")
    return float(np.dot(first, second) / denominator)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--app-data-dir")
    parser.add_argument("--logs-dir")
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Model cache içinde değilse indirmeye açıkça izin ver.",
    )
    return parser


def _embedding(client: Any, text: str) -> list[float]:
    result = client.generate_embedding(text)
    return list(result.data[0].embedding)


def run_demo(
    args: argparse.Namespace,
    runtime_factory: Callable[[FoundryRuntimeConfig], Any] = FoundryRuntime,
) -> None:
    config = FoundryRuntimeConfig(
        app_name="local-rag-assistant",
        app_data_dir=args.app_data_dir,
        model_cache_dir=args.model_cache_dir,
        logs_dir=args.logs_dir,
    )

    with runtime_factory(config) as runtime:
        client = runtime.get_embedding_client(allow_download=args.allow_download)
        embeddings = [_embedding(client, sentence) for sentence in SENTENCES]
        query_vector = _embedding(client, QUERY)

    vectors = [*embeddings, query_vector]
    if not vectors or not vectors[0]:
        raise RuntimeError("Embedding servisi boş vektör döndürdü.")
    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        raise RuntimeError("Embedding boyutları birbiriyle uyuşmuyor.")

    all_finite = all(math.isfinite(value) for vector in vectors for value in vector)
    similarity = cosine_similarity(query_vector, embeddings[0])
    print(f"embedding_count={len(vectors)}")
    print(f"embedding_dimension={dimension}")
    print(f"all_values_finite={str(all_finite).lower()}")
    print(f"sample_cosine_similarity={similarity:.6f}")
    if not all_finite:
        raise RuntimeError("Embedding sonucu finite olmayan değer içeriyor.")


def main(
    argv: Sequence[str] | None = None,
    runtime_factory: Callable[[FoundryRuntimeConfig], Any] = FoundryRuntime,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_demo(args, runtime_factory)
    except Exception as exc:
        print(f"Embedding smoke başarısız: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
