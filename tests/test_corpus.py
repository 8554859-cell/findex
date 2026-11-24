import inspect

from findex.corpus import iter_documents
from findex.stats import collect_stats
from findex.tokenize import tokenize


def test_stream(tmp_path):
    (tmp_path / "a.txt").write_text("Hello hello", encoding="utf-8")
    (tmp_path / "bad.txt").write_bytes(b"\xff")
    folder = tmp_path / "sub"
    folder.mkdir()
    (folder / "b.txt").write_text("world", encoding="utf-8")
    assert inspect.isgeneratorfunction(iter_documents)
    assert inspect.isgeneratorfunction(tokenize)
    docs = list(iter_documents(tmp_path))
    assert {doc.doc_id for doc in docs} == {"a.txt", "sub/b.txt"}
    lazy = collect_stats(tmp_path)
    assert lazy == collect_stats(tmp_path, eager=True)
    assert lazy[0] == 2
    assert lazy[1] == {"hello": 2, "world": 1}
    assert collect_stats(tmp_path, limit=1)[0] == 1
