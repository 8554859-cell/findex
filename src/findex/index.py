"""Build a streaming inverted index."""

import argparse
import tracemalloc
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from functools import cached_property
from itertools import islice
from multiprocessing import get_context
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from findex.vector import Arrays

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

    @cached_property
    def arrays(self) -> Arrays:
        from findex.vector import Arrays

        return Arrays(self)

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


ExecutorName = Literal["serial", "threads", "processes"]
PartialIndex = Index


def build_partial(
    doc_paths: list[Path], root: Path, start_id: int = 0, positions: bool = False
) -> PartialIndex:
    postings: defaultdict[str, list[Posting]] = defaultdict(list)
    lengths: dict[int, int] = {}
    meta: dict[int, DocMeta] = {}
    for number, path in enumerate(doc_paths, start_id):
        text = path.read_text(encoding="utf-8")
        counts: Counter[str] = Counter()
        offsets: defaultdict[str, list[int]] = defaultdict(list)
        for offset, token in enumerate(tokenize(text)):
            counts[token] += 1
            if positions:
                offsets[token].append(offset)
        lengths[number] = sum(counts.values())
        meta[number] = DocMeta(path.relative_to(root).as_posix(), path.stem)
        for term, tf in counts.items():
            postings[term].append(Posting(number, tf, tuple(offsets[term])))
    return Index(dict(postings), lengths, meta)


def merge(partials: Iterable[PartialIndex]) -> Index:
    postings: defaultdict[str, list[Posting]] = defaultdict(list)
    lengths: dict[int, int] = {}
    meta: dict[int, DocMeta] = {}
    for partial in partials:
        if lengths.keys() & partial.doc_lengths.keys():
            raise ValueError("Duplicate document ID")
        lengths.update(partial.doc_lengths)
        meta.update(partial.doc_meta)
        for term, records in partial.postings.items():
            postings[term].extend(records)
    return Index(dict(postings), lengths, meta)


def build_measured(
    root: Path,
    positions: bool = False,
    limit: int | None = None,
    workers: int = 1,
    executor: ExecutorName = "serial",
) -> tuple[Index, float]:
    if root.is_file() and root.suffix == ".jsonl":
        postings: defaultdict[str, list[Posting]] = defaultdict(list)
        lengths: dict[int, int] = {}
        meta: dict[int, DocMeta] = {}
        for number, doc in enumerate(islice(iter_documents(root), limit)):
            offsets: defaultdict[str, list[int]] = defaultdict(list)
            for offset, token in enumerate(tokenize(doc.text)):
                offsets[token].append(offset)
            lengths[number] = sum(map(len, offsets.values()))
            meta[number] = DocMeta(doc.doc_id, doc.doc_id)
            for term, places in offsets.items():
                postings[term].append(
                    Posting(number, len(places), tuple(places) if positions else ())
                )
        return Index(dict(postings), lengths, meta), 0.0
    if workers < 1:
        raise ValueError("workers must be positive")
    paths = list(islice((p for p in root.rglob("*.txt") if p.is_file()), limit))
    size = max(1, (len(paths) + workers - 1) // workers)
    chunks = [
        (paths[i : i + size], root, i, positions) for i in range(0, len(paths), size)
    ]
    if executor == "serial":
        partials = [build_partial(paths, root, 0, positions)]
    elif executor in ("threads", "processes"):
        pool = (
            ThreadPoolExecutor(max_workers=workers)
            if executor == "threads"
            else ProcessPoolExecutor(
                max_workers=workers, mp_context=get_context("spawn")
            )
        )
        with pool:
            futures = [pool.submit(build_partial, *chunk) for chunk in chunks]
            partials = [future.result() for future in futures]
    else:
        raise ValueError("Unknown executor")
    start = perf_counter()
    index = merge(partials)
    return index, perf_counter() - start


@timed
def build_index(
    root: Path,
    positions: bool = False,
    limit: int | None = None,
    workers: int = 1,
    executor: ExecutorName = "serial",
) -> Index:
    return build_measured(root, positions, limit, workers, executor)[0]


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
    print(f"Elapsed: {perf_counter() - start:.6f}s; peak: {peak / 1048576:.3f} MiB")


if __name__ == "__main__":
    main()
