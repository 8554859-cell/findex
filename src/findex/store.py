"""Persist indexes in pickle or JSON."""
import json
import pickle
from pathlib import Path

from findex.index import DocMeta, Index, Posting


def save(index, path):
    path = Path(path)
    if path.suffix == ".json":
        data = {
            "postings": {k: [[p.doc_id, p.tf] for p in v] for k, v in index.postings.items()},
            "lengths": index.doc_lengths,
            "meta": {k: [v.path, v.title] for k, v in index.doc_meta.items()},
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    else:
        # Use primitive records so CLI execution as __main__ remains portable.
        data = (
            {k: [(p.doc_id, p.tf) for p in v] for k, v in index.postings.items()},
            index.doc_lengths,
            {k: (v.path, v.title) for k, v in index.doc_meta.items()},
        )
        path.write_bytes(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))


def load(path):
    path = Path(path)
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        postings, lengths, meta = data["postings"], data["lengths"], data["meta"]
    else:
        # Never load an untrusted pickle: deserialization can execute arbitrary code.
        postings, lengths, meta = pickle.loads(path.read_bytes())
    return Index(
        {k: [Posting(*p) for p in v] for k, v in postings.items()},
        {int(k): v for k, v in lengths.items()},
        {int(k): DocMeta(*v) for k, v in meta.items()},
    )
