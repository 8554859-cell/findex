import numpy as np

from findex.compact import decode_gaps, encode_gaps, mapped_postings, write_postings


def test_compact(tmp_path):
    ids = np.array([0, 4, 12, 20], dtype=np.int32)
    tfs = np.array([1, 2, 3, 4], dtype=np.int32)
    assert np.array_equal(decode_gaps(encode_gaps(ids)), ids)
    a, b = mapped_postings(tmp_path, ids, tfs)
    assert isinstance(a, np.memmap)
    assert np.array_equal(a, ids)
    assert np.array_equal(b, tfs)
    write_postings(tmp_path / "gaps.npz", ids, tfs)
    with np.load(tmp_path / "gaps.npz", allow_pickle=False) as archive:
        assert np.array_equal(decode_gaps(archive["gaps"]), ids)
