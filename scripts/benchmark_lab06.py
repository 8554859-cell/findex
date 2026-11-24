"""Real loopback HTTP benchmark; no outside websites."""
import argparse
import asyncio
import json
import logging
import resource
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import perf_counter, sleep

from findex.crawler.crawl import CrawlStats, crawl


class Handler(BaseHTTPRequestHandler):
    retried = False

    def do_GET(self):
        sleep(0.025)
        if self.path == "/robots.txt":
            body = b"User-agent: *\nAllow: /\n"
            status = 200
        elif self.path == "/1" and not Handler.retried:
            Handler.retried = True
            body, status = b"retry", 429
        else:
            links = "".join(f'<a href="/{i}">page {i}</a>' for i in range(1, 200)) if self.path == "/" else ""
            body = f"<title>Local test {self.path}</title>Python asyncio documentation {links}".encode()
            status = 200
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        if status == 429:
            self.send_header("Retry-After", "0")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


async def run(seed, concurrency):
    stats = CrawlStats()
    start = perf_counter()
    async for _page in crawl([seed], max_pages=200, concurrency=concurrency,
                            per_host=5, allowed_domains={"127.0.0.1"}, delay=0.005, stats=stats):
        pass
    wall = perf_counter() - start
    return dict(concurrency=concurrency, pages=stats.pages, wall=wall,
                pages_per_second=stats.pages / wall, errors=stats.errors,
                rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("concurrency", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s",
                        handlers=[logging.FileHandler(f"crawl-{args.concurrency}.log"), logging.StreamHandler()])
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.request_queue_size = 64
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = asyncio.run(run(f"http://127.0.0.1:{server.server_port}/", args.concurrency), debug=True)
        assert result["pages"] == 200
        print("LAB06_ROW " + json.dumps(result))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
