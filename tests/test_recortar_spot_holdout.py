"""El recorte de los SPOT de Dukascopy (P-96 P4) sólo quita filas desde la apertura del holdout y conserva el prefijo exacto."""
import importlib.util
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS as F

_sp = importlib.util.spec_from_file_location("rsh", Path(__file__).resolve().parents[1] / "tools/recortar_spot_holdout.py")
R = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(R)
MIN = 60_000_000_000


def _escribir(p, ts, rg=3):
    t = pa.table({"time_utc_ns": pa.array(ts, pa.int64()), "bid": pa.array([float(i) for i in range(len(ts))])})
    pq.write_table(t, p, row_group_size=rg)


def test_quita_solo_el_holdout_y_conserva_el_prefijo(tmp_path):
    ts = [F - 5 * MIN + i * MIN for i in range(10)]                    # 5 antes, 5 desde la frontera (incluida)
    _escribir(tmp_path / "a.parquet", ts)
    r = R.recortar_parquet(tmp_path / "a.parquet", tmp_path / "b.parquet")
    assert (r["filas_entrada"], r["filas_salida"], r["filas_quitadas"]) == (10, 5, 5)
    out = pq.read_table(tmp_path / "b.parquet")
    assert out["time_utc_ns"].to_pylist() == ts[:5] and out["bid"].to_pylist() == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert out.schema.types == pq.read_schema(tmp_path / "a.parquet").types


def test_no_ascendente_falla(tmp_path):
    _escribir(tmp_path / "a.parquet", [F - 3 * MIN, F - 5 * MIN, F - MIN, F])
    with pytest.raises(SystemExit):
        R.recortar_parquet(tmp_path / "a.parquet", tmp_path / "b.parquet")


def test_calidad_pierde_lo_que_describe_al_holdout():
    ms = F // 1_000_000
    c = {"dias": {"2026-09-30": {"ticks": 100}}, "huecos_5min": [{"desde_ms": ms - 10**7, "hasta_ms": ms + 5790}, {"desde_ms": 1, "hasta_ms": 2}]}
    o = R.recortar_calidad(c, 80)
    assert o["dias"]["2026-09-30"]["ticks"] == 80 and o["huecos_5min"] == [{"desde_ms": 1, "hasta_ms": 2}]
    assert c["dias"]["2026-09-30"]["ticks"] == 100                       # no muta la entrada


def test_carpeta_completa_sin_subir(tmp_path):
    ori = tmp_path / "o"; ori.mkdir()
    _escribir(ori / "X_ticks.parquet", [F - 2 * MIN, F - MIN, F, F + MIN])
    _escribir(ori / "X_m1.parquet", [F - MIN, F])
    (ori / "README.md").write_text("# X\n", encoding="utf-8")
    (ori / "calidad.json").write_text(json.dumps({"dias": {"2026-09-30": {"ticks": 4}}, "huecos_5min": []}), encoding="utf-8")
    reg = R.main(["--slug", "o/x", "--trabajo", str(tmp_path / "w"), "--origen", str(ori)])
    out = tmp_path / "w" / "recortado"
    assert {r["archivo"]: r["filas_quitadas"] for r in reg["archivos"]} == {"X_m1.parquet": 1, "X_ticks.parquet": 2}
    assert json.loads((out / "calidad.json").read_text())["dias"]["2026-09-30"]["ticks"] == 2
    assert "HOLDOUT-A4" in (out / "README.md").read_text() and (out / "RECORTE_HOLDOUT.json").exists()


def test_la_subida_rechaza_parquets_con_holdout(tmp_path):
    sp = importlib.util.spec_from_file_location("kd", Path(__file__).resolve().parents[1] / "tools/kaggle_dataset.py")
    K = importlib.util.module_from_spec(sp); sp.loader.exec_module(K)
    _escribir(tmp_path / "con.parquet", [F - MIN, F])
    _escribir(tmp_path / "sin.parquet", [F - 2 * MIN, F - MIN])
    (tmp_path / "x.json").write_text("{}")
    assert K.holdout_en(sorted(tmp_path.iterdir())) == ["con.parquet:time_utc_ns"]
    R.recortar_parquet(tmp_path / "con.parquet", tmp_path / "rec.parquet")
    assert K.holdout_en([tmp_path / "rec.parquet"]) == []
