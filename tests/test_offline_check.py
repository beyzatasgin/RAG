from pathlib import Path

from offline_check import scan_runtime_sources


def test_source_scan_ignores_markdown_urls_and_finds_runtime_endpoint(tmp_path):
    (tmp_path / "README.md").write_text("https://api.openai.com", encoding="utf-8")
    (tmp_path / "safe.py").write_text("value = 'local'", encoding="utf-8")
    assert scan_runtime_sources(tmp_path) == []
    (tmp_path / "bad.py").write_text("endpoint = 'https://api.openai.com'", encoding="utf-8")
    assert scan_runtime_sources(tmp_path) == ["OpenAI cloud endpoint: " + (tmp_path / "bad.py").as_posix()]
