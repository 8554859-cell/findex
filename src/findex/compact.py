"""Gap encoding and memory-mapped posting storage for large corpora."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray


def encode_gaps(ids: NDArray[np.int32]) -> NDArray[np.int32]:
    return np.diff(ids, prepend=np.int32(0))


def decode_gaps(gaps: NDArray[np.int32]) -> NDArray[np.int32]:
    return np.cumsum(gaps, dtype=np.int32)


def write_postings(
    path: Path, ids: NDArray[np.int32], tfs: NDArray[np.int32]
) -> None:
    gaps = encode_gaps(ids)
    np.savez_compressed(path, gaps=gaps, tfs=tfs)


def mapped_postings(
    path: Path, ids: NDArray[np.int32], tfs: NDArray[np.int32]
) -> tuple[NDArray[np.int32], NDArray[np.int32]]:
    np.save(path / "ids.npy", ids)
    np.save(path / "tfs.npy", tfs)
    return (
        np.load(path / "ids.npy", mmap_mode="r", allow_pickle=False),
        np.load(path / "tfs.npy", mmap_mode="r", allow_pickle=False),
    )
