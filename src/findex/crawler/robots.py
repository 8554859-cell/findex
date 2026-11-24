"""Cache robots rules by origin; fail closed on unavailable rules."""
import asyncio
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from findex.crawler.fetch import USER_AGENT, fetch


class RobotsCache:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.rules: dict[str, RobotFileParser] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    async def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        async with self.locks.setdefault(origin, asyncio.Lock()):
            if origin not in self.rules:
                parser = RobotFileParser()
                result = await fetch(self.client, origin + "/robots.txt")
                if result.status == 200:
                    parser.parse(result.body.decode("utf-8", errors="replace").splitlines())
                elif result.status == 404:
                    parser.parse(["User-agent: *", "Allow: /"])
                else:
                    parser.parse(["User-agent: *", "Disallow: /"])
                self.rules[origin] = parser
            return self.rules[origin].can_fetch(USER_AGENT, url)
