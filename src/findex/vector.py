"""Vector scoring with deterministic tie breaking and cached compact postings."""

from dataclasses import dataclass
from functools import cached_property

import numpy as np
from numpy.typing import NDArray

from findex.index import Index
from findex.ranking import BM25, SearchResult, TfIdf


@dataclass
class Arrays:
    index: Index

    @cached_property
    def lengths(self) -> NDArray[np.int32]:
        result = np.zeros(max(self.index.doc_meta, default=-1) + 1, dtype=np.int32)
        for doc_id, length in self.index.doc_lengths.items():
            result[doc_id] = length
        return result

    @cached_property
    def postings(self) -> dict[str, tuple[NDArray[np.int32], NDArray[np.int32]]]:
        return {
            term: (
                np.fromiter((p.doc_id for p in ps), dtype=np.int32, count=len(ps)),
                np.fromiter((p.tf for p in ps), dtype=np.int32, count=len(ps)),
            )
            for term, ps in self.index.postings.items()
        }


def vector_rank(
    index: Index, ids: frozenset[int], terms: set[str], scorer: BM25 | TfIdf, k: int
) -> list[SearchResult]:
    if not ids or k <= 0:
        return []
    arrays = index.arrays
    scores = np.zeros(len(arrays.lengths), dtype=np.float64)
    for term in sorted(terms):
        pair = arrays.postings.get(term)
        if pair is None:
            continue
        docs, tfs = pair
        df = len(docs)
        if isinstance(scorer, BM25):
            idf = np.log1p((index.num_docs - df + 0.5) / (df + 0.5))
            norm = scorer.k1 * (
                1
                - scorer.b
                + scorer.b * arrays.lengths[docs] / max(index.avg_doc_length, 1e-12)
            )
            scores[docs] += idf * tfs * (scorer.k1 + 1) / (tfs + norm)
        else:
            scores[docs] += (1 + np.log(tfs)) * (
                1 + np.log((index.num_docs + 1) / (df + 1))
            )
    candidates = np.fromiter(ids, dtype=np.int32, count=len(ids))
    values = scores[candidates]
    n = min(k, len(candidates))
    cutoff = np.partition(values, len(values) - n)[len(values) - n]
    above = candidates[values > cutoff]
    tied = candidates[values == cutoff]
    remaining = n - len(above)
    chosen = np.concatenate(
        (
            above,
            tied[np.argpartition(tied, len(tied) - remaining)[-remaining:]]
            if remaining
            else tied[:0],
        )
    )
    return sorted(
        (
            SearchResult(float(scores[d]), int(d), index.doc_meta[int(d)].title)
            for d in chosen
        ),
        reverse=True,
    )
