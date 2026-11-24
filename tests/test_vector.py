import pytest
from findex.index import build_index
from findex.query import parse, positive_terms
from findex.ranking import BM25, Searcher, TfIdf

@pytest.mark.parametrize("query", ["python", "python OR loop", "NOT python", "missing"])
@pytest.mark.parametrize("scorer", [BM25(), TfIdf()])
def test_identical_ranking(corpus, query, scorer):
    engine = Searcher(build_index(corpus, positions=True))
    expected = engine.scalar_rank(engine.ids(query), positive_terms(parse(query)), scorer, 10)
    actual = engine.search(query, scorer)
    assert [x.doc_id for x in actual] == [x.doc_id for x in expected]
    assert [x.score for x in actual] == pytest.approx([x.score for x in expected])

def test_benchmark_search(corpus, benchmark):
    engine = Searcher(build_index(corpus))
    engine.search("python")
    benchmark(engine.search, "python")

def test_benchmark_index(corpus, benchmark):
    benchmark(build_index, corpus)
