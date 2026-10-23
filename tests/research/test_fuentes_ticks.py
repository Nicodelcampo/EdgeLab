"""Los kernels no cargan config/costos: la copia de la fricción en fuentes_ticks debe valer lo mismo que edgelab.costos."""
import pytest

from edgelab import costos as C
from edgelab.research import fuentes_ticks as F


def test_friccion_de_los_kernels_es_la_canonica():
    _, tick, base, extra = F.FUENTES["NQ"]
    assert tick == C.tick_size("NQ")
    assert base == pytest.approx(C.friccion_rt_puntos("NQ", "base"), abs=1e-9)
    assert base + extra == pytest.approx(C.friccion_rt_puntos("NQ", "adverso"), abs=1e-9)
    assert F.FUENTES["USATECH"][2:] == F.FUENTES["NQ"][2:]                 # CFD: referencia con los costos de NQ


def test_ventana_que_toca_el_holdout_falla():
    with pytest.raises(ValueError):
        next(F.bloques_nq(20260901, 20261001, entrada="/no/existe"))


def test_lector_sellado_exige_acta_y_no_mezcla_desarrollo(tmp_path):
    with pytest.raises(ValueError): next(F.bloques_nq_sellado(20261001, 20261020, "x.parquet", None))
    acta = tmp_path / "acta.md"; acta.write_text("x")
    with pytest.raises(ValueError): next(F.bloques_nq_sellado(20260930, 20261020, "x.parquet", str(acta)))


def test_ticks_de_futuros_coinciden_con_el_catalogo():
    import json
    from pathlib import Path
    d = json.loads((Path(__file__).resolve().parents[2] / "docs/data_catalog/RESOLVER.json").read_text(encoding="utf-8"))["instruments"]
    assert {k: v["tick_size"] for k, v in d.items()} == F.TICK_FUTURO


def test_lector_generico_equivale_al_de_nq(tmp_path):
    import numpy as np, pandas as pd, pyarrow as pa, pyarrow.parquet as pq
    ts = (1_760_000_000 + np.arange(1000) * 7) * 10**9
    t = pa.table(dict(ts_utc_ns=ts, price_ticks=np.arange(1000, dtype=np.int64) + 80000, volume=np.ones(1000, np.int64), trade_date=np.full(1000, 20251010, np.int64),
                      regime_id=np.zeros(1000, np.int64), outside_regular=np.zeros(1000, bool)))
    pq.write_table(t, tmp_path / "NQ_ticks.parquet")
    a = pd.concat(F.bloques_nq(20251001, 20251031, str(tmp_path))); b = pd.concat(F.bloques_futuro("NQ", 20251001, 20251031, str(tmp_path)))
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))
    lector, tick = F.resolver("NQ"); assert tick == 0.25 and len(pd.concat(lector(20251001, 20251031, str(tmp_path)))) == 1000
