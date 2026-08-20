"""Small, honest local latency benchmark for retrieval and optional generation."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from chat_utils import collect_streaming_answer, configure_generation
from foundry_runtime import FoundryRuntime, FoundryRuntimeConfig
from prompt_builder import build_prompt
from retriever import Retriever
from storage import Storage


QUESTIONS = (
    "Grand Slam turnuvaları hangileridir?",
    "Wimbledon hangi zeminde oynanır?",
    "Teniste 40-40 skoruna ne ad verilir?",
)


class TimedEmbeddingClient:
    def __init__(self, client: Any):
        self.client = client
        self.last_embedding_ms = 0.0

    def generate_embedding(self, text: str) -> Any:
        started = time.perf_counter()
        result = self.client.generate_embedding(text)
        self.last_embedding_ms = (time.perf_counter() - started) * 1000
        return result


def database_metrics(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        documents = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunks = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    finally:
        connection.close()
    disk = shutil.disk_usage(path.parent)
    return {
        "documents": documents,
        "chunks": chunks,
        "db_bytes": path.stat().st_size,
        "disk_free_bytes": disk.free,
        "ram_pagefile_note": "Collected in final PowerShell system verification, not inferred here.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="runtime_data/rag.db")
    parser.add_argument("--model-cache-dir", required=True)
    parser.add_argument("--app-data-dir")
    parser.add_argument("--logs-dir")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.2)
    parser.add_argument("--include-generation", action="store_true")
    parser.add_argument("--output")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    config = FoundryRuntimeConfig(
        app_name="local-rag-assistant",
        model_cache_dir=args.model_cache_dir,
        app_data_dir=args.app_data_dir,
        logs_dir=args.logs_dir,
    )
    storage = Storage(args.db_path)
    retrieval_runs: list[dict[str, Any]] = []
    runtime_started = time.perf_counter()
    with FoundryRuntime(config) as runtime:
        client = TimedEmbeddingClient(runtime.get_embedding_client(allow_download=False))
        initialize_ms = (time.perf_counter() - runtime_started) * 1000
        retriever = Retriever(storage, client, config.embedding_model_alias)
        first_results = None
        for question in QUESTIONS:
            started = time.perf_counter()
            results = retriever.search(question, top_k=args.top_k, min_score=args.min_score)
            total_ms = (time.perf_counter() - started) * 1000
            first_results = first_results or results
            retrieval_runs.append(
                {
                    "question": question,
                    "embedding_ms": client.last_embedding_ms,
                    "retrieval_without_embedding_ms": max(0.0, total_ms - client.last_embedding_ms),
                    "total_retrieval_ms": total_ms,
                    "sources": [item.source for item in results],
                }
            )

    generation = None
    if args.include_generation and first_results:
        prompt_started = time.perf_counter()
        prompt = build_prompt(QUESTIONS[0], first_results, max_output_tokens=192)
        prompt_ms = (time.perf_counter() - prompt_started) * 1000
        chat_started = time.perf_counter()
        with FoundryRuntime(config) as runtime:
            chat_client = runtime.get_chat_client(allow_download=False)
            configure_generation(chat_client, max_tokens=192, temperature=0.0, completions=1)
            generation_started = time.perf_counter()
            answer = collect_streaming_answer(chat_client, prompt.messages)
            generation_ms = (time.perf_counter() - generation_started) * 1000
        generation = {
            "prompt_ms": prompt_ms,
            "chat_runtime_and_generation_ms": (time.perf_counter() - chat_started) * 1000,
            "generation_ms": generation_ms,
            "answer_preview": answer[:200],
            "verified_sources": [item.result.source for item in prompt.contexts],
            "quality_scored": False,
        }

    payload = {
        "cold_warm_classification": "not claimed; one process run only",
        "embedding_model": config.embedding_model_alias,
        "chat_model": config.chat_model_alias,
        "runtime_initialize_and_embedding_load_ms": initialize_ms,
        "retrieval_runs": retrieval_runs,
        "generation": generation,
        "database": database_metrics(Path(args.db_path)),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    try:
        run(build_parser().parse_args(argv))
    except Exception as exc:
        print(f"Benchmark başarısız: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
