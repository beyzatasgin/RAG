"""Week 2 interaktif retrieval CLI; henüz LLM cevabı üretmez."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from foundry_runtime import FoundryRuntime, FoundryRuntimeConfig
from retriever import Retriever
from storage import Storage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="runtime_data/rag.db")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--app-data-dir")
    parser.add_argument("--logs-dir")
    parser.add_argument("--allow-download", action="store_true")
    return parser


def run(args: argparse.Namespace) -> int:
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
        retriever = Retriever(storage, client, config.embedding_model_alias)
        while True:
            query = input("Soru ('q' ile çık): ").strip()
            if query.casefold() == "q":
                break
            if not query:
                continue
            for result in retriever.search(query, top_k=args.top_k):
                print(f"[{result.source} / chunk {result.chunk_index}]")
                print(result.content)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
