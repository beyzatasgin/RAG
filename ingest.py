"""Dokümanları güvenli ve idempotent biçimde runtime SQLite DB'ye indeksle."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from foundry_runtime import FoundryRuntime, FoundryRuntimeConfig
from ingestion_service import IngestionService
from storage import Storage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--db-path", default="runtime_data/rag.db")
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=100)
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--app-data-dir")
    parser.add_argument("--logs-dir")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--delete-missing", action="store_true")
    return parser


def run(args: argparse.Namespace) -> int:
    config = FoundryRuntimeConfig(
        app_name="local-rag-assistant",
        app_data_dir=args.app_data_dir,
        model_cache_dir=args.model_cache_dir,
        logs_dir=args.logs_dir,
    )
    storage = Storage(args.db_path)
    service = IngestionService(
        storage,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        model_alias=config.embedding_model_alias,
    )
    with FoundryRuntime(config) as runtime:
        client = runtime.get_embedding_client(allow_download=args.allow_download)
        summary = service.ingest(
            args.data_dir, client, delete_missing=args.delete_missing
        )

    for name in (
        "discovered", "added", "updated", "unchanged", "skipped",
        "failed", "missing", "deleted", "total_chunks",
    ):
        print(f"{name}={getattr(summary, name)}")
    for error in summary.errors:
        print(f"error={error}", file=sys.stderr)
    return 1 if summary.failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except Exception as exc:
        print(f"Ingestion başarısız: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
