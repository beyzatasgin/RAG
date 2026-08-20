import json
import sqlite3

import pytest

from storage import Storage, StorageDataError


def populated_storage(tmp_path):
    storage = Storage(tmp_path / "rag.db")
    storage.initialize_schema()
    storage.replace_document(
        source="a.txt", content_hash="hash", file_size=3,
        chunks=["ilk", "ikinci"], embeddings=[[1, 0], [0, 1]],
        model_alias="model",
    )
    return storage


def test_schema_initialization_is_idempotent(tmp_path):
    storage = Storage(tmp_path / "rag.db")
    storage.initialize_schema()
    storage.initialize_schema()
    with storage.connection() as connection:
        assert connection.execute("SELECT value FROM schema_info WHERE key=?", ("schema_version",)).fetchone()[0] == "1"


def test_foreign_keys_are_enabled(tmp_path):
    storage = Storage(tmp_path / "rag.db")
    with storage.connection() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_insert_and_read_normalized_records(tmp_path):
    storage = populated_storage(tmp_path)
    assert storage.counts() == (1, 2, 2)
    rows = storage.load_chunks_with_embeddings()
    assert rows[0]["source"] == "a.txt"
    assert rows[1]["chunk_index"] == 1


def test_duplicate_source_is_rejected_by_schema(tmp_path):
    storage = populated_storage(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        with storage.connection() as connection:
            connection.execute(
                "INSERT INTO documents(source,content_hash,file_size,indexed_at) VALUES(?,?,?,?)",
                ("a.txt", "other", 1, "now"),
            )


def test_cascade_delete_removes_chunks_and_embeddings(tmp_path):
    storage = populated_storage(tmp_path)
    assert storage.delete_sources(["a.txt"]) == 1
    assert storage.counts() == (0, 0, 0)


@pytest.mark.parametrize("vector,dimensions", [("not-json", 2), (json.dumps([1]), 2), (json.dumps([float("nan")]), 1)])
def test_invalid_stored_embedding_is_rejected(tmp_path, vector, dimensions):
    storage = populated_storage(tmp_path)
    with storage.connection() as connection:
        connection.execute("UPDATE embeddings SET vector=?, dimensions=?", (vector, dimensions))
    with pytest.raises(StorageDataError):
        storage.load_chunks_with_embeddings()


def test_transaction_rolls_back_on_error(tmp_path):
    storage = Storage(tmp_path / "rag.db")
    storage.initialize_schema()
    with pytest.raises(RuntimeError):
        with storage.connection() as connection:
            connection.execute(
                "INSERT INTO documents(source,content_hash,file_size,indexed_at) VALUES(?,?,?,?)",
                ("a.txt", "hash", 1, "now"),
            )
            raise RuntimeError("rollback")
    assert storage.counts() == (0, 0, 0)


def test_only_requested_database_is_created(tmp_path):
    storage = Storage(tmp_path / "nested" / "rag.db")
    storage.initialize_schema()
    assert [path.name for path in (tmp_path / "nested").iterdir()] == ["rag.db"]
