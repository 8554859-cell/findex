"""Measure corpus statistics with eager and lazy pipelines."""

import argparse
import tracemalloc
from collections import Counter
from collections.abc import Iterator
from itertools import islice
from pathlib import Path
from time import perf_counter

from findex.corpus import Document, iter_documents
from findex.tokenize import tokenize


def collect_stats(
    root: Path, limit: int | None = None, eager: bool = False
) -> tuple[int, Counter[str]]:
    docs: Iterator[Document] = iter_documents(root)
    if limit is not None:
        docs = islice(docs, limit)
    counts: Counter[str] = Counter()
    n_docs = 0
    if eager:
        documents = list(docs)
        tokens = [list(tokenize(doc.text)) for doc in documents]
        n_docs = len(documents)
        for words in tokens:
            counts.update(words)
    else:
        for doc in docs:
            n_docs += 1
            counts.update(tokenize(doc.text))
    return n_docs, counts


def measure(
    root: Path, limit: int | None = None, eager: bool = False
) -> tuple[tuple[int, Counter[str]], float, int]:
    tracemalloc.start()
    start = perf_counter()
    try:
        result = collect_stats(root, limit, eager)
        elapsed = perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        return result, elapsed, peak
    finally:
        tracemalloc.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error("Corpus directory does not exist")
    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be nonnegative")
    lazy, elapsed, peak = measure(args.root, args.limit)
    n, counts = lazy
    print(f"Documents: {n}")
    print(f"Tokens: {sum(counts.values())}")
    print(f"Vocabulary: {len(counts)}")
    for term, count in counts.most_common(50):
        print(f"{term}: {count}")
    print(f"lazy: {n} documents | {peak / 1048576:.6f} MiB | {elapsed:.6f} s")
    if args.compare:
        eager, elapsed, peak = measure(args.root, args.limit, True)
        print(
            f"eager: {eager[0]} documents | {peak / 1048576:.6f} MiB | {elapsed:.6f} s"
        )
        if eager != lazy:
            raise RuntimeError("Statistics differ")
        print("Statistics match")


if __name__ == "__main__":
    main()
