"""Bounded asynchronous HTTP requests."""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import perf_counter

import httpx

logger = logging.getLogger("findex.crawler")
USER_AGENT = "FindexLabCrawler/0.6 (+https://github.com/8554859-cell/findex)"


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    body: bytes
    elapsed: float
    content_type: str = ""


def retry_delay(value: str | None, attempt: int) -> float:
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                return max(
                    0.0,
                    (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds(),
                )
            except (ValueError, TypeError, OverflowError):
                pass
    return 0.25 * 2**attempt + random.uniform(0, 0.1)


async def fetch(
    client: httpx.AsyncClient, url: str, *, timeout: float = 10.0
) -> FetchResult:
    start = perf_counter()
    result = FetchResult(url, 0, b"", 0.0)
    for attempt in range(4):
        delay = retry_delay(None, attempt)
        try:
            async with asyncio.timeout(timeout):
                response = await client.get(url, follow_redirects=False)
            result = FetchResult(
                url,
                response.status_code,
                response.content,
                perf_counter() - start,
                response.headers.get("content-type", ""),
            )
            logger.info(
                "url=%s status=%d bytes=%d elapsed=%.4f attempt=%d",
                url,
                result.status,
                len(result.body),
                result.elapsed,
                attempt + 1,
            )
            if result.status != 429 and not 500 <= result.status <= 599:
                return result
            delay = retry_delay(response.headers.get("Retry-After"), attempt)
        except (TimeoutError, httpx.TimeoutException):
            result = FetchResult(url, 0, b"", perf_counter() - start)
            logger.warning("url=%s timeout attempt=%d", url, attempt + 1)
        except httpx.RequestError as exc:
            logger.warning("url=%s error=%s", url, exc)
            return FetchResult(url, 0, b"", perf_counter() - start)
        if attempt < 3:
            logger.info("url=%s retry delay=%.3f", url, delay)
            await asyncio.sleep(delay)
    return result
