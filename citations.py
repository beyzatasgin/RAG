"""Validate citation labels emitted by the local language model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Iterable


_CITATION = re.compile(r"\[K([1-9]\d*)\]")


@dataclass(frozen=True)
class CitationValidation:
    valid: tuple[str, ...]
    unknown: tuple[str, ...]


def validate_citations(answer: str, allowed_labels: Iterable[str]) -> CitationValidation:
    """Classify citations without rewriting or inventing answer text."""

    allowed = set(allowed_labels)
    valid: list[str] = []
    unknown: list[str] = []
    for match in _CITATION.finditer(answer):
        label = f"[K{match.group(1)}]"
        target = valid if label in allowed else unknown
        if label not in target:
            target.append(label)
    return CitationValidation(tuple(valid), tuple(unknown))
