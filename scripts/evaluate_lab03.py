"""Evaluate ranking on the real corpus and controlled corpus-derived probes."""
import json
from pathlib import Path

from findex.index import Index, Posting, build_index
from findex.ranking import BM25, Searcher, TfIdf


# Relevance is defined before ranking, by the source module and the concept.
# These are assistant-defined judgments, not labels supplied by the student.
QUERIES = [
    ("event AND loop", ("asyncio/",), "event loop"),
    ("regular AND expression", ("re/", "re-"), "regular expression"),
    ("json AND encode", ("json/",), "encode"),
    ("path AND directory", ("pathlib/", "pathlib-"), "directory"),
    ("thread AND lock", ("threading-",), "lock"),
    ("hash AND digest", ("hashlib-",), "digest"),
    ("date AND time", ("datetime-", "_pydatetime-"), "date"),
    ("socket AND address", ("socket-",), "address"),
    ("compress AND data", ("gzip-", "bz2-", "lzma-"), "compress"),
    ("argument AND parser", ("argparse-",), "argument"),
]


def main():
    root = Path("data/python_docs")
    index = build_index(root, positions=True)
    engine = Searcher(index, root)
    rows = []
    for query, prefixes, concept in QUERIES:
        relevant = {
            i for i, meta in index.doc_meta.items()
            if meta.path.startswith(prefixes)
            and concept in (root / meta.path).read_text(encoding="utf-8").casefold()
        }
        row = {"query": query, "relevant_count": len(relevant)}
        for scorer in (TfIdf(), BM25()):
            results = engine.search(query, scorer, 5)
            row[type(scorer).__name__] = sum(r.doc_id in relevant for r in results) / 5
            row[type(scorer).__name__ + "_paths"] = [index.doc_meta[r.doc_id].path for r in results]
        rows.append(row)
    terms = sorted(index.postings, key=lambda t: (index.df(t), t))
    rare = next(t for t in terms if index.df(t) == 1)
    common = terms[-1]
    bm = BM25()
    # Controlled counterfactual probes use actual corpus DF and mean length.
    length = max(20, round(index.avg_doc_length))
    probe = Index(index.postings, {0: length, 1: length, 2: length * 10}, index.doc_meta)
    probe.__dict__["avg_doc_length"] = index.avg_doc_length
    rare_score = bm.score(rare, Posting(0, 1), probe)
    common_score = bm.score(common, Posting(0, 1), probe)
    repeated19 = bm.score(common, Posting(0, 19), probe)
    repeated20 = bm.score(common, Posting(0, 20), probe)
    short = bm.score(common, Posting(0, 1), probe)
    long = bm.score(common, Posting(2, 1), probe)
    assert rare_score > common_score
    assert 0 < repeated20 - repeated19 < common_score * 0.1
    assert short > long
    print("LAB03_RESULT " + json.dumps({"rows": rows, "rare": rare, "common": common,
          "rare_score": rare_score, "common_score": common_score, "tf19": repeated19,
          "tf20": repeated20, "short": short, "long": long, "length": length,
          "docs": index.num_docs, "avgdl": index.avg_doc_length,
          "cache_hits": engine.ids.cache_info().hits}, ensure_ascii=False))


if __name__ == "__main__":
    main()
