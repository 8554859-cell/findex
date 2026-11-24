import json

import pytest
from hypothesis import given, strategies as st
from typer.testing import CliRunner

from findex.cli import app
from findex.index import build_index
from findex.query import parse
from findex.search import combine, merge
from findex.tokenize import tokenize


@pytest.mark.parametrize(("text", "expected"), [
    ("HELLO", ["hello"]), ("КИЇВ", ["київ"]), ("п’ять", ["п'ять"]),
    ("a-b", ["a", "b"]), ("123", ["123"]), ("", []), ("!!!", []),
    ("Straße", ["strasse"]), ("café", ["café"]), ("a_b", ["a", "b"]),
])
def test_tokens(text, expected):
    assert list(tokenize(text)) == expected


@pytest.mark.parametrize("query", ["(", "a OR", "NOT", "a AND", '"bad', ")"])
def test_bad_query(query):
    with pytest.raises(ValueError):
        parse(query)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_merge_and(a, b):
    assert merge(sorted(a), sorted(b), "AND") == sorted(a & b)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_merge_or(a, b):
    assert combine(sorted(a), sorted(b), "OR", "merge") == sorted(a | b)


@given(st.sets(st.integers()), st.sets(st.integers()))
def test_merge_not(a, b):
    assert merge(sorted(a), sorted(b), "NOT") == sorted(a - b)


def test_sorted(corpus):
    ix = build_index(corpus)
    for postings in ix.postings.values():
        assert [p.doc_id for p in postings] == sorted(p.doc_id for p in postings)


def test_cli(corpus):
    runner = CliRunner()
    path = corpus / "index.json"
    assert runner.invoke(app, ["index", str(corpus), "--out", str(path)]).exit_code == 0
    result = runner.invoke(app, ["search", str(path), "python", "--json"])
    assert result.exit_code == 0
    assert len([json.loads(line) for line in result.stdout.splitlines()]) == 2
    assert runner.invoke(app, ["stats", str(path)]).exit_code == 0
    assert runner.invoke(app, ["search", str(path), "("]).exit_code != 0
