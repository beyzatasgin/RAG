"""Conservative offline-readiness check; it does not prove network isolation."""

from __future__ import annotations

import argparse
import sqlite3
from collections.abc import Sequence
from pathlib import Path


FORBIDDEN_PATTERNS = {
    "Azure endpoint": "azure.com",
    "OpenAI cloud endpoint": "api.openai.com",
    "API key": "api_key",
    "Ollama endpoint": "localhost:11434",
    "Hugging Face API": "api-inference.huggingface.co",
}


def scan_runtime_sources(root: Path) -> list[str]:
    findings: list[str] = []
    excluded = {".venv", ".git", "recovery", "runtime_data", "tests"}
    for path in root.rglob("*.py"):
        if any(part in excluded for part in path.parts):
            continue
        if path.name == Path(__file__).name:
            # This checker necessarily contains the patterns it searches for.
            continue
        text = path.read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.casefold() in text.casefold():
                findings.append(f"{label}: {path.as_posix()}")
    return findings


def check_db(path: Path) -> tuple[str, str]:
    if not path.is_file():
        return "FAIL", "Runtime DB bulunamadı."
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        metadata = connection.execute(
            "SELECT COUNT(DISTINCT model_alias), COUNT(DISTINCT dimensions) FROM embeddings"
        ).fetchone()
    finally:
        connection.close()
    if integrity != "ok" or metadata != (1, 1):
        return "FAIL", f"DB integrity={integrity}, embedding metadata={metadata}"
    return "PASS", "DB integrity ve embedding alias/dimension tutarlı."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="runtime_data/rag.db")
    parser.add_argument("--model-cache-dir", required=True)
    return parser


def run(args: argparse.Namespace) -> str:
    cache = Path(args.model_cache_dir)
    expected = ("qwen3-embedding-0.6b-generic-cpu-1", "qwen3-1.7b-generic-cpu-2")
    cached_names = {path.name for path in cache.rglob("*") if path.is_dir()}
    model_status = "PASS" if all(name in cached_names for name in expected) else "FAIL"
    db_status, db_detail = check_db(Path(args.db_path))
    findings = scan_runtime_sources(Path("."))
    source_status = "FAIL" if findings else "PASS"
    print(f"{model_status}: Hedef cached modeller")
    print(f"{db_status}: {db_detail}")
    print(f"{source_status}: Cloud/API runtime taraması" + (f" — {findings}" if findings else ""))
    print("PASS: CLI ve UI download varsayılanı kapalı; allow_download yalnızca explicit ilk kurulum yoludur.")
    print("WARN: SDK katalog metadata güncellemesi ağsızlık kanıtı değildir.")
    print("WARN: Proxy testi kesin izolasyon değildir; ağ adaptörü kapalı manuel test ayrıca yapılmalıdır.")
    overall = "FAIL" if "FAIL" in {model_status, db_status, source_status} else "WARN"
    print(f"OVERALL={overall}")
    return overall


def main(argv: Sequence[str] | None = None) -> int:
    return 1 if run(build_parser().parse_args(argv)) == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
