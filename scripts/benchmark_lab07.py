"""Measure 20 concurrent ASGI requests for each route mode."""
import asyncio
import json
import sys
from pathlib import Path
from time import perf_counter

import httpx

from findex.store import load
from findex.web.app import Settings, create_app, get_index, get_settings


async def measure(mode, index, corpus):
    app = create_app(mode)
    app.dependency_overrides[get_index] = lambda: index
    app.dependency_overrides[get_settings] = lambda: Settings(corpus_path=corpus)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async def request():
            start = perf_counter()
            response = await client.get("/search", params={"q": "python OR module", "k": 10})
            response.raise_for_status()
            return (perf_counter() - start) * 1000
        start = perf_counter()
        times = sorted(await asyncio.gather(*(request() for _ in range(20))))
        wall = perf_counter() - start
        print("LAB07_ASGI " + json.dumps({"mode": mode, "wall": wall, "rps": 20/wall, "p50": times[9], "p95": times[18], "p99": times[19]}))


if __name__ == "__main__":
    index = load(Path(sys.argv[1]))
    corpus = Path(sys.argv[2])
    for mode in ("async", "sync"):
        asyncio.run(measure(mode, index, corpus))
