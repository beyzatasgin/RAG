from __future__ import annotations

import importlib
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_import_is_model_safe(monkeypatch):
    monkeypatch.delitem(sys.modules, "foundry_local_sdk", raising=False)
    module = importlib.import_module("app_ui")
    importlib.reload(module)
    assert "foundry_local_sdk" not in sys.modules


def test_headless_initial_render_does_not_initialize_model():
    app_path = Path(__file__).resolve().parents[1] / "app_ui.py"
    test = AppTest.from_file(app_path, default_timeout=10).run()
    assert not test.exception
    assert any("Yerel RAG Asistanı" in title.value for title in test.title)
    assert any(button.label == "Sor" for button in test.button)
    assert any(button.label == "Belgeleri indeksle" for button in test.button)
