import pytest

from chunking import chunk_text


def test_empty_text_returns_empty_list():
    assert chunk_text(" \n\n ") == []


def test_short_paragraph_stays_whole():
    assert chunk_text("Kısa bir paragraf.", 50, 5) == ["Kısa bir paragraf."]


def test_long_paragraph_is_split_with_maximum_size():
    chunks = chunk_text("kelime " * 100, 80, 10)
    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 80 for chunk in chunks)


def test_paragraph_boundary_is_preferred():
    text = "Birinci paragraf.\n\nİkinci paragraf biraz daha uzun."
    assert chunk_text(text, 30, 0)[0] == "Birinci paragraf."


def test_overlap_repeats_tail_content():
    text = "bir iki üç dört beş altı yedi sekiz dokuz on"
    chunks = chunk_text(text, 24, 8)
    assert len(chunks) >= 2
    assert any(word in chunks[1].split() for word in chunks[0].split()[-2:])


def test_chunking_is_deterministic_and_ordered():
    text = "A " * 100 + "SON"
    first = chunk_text(text, 40, 5)
    assert first == chunk_text(text, 40, 5)
    assert first[-1].endswith("SON")


def test_turkish_characters_are_preserved():
    assert "öğrenci" in " ".join(chunk_text("Türkçe öğrenci içeriği", 12, 2))


@pytest.mark.parametrize("size,overlap", [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)])
def test_invalid_config_is_rejected(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("metin", size, overlap)
