"""Embedding ve chat demo betikleri için gerçek model kullanmayan testler."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import pytest

import app
import embedding_test


class FakeEmbeddingClient:
    def generate_embedding(self, text):
        offset = float(len(text) % 3)
        vector = [1.0 + offset, 2.0, 3.0]
        return SimpleNamespace(data=[SimpleNamespace(embedding=vector)])


class FakeChatClient:
    def __init__(self, parts=("Kısa ", "cevap.")):
        self.parts = parts

    def complete_streaming_chat(self, messages):
        assert len(messages) == 1
        for part in self.parts:
            delta = SimpleNamespace(content=part)
            yield SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


class FakeRuntime:
    def __init__(self, config, *, embedding_client=None, chat_client=None):
        self.config = config
        self.embedding_client = embedding_client or FakeEmbeddingClient()
        self.chat_client = chat_client or FakeChatClient()
        self.allow_download = None
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.exited = True
        return False

    def get_embedding_client(self, *, allow_download=False):
        self.allow_download = allow_download
        return self.embedding_client

    def get_chat_client(self, *, allow_download=False):
        self.allow_download = allow_download
        return self.chat_client


def factory_for(created, **runtime_kwargs):
    def factory(config):
        runtime = FakeRuntime(config, **runtime_kwargs)
        created.append(runtime)
        return runtime

    return factory


def test_imports_do_not_load_sdk(monkeypatch):
    monkeypatch.delitem(sys.modules, "foundry_local_sdk", raising=False)

    importlib.reload(embedding_test)
    importlib.reload(app)

    assert "foundry_local_sdk" not in sys.modules


@pytest.mark.parametrize("module", [embedding_test, app])
def test_cli_defaults_to_offline_and_forwards_paths(module, capsys):
    created = []
    result = module.main(
        [
            "--model-cache-dir",
            "shared-cache",
            "--app-data-dir",
            "app-data",
            "--logs-dir",
            "logs",
        ],
        runtime_factory=factory_for(created),
    )

    assert result == 0
    assert created[0].config.model_cache_dir == "shared-cache"
    assert created[0].config.app_data_dir == "app-data"
    assert created[0].config.logs_dir == "logs"
    assert created[0].allow_download is False
    assert created[0].entered and created[0].exited
    assert capsys.readouterr().out


@pytest.mark.parametrize("module", [embedding_test, app])
def test_allow_download_requires_explicit_flag(module):
    created = []

    assert module.main(["--allow-download"], factory_for(created)) == 0

    assert created[0].allow_download is True


def test_embedding_demo_reports_machine_readable_metrics(capsys):
    created = []

    assert embedding_test.main([], factory_for(created)) == 0

    output = capsys.readouterr().out
    assert "embedding_count=5" in output
    assert "embedding_dimension=3" in output
    assert "all_values_finite=true" in output
    assert "sample_cosine_similarity=" in output


def test_chat_demo_reports_non_empty_answer(capsys):
    created = []

    assert app.main([], factory_for(created)) == 0

    assert "answer=Kısa cevap." in capsys.readouterr().out


def test_chat_output_replaces_characters_unsupported_by_console():
    assert app._console_safe("oran φ", "ascii") == "oran ?"


def test_chat_hides_completed_reasoning_block(capsys):
    created = []
    client = FakeChatClient(parts=("<think>özel düşünme</think>", "Kısa cevap."))

    assert app.main([], factory_for(created, chat_client=client)) == 0

    output = capsys.readouterr().out
    assert "özel düşünme" not in output
    assert "answer=Kısa cevap." in output


@pytest.mark.parametrize("module", [embedding_test, app])
def test_demo_failure_returns_nonzero_and_still_cleans_up(module, capsys):
    created = []

    class FailingRuntime(FakeRuntime):
        def get_embedding_client(self, *, allow_download=False):
            raise RuntimeError("fake failure")

        def get_chat_client(self, *, allow_download=False):
            raise RuntimeError("fake failure")

    def factory(config):
        runtime = FailingRuntime(config)
        created.append(runtime)
        return runtime

    assert module.main([], factory) == 1
    assert created[0].exited
    assert "fake failure" in capsys.readouterr().err


def test_empty_chat_answer_is_an_error_and_cleans_up(capsys):
    created = []
    factory = factory_for(created, chat_client=FakeChatClient(parts=()))

    assert app.main([], factory) == 1

    assert created[0].exited
    assert "boş cevap" in capsys.readouterr().err
