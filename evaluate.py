"""Offline retrieval evaluation without an online or LLM judge."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from foundry_runtime import FoundryRuntime, FoundryRuntimeConfig
from retriever import Retriever
from storage import Storage


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    answerable: bool
    sources: tuple[str, ...]
    hit: bool
    reciprocal_rank: float
    no_result: bool
    latency_ms: float


def percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def score_case(case: dict[str, Any], sources: Sequence[str], latency_ms: float) -> CaseResult:
    expected = set(case["expected_sources"])
    first_rank = next((i for i, source in enumerate(sources, 1) if source in expected), None)
    hit = first_rank is not None if case["answerable"] else not sources
    return CaseResult(
        case["id"],
        bool(case["answerable"]),
        tuple(sources),
        hit,
        1.0 / first_rank if first_rank else 0.0,
        not sources,
        latency_ms,
    )


def summarize(results: Sequence[CaseResult]) -> dict[str, Any]:
    answerable = [item for item in results if item.answerable]
    unanswerable = [item for item in results if not item.answerable]
    latencies = [item.latency_ms for item in results]
    return {
        "case_count": len(results),
        "answerable_count": len(answerable),
        "hit_rate_at_k": sum(item.hit for item in answerable) / len(answerable) if answerable else 0.0,
        "mrr": sum(item.reciprocal_rank for item in answerable) / len(answerable) if answerable else 0.0,
        "unanswerable_no_result_rate": sum(item.no_result for item in unanswerable) / len(unanswerable) if unanswerable else 0.0,
        "source_accuracy": sum(item.hit for item in results) / len(results) if results else 0.0,
        "average_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "citation_validity_rate": None,
        "citation_note": "Retrieval-only evaluation; generation citations are not measured.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="evaluation/evaluation_cases.json")
    parser.add_argument("--db-path", default="runtime_data/rag.db")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.2)
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--app-data-dir")
    parser.add_argument("--logs-dir")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--output")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    cases = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    config = FoundryRuntimeConfig(
        app_name="local-rag-assistant",
        model_cache_dir=args.model_cache_dir,
        app_data_dir=args.app_data_dir,
        logs_dir=args.logs_dir,
    )
    storage = Storage(args.db_path)
    results: list[CaseResult] = []
    with FoundryRuntime(config) as runtime:
        client = runtime.get_embedding_client(allow_download=args.allow_download)
        retriever = Retriever(storage, client, config.embedding_model_alias)
        for case in cases:
            started = time.perf_counter()
            retrieved = retriever.search(
                case["question"], top_k=args.top_k, min_score=args.min_score
            )
            elapsed = (time.perf_counter() - started) * 1000
            result = score_case(case, [item.source for item in retrieved], elapsed)
            results.append(result)
            print(
                f"{result.case_id}: hit={result.hit} sources={list(result.sources)} "
                f"latency_ms={result.latency_ms:.2f}"
            )
    payload = {
        "parameters": {"top_k": args.top_k, "min_score": args.min_score},
        "results": [item.__dict__ for item in results],
        "summary": summarize(results),
    }
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    try:
        run(build_parser().parse_args(argv))
    except Exception as exc:
        print(f"Evaluation başarısız: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
