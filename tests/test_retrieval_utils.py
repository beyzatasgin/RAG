"""Yan etkisiz retrieval yardımcıları için birim testleri."""

import importlib
import sys

import pytest

from retrieval_utils import cosine_similarity, hybrid_score, keyword_score


def test_cosine_similarity_same_direction():
    assert cosine_similarity([1, 2], [2, 4]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_cosine_similarity_opposite_directions():
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector_returns_zero():
    assert cosine_similarity([0, 0], [1, 2]) == 0.0


def test_cosine_similarity_rejects_different_dimensions():
    with pytest.raises(ValueError, match="boyutları aynı"):
        cosine_similarity([1, 2], [1, 2, 3])


def test_cosine_similarity_rejects_empty_vector():
    with pytest.raises(ValueError, match="boş olmamalıdır"):
        cosine_similarity([], [])


def test_cosine_similarity_rejects_two_dimensional_vector():
    with pytest.raises(ValueError, match="tek boyutlu"):
        cosine_similarity([[1, 2]], [[1, 2]])


@pytest.mark.parametrize("invalid_value", [float("nan"), float("inf"), -float("inf")])
def test_cosine_similarity_rejects_non_finite_values(invalid_value):
    with pytest.raises(ValueError, match="sonlu sayılar"):
        cosine_similarity([1, invalid_value], [1, 2])


def test_cosine_similarity_stays_in_mathematical_range():
    result = cosine_similarity([0.1, 0.2, 0.3], [0.1, 0.2, 0.3])

    assert -1.0 <= result <= 1.0


def test_keyword_score_empty_query():
    assert keyword_score("", "tenis kortu") == 0.0


@pytest.mark.parametrize(
    ("query", "content", "expected"),
    [
        ("tenis kort", "Tenis bir kort üzerinde oynanır.", 1.0),
        ("futbol kale", "Tenis bir raket sporudur.", 0.0),
        ("çim zemin", "Wimbledon çim zeminde oynanır.", 1.0),
        ("tenis", "", 0.0),
    ],
)
def test_keyword_score_scenarios(query, content, expected):
    assert keyword_score(query, content) == pytest.approx(expected)


def test_keyword_score_counts_repeated_query_word_once():
    assert keyword_score("tenis tenis kort", "Tenis bir spordur.") == pytest.approx(0.5)


def test_keyword_score_preserves_substring_matching():
    assert keyword_score("tenis", "Profesyonel tenisçiler") == pytest.approx(1.0)


def test_hybrid_score_uses_expected_weights():
    assert hybrid_score(0.8, 0.5) == pytest.approx(0.71)


@pytest.mark.parametrize(
    ("semantic_weight", "keyword_weight"),
    [
        (-0.1, 1.1),
        (1.1, -0.1),
        (0.5, 0.4),
        (float("nan"), 0.3),
        (float("inf"), 0.0),
    ],
)
def test_hybrid_score_rejects_invalid_weights(semantic_weight, keyword_weight):
    with pytest.raises(ValueError):
        hybrid_score(0.8, 0.5, semantic_weight, keyword_weight)


@pytest.mark.parametrize(
    ("semantic_score", "keyword_match_score"),
    [
        (float("nan"), 0.5),
        (float("inf"), 0.5),
        (-float("inf"), 0.5),
        (0.8, float("nan")),
        (0.8, float("inf")),
        (0.8, -float("inf")),
    ],
)
def test_hybrid_score_rejects_non_finite_scores(
    semantic_score, keyword_match_score
):
    with pytest.raises(ValueError, match="skorları sonlu"):
        hybrid_score(semantic_score, keyword_match_score)


def test_importing_retrieval_has_no_foundry_or_database_side_effects(monkeypatch):
    import sqlite3

    monkeypatch.setattr(
        sqlite3,
        "connect",
        lambda *args, **kwargs: pytest.fail("Import sırasında SQLite açılmamalı."),
    )
    monkeypatch.delitem(sys.modules, "retrieval", raising=False)
    monkeypatch.delitem(sys.modules, "foundry_local_sdk", raising=False)

    imported_module = importlib.import_module("retrieval")

    assert imported_module.get_top_chunks is not None
    assert "foundry_local_sdk" not in sys.modules
