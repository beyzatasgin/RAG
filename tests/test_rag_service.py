from __future__ import annotations

from types import SimpleNamespace

import pytest

from rag_service import RagGenerationError, RagRetrievalError, RagService
from retriever import RetrievalResult


def item(source="a.txt", chunk=0, content="bağlam", score=0.8):
    return RetrievalResult(source, chunk, content, score, 0.2, score)


class FakeRetriever:
    def __init__(self, results=None, error=None):
        self.results = results or []
        self.error = error
        self.calls = []

    def search(self, question, **kwargs):
        self.calls.append((question, kwargs))
        if self.error:
            raise self.error
        return self.results


class FakeChat:
    def __init__(self, parts=("Cevap [K1]",), error=None):
        self.parts = parts
        self.error = error
        self.calls = []
        self.settings = SimpleNamespace(max_tokens=None, temperature=None, n=None)

    def complete_streaming_chat(self, messages):
        self.calls.append(messages)
        if self.error:
            raise self.error
        for part in self.parts:
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=part))]
            )


def test_full_flow_and_real_metadata_sources():
    retriever = FakeRetriever([item("grand_slam.txt", 2)])
    chat = FakeChat()
    answer = RagService(retriever, chat).answer("Turnuvalar?", top_k=2, min_score=.2)
    assert answer.answer == "Cevap [K1]"
    assert answer.sources[0].source == "grand_slam.txt"
    assert retriever.calls[0][1] == {"top_k": 2, "min_score": .2}
    assert chat.calls[0][0]["role"] == "system"
    assert chat.settings.max_tokens == 192
    assert chat.settings.temperature == 0.0
    assert chat.settings.n == 1
    assert answer.has_valid_inline_citation is True


def test_duplicate_source_chunk_is_removed():
    answer = RagService(chat_client=FakeChat()).generate_from_results(
        "Soru?", [item(), item(content="duplicate")]
    )
    assert answer.retrieved_count == 2
    assert answer.used_context_count == 1
    assert len(answer.sources) == 1


def test_no_results_never_calls_chat():
    chat = FakeChat()
    answer = RagService(FakeRetriever([]), chat).answer("Soru?")
    assert answer.insufficient_context is True
    assert answer.answer == "Belgelerde bu bilgi bulunamadı."
    assert not chat.calls
    assert answer.has_valid_inline_citation is False


@pytest.mark.parametrize("question", ["", "  "])
def test_empty_question(question):
    with pytest.raises(ValueError):
        RagService(FakeRetriever()).answer(question)


def test_reasoning_is_hidden():
    answer = RagService(chat_client=FakeChat(("<think>gizli</think>", "Yanıt"))).generate_from_results(
        "Soru?", [item()]
    )
    assert answer.answer == "Yanıt"


def test_empty_visible_answer_is_error_with_cause():
    with pytest.raises(RagGenerationError) as caught:
        RagService(chat_client=FakeChat(("<think>gizli</think>",))).generate_from_results(
            "Soru?", [item()]
        )
    assert caught.value.__cause__ is not None


def test_unclosed_reasoning_is_not_exposed():
    with pytest.raises(RagGenerationError):
        RagService(chat_client=FakeChat(("<think>yarım reasoning",))).generate_from_results(
            "Soru?", [item()]
        )


def test_retrieval_error_has_cause():
    with pytest.raises(RagRetrievalError) as caught:
        RagService(FakeRetriever(error=RuntimeError("boom"))).answer("Soru?")
    assert isinstance(caught.value.__cause__, RuntimeError)


def test_generation_error_has_cause():
    with pytest.raises(RagGenerationError) as caught:
        RagService(chat_client=FakeChat(error=RuntimeError("boom"))).generate_from_results(
            "Soru?", [item()]
        )
    assert isinstance(caught.value.__cause__, RuntimeError)


def test_only_context_that_fits_is_a_source():
    answer = RagService(chat_client=FakeChat()).generate_from_results(
        "Soru?", [item(content="kısa"), item("b.txt", 1, "x" * 500)], context_budget=70
    )
    assert [source.source for source in answer.sources] == ["a.txt"]


def test_unknown_model_citation_is_not_a_source():
    answer = RagService(chat_client=FakeChat(("Yanıt [K99]",))).generate_from_results(
        "Soru?", [item()]
    )
    assert answer.unknown_citations == ("[K99]",)
    assert answer.has_valid_inline_citation is False
    assert all(source.label != "[K99]" for source in answer.sources)


def test_model_answer_is_not_rewritten_when_citation_is_missing():
    answer = RagService(chat_client=FakeChat(("Citation içermeyen yanıt",))).generate_from_results(
        "Soru?", [item("gercek.txt", 4)]
    )
    assert answer.answer == "Citation içermeyen yanıt"
    assert answer.valid_citations == ()
    assert answer.sources[0].source == "gercek.txt"
    assert answer.sources[0].chunk_index == 4
