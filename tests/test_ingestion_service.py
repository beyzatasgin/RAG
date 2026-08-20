from types import SimpleNamespace

from ingestion_service import IngestionService
from storage import Storage


class FakeEmbeddingClient:
    def __init__(self, *, fail_text=None, varying_dimensions=False):
        self.fail_text = fail_text
        self.varying_dimensions = varying_dimensions
        self.calls = []

    def generate_embedding(self, text):
        self.calls.append(text)
        if self.fail_text and self.fail_text in text:
            raise RuntimeError("embedding failed")
        vector = [float(len(text)), 1.0]
        if self.varying_dimensions and len(self.calls) % 2 == 0:
            vector.append(2.0)
        return SimpleNamespace(data=[SimpleNamespace(embedding=vector)])


def make_service(tmp_path, **kwargs):
    storage = Storage(tmp_path / "rag.db")
    return storage, IngestionService(storage, chunk_size=40, chunk_overlap=5, **kwargs)


def test_new_file_is_added(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    (data / "tenis.txt").write_text("Türkçe tenis belgesi.", encoding="utf-8")
    storage, service = make_service(tmp_path)
    summary = service.ingest(data, FakeEmbeddingClient())
    assert (summary.added, summary.failed) == (1, 0)
    assert storage.counts()[0] == 1


def test_second_ingestion_is_unchanged_without_embedding(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    (data / "a.txt").write_text("aynı içerik", encoding="utf-8")
    _, service = make_service(tmp_path)
    service.ingest(data, FakeEmbeddingClient())
    second_client = FakeEmbeddingClient()
    summary = service.ingest(data, second_client)
    assert summary.unchanged == 1
    assert second_client.calls == []


def test_changed_file_replaces_without_duplicates(tmp_path):
    data = tmp_path / "data"; data.mkdir(); path = data / "a.txt"
    path.write_text("ilk içerik", encoding="utf-8")
    storage, service = make_service(tmp_path)
    service.ingest(data, FakeEmbeddingClient())
    path.write_text("değişmiş ve daha uzun içerik", encoding="utf-8")
    summary = service.ingest(data, FakeEmbeddingClient())
    assert summary.updated == 1
    assert storage.counts()[0] == 1
    assert storage.get_document("a.txt")["file_size"] == len(path.read_bytes())


def test_empty_and_unsupported_files_are_not_indexed(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    (data / "empty.md").write_text("  \n", encoding="utf-8")
    (data / "ignore.pdf").write_bytes(b"pdf")
    storage, service = make_service(tmp_path)
    summary = service.ingest(data, FakeEmbeddingClient())
    assert (summary.discovered, summary.skipped) == (1, 1)
    assert storage.counts() == (0, 0, 0)


def test_decode_failure_does_not_block_other_files(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    (data / "bad.txt").write_bytes(b"\xff")
    (data / "good.txt").write_text("geçerli", encoding="utf-8")
    storage, service = make_service(tmp_path)
    summary = service.ingest(data, FakeEmbeddingClient())
    assert (summary.added, summary.failed) == (1, 1)
    assert storage.list_sources() == ["good.txt"]


def test_embedding_failure_preserves_previous_document(tmp_path):
    data = tmp_path / "data"; data.mkdir(); path = data / "a.txt"
    path.write_text("geçerli sürüm", encoding="utf-8")
    storage, service = make_service(tmp_path)
    service.ingest(data, FakeEmbeddingClient())
    old_hash = storage.get_document("a.txt")["content_hash"]
    path.write_text("HATA yeni sürüm", encoding="utf-8")
    summary = service.ingest(data, FakeEmbeddingClient(fail_text="HATA"))
    assert summary.failed == 1
    assert storage.get_document("a.txt")["content_hash"] == old_hash


def test_batch_dimension_mismatch_rolls_back(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    (data / "long.txt").write_text("kelime " * 30, encoding="utf-8")
    storage, service = make_service(tmp_path)
    summary = service.ingest(data, FakeEmbeddingClient(varying_dimensions=True))
    assert summary.failed == 1
    assert storage.counts() == (0, 0, 0)


def test_missing_is_reported_but_not_deleted_by_default(tmp_path):
    data = tmp_path / "data"; data.mkdir(); path = data / "a.txt"
    path.write_text("içerik", encoding="utf-8")
    storage, service = make_service(tmp_path)
    service.ingest(data, FakeEmbeddingClient()); path.unlink()
    summary = service.ingest(data, FakeEmbeddingClient())
    assert (summary.missing, summary.deleted) == (1, 0)
    assert storage.list_sources() == ["a.txt"]


def test_delete_missing_requires_explicit_option(tmp_path):
    data = tmp_path / "data"; data.mkdir(); path = data / "a.txt"
    path.write_text("içerik", encoding="utf-8")
    storage, service = make_service(tmp_path)
    service.ingest(data, FakeEmbeddingClient()); path.unlink()
    summary = service.ingest(data, FakeEmbeddingClient(), delete_missing=True)
    assert (summary.missing, summary.deleted) == (1, 1)
    assert storage.counts() == (0, 0, 0)


def test_files_are_processed_in_deterministic_name_order(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    for name in ("z.txt", "A.md", "b.txt"):
        (data / name).write_text(name, encoding="utf-8")
    _, service = make_service(tmp_path)
    summary = service.ingest(data, FakeEmbeddingClient())
    assert summary.processed_sources == ["A.md", "b.txt", "z.txt"]


def test_turkish_utf8_content_is_preserved(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    (data / "türkçe.md").write_text("İçerik: çığ öşü", encoding="utf-8")
    storage, service = make_service(tmp_path)
    service.ingest(data, FakeEmbeddingClient())
    assert "çığ" in storage.load_chunks_with_embeddings()[0]["content"]
