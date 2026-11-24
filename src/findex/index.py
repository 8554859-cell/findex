"""Build a streaming inverted index."""
import argparse
import tracemalloc
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from findex.corpus import iter_documents
from findex.tokenize import tokenize


@dataclass(frozen=True, slots=True)
class Posting:
    doc_id: int
    tf: int


@dataclass(frozen=True, slots=True)
class DocMeta:
    path: str
    title: str


@dataclass
class Index:
    postings: dict
    doc_lengths: dict
    doc_meta: dict


def build_index(root):
    postings = defaultdict(list)
    lengths = {}
    meta = {}
    for number, doc in enumerate(iter_documents(root)):
        counts = Counter(tokenize(doc.text))
        lengths[number] = sum(counts.values())
        meta[number] = DocMeta(doc.doc_id, doc.path.stem)
        for term, tf in counts.items():
            postings[term].append(Posting(number, tf))
    return Index(dict(postings), lengths, meta)


def main():
    from findex.store import save

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error("Corpus directory does not exist")
    tracemalloc.start()
    start = perf_counter()
    index = build_index(args.root)
    save(index, args.out)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"Documents: {len(index.doc_meta)}; terms: {len(index.postings)}")
    print(f"Elapsed: {perf_counter()-start:.6f}s; peak: {peak/1048576:.3f} MiB")


if __name__ == "__main__":
    main()
