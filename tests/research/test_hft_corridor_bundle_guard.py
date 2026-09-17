import importlib.util
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "build_hft_corridor_bundle.py"
spec = importlib.util.spec_from_file_location("build_hft_corridor_bundle", MODULE_PATH)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def write_ticks(path, timestamps):
    table = pa.table({"ts_utc_ns": pa.array(timestamps, type=pa.int64()), "price_ticks": pa.array([80000 + i for i in range(len(timestamps))], type=pa.int64())})
    pq.write_table(table, path, row_group_size=2)


def test_canonical_holdout_boundary_is_2200_utc():
    assert builder.HOLDOUT_START_NS == 1_782_856_800_000_000_000


def test_preholdout_parquet_passes(tmp_path):
    path = tmp_path / "safe.parquet"
    write_ticks(path, [builder.HOLDOUT_START_NS - 3, builder.HOLDOUT_START_NS - 2, builder.HOLDOUT_START_NS - 1])
    _, ts_col, px_col = builder.parquet_preflight(path)
    assert ts_col == "ts_utc_ns"
    assert px_col == "price_ticks"


def test_any_row_group_reaching_holdout_fails_before_decode(tmp_path, monkeypatch):
    path = tmp_path / "unsafe.parquet"
    write_ticks(path, [builder.HOLDOUT_START_NS - 1, builder.HOLDOUT_START_NS])
    called = False
    original = pq.read_table
    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        return original(*args, **kwargs)
    monkeypatch.setattr(pq, "read_table", forbidden)
    with pytest.raises(ValueError, match="before decode"):
        builder.parquet_preflight(path)
    assert called is False
