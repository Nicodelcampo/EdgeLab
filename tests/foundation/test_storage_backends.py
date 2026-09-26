"""Backends de storage (bridge): duckdb y polars sobre parquet — lectura
selectiva (predicate), join pequeño y preservación de int64. Se saltan
(skip) si el backend no está instalado."""
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

BASE = 1_700_000_000_000_000_000


def _make(tmp_path):
    n = 1000
    fact = pa.table({
        "ts_ns": pa.array([BASE + i * 1_000_000 for i in range(n)], pa.int64()),
        "price_ticks": pa.array([100 + (i % 50) for i in range(n)], pa.int64()),
        "key": pa.array([i % 10 for i in range(n)], pa.int64()),
    })
    dim = pa.table({
        "key": pa.array(list(range(10)), pa.int64()),
        "label": pa.array([f"k{i}" for i in range(10)], pa.string()),
    })
    p = str(tmp_path / "fact.parquet").replace("\\", "/")
    d = str(tmp_path / "dim.parquet").replace("\\", "/")
    pq.write_table(fact, p)
    pq.write_table(dim, d)
    return p, d


def test_duckdb_predicate_join_int64(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    p, d = _make(tmp_path)
    lo, hi = BASE + 100 * 1_000_000, BASE + 200 * 1_000_000
    c = duckdb.connect()
    cnt = c.execute(f"SELECT count(*) FROM read_parquet('{p}') WHERE ts_ns>={lo} AND ts_ns<{hi}").fetchone()[0]
    typ = c.execute(f"SELECT typeof(ts_ns) FROM read_parquet('{p}') LIMIT 1").fetchone()[0]
    j = c.execute(f"SELECT count(*) FROM read_parquet('{p}') f JOIN read_parquet('{d}') dd USING(key)").fetchone()[0]
    c.close()
    assert cnt == 100
    assert typ.upper() in ("BIGINT", "INT64")
    assert j == 1000


def test_polars_predicate_join_int64(tmp_path):
    pl = pytest.importorskip("polars")
    p, d = _make(tmp_path)
    lo, hi = BASE + 100 * 1_000_000, BASE + 200 * 1_000_000
    cnt = pl.scan_parquet(p).filter((pl.col("ts_ns") >= lo) & (pl.col("ts_ns") < hi)).select(pl.len()).collect().item()
    j = pl.scan_parquet(p).join(pl.scan_parquet(d), on="key").select(pl.len()).collect().item()
    assert cnt == 100
    assert j == 1000
    assert str(pl.read_parquet(p).schema["ts_ns"]) == "Int64"
