"""Persist indexes in pickle or JSON."""
import json
import pickle
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from findex.index import DocMeta, Index, Posting
from findex.timing import timed


def save(index: Index, path: Path) -> None:
    path = Path(path)
    if path.suffix == ".json":
        data = {
            "postings": {k: [[p.doc_id, p.tf, p.positions] for p in v] for k, v in index.postings.items()},
            "lengths": index.doc_lengths,
            "meta": {k: [v.path, v.title] for k, v in index.doc_meta.items()},
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    else:
        # Use primitive records so CLI execution as __main__ remains portable.
        data = (
            {k: [(p.doc_id, p.tf, p.positions) for p in v] for k, v in index.postings.items()},
            index.doc_lengths,
            {k: (v.path, v.title) for k, v in index.doc_meta.items()},
        )
        path.write_bytes(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))


@timed
def load(path: Path) -> Index:
    path = Path(path)
    if path.suffix == ".json":
        data = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        raw = (data["postings"], data["lengths"], data["meta"])
    else:
        # Never load an untrusted pickle: deserialization can execute arbitrary code.
        raw = pickle.loads(path.read_bytes())
    postings, lengths, meta = cast(tuple[dict[str, list[tuple[int, int] | tuple[int, int, tuple[int, ...]]]], dict[int | str, int], dict[int | str, tuple[str, str]]], raw)
    return Index(
        {k: [Posting(p[0], p[1], tuple(p[2]) if len(p) > 2 else ()) for p in v] for k, v in postings.items()},
        {int(k): v for k, v in lengths.items()},
        {int(k): DocMeta(*v) for k, v in meta.items()},
    )


@contextmanager
def open_index(path: Path) -> Iterator[Index]:
    # load uses Path methods that close files before returning, even on errors.
    index = load(path)
    try:
        yield index
    finally:
        del index
