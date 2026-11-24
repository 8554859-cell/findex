from findex.index import build_index
from findex.query import And, Or, Term, parse
from findex.ranking import BM25, Searcher, TfIdf
from findex.store import open_index, save


def test_parser():
    assert parse("a OR b c") == Or(Term("a"), And(Term("b"), Term("c")))
    assert parse("(a OR b) NOT c") == (Term("a") | Term("b")) & ~Term("c")


def test_ranked(tmp_path):
    (tmp_path / "a.txt").write_text("event loop python", encoding="utf-8")
    (tmp_path / "b.txt").write_text("loop event python", encoding="utf-8")
    index = build_index(tmp_path, positions=True)
    assert len(index) == 3
    assert index.num_docs == 2
    assert "event" in index
    assert index.df("event") == 2
    assert index.avg_doc_length == 3
    path = tmp_path / "index.json"
    save(index, path)
    with open_index(path) as ix:
        for scorer in (BM25(), TfIdf()):
            engine = Searcher(ix, tmp_path)
            results = engine.search('"event loop"', scorer)
            assert len(results) == 1
            assert results[0].title == "a"
            assert "**event**" in results[0].snippet
            assert engine.search('"event loop"', scorer) == results
            assert engine.ids.cache_info().hits >= 1
