"""Measure each repetition in an isolated interpreter (Linux)."""

import argparse
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
from pathlib import Path
from time import perf_counter

from findex.index import build_measured


def one(root, executor, workers):
    start = perf_counter()
    index, merge_seconds = build_measured(root, True, None, workers, executor)
    wall = perf_counter() - start
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "wall": wall,
        "cpu": own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime,
        "rss_mib": own.ru_maxrss / 1024,
        "merge": merge_seconds,
        "docs": index.num_docs,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--free", action="store_true")
    parser.add_argument("--one", nargs=2)
    args = parser.parse_args()
    if args.one:
        print(json.dumps(one(args.root, args.one[0], int(args.one[1]))))
        return
    gil = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(
        "LAB05_MACHINE "
        + json.dumps(
            {
                "python": sys.version,
                "gil": gil,
                "cpu_count": os.cpu_count(),
                "affinity": len(os.sched_getaffinity(0)),
                "platform": platform.platform(),
                "cpu_model": next(
                    (
                        line.split(":", 1)[1].strip()
                        for line in Path("/proc/cpuinfo").read_text().splitlines()
                        if line.startswith("model name")
                    ),
                    "unknown",
                ),
            }
        ),
        flush=True,
    )
    for executor in ["threads"] if args.free else ["serial", "threads", "processes"]:
        for workers in sorted({1, 2, 4, 8, os.cpu_count() or 1}):
            samples = []
            for _ in range(3):
                command = [
                    sys.executable,
                    __file__,
                    str(args.root),
                    "--one",
                    executor,
                    str(workers),
                ]
                samples.append(json.loads(subprocess.check_output(command, text=True)))
            row = {
                key: statistics.median(s[key] for s in samples) for key in samples[0]
            }
            row.update(executor=executor, workers=workers, gil=gil, samples=samples)
            print("LAB05_ROW " + json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
