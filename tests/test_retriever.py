import importlib
import json
from types import SimpleNamespace

import pytest

import ingest
import main
import retrieval
from retriever import RetrievalConfigurationError, Retriever
from storage import Storage, StorageDataError


class FakeClient:
    def __init__(self, vector):
        self.vector = vector
        self.calls = 0

    def generate_embedding(self, query):
        self.calls += 1
        return SimpleNamespace(data=[SimpleNamespace(embedding=self.vector)])


def make_index(tmp_path):
    storage = Storage(tmp_path / "rag.db")
    storage.initialize_schema()
    storage.replace_document(
        source="grand_slam.txt", content_hash="a", file_size=10,
        chunks=["Grand Slam turnuvaları tenis için önemlidir."],
        embeddings=[[1.0, 0.0]], model_alias="model",
    )
    storage.replace_document(
        source="kurallar.txt", content_hash="b", file_size=10,
        chunks=["Servis ve puanlama kuralları."],
        embeddings=[[0.0, 1.0]], model_alias="model",
    )
    return storage


def test_cosine_similarity_orders_results(tmp_path):
    results = Retriever(make_index(tmp_path), FakeClient([1, 0]), "model").search(
        "bilinmeyen", semantic_weight=1.0, keyword_weight=0.0
    )
    assert results[0].source == "grand_slam.txt"


def test_top_k_limits_results(tmp_path):
    results = Retriever(make_index(tmp_path), FakeClient([1, 0]), "model").search("tenis", top_k=1)
    assert len(results) == 1


def test_min_score_filters_results(tmp_path):
    results = Retriever(make_index(tmp_path), FakeClient([1, 0]), "model").search("x", min_score=0.6)
    assert len(results) == 1


def test_empty_query_and_invalid_top_k_are_rejected(tmp_path):
    retriever = Retriever(make_index(tmp_path), FakeClient([1, 0]), "model")
    with pytest.raises(RetrievalConfigurationError):
        retriever.search(" ")
    with pytest.raises(RetrievalConfigurationError):
        retriever.search("x", top_k=0)


def test_empty_database_is_safe_and_does_not_embed(tmp_path):
    storage = Storage(tmp_path / "empty.db"); storage.initialize_schema()
    client = FakeClient([1, 0])
    assert Retriever(storage, client, "model").search("query") == []
    assert client.calls == 0


def test_hybrid_weights_change_order(tmp_path):
    storage = make_index(tmp_path)
    retriever = Retriever(storage, FakeClient([0, 1]), "model")
    semantic = retriever.search("Grand", semantic_weight=1.0, keyword_weight=0.0)
    keyword = retriever.search("Grand", semantic_weight=0.0, keyword_weight=1.0)
    assert semantic[0].source == "kurallar.txt"
    assert keyword[0].source == "grand_slam.txt"


def test_tie_breaker_is_deterministic(tmp_path):
    storage = make_index(tmp_path)
    results = Retriever(storage, FakeClient([1, 1]), "model").search(
        "x", semantic_weight=1.0, keyword_weight=0.0
    )
    assert [item.source for item in results] == ["grand_slam.txt", "kurallar.txt"]


def test_model_alias_mismatch_is_rejected(tmp_path):
    with pytest.raises(RetrievalConfigurationError, match="uyuşmuyor"):
        Retriever(make_index(tmp_path), FakeClient([1, 0]), "other").search("x")


def test_mixed_stored_aliases_are_rejected(tmp_path):
    storage = make_index(tmp_path)
    with storage.connection() as connection:
        connection.execute(
            "UPDATE embeddings SET model_alias='other' "
            "WHERE chunk_id=(SELECT MAX(chunk_id) FROM embeddings)"
        )
    with pytest.raises(StorageDataError, match="karışık"):
        Retriever(storage, FakeClient([1, 0]), "model").search("x")


def test_mixed_stored_dimensions_are_rejected(tmp_path):
    storage = make_index(tmp_path)
    with storage.connection() as connection:
        connection.execute(
            "UPDATE embeddings SET dimensions=3, vector='[0, 1, 2]' "
            "WHERE chunk_id=(SELECT MAX(chunk_id) FROM embeddings)"
        )
    with pytest.raises(StorageDataError, match="karışık"):
        Retriever(storage, FakeClient([1, 0]), "model").search("x")


def test_query_dimension_mismatch_is_rejected(tmp_path):
    with pytest.raises(StorageDataError):
        Retriever(make_index(tmp_path), FakeClient([1]), "model").search("x")


@pytest.mark.parametrize("raw", ["broken", json.dumps([float("inf"), 0])])
def test_corrupt_or_nonfinite_stored_vector_is_rejected(tmp_path, raw):
    storage = make_index(tmp_path)
    with storage.connection() as connection:
        connection.execute("UPDATE embeddings SET vector=? WHERE chunk_id=(SELECT MIN(chunk_id) FROM embeddings)", (raw,))
    with pytest.raises(StorageDataError):
        Retriever(storage, FakeClient([1, 0]), "model").search("x")


def test_real_source_and_chunk_metadata_are_returned(tmp_path):
    result = Retriever(make_index(tmp_path), FakeClient([1, 0]), "model").search("Grand")[0]
    assert result.source == "grand_slam.txt"
    assert result.chunk_index == 0
    assert "Grand Slam" in result.content
    assert result.combined_score == pytest.approx(0.7 * result.semantic_score + 0.3 * result.keyword_score)


def test_cli_modules_are_import_safe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    importlib.reload(ingest)
    importlib.reload(retrieval)
    importlib.reload(main)
    assert not (tmp_path / "runtime_data").exists()
