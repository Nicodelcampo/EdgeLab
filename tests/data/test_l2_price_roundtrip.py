"""L2/L1 -- `price` (float64) se valida fila a fila contra `price_tick*tick_size` ANTES de eliminarla
(edgelab/data/l2.py::convert_l2_session). Auditoria 2026-09-22: no alcanza con confiar en que el redondeo que
CREO `price_tick` es autoconsistente -- eso es tautologico. Lo que hay que probar es que la fila original
efectivamente caia en la grilla del tick para empezar; si no caia, es un dato malo, no ruido de punto flotante,
y la conversion tiene que abortar sin escribir nada (fail-closed).
"""
from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from edgelab.data.l2 import (
    L2_SCHEMA, PRICE_ROUNDTRIP_TOLERANCE, PriceRoundtripError, convert_l2_session, _validate_price_roundtrip)

TICK = 0.1

CSV_OK = "\n".join([
    "L2;0;20260901010000;0;0;0;;4300.0;5",
    "L2;1;20260901010000;0;0;0;;4299.9;3",
    "L1;0;20260901010000;0;4300.0;5",
    "L1;2;20260901010000;1;4300.0;1",
]) + "\n"


@pytest.fixture
def csv_ok(tmp_path):
    p = tmp_path / "20260901.csv"
    p.write_text(CSV_OK, encoding="utf-8")
    return p


def test_convierte_ok_borra_price_y_escribe_manifest(csv_ok, tmp_path):
    out = tmp_path / "out"
    p_l2, p_l1 = convert_l2_session(csv_ok, out, tick_size=TICK)

    assert "price" not in pq.read_schema(p_l2).names
    assert "price_tick" in pq.read_schema(p_l2).names
    assert "price" not in pq.read_schema(p_l1).names
    assert "price_tick" in pq.read_schema(p_l1).names

    man_path = out / "manifests" / "20260901.manifest.json"
    assert man_path.exists()
    import json
    man = json.loads(man_path.read_text(encoding="utf-8"))
    assert man["schema"] == L2_SCHEMA
    assert man["conversion"]["tick_size"] == TICK
    assert man["conversion"]["tick_size_repr"] == repr(TICK)
    assert "rounding_policy" in man["conversion"]
    rt = man["conversion"]["price_roundtrip"]
    assert rt["tolerance"] == PRICE_ROUNDTRIP_TOLERANCE
    assert rt["l2"]["violations"] == 0 and rt["l1"]["violations"] == 0
    assert rt["price_column_dropped"] is True
    # el manifest sigue exponiendo conversion.tick_size en la ruta que lee build_l2_viewer_bundle.py::main
    assert man["conversion"]["tick_size"] == TICK


def test_price_en_grilla_tiene_error_de_punto_flotante_no_de_grilla(csv_ok):
    """El residuo real (float64 puro) tiene que quedar muy por debajo de la tolerancia -- si esto empezara a
    fallar, la tolerancia esta mal calibrada, no el dato."""
    import pandas as pd
    from edgelab.data.l2 import parse_l2_raw_csv
    df_l2, df_l1 = parse_l2_raw_csv(csv_ok, tick_size=TICK)
    rt = _validate_price_roundtrip(df_l1, TICK)
    assert rt["violations"] == 0
    assert rt["max_error"] < 1e-9          # muy por debajo de PRICE_ROUNDTRIP_TOLERANCE (1e-6)


def test_precio_fuera_de_grilla_aborta_la_conversion_sin_escribir_nada(tmp_path):
    """Un precio que NO cae en ningun multiplo de tick_size (dato corrupto/off-tick) tiene que abortar, no
    colarse silenciosamente redondeado al tick mas cercano."""
    bad_csv = tmp_path / "20260902.csv"
    # 4300.037 no es multiplo de 0.1: redondea a price_tick=43000 (4300.0), residuo 0.037 >> tolerancia 1e-6.
    bad_csv.write_text("L1;0;20260902010000;0;4300.037;5\n", encoding="utf-8")
    out = tmp_path / "out"

    with pytest.raises(PriceRoundtripError, match="fuera de grilla"):
        convert_l2_session(bad_csv, out, tick_size=TICK)

    assert not (out / "l2_depth" / "20260902.parquet").exists()
    assert not (out / "l1_quotes" / "20260902.parquet").exists()
    assert not (out / "manifests" / "20260902.manifest.json").exists()


def test_validate_price_roundtrip_con_dataframe_vacio_no_rompe():
    import pandas as pd
    df = pd.DataFrame({"price": pd.Series(dtype="float64"), "price_tick": pd.Series(dtype="int32")})
    rt = _validate_price_roundtrip(df, TICK)
    assert rt == dict(tolerance=PRICE_ROUNDTRIP_TOLERANCE, max_error=0.0, violations=0, rows_checked=0)


def test_subsecond_field_in_100ns_ticks_is_divided_by_ten(tmp_path):
    """NT8 escribe la fraccion en ticks de 100 ns; sumarla como us la multiplicaba x10 (bug 2026-09-23)."""
    from edgelab.data.l2 import SUBSEC_100NS, parse_l2_raw_csv
    csv = tmp_path / "20260609.csv"
    csv.write_text("L2;0;20260609010001;1960000;0;0;;3400.1;2\n"
                   "L1;1;20260609010001;2000000;3400.0;1\n", encoding="utf-8")
    l2, l1 = parse_l2_raw_csv(csv, tick_size=0.1)
    assert int(l2["ts_us"].iloc[0] % 1_000_000) == 196_000
    assert int(l1["ts_us"].iloc[0] % 1_000_000) == 200_000
    assert l2.attrs["subsecond_unit"] == SUBSEC_100NS


def test_microsecond_field_is_kept(tmp_path):
    from edgelab.data.l2 import SUBSEC_US, parse_l2_raw_csv
    csv = tmp_path / "20260609.csv"
    csv.write_text("L2;0;20260609010001;196000;0;0;;3400.1;2\n", encoding="utf-8")
    l2, _ = parse_l2_raw_csv(csv, tick_size=0.1)
    assert int(l2["ts_us"].iloc[0] % 1_000_000) == 196_000 and l2.attrs["subsecond_unit"] == SUBSEC_US
