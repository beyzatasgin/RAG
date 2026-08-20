from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from rag_service import RagAnswer, RagSource
from ui_logic import (
    MAX_UPLOAD_BYTES,
    UiValidationError,
    answer_view,
    ingestion_summary_view,
    safe_error_message,
    save_upload,
    validate_question,
    validate_upload,
    validate_upload_name,
)


@pytest.mark.parametrize("name", ["not.txt", "notes.md", "TÜRKÇE.TXT"])
def test_safe_upload_names(name):
    assert validate_upload_name(name) == name


@pytest.mark.parametrize(
    "name", ["../x.txt", "a/b.txt", "a\\b.txt", "C:\\x.txt", "/tmp/x.txt", "x.pdf"]
)
def test_unsafe_upload_names(name):
    with pytest.raises(UiValidationError):
        validate_upload_name(name)


def test_upload_size_limit_and_utf8():
    assert validate_upload("a.txt", b"x" * MAX_UPLOAD_BYTES) == "a.txt"
    with pytest.raises(UiValidationError):
        validate_upload("a.txt", b"x" * (MAX_UPLOAD_BYTES + 1))
    with pytest.raises(UiValidationError):
        validate_upload("a.md", b"\xff")


def test_atomic_save_and_defined_overwrite(tmp_path):
    target = save_upload("a.txt", "ilk".encode(), upload_dir=tmp_path)
    assert target.read_text(encoding="utf-8") == "ilk"
    save_upload("a.txt", "ikinci".encode(), upload_dir=tmp_path, overwrite=True)
    assert target.read_text(encoding="utf-8") == "ikinci"
    assert not list(tmp_path.glob(".upload-*.tmp"))
    with pytest.raises(UiValidationError):
        save_upload("a.txt", b"ucuncu", upload_dir=tmp_path, overwrite=False)


def test_empty_question_and_safe_error():
    with pytest.raises(UiValidationError):
        validate_question("  ")
    assert safe_error_message(UiValidationError("güvenli")) == "güvenli"
    assert "secret content" not in safe_error_message(RuntimeError("secret content"))


def test_answer_view_uses_verified_metadata():
    answer = RagAnswer(
        "model text",
        (RagSource("[K1]", "real.txt", 3, .8, .7),),
        1,
        1,
        False,
        (),
        ("[K99]",),
    )
    view = answer_view(answer)
    assert view.answer == "model text"
    assert view.sources[0].source == "real.txt"
    assert view.has_valid_inline_citation is False
    assert view.unknown_citations == ("[K99]",)


def test_ingestion_summary_view():
    summary = SimpleNamespace(added=1, updated=2, unchanged=3, skipped=4, failed=0, total_chunks=9)
    assert ingestion_summary_view(summary) == {
        "added": 1, "updated": 2, "unchanged": 3,
        "skipped": 4, "failed": 0, "total_chunks": 9,
    }
