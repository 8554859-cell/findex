"""Ranking strategies, cached query evaluation and highlighted snippets."""

import heapq
import logging
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from findex.index import Index, Posting
from findex.query import parse, positive_terms
from findex.timing import timed

logger = logging.getLogger(__name__)


class Scorer(Protocol):
    def score(self, term: str, posting: Posting, index: Index) -> float: ...


class TfIdf:
    def score(self, term: str, posting: Posting, index: Index) -> float:
        return (1 + math.log(posting.tf)) * (
            1 + math.log((index.num_docs + 1) / (index.df(term) + 1))
        )


@dataclass(frozen=True)
class BM25:
    k1: float = 1.5
    b: float = 0.75

    def score(self, term: str, posting: Posting, index: Index) -> float:
        df = index.df(term)
        idf = math.log1p((index.num_docs - df + 0.5) / (df + 0.5))
        ratio = index.doc_length(posting.doc_id) / max(index.avg_doc_length, 1e-12)
        norm = self.k1 * (1 - self.b + self.b * ratio)
        return idf * posting.tf * (self.k1 + 1) / (posting.tf + norm)


@dataclass(order=True, frozen=True)
class SearchResult:
    score: float
    doc_id: int
    title: str = field(compare=False)
    snippet: str = field(default="", compare=False)


def snippet(text: str, terms: set[str]) -> str:
    if not terms:
        return text[:160]
    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(t) for t in sorted(terms)) + r")\b", re.IGNORECASE
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return text[:160]
    best = max(
        matches, key=lambda m: sum(abs(n.start() - m.start()) <= 80 for n in matches)
    )
    start = max(0, best.start() - 80)
    end = min(len(text), best.end() + 80)
    return pattern.sub(lambda m: "**" + m.group() + "**", text[start:end])


class Searcher:
    def __init__(self, index: Index, corpus: Path | None = None) -> None:
        self.index = index
        self.corpus = corpus

        @lru_cache(maxsize=256)
        def ids(query: str) -> frozenset[int]:
            return frozenset(parse(query).evaluate(index))

        self.ids = ids

    @timed
    def search(
        self, query: str, scorer: Scorer | None = None, k: int = 10
    ) -> list[SearchResult]:
        scorer = scorer if scorer is not None else BM25()
        before = self.ids.cache_info().hits
        ids = self.ids(query)
        logger.info("cache hit=%s", self.ids.cache_info().hits > before)
        terms = positive_terms(parse(query))
        if isinstance(scorer, (BM25, TfIdf)):
            from findex.vector import vector_rank

            best = vector_rank(self.index, ids, terms, scorer, k)
        else:
            best = self.scalar_rank(ids, terms, scorer, k)
        if self.corpus is None:
            return best
        results: list[SearchResult] = []
        for result in best:
            path = self.corpus / self.index.doc_meta[result.doc_id].path
            text = path.read_text(encoding="utf-8")
            results.append(
                SearchResult(
                    result.score, result.doc_id, result.title, snippet(text, terms)
                )
            )
        return results

    def scalar_rank(
        self, ids: frozenset[int], terms: set[str], scorer: Scorer, k: int
    ) -> list[SearchResult]:
        scores = dict.fromkeys(ids, 0.0)
        for term in sorted(terms):
            for posting in self.index.postings.get(term, []):
                if posting.doc_id in scores:
                    scores[posting.doc_id] += scorer.score(term, posting, self.index)
        return heapq.nlargest(
            k,
            (
                SearchResult(s, d, self.index.doc_meta[d].title)
                for d, s in scores.items()
            ),
        )
