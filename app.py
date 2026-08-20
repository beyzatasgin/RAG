"""Foundry Local ile kısa ve varsayılan-offline chat smoke demosu."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any, Callable

from chat_utils import (
    collect_streaming_answer,
    console_safe as _console_safe,
    visible_answer as _visible_answer,
)
from foundry_runtime import FoundryRuntime, FoundryRuntimeConfig


QUESTION = "Altın oran nedir? Kısaca açıkla."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--app-data-dir")
    parser.add_argument("--logs-dir")
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Model cache içinde değilse indirmeye açıkça izin ver.",
    )
    return parser


def run_demo(
    args: argparse.Namespace,
    runtime_factory: Callable[[FoundryRuntimeConfig], Any] = FoundryRuntime,
) -> str:
    config = FoundryRuntimeConfig(
        app_name="local-rag-assistant",
        app_data_dir=args.app_data_dir,
        model_cache_dir=args.model_cache_dir,
        logs_dir=args.logs_dir,
    )
    messages = [{"role": "user", "content": QUESTION}]

    with runtime_factory(config) as runtime:
        client = runtime.get_chat_client(allow_download=args.allow_download)
        answer = collect_streaming_answer(client, messages)
    print(f"answer={_console_safe(answer)}")
    return answer


def main(
    argv: Sequence[str] | None = None,
    runtime_factory: Callable[[FoundryRuntimeConfig], Any] = FoundryRuntime,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_demo(args, runtime_factory)
    except Exception as exc:
        print(f"Chat smoke başarısız: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
