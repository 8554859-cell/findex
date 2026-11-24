"""Measure three postings layouts, persistence and Boolean engines."""
import json
import pickle
import tempfile
import tracemalloc
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from findex.corpus import iter_documents
from findex.index import Posting, build_index
from findex.search import combine
from findex.store import load, save
from findex.tokenize import tokenize


@dataclass(frozen=True)
class Plain:
    doc_id: int
    tf: int


def layout(root, kind):
    table = defaultdict(list)
    for i, doc in enumerate(iter_documents(root)):
        for term, tf in Counter(tokenize(doc.text)).items():
            if kind == "array":
                if term not in table:
                    table[term] = array("I")
                table[term].extend((i, tf))
            else:
                table[term].append((Plain if kind == "plain" else Posting)(i, tf))
    return dict(table)


def main():
    root = Path("data/python_docs")
    results = {"layouts": [], "formats": [], "queries": []}
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        for kind in ("plain", "slots", "array"):
            tracemalloc.start()
            table = layout(root, kind)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            path = base / "layout.bin"
            path.write_bytes(pickle.dumps(table, protocol=pickle.HIGHEST_PROTOCOL))
            start = perf_counter()
            restored = pickle.loads(path.read_bytes())
            elapsed = perf_counter() - start
            assert restored == table
            results["layouts"].append([kind, peak, path.stat().st_size, elapsed])
            del restored, table
        index = build_index(root)
        for suffix in ("bin", "json"):
            path = base / f"index.{suffix}"
            start = perf_counter()
            save(index, path)
            saved = perf_counter() - start
            start = perf_counter()
            restored = load(path)
            loaded = perf_counter() - start
            assert restored == index
            results["formats"].append([suffix, path.stat().st_size, saved, loaded])
        terms = sorted(index.postings, key=lambda t: (len(index.postings[t]), t))
        for label, pair in (("rare", terms[:2]), ("common", terms[-2:])):
            a, b = ([p.doc_id for p in index.postings[t]] for t in pair)
            assert combine(a, b, "AND", "merge") == combine(a, b, "AND", "set")
            for engine in ("merge", "set"):
                start = perf_counter()
                for _ in range(100):
                    combine(a, b, "AND", engine)
                results["queries"].append([label, pair, engine, (perf_counter()-start)/100])
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
