"""Normalize Week 2 SQLite şeması ve güvenli veri erişimi."""

from __future__ import annotations

import json
import hashlib
import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence


SCHEMA_VERSION = "1"


class StorageDataError(ValueError):
    """SQLite içindeki embedding verisi geçersiz olduğunda üretilir."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_vector(vector: Sequence[float], dimensions: int | None = None) -> list[float]:
    if isinstance(vector, (str, bytes)):
        raise StorageDataError("Embedding bir sayı listesi olmalıdır.")
    try:
        values = [float(value) for value in vector]
    except (TypeError, ValueError) as exc:
        raise StorageDataError("Embedding yalnızca sayılar içermelidir.") from exc
    if not values:
        raise StorageDataError("Embedding boş olmamalıdır.")
    if dimensions is not None and (dimensions <= 0 or len(values) != dimensions):
        raise StorageDataError("Embedding dimension metadata ile uyuşmuyor.")
    if not all(math.isfinite(value) for value in values):
        raise StorageDataError("Embedding yalnızca finite değerler içermelidir.")
    return values


def decode_vector(raw: str, dimensions: int) -> list[float]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise StorageDataError("Embedding JSON verisi bozuk.") from exc
    if not isinstance(value, list):
        raise StorageDataError("Embedding JSON bir liste olmalıdır.")
    return validate_vector(value, dimensions)


class Storage:
    def __init__(self, db_path: str | Path = "runtime_data/rag.db") -> None:
        self.db_path = Path(db_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize_schema(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    source TEXT NOT NULL UNIQUE,
                    content_hash TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    indexed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(document_id, chunk_index)
                );
                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id INTEGER PRIMARY KEY,
                    model_alias TEXT NOT NULL,
                    dimensions INTEGER NOT NULL,
                    vector TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
                );
                """
            )
            connection.execute(
                "INSERT INTO schema_info(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("schema_version", SCHEMA_VERSION),
            )

    def get_document(self, source: str) -> sqlite3.Row | None:
        with self.connection() as connection:
            return connection.execute(
                "SELECT id, source, content_hash, file_size, indexed_at "
                "FROM documents WHERE source = ?",
                (source,),
            ).fetchone()

    def list_sources(self) -> list[str]:
        with self.connection() as connection:
            return [
                row["source"]
                for row in connection.execute(
                    "SELECT source FROM documents ORDER BY source"
                )
            ]

    def replace_document(
        self,
        *,
        source: str,
        content_hash: str,
        file_size: int,
        chunks: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        model_alias: str,
    ) -> None:
        if len(chunks) != len(embeddings) or not chunks:
            raise ValueError("Her chunk için bir embedding bulunmalıdır.")
        validated = [validate_vector(vector) for vector in embeddings]
        dimensions = len(validated[0])
        if any(len(vector) != dimensions for vector in validated):
            raise StorageDataError("Bir belgedeki embedding boyutları aynı olmalıdır.")

        with self.connection() as connection:
            existing = connection.execute(
                "SELECT id FROM documents WHERE source = ?", (source,)
            ).fetchone()
            if existing:
                document_id = existing["id"]
                connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                connection.execute(
                    "UPDATE documents SET content_hash=?, file_size=?, indexed_at=? WHERE id=?",
                    (content_hash, file_size, utc_now(), document_id),
                )
            else:
                cursor = connection.execute(
                    "INSERT INTO documents(source, content_hash, file_size, indexed_at) "
                    "VALUES(?, ?, ?, ?)",
                    (source, content_hash, file_size, utc_now()),
                )
                document_id = cursor.lastrowid

            created_at = utc_now()
            for index, (content, vector) in enumerate(zip(chunks, validated, strict=True)):
                chunk_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                cursor = connection.execute(
                    "INSERT INTO chunks(document_id, chunk_index, content, content_hash) "
                    "VALUES(?, ?, ?, ?)",
                    (document_id, index, content, chunk_hash),
                )
                connection.execute(
                    "INSERT INTO embeddings(chunk_id, model_alias, dimensions, vector, created_at) "
                    "VALUES(?, ?, ?, ?, ?)",
                    (cursor.lastrowid, model_alias, dimensions, json.dumps(vector), created_at),
                )

    def delete_sources(self, sources: Sequence[str]) -> int:
        if not sources:
            return 0
        with self.connection() as connection:
            return sum(
                connection.execute("DELETE FROM documents WHERE source = ?", (source,)).rowcount
                for source in sources
            )

    def load_chunks_with_embeddings(self) -> list[dict[str, object]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT c.id, d.source, c.chunk_index, c.content,
                       e.model_alias, e.dimensions, e.vector
                FROM chunks AS c
                JOIN documents AS d ON d.id = c.document_id
                JOIN embeddings AS e ON e.chunk_id = c.id
                ORDER BY d.source, c.chunk_index
                """
            ).fetchall()
        return [
            {
                "id": row["id"],
                "source": row["source"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "model_alias": row["model_alias"],
                "dimensions": row["dimensions"],
                "vector": decode_vector(row["vector"], row["dimensions"]),
            }
            for row in rows
        ]

    def counts(self) -> tuple[int, int, int]:
        with self.connection() as connection:
            return tuple(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("documents", "chunks", "embeddings")
            )
