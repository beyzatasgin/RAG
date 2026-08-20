"""Doküman keşfi, chunking, embedding ve atomik SQLite yazımı."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chunking import chunk_text
from storage import Storage, StorageDataError, validate_vector


SUPPORTED_SUFFIXES = {".txt", ".md"}


@dataclass
class IngestionSummary:
    discovered: int = 0
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0
    missing: int = 0
    deleted: int = 0
    total_chunks: int = 0
    processed_sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def discover_documents(data_dir: Path) -> list[Path]:
    if not data_dir.is_dir():
        raise ValueError(f"Doküman dizini bulunamadı: {data_dir}")
    return sorted(
        (
            path
            for path in data_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        ),
        key=lambda path: (path.name.casefold(), path.name),
    )


def _generate_embeddings(client: Any, chunks: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for content in chunks:
        result = client.generate_embedding(content)
        vectors.append(validate_vector(result.data[0].embedding))
    if not vectors:
        raise StorageDataError("Boş belge için embedding üretilemez.")
    dimensions = len(vectors[0])
    if any(len(vector) != dimensions for vector in vectors):
        raise StorageDataError("Batch embedding boyutları birbiriyle uyuşmuyor.")
    return vectors


class IngestionService:
    def __init__(
        self,
        storage: Storage,
        *,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        model_alias: str = "qwen3-embedding-0.6b",
    ) -> None:
        # Config hatalarını herhangi bir dosya/DB işleminden önce üret.
        chunk_text("", chunk_size, chunk_overlap)
        self.storage = storage
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model_alias = model_alias

    def ingest(
        self,
        data_dir: str | Path,
        client: Any,
        *,
        delete_missing: bool = False,
    ) -> IngestionSummary:
        root = Path(data_dir)
        files = discover_documents(root)
        summary = IngestionSummary(discovered=len(files))
        self.storage.initialize_schema()
        discovered_sources = {path.name for path in files}

        for path in files:
            source = path.name
            summary.processed_sources.append(source)
            try:
                raw = path.read_bytes()
                content = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                summary.failed += 1
                summary.errors.append(f"{source}: {type(exc).__name__}: {exc}")
                continue

            if not content.strip():
                summary.skipped += 1
                continue

            content_hash = hashlib.sha256(raw).hexdigest()
            existing = self.storage.get_document(source)
            if existing is not None and existing["content_hash"] == content_hash:
                summary.unchanged += 1
                continue

            try:
                chunks = chunk_text(content, self.chunk_size, self.chunk_overlap)
                vectors = _generate_embeddings(client, chunks)
                self.storage.replace_document(
                    source=source,
                    content_hash=content_hash,
                    file_size=len(raw),
                    chunks=chunks,
                    embeddings=vectors,
                    model_alias=self.model_alias,
                )
            except Exception as exc:
                summary.failed += 1
                summary.errors.append(f"{source}: {type(exc).__name__}: {exc}")
                continue

            if existing is None:
                summary.added += 1
            else:
                summary.updated += 1

        missing = sorted(set(self.storage.list_sources()) - discovered_sources)
        summary.missing = len(missing)
        if delete_missing:
            summary.deleted = self.storage.delete_sources(missing)
        summary.total_chunks = self.storage.counts()[1]
        return summary
