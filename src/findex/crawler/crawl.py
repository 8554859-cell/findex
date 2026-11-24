"""Queue-based asynchronous crawler."""
import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from time import monotonic
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx

from findex.crawler.fetch import USER_AGENT, fetch
from findex.crawler.robots import RobotsCache

logger = logging.getLogger("findex.crawler")


def canonicalize(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path.rstrip("/") or "/", urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True))), ""))


class Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.words: list[str] = []
        self.titles: list[str] = []
        self.in_title = False
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if tag == "title":
            self.in_title = True
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data: str) -> None:
        if not self.hidden and data.strip():
            self.words.append(data.strip())
            if self.in_title:
                self.titles.append(data.strip())


@dataclass(frozen=True)
class Page:
    url: str
    title: str
    text: str
    fetched_at: str


@dataclass
class CrawlStats:
    pages: int = 0
    errors: int = 0
    in_flight: int = 0
    queue_depth: int = 0


async def crawl(
    seeds: list[str], *, max_pages: int = 500, concurrency: int = 10,
    per_host: int = 2, allowed_domains: set[str], delay: float = 0.05,
    stats: CrawlStats | None = None, transport: httpx.AsyncBaseTransport | None = None,
) -> AsyncIterator[Page]:
    if min(max_pages, concurrency, per_host) < 1 or delay < 0:
        raise ValueError("Invalid crawl limits")
    metrics = stats if stats is not None else CrawlStats()
    frontier: asyncio.Queue[str] = asyncio.Queue()
    results: asyncio.Queue[Page | None] = asyncio.Queue(maxsize=concurrency)
    seen: set[str] = set()
    domains = {domain.lower() for domain in allowed_domains}
    global_limit = asyncio.Semaphore(concurrency)
    host_limits: dict[str, asyncio.Semaphore] = {}
    host_locks: dict[str, asyncio.Lock] = {}
    last: dict[str, float] = {}
    attempted = 0

    def enqueue(url: str) -> None:
        try:
            url = canonicalize(url)
            parts = urlsplit(url)
            if parts.scheme not in ("http", "https") or parts.hostname not in domains or parts.username:
                return
        except ValueError:
            return
        if url not in seen:
            seen.add(url)
            frontier.put_nowait(url)
            metrics.queue_depth = frontier.qsize()

    for seed in seeds:
        enqueue(seed)
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, transport=transport, trust_env=False) as client:
        robots = RobotsCache(client)

        async def worker() -> None:
            nonlocal attempted
            while True:
                url = await frontier.get()
                metrics.queue_depth = frontier.qsize()
                try:
                    if attempted >= max_pages:
                        continue
                    attempted += 1
                    host = urlsplit(url).hostname or ""
                    async with global_limit, host_limits.setdefault(host, asyncio.Semaphore(per_host)):
                        metrics.in_flight += 1
                        try:
                            if not await robots.allowed(url):
                                logger.info("url=%s robots denied", url)
                                continue
                            async with host_locks.setdefault(host, asyncio.Lock()):
                                await asyncio.sleep(max(0.0, last.get(host, 0.0) + delay - monotonic()))
                                last[host] = monotonic()
                            response = await fetch(client, url)
                        finally:
                            metrics.in_flight -= 1
                    if response.status != 200:
                        metrics.errors += 1
                        continue
                    if "html" not in response.content_type.lower():
                        continue
                    parser = Extractor()
                    await asyncio.to_thread(parser.feed, response.body.decode("utf-8", errors="replace"))
                    for link in parser.links:
                        enqueue(urljoin(url, link))
                    metrics.pages += 1
                    await results.put(Page(url, " ".join(parser.titles) or url,
                                           " ".join(parser.words), datetime.now(timezone.utc).isoformat()))
                finally:
                    frontier.task_done()

        async def supervise() -> None:
            async with asyncio.TaskGroup() as group:
                workers = [group.create_task(worker()) for _ in range(concurrency)]
                await frontier.join()
                for task in workers:
                    task.cancel()
            await results.put(None)

        supervisor = asyncio.create_task(supervise())
        try:
            while True:
                page = await results.get()
                if page is None:
                    await supervisor
                    break
                yield page
        finally:
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)
