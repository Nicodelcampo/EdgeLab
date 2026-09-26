"""Precisión temporal int64 ns: round-trip Python -> PyArrow -> Parquet -> back.
Conserva ns exactos, orden, duplicados legítimos; NO deduplica."""
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def test_int64_ns_roundtrip_preserves_exact(tmp_path):
    base = np.int64(1_700_000_000_000_000_000)
    offs = np.array([0, 1, 1, 2, 1_000_000, 1_000_000, 1_000_001, 2_000_000, 2_000_000, 3], np.int64)
    ts = base + offs
    tbl = pa.table({
        "ts_ns": pa.array(ts, pa.int64()),
        "ts_native": pa.array(ts, pa.timestamp("ns", tz="UTC")),
    })
    p = tmp_path / "t.parquet"
    pq.write_table(tbl, str(p))
    back = pq.read_table(str(p))
    r_int = back.column("ts_ns").to_numpy()
    r_nat = back.column("ts_native").to_numpy().astype("datetime64[ns]").astype(np.int64)
    assert np.array_equal(r_int, ts)
    assert np.array_equal(r_nat, ts)
    assert len(r_int) == 10  # sin dedup
    assert int((np.diff(r_int) == 0).sum()) == int((np.diff(ts) == 0).sum())
