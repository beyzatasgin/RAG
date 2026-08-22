from __future__ import annotations

import importlib
import sys

import foundry_runtime
import sqlite3
import storage


EXPECTED_QUESTIONS = (
    "Windows PowerShell'de proje için sanal ortam nasıl oluşturulur?",
    "SQLite database is locked hatası ne anlama gelir?",
    "RAG sisteminde kaynak listesi nasıl oluşturulur?",
)


def test_import_is_runtime_and_database_safe(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("benchmark importu runtime, model veya DB başlatmamalı")

    monkeypatch.setattr(sqlite3, "connect", fail)
    monkeypatch.setattr(foundry_runtime.FoundryRuntime, "__init__", fail)
    monkeypatch.setattr(storage.Storage, "__init__", fail)
    monkeypatch.delitem(sys.modules, "foundry_local_sdk", raising=False)
    monkeypatch.delitem(sys.modules, "benchmark", raising=False)

    module = importlib.import_module("benchmark")

    assert "foundry_local_sdk" not in sys.modules
    assert module.main.__module__ == "benchmark"


def test_questions_are_exactly_the_software_support_queries():
    from benchmark import QUESTIONS

    assert QUESTIONS == EXPECTED_QUESTIONS
    assert len(QUESTIONS) == 3
    assert all(isinstance(question, str) and question.strip() for question in QUESTIONS)
    assert all("Grand Slam" not in question for question in QUESTIONS)
    assert all("tenis" not in question.casefold() for question in QUESTIONS)
