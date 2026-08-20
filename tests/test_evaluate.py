from __future__ import annotations

from evaluate import percentile, score_case, summarize


def test_score_case_hit_and_rank():
    case = {"id": "x", "answerable": True, "expected_sources": ["b.txt"]}
    result = score_case(case, ["a.txt", "b.txt"], 12.0)
    assert result.hit is True and result.reciprocal_rank == .5


def test_unanswerable_no_result_and_summary():
    answerable = score_case(
        {"id": "a", "answerable": True, "expected_sources": ["a.txt"]}, ["a.txt"], 10
    )
    unanswerable = score_case(
        {"id": "u", "answerable": False, "expected_sources": []}, [], 20
    )
    summary = summarize([answerable, unanswerable])
    assert summary["hit_rate_at_k"] == 1
    assert summary["mrr"] == 1
    assert summary["unanswerable_no_result_rate"] == 1
    assert summary["citation_validity_rate"] is None
    assert percentile([10, 20], .5) in {10, 20}
