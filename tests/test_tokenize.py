from findex.tokenize import tokenize


def test_mixed_case():
    assert list(tokenize("Python PYTHON")) == ["python", "python"]


def test_cyrillic():
    assert list(tokenize("Київ УКРАЇНА")) == ["київ", "україна"]


def test_accent():
    assert list(tokenize("café cafe\u0301")) == ["café", "café"]


def test_punctuation():
    assert list(tokenize("Hello, world!")) == ["hello", "world"]


def test_empty():
    assert list(tokenize("")) == []


def test_apostrophes():
    assert list(tokenize("п’ять don't пʼять")) == ["п'ять", "don't", "п'ять"]


def test_hyphens():
    assert list(tokenize("open-source a_b")) == ["open", "source", "a", "b"]


def test_digits():
    assert list(tokenize("IPv6 3.14")) == ["ipv6", "3", "14"]


def test_casefold():
    assert list(tokenize("Straße STRASSE")) == ["strasse", "strasse"]
