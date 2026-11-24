"""Measure gap coding and mmap on replicated posting lists."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import numpy as np

from findex.compact import decode_gaps, mapped_postings, write_postings
from findex.store import load


def main():
    index = load(Path("data/index.json"))
    term = max(index.postings, key=index.df)
    ids, tfs = index.arrays.postings[term]
    for factor in (1, 10):
        large_ids = np.concatenate(
            [ids + index.num_docs * i for i in range(factor)]
        ).astype(np.int32)
        large_tfs = np.tile(tfs, factor)
        with TemporaryDirectory() as directory:
            path = Path(directory)
            start = perf_counter()
            mapped_ids, mapped_tfs = mapped_postings(path, large_ids, large_tfs)
            mapped_ms = (perf_counter() - start) * 1000
            start = perf_counter()
            write_postings(path / "gaps.npz", large_ids, large_tfs)
            compressed_ms = (perf_counter() - start) * 1000
            start = perf_counter()
            with np.load(path / "gaps.npz", allow_pickle=False) as archive:
                decoded = decode_gaps(archive["gaps"])
                assert np.array_equal(archive["tfs"], mapped_tfs)
            assert np.array_equal(decoded, mapped_ids)
            decode_ms = (perf_counter() - start) * 1000
            print(
                "LAB08_LARGE "
                + json.dumps(
                    {
                        "factor": factor,
                        "virtual_docs": factor * index.num_docs,
                        "postings": len(large_ids),
                        "raw_bytes": large_ids.nbytes + large_tfs.nbytes,
                        "compressed_bytes": (path / "gaps.npz").stat().st_size,
                        "mmap_write_open_ms": mapped_ms,
                        "compress_ms": compressed_ms,
                        "decode_ms": decode_ms,
                    }
                )
            )


if __name__ == "__main__":
    main()
