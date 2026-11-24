"""Create the speedup chart from collected JSON rows."""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    rows = [
        json.loads(line.split("LAB05_ROW ", 1)[1])
        for line in Path(sys.argv[1]).read_text().splitlines()
        if "LAB05_ROW " in line
    ]
    baseline = next(
        r["wall"] for r in rows if r["executor"] == "serial" and r["workers"] == 1
    )
    for executor, gil in sorted({(r["executor"], r["gil"]) for r in rows}):
        group = sorted(
            (r for r in rows if r["executor"] == executor and r["gil"] == gil),
            key=lambda r: r["workers"],
        )
        plt.plot(
            [r["workers"] for r in group],
            [baseline / r["wall"] for r in group],
            marker="o",
            label=f"{executor}, GIL={gil}",
        )
    maximum = max(r["workers"] for r in rows)
    plt.plot([1, maximum], [1, maximum], "--", label="Ideal linear")
    plt.xlabel("Workers")
    plt.ylabel("Speedup vs serial")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig("lab05-speedup.png", dpi=110)


if __name__ == "__main__":
    main()
