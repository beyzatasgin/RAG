from __future__ import annotations

import importlib
import sys

import main
from rag_service import RagAnswer, RagSource


def response(no_result=False, *, valid_citation=True, unknown=()):
    sources = () if no_result else (RagSource("[K1]", "a.txt", 0, .9, .8),)
    return RagAnswer(
        "Belgelerde bu bilgi bulunamadı." if no_result else "Yanıt [K1]",
        sources,
        0 if no_result else 1,
        0 if no_result else 1,
        no_result,
        ("[K1]",) if valid_citation and not no_result else (),
        unknown,
    )


def test_import_does_not_load_sdk(monkeypatch):
    monkeypatch.delitem(sys.modules, "foundry_local_sdk", raising=False)
    importlib.reload(main)
    assert "foundry_local_sdk" not in sys.modules


def test_single_question_forwards_cli_and_prints_source(capsys):
    seen = []
    def provider(args, question):
        seen.append((args, question))
        return response()
    code = main.main(
        ["--question", "Soru?", "--top-k", "4", "--min-score", ".3", "--debug"],
        provider,
    )
    output = capsys.readouterr().out
    assert code == 0 and seen[0][1] == "Soru?"
    assert seen[0][0].top_k == 4 and seen[0][0].min_score == .3
    assert "[K1] a.txt" in output and "semantic=0.9000" in output
    assert "geçerli bir kaynak etiketi üretmedi" not in output
    assert "Model yanıtını aşağıdaki kaynaklarla kontrol edin." in output
    assert seen[0][0].allow_download is False
    assert seen[0][0].max_output_tokens == 192


def test_no_result_output(capsys):
    assert main.main(["--question", "yok"], lambda args, q: response(True)) == 0
    output = capsys.readouterr().out
    assert "Belgelerde bu bilgi bulunamadı." in output and "- Yok" in output
    assert "geçerli bir kaynak etiketi üretmedi" not in output
    assert "Model yanıtını aşağıdaki kaynaklarla kontrol edin." not in output


def test_missing_inline_citation_warns_without_rewriting_answer(capsys):
    result = response(valid_citation=False)
    result = RagAnswer(
        "Citation içermeyen özgün cevap",
        result.sources,
        result.retrieved_count,
        result.used_context_count,
        result.insufficient_context,
    )
    assert main.main(["--question", "Soru?"], lambda args, q: result) == 0
    output = capsys.readouterr().out
    assert "Citation içermeyen özgün cevap" in output
    assert "geçerli bir kaynak etiketi üretmedi" in output
    assert "retrieval sonuçlarından doğrulanmıştır" in output
    assert "[K1] a.txt" in output


def test_unknown_citation_is_not_valid_and_only_debug_reports_it(capsys):
    result = response(valid_citation=False, unknown=("[K99]",))
    assert main.main(["--question", "Soru?", "--debug"], lambda args, q: result) == 0
    output = capsys.readouterr().out
    assert "geçerli bir kaynak etiketi üretmedi" in output
    assert "doğrulanamayan model etiketleri: [K99]" in output
    assert "[K99] a.txt" not in output


def test_empty_single_question_does_not_call_provider(capsys):
    calls = []
    assert main.main(["--question", "  "], lambda a, q: calls.append(q)) == 1
    assert not calls and "boş" in capsys.readouterr().err


def test_provider_failure_is_nonzero(capsys):
    def fail(args, question):
        raise RuntimeError("boom")
    assert main.main(["--question", "Soru?"], fail) == 1
    assert "boom" in capsys.readouterr().err


def test_interactive_exit_does_not_call_provider(monkeypatch):
    calls = []
    monkeypatch.setattr("builtins.input", lambda prompt: "çık")
    assert main.main([], lambda a, q: calls.append(q)) == 0
    assert not calls
