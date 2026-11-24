from findex.index import Posting, build_index
from findex.search import search
from findex.store import load, save


def test_index_search_store(tmp_path):
    (tmp_path / "a.txt").write_text("alpha alpha beta", encoding="utf-8")
    (tmp_path / "b.txt").write_text("beta gamma", encoding="utf-8")
    (tmp_path / "c.txt").write_text("gamma", encoding="utf-8")
    index = build_index(tmp_path)
    a = next(i for i, m in index.doc_meta.items() if m.title == "a")
    b = next(i for i, m in index.doc_meta.items() if m.title == "b")
    c = next(i for i, m in index.doc_meta.items() if m.title == "c")
    assert index.postings["alpha"] == [Posting(a, 2)]
    assert index.doc_lengths[a] == 3
    assert len({Posting(a, 2), Posting(a, 2)}) == 1
    for engine in ("merge", "set"):
        assert search(index, "alpha beta", engine) == [a]
        assert search(index, "alpha OR gamma", engine) == sorted([a, b, c])
        assert search(index, "gamma NOT beta", engine) == [c]
        assert search(index, "NOT beta", engine) == [c]
        assert search(index, "missing", engine) == []
    for name in ("index.bin", "index.json"):
        path = tmp_path / name
        save(index, path)
        assert load(path) == index
