"""Foundry Local chat responses shared by demos and the RAG service."""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from typing import Any


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK_BLOCK = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)


class ChatResponseError(RuntimeError):
    """Raised when Foundry Local returns no user-visible answer."""


def visible_answer(text: str) -> str:
    """Remove model reasoning blocks and return only user-visible text."""

    without_completed_blocks = _THINK_BLOCK.sub("", text)
    return _UNCLOSED_THINK_BLOCK.sub("", without_completed_blocks).strip()


def console_safe(text: str, encoding: str | None = None) -> str:
    """Make text printable on consoles with a limited output encoding."""

    target_encoding = encoding or sys.stdout.encoding or "utf-8"
    return text.encode(target_encoding, errors="replace").decode(
        target_encoding, errors="replace"
    )


def collect_streaming_answer(client: Any, messages: Iterable[Any]) -> str:
    """Collect the verified SDK streaming shape into a visible answer."""

    message_list = list(messages)
    fragments: list[str] = []
    for chunk in client.complete_streaming_chat(message_list):
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        content = getattr(delta, "content", None)
        if content:
            fragments.append(content)

    answer = visible_answer("".join(fragments))
    if not answer:
        raise ChatResponseError("Foundry Local boş cevap üretti; görünür içerik yok.")
    return answer


def configure_generation(
    client: Any,
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
    completions: int | None = None,
) -> None:
    """Apply options exposed by Foundry Local SDK 1.2.4 client settings."""

    settings = getattr(client, "settings", None)
    if settings is None:
        return
    if max_tokens is not None:
        settings.max_tokens = max_tokens
    if temperature is not None:
        settings.temperature = temperature
    if completions is not None:
        settings.n = completions
