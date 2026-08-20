"""Harici NLP bağımlılığı olmadan deterministik karakter tabanlı chunking."""

from __future__ import annotations


def _validate_config(chunk_size: int, overlap: int) -> None:
    if not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size pozitif bir tam sayı olmalıdır.")
    if not isinstance(overlap, int) or overlap < 0:
        raise ValueError("overlap negatif olmayan bir tam sayı olmalıdır.")
    if overlap >= chunk_size:
        raise ValueError("overlap, chunk_size değerinden küçük olmalıdır.")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Metni paragraf ve kelime sınırlarını tercih ederek sırayla böl."""
    _validate_config(chunk_size, overlap)
    if not isinstance(text, str):
        raise TypeError("text bir str olmalıdır.")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            minimum_break = start + max(1, chunk_size // 2)
            paragraph_break = normalized.rfind("\n\n", minimum_break, end + 1)
            word_break = normalized.rfind(" ", minimum_break, end + 1)
            if paragraph_break >= minimum_break:
                end = paragraph_break
            elif word_break >= minimum_break:
                end = word_break

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break

        next_start = max(0, end - overlap)
        while next_start < end and normalized[next_start].isspace():
            next_start += 1
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks
