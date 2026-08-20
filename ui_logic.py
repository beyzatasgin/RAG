"""Pure validation and presentation helpers for the local Streamlit UI."""

from __future__ import annotations

import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from rag_service import RagAnswer


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_UPLOAD_SUFFIXES = {".txt", ".md"}
DEFAULT_UPLOAD_DIR = Path("runtime_data/uploads")
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


class UiValidationError(ValueError):
    """A safe, user-actionable UI input error."""


@dataclass(frozen=True)
class DbStatus:
    exists: bool
    integrity: str | None = None
    documents: int = 0
    chunks: int = 0
    embeddings: int = 0
    model_alias: str | None = None
    dimensions: int | None = None


@dataclass(frozen=True)
class SourceView:
    label: str
    source: str
    chunk_index: int
    semantic_score: float
    combined_score: float


@dataclass(frozen=True)
class AnswerView:
    answer: str
    sources: tuple[SourceView, ...]
    insufficient_context: bool
    has_valid_inline_citation: bool
    unknown_citations: tuple[str, ...]


def validate_upload_name(name: str) -> str:
    """Reject traversal, directories, drive paths, and unsupported extensions."""

    if not isinstance(name, str) or not name.strip():
        raise UiValidationError("Dosya adı boş olamaz.")
    candidate = name.strip()
    if (
        candidate in {".", ".."}
        or Path(candidate).is_absolute()
        or PureWindowsPath(candidate).is_absolute()
        or _DRIVE_PREFIX.match(candidate)
        or Path(candidate).name != candidate
        or PureWindowsPath(candidate).name != candidate
        or "/" in candidate
        or "\\" in candidate
    ):
        raise UiValidationError("Dosya adı klasör veya path bileşeni içeremez.")
    if Path(candidate).suffix.lower() not in ALLOWED_UPLOAD_SUFFIXES:
        raise UiValidationError("Yalnızca .txt ve .md dosyaları desteklenir.")
    return candidate


def validate_upload(name: str, data: bytes, max_bytes: int = MAX_UPLOAD_BYTES) -> str:
    safe_name = validate_upload_name(name)
    if not isinstance(data, bytes):
        raise UiValidationError("Upload içeriği byte olmalıdır.")
    if len(data) > max_bytes:
        raise UiValidationError("Dosya 5 MiB upload sınırını aşıyor.")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UiValidationError("Dosya geçerli UTF-8 metni değil.") from exc
    if not text.strip():
        raise UiValidationError("Boş belge yüklenemez.")
    return safe_name


def save_upload(
    name: str,
    data: bytes,
    *,
    upload_dir: str | Path = DEFAULT_UPLOAD_DIR,
    overwrite: bool = True,
) -> Path:
    """Validate and atomically save an upload; overwrite is explicit and deterministic."""

    safe_name = validate_upload(name, data)
    root = Path(upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    target = root / safe_name
    if target.exists() and not overwrite:
        raise UiValidationError("Aynı adlı dosya zaten mevcut.")

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=root, prefix=".upload-", suffix=".tmp", delete=False
        ) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return target


def validate_question(question: str) -> str:
    clean = question.strip() if isinstance(question, str) else ""
    if not clean:
        raise UiValidationError("Soru boş olamaz.")
    return clean


def validate_settings(
    *, top_k: int, min_score: float, context_budget: int, max_output_tokens: int
) -> None:
    if top_k <= 0:
        raise UiValidationError("top_k pozitif olmalıdır.")
    if not -1.0 <= min_score <= 1.0:
        raise UiValidationError("min_score -1 ile 1 arasında olmalıdır.")
    if context_budget <= 0 or max_output_tokens <= 0:
        raise UiValidationError("Context ve çıktı limitleri pozitif olmalıdır.")


def answer_view(answer: RagAnswer) -> AnswerView:
    sources = tuple(
        SourceView(
            item.label,
            item.source,
            item.chunk_index,
            item.semantic_score,
            item.combined_score,
        )
        for item in answer.sources
    )
    return AnswerView(
        answer.answer,
        sources,
        answer.insufficient_context,
        answer.has_valid_inline_citation,
        answer.unknown_citations,
    )


def ingestion_summary_view(summary: Any) -> dict[str, int]:
    return {
        key: int(getattr(summary, key))
        for key in ("added", "updated", "unchanged", "skipped", "failed", "total_chunks")
    }


def safe_error_message(exc: Exception) -> str:
    """Return a concise error without logging document or question content."""

    if isinstance(exc, UiValidationError):
        return str(exc)
    return f"İşlem başarısız: {type(exc).__name__}. Ayrıntılar terminal logunda."


def read_db_status(db_path: str | Path) -> DbStatus:
    path = Path(db_path)
    if not path.is_file():
        return DbStatus(exists=False)
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        documents = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunks = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        embeddings = connection.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        metadata = connection.execute(
            "SELECT model_alias, dimensions FROM embeddings LIMIT 1"
        ).fetchone()
        return DbStatus(
            True,
            integrity,
            documents,
            chunks,
            embeddings,
            metadata[0] if metadata else None,
            metadata[1] if metadata else None,
        )
    finally:
        connection.close()
