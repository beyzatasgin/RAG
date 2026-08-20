import pytest

from citations import validate_citations


@pytest.mark.parametrize(
    ("answer", "valid", "unknown"),
    [
        ("Bilgi [K1]", ("[K1]",), ()),
        ("[K1] ve [K2]", ("[K1]", "[K2]"), ()),
        ("[K1] tekrar [K1]", ("[K1]",), ()),
        ("uydurma [K99]", (), ("[K99]",)),
        ("etiket yok", (), ()),
        ("[K0] [K-1] K1 [Kx]", (), ()),
    ],
)
def test_citation_validation(answer, valid, unknown):
    result = validate_citations(answer, ["[K1]", "[K2]"])
    assert result.valid == valid
    assert result.unknown == unknown
