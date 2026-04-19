from app.utils.text import normalize_description


def test_uppercase():
    assert normalize_description("carrefour palermo") == "CARREFOUR PALERMO"


def test_strips_accents():
    assert normalize_description("Compra en café") == "COMPRA EN CAFE"


def test_collapses_whitespace():
    assert normalize_description("YPF   CABA   123") == "YPF CABA 123"


def test_strips_leading_trailing():
    assert normalize_description("  hola  ") == "HOLA"
