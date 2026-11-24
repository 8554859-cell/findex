import asyncio

import httpx

from findex.crawler.crawl import canonicalize, crawl
from findex.crawler.fetch import fetch
from findex.index import build_index


def test_canonical():
    assert (
        canonicalize("HTTP://EXAMPLE.COM/a/?z=2&a=1#x")
        == "http://example.com/a?a=1&z=2"
    )


def test_retry():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429 if calls == 1 else 200, headers={"Retry-After": "0"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert (await fetch(client, "https://example.com")).status == 200

    asyncio.run(run())
    assert calls == 2


def test_robots_and_budget():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text='<title>Test</title><a href="/a">a</a><a href="/a#x">again</a><a href="/private">no</a><a href="https://other.test/">other</a>',
        )

    async def run():
        return [
            p
            async for p in crawl(
                ["https://example.com"],
                max_pages=5,
                concurrency=3,
                per_host=2,
                allowed_domains={"example.com"},
                delay=0,
                transport=httpx.MockTransport(handler),
            )
        ]

    pages = asyncio.run(run(), debug=True)
    assert len(pages) == 2
    assert calls.count("/robots.txt") == 1
    assert "/private" not in calls
    assert calls.count("/a") == 1


def test_jsonl(tmp_path):
    path = tmp_path / "crawl.jsonl"
    path.write_text(
        '{"url":"https://example.com/","title":"T","text":"python async","fetched_at":"now"}\n'
    )
    assert build_index(path).df("python") == 1
