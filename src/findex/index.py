"""Build a streaming inverted index."""
import argparse
import tracemalloc
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from itertools import islice
from pathlib import Path
from time import perf_counter

from findex.corpus import iter_documents
from findex.timing import timed
from findex.tokenize import tokenize


@dataclass(frozen=True, slots=True)
class Posting:
    doc_id: int
    tf: int
    positions: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class DocMeta:
    path: str
    title: str


@dataclass
class Index:
    postings: dict[str, list[Posting]]
    doc_lengths: dict[int, int]
    doc_meta: dict[int, DocMeta]


    def __len__(self) -> int:
        return len(self.postings)

    def __contains__(self, term: object) -> bool:
        return term in self.postings

    def __getitem__(self, term: str) -> list[Posting]:
        return self.postings[term]

    def __iter__(self) -> Iterator[str]:
        return iter(self.postings)

    def __repr__(self) -> str:
        return f"Index(terms={len(self)}, docs={self.num_docs})"

    @property
    def num_docs(self) -> int:
        return len(self.doc_meta)

    @cached_property
    def avg_doc_length(self) -> float:
        return sum(self.doc_lengths.values()) / max(1, self.num_docs)

    def doc_length(self, doc_id: int) -> int:
        return self.doc_lengths[doc_id]

    def df(self, term: str) -> int:
        return len(self.postings.get(term, []))


@timed
def build_index(root: Path, positions: bool = False, limit: int | None = None) -> Index:
    postings: defaultdict[str, list[Posting]] = defaultdict(list)
    lengths: dict[int, int] = {}
    meta: dict[int, DocMeta] = {}
    docs = iter_documents(root)
    for number, doc in enumerate(islice(docs, limit)):
        counts: Counter[str] = Counter()
        offsets: defaultdict[str, list[int]] = defaultdict(list)
        for offset, token in enumerate(tokenize(doc.text)):
            counts[token] += 1
            if positions:
                offsets[token].append(offset)
        lengths[number] = sum(counts.values())
        meta[number] = DocMeta(doc.doc_id, doc.path.stem)
        for term, tf in counts.items():
            postings[term].append(Posting(number, tf, tuple(offsets[term])))
    return Index(dict(postings), lengths, meta)


def main() -> None:
    from findex.store import save

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--positions", action="store_true")
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error("Corpus directory does not exist")
    tracemalloc.start()
    start = perf_counter()
    index = build_index(args.root, args.positions)
    save(index, args.out)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"Documents: {len(index.doc_meta)}; terms: {len(index.postings)}")
    print(f"Elapsed: {perf_counter()-start:.6f}s; peak: {peak/1048576:.3f} MiB")


if __name__ == "__main__":
    main()
