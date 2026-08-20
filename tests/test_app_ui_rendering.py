from __future__ import annotations

from types import SimpleNamespace

import app_ui


class FakeStreamlit:
    def __init__(self):
        self.events = []

    def __getattr__(self, name):
        def record(value="", *args, **kwargs):
            self.events.append((name, str(value)))
        return record


def view(*, sources=True, citation=True, insufficient=False, unknown=()):
    items = () if not sources else (
        SimpleNamespace(label="[K1]", source="real.txt", chunk_index=2, semantic_score=.8, combined_score=.7),
    )
    return SimpleNamespace(
        sources=items,
        has_valid_inline_citation=citation,
        insufficient_context=insufficient,
        unknown_citations=unknown,
    )


def test_grounded_source_and_responsible_note(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(app_ui, "st", fake)
    app_ui._render_sources(view(), debug=True)
    output = "\n".join(value for _, value in fake.events)
    assert "real.txt" in output and "semantic=0.8000" in output
    assert "Model yanıtını" in output
    assert "geçerli bir kaynak etiketi üretmedi" not in output


def test_missing_and_unknown_citation_warning(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(app_ui, "st", fake)
    app_ui._render_sources(view(citation=False, unknown=("[K99]",)), debug=True)
    output = "\n".join(value for _, value in fake.events)
    assert "geçerli bir kaynak etiketi üretmedi" in output
    assert "[K99]" in output


def test_no_result_source_view(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(app_ui, "st", fake)
    app_ui._render_sources(view(sources=False, citation=False, insufficient=True), debug=False)
    output = "\n".join(value for _, value in fake.events)
    assert "Kaynak yok" in output
    assert "geçerli bir kaynak etiketi üretmedi" not in output
