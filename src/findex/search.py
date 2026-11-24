"""Boolean search using sorted merges or sets."""
import argparse
import tracemalloc
from pathlib import Path
from time import perf_counter

from findex.store import load
from findex.tokenize import tokenize


def merge(a, b, op):
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            if op != "NOT":
                out.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            if op != "AND":
                out.append(a[i])
            i += 1
        else:
            if op == "OR":
                out.append(b[j])
            j += 1
    if op != "AND":
        out.extend(a[i:])
    if op == "OR":
        out.extend(b[j:])
    return out


def combine(a, b, op, engine):
    if engine == "merge":
        return merge(a, b, op)
    left, right = set(a), set(b)
    return sorted({"AND": left & right, "OR": left | right, "NOT": left - right}[op])


def search(index, query, engine="merge"):
    parts = query.split()
    result = None
    op = "AND"
    negate = False
    pending = False
    for part in parts:
        if part in {"AND", "OR"}:
            if result is None or pending:
                raise ValueError("Unexpected Boolean operator")
            op, pending = part, True
            continue
        if part == "NOT":
            if negate:
                raise ValueError("Repeated NOT")
            negate, pending = True, True
            continue
        for term in tokenize(part):
            ids = [p.doc_id for p in index.postings.get(term, [])]
            if negate:
                ids = combine(sorted(index.doc_meta), ids, "NOT", engine)
            result = ids if result is None else combine(result, ids, op, engine)
            op, negate, pending = "AND", False, False
    if pending:
        raise ValueError("Missing operand")
    return result or []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("query")
    parser.add_argument("--engine", choices=["merge", "set"], default="merge")
    args = parser.parse_args()
    tracemalloc.start()
    start = perf_counter()
    index = load(args.index)
    for doc_id in search(index, args.query, args.engine):
        print(doc_id, index.doc_meta[doc_id].title, index.doc_meta[doc_id].path)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"Elapsed: {perf_counter()-start:.6f}s; peak: {peak/1048576:.3f} MiB")


if __name__ == "__main__":
    main()
