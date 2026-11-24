"""Compare warmed scalar and vector scorers on identical candidate sets."""
import json
import statistics
from pathlib import Path
from time import perf_counter

from findex.query import parse, positive_terms
from findex.ranking import BM25, Searcher
from findex.store import load

index = load(Path("data/index.json"))
engine = Searcher(index)
common = max(index.postings, key=index.df)
rare = next(term for term in sorted(index.postings) if index.df(term) == 1 and term.isalpha())
for label, query in (("common", common), ("rare", rare), ("three", "python OR module OR class")):
    ids = engine.ids(query)
    terms = positive_terms(parse(query))
    scorer = BM25()
    def scalar(ids=ids, terms=terms, scorer=scorer):
        return engine.scalar_rank(ids, terms, scorer, 10)

    def vector(query=query, scorer=scorer):
        return engine.search(query, scorer, 10)
    scalar()
    vector()
    times = []
    for fn in (scalar, vector):
        samples = []
        for _ in range(30):
            start = perf_counter()
            fn()
            samples.append((perf_counter()-start)*1000)
        times.append(statistics.median(samples))
    print("LAB08_ROW "+json.dumps({"label":label,"query":query,"docs":len(ids),"scalar_ms":times[0],"numpy_ms":times[1],"speedup":times[0]/times[1]}))
