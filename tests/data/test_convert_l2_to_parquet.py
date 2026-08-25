"""Conversor L2 CSV -> Parquet: streaming, orden e integridad fail-closed."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from tools.convert_l2_to_parquet import convert_one_file

CSV = "\n".join(
    [
        "L2;0;20260609090000;100;0;0;;3400.1;20",   # 0 ASK add
        "L1;0;20260609090000;100;3400.1;20",        # 1 ASK
        "L2;1;20260609090000;100;0;0;;3400.0;18",   # 2 BID add
        "L1;1;20260609090000;100;3400.0;18",        # 3 BID
        "L1;2;20260609090000;100;3400.1;1",         # 4 LAST
        "L2;0;20260609090000;100;1;0;;3400.1;19",   # 5 ASK update
        "L1;5;20260609090001;0;0;123456",           # 6 DAILY_VOLUME
        "L2;1;20260609090001;0;2;0;;3400.0;0",      # 7 BID remove
    ]
) + "\n"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_conversion_por_chunks_preserva_orden_y_publica_manifest(tmp_path):
    source = tmp_path / "GC_08-26_20260609.csv"
    source.write_text(CSV, encoding="utf-8")
    out = tmp_path / "out"

    manifest = convert_one_file(
        source,
        out,
        instrument="GC 08-26",
        tick_size=0.1,
        chunk_rows=3,  # fuerza fronteras dentro de timestamps empatados
        allow_dirty=True,
    )

    l2_path = out / "l2_depth" / f"{source.stem}.parquet"
    l1_path = out / "l1_quotes" / f"{source.stem}.parquet"
    manifest_path = out / "manifests" / f"{source.stem}.manifest.json"
    assert l2_path.is_file() and l1_path.is_file() and manifest_path.is_file()

    l2 = pd.read_parquet(l2_path)
    l1 = pd.read_parquet(l1_path)
    combined = np.sort(
        np.concatenate([l2["source_row"].to_numpy(), l1["source_row"].to_numpy()])
    )
    assert np.array_equal(combined, np.arange(8))
    assert list(l2["source_row"]) == [0, 2, 5, 7]
    assert list(l1["source_row"]) == [1, 3, 4, 6]
    assert set(l1["side"]) == {0, 1, 2, 5}
    assert set(l2["operation"]) == {0, 1, 2}

    disk_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest == disk_manifest
    assert disk_manifest["source"]["sha256"] == _sha(source)
    assert disk_manifest["source"]["rows"] == 8
    assert disk_manifest["outputs"]["l2_depth"]["rows"] == 4
    assert disk_manifest["outputs"]["l1_quotes"]["rows"] == 4
    assert disk_manifest["outputs"]["l2_depth"]["sha256"] == _sha(l2_path)
    assert disk_manifest["outputs"]["l1_quotes"]["sha256"] == _sha(l1_path)
    assert disk_manifest["conversion"]["preserved_original_order"] is True
    assert disk_manifest["conversion"]["timestamp_inversions"] == 0
    assert disk_manifest["scope"]["outcomes_computed"] is False


def test_aborta_fuera_de_tick_y_no_publica_outputs(tmp_path):
    source = tmp_path / "off_grid.csv"
    source.write_text(
        "L2;0;20260609090000;0;0;0;;3400.1;1\n"
        "L1;2;20260609090000;1;3400.05;1\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="fuera de tick"):
        convert_one_file(
            source,
            out,
            instrument="GC 08-26",
            tick_size=0.1,
            chunk_rows=1,
            allow_dirty=True,
        )
    assert not list(out.rglob("*.parquet"))
    assert not list(out.rglob("*.manifest.json"))


def test_aborta_record_type_desconocido(tmp_path):
    source = tmp_path / "unknown.csv"
    source.write_text(
        "L2;0;20260609090000;0;0;0;;3400.1;1\n"
        "XXX;2;20260609090000;1;3400.1;1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="record_type"):
        convert_one_file(
            source,
            tmp_path / "out",
            instrument="GC 08-26",
            tick_size=0.1,
            chunk_rows=1,
            allow_dirty=True,
        )


def test_no_sobreescribe_sin_flag_explicito(tmp_path):
    source = tmp_path / "session.csv"
    source.write_text(CSV, encoding="utf-8")
    out = tmp_path / "out"
    convert_one_file(
        source,
        out,
        instrument="GC 08-26",
        tick_size=0.1,
        chunk_rows=3,
        allow_dirty=True,
    )
    with pytest.raises(FileExistsError, match="--overwrite"):
        convert_one_file(
            source,
            out,
            instrument="GC 08-26",
            tick_size=0.1,
            chunk_rows=3,
            allow_dirty=True,
        )


def test_conversion_soporta_subsegundos_en_escala_100ns(tmp_path):
    csv_100ns = (
        "L2;0;20260609010001;1960000;0;0;;3400.1;2\n"
        "L1;1;20260609010001;2000000;3400.0;1\n"
    )
    source = tmp_path / "GC_08-26_100ns.csv"
    source.write_text(csv_100ns, encoding="utf-8")
    out = tmp_path / "out"
    manifest = convert_one_file(
        source,
        out,
        instrument="GC 08-26",
        tick_size=0.1,
        chunk_rows=1,
        allow_dirty=True,
    )
    l2 = pd.read_parquet(out / "l2_depth" / f"{source.stem}.parquet")
    l1 = pd.read_parquet(out / "l1_quotes" / f"{source.stem}.parquet")
    assert int(l2["ts_us"].iloc[0] % 1_000_000) == 196000
    assert int(l1["ts_us"].iloc[0] % 1_000_000) == 200000
