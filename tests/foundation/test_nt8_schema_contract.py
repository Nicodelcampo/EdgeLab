"""Contrato de schema para ticks NT8 (futuro Data Contract). Verifica que
int64 (precios/timestamps en ticks) y columnas nullable (bid/ask) sobreviven
el round-trip parquet en pyarrow y polars. Fixtures sintéticos."""
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

NT8_SCHEMA = pa.schema([
    ("ts_utc_ns", pa.int64()), ("sequence", pa.int64()),
    ("instrument", pa.string()), ("tick_type", pa.string()),
    ("price_ticks", pa.int64()), ("size", pa.int64()),
    ("bid_ticks", pa.int64()), ("ask_ticks", pa.int64()),
    ("source_file", pa.string()), ("source_row", pa.int64()),
])


def _fixture(n=8):
    return pa.table({
        "ts_utc_ns": pa.array([1_700_000_000_000_000_000 + i for i in range(n)], pa.int64()),
        "sequence": pa.array(list(range(n)), pa.int64()),
        "instrument": pa.array(["NQ"] * n, pa.string()),
        "tick_type": pa.array(["LAST", "BID", "ASK", "LAST", "BID", "ASK", "LAST", "LAST"], pa.string()),
        "price_ticks": pa.array([100 + i for i in range(n)], pa.int64()),
        "size": pa.array([1] * n, pa.int64()),
        "bid_ticks": pa.array([99 + i if i % 2 else None for i in range(n)], pa.int64()),
        "ask_ticks": pa.array([101 + i if i % 2 else None for i in range(n)], pa.int64()),
        "source_file": pa.array(["NQ 09-26.Last.txt"] * n, pa.string()),
        "source_row": pa.array(list(range(n)), pa.int64()),
    }, schema=NT8_SCHEMA)


def test_pyarrow_int64_and_nullable(tmp_path):
    p = tmp_path / "nt8.parquet"
    pq.write_table(_fixture(), str(p))
    t = pq.read_table(str(p))
    assert t.schema.field("price_ticks").type == pa.int64()
    assert t.schema.field("ts_utc_ns").type == pa.int64()
    assert t.column("bid_ticks").null_count > 0


def test_polars_reads_int64(tmp_path):
    pl = pytest.importorskip("polars")
    p = tmp_path / "nt8.parquet"
    pq.write_table(_fixture(), str(p))
    df = pl.read_parquet(str(p))
    assert df.height == 8
    assert str(df.schema["price_ticks"]) == "Int64"
    assert df["bid_ticks"].null_count() > 0
