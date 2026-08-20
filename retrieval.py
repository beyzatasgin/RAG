"""Normalize runtime DB üzerinde semantic/hybrid retrieval CLI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from foundry_runtime import FoundryRuntime, FoundryRuntimeConfig
from retriever import Retriever
from storage import Storage


def get_top_chunks(
    query,
    client,
    top_k=3,
    *,
    db_path="runtime_data/rag.db",
    model_alias="qwen3-embedding-0.6b",
    min_score=None,
):
    """Eski çağrı noktaları için yeni retriever'a ince uyumluluk köprüsü."""
    return Retriever(Storage(db_path), client, model_alias).search(
        query, top_k=top_k, min_score=min_score
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="runtime_data/rag.db")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-score", type=float)
    parser.add_argument("--semantic-weight", type=float, default=0.7)
    parser.add_argument("--keyword-weight", type=float, default=0.3)
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--app-data-dir")
    parser.add_argument("--logs-dir")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser


def search_with_runtime(args: argparse.Namespace):
    config = FoundryRuntimeConfig(
        app_name="local-rag-assistant",
        app_data_dir=args.app_data_dir,
        model_cache_dir=args.model_cache_dir,
        logs_dir=args.logs_dir,
    )
    storage = Storage(args.db_path)
    storage.initialize_schema()
    with FoundryRuntime(config) as runtime:
        client = runtime.get_embedding_client(allow_download=args.allow_download)
        return Retriever(storage, client, config.embedding_model_alias).search(
            args.query,
            top_k=args.top_k,
            min_score=args.min_score,
            semantic_weight=args.semantic_weight,
            keyword_weight=args.keyword_weight,
        )


def run(args: argparse.Namespace) -> int:
    results = search_with_runtime(args)
    for rank, result in enumerate(results, start=1):
        print(f"[{rank}] source={result.source} chunk={result.chunk_index}")
        if args.debug:
            print(
                f"semantic={result.semantic_score:.6f} "
                f"keyword={result.keyword_score:.6f} "
                f"combined={result.combined_score:.6f}"
            )
        print(result.content)
    print(f"result_count={len(results)}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except Exception as exc:
        print(f"Retrieval başarısız: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
