from collections import Counter
from pathlib import Path

import pytest

from findex.corpus import iter_documents
from findex.index import DocMeta, Index, Posting, build_index, build_partial, merge
from findex.store import save
from findex.tokenize import tokenize


def test_lab04_equivalence(corpus: Path):
    postings = {}
    lengths = {}
    meta = {}
    for i, doc in enumerate(iter_documents(corpus)):
        counts = Counter(tokenize(doc.text))
        lengths[i] = sum(counts.values())
        meta[i] = DocMeta(doc.doc_id, doc.path.stem)
        for term, tf in counts.items():
            postings.setdefault(term, []).append(Posting(i, tf))
    assert build_index(corpus) == Index(postings, lengths, meta)


@pytest.mark.parametrize("positions", [False, True])
def test_parallel_identical(corpus: Path, tmp_path: Path, positions: bool):
    serial = build_index(corpus, positions)
    reference = tmp_path / "reference.bin"
    save(serial, reference)
    for executor in ("threads", "processes"):
        other = build_index(corpus, positions, workers=2, executor=executor)
        assert other == serial
        path = tmp_path / f"{executor}.bin"
        save(other, path)
        assert path.read_bytes() == reference.read_bytes()


def test_duplicate_ids(corpus: Path):
    part = build_partial([corpus / "a.txt"], corpus)
    with pytest.raises(ValueError, match="Duplicate"):
        merge([part, part])


def test_worker_error(corpus: Path):
    (corpus / "bad.txt").write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        build_index(corpus, workers=2, executor="processes")
