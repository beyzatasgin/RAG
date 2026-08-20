"""Week 3 grounded, source-verified, fully local RAG command-line app."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence

from chat_utils import console_safe
from foundry_runtime import FoundryRuntime, FoundryRuntimeConfig
from prompt_builder import DEFAULT_CONTEXT_BUDGET
from rag_service import RagAnswer, RagService, RagServiceError
from retriever import Retriever
from storage import Storage


AnswerProvider = Callable[[argparse.Namespace, str], RagAnswer]
EXIT_WORDS = {"çık", "exit", "quit"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="runtime_data/rag.db")
    parser.add_argument("--question")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-score", type=float)
    parser.add_argument("--context-budget", type=int, default=DEFAULT_CONTEXT_BUDGET)
    parser.add_argument("--max-output-tokens", type=int, default=192)
    parser.add_argument("--model-cache-dir")
    parser.add_argument("--app-data-dir")
    parser.add_argument("--logs-dir")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser


def _config(args: argparse.Namespace) -> FoundryRuntimeConfig:
    return FoundryRuntimeConfig(
        app_name="local-rag-assistant",
        app_data_dir=args.app_data_dir,
        model_cache_dir=args.model_cache_dir,
        logs_dir=args.logs_dir,
    )


def answer_question(args: argparse.Namespace, question: str) -> RagAnswer:
    """Use staged runtimes so both models need not remain loaded on an 8 GiB PC."""

    config = _config(args)
    storage = Storage(args.db_path)
    storage.initialize_schema()
    with FoundryRuntime(config) as embedding_runtime:
        embedding_client = embedding_runtime.get_embedding_client(
            allow_download=args.allow_download
        )
        retriever = Retriever(storage, embedding_client, config.embedding_model_alias)
        results = RagService(retriever=retriever).retrieve(
            question, top_k=args.top_k, min_score=args.min_score
        )

    if not results:
        return RagService().generate_from_results(question, results)

    with FoundryRuntime(config) as chat_runtime:
        chat_client = chat_runtime.get_chat_client(allow_download=args.allow_download)
        return RagService(chat_client=chat_client).generate_from_results(
            question,
            results,
            context_budget=args.context_budget,
            max_output_tokens=args.max_output_tokens,
        )


def _print_answer(result: RagAnswer, *, debug: bool = False) -> None:
    print("\nCevap")
    print(console_safe(result.answer))
    print("\nKullanılan kaynaklar")
    if not result.insufficient_context and not result.has_valid_inline_citation:
        print("Not: Model cevap içinde geçerli bir kaynak etiketi üretmedi.")
        print(
            "Aşağıdaki kaynaklar uygulama tarafından retrieval "
            "sonuçlarından doğrulanmıştır."
        )
    if not result.sources:
        print("- Yok")
    for source in result.sources:
        print(f"- {source.label} {source.source} (chunk {source.chunk_index})")
        if debug:
            print(
                f"  semantic={source.semantic_score:.4f} "
                f"combined={source.combined_score:.4f}"
            )
    if debug:
        print(
            f"retrieved={result.retrieved_count} "
            f"used_context={result.used_context_count}"
        )
        if result.unknown_citations:
            print(
                "Uyarı: doğrulanamayan model etiketleri: "
                + ", ".join(result.unknown_citations)
            )
    if not result.insufficient_context:
        print("\nModel yanıtını aşağıdaki kaynaklarla kontrol edin.")


def run(args: argparse.Namespace, answer_provider: AnswerProvider = answer_question) -> int:
    def ask(question: str) -> None:
        if question.strip():
            _print_answer(answer_provider(args, question.strip()), debug=args.debug)

    try:
        if args.question is not None:
            if not args.question.strip():
                raise ValueError("Soru boş olamaz.")
            ask(args.question)
            return 0
        while True:
            try:
                question = input("Soru ('çık' ile çık): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if question.casefold() in EXIT_WORDS:
                return 0
            if question:
                ask(question)
    except (RagServiceError, ValueError, OSError) as exc:
        print(console_safe(f"RAG işlemi başarısız: {exc}"), file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            console_safe(f"Beklenmeyen RAG hatası: {type(exc).__name__}: {exc}"),
            file=sys.stderr,
        )
        return 1


def main(
    argv: Sequence[str] | None = None,
    answer_provider: AnswerProvider = answer_question,
) -> int:
    return run(build_parser().parse_args(argv), answer_provider)


if __name__ == "__main__":
    raise SystemExit(main())
