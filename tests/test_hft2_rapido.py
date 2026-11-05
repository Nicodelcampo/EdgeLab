"""Identidad exacta de zonas entre el motor numba y `hftzones2.run`, y bloques trimestrales del almacén sin zonas repetidas."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from edgelab.research import prerange_hft as P

DIA_NS = 86_400 * 10**9
T0 = int(pd.Timestamp("2025-07-07 13:30", tz="UTC").value)      # lunes


def ticks(seed, dias, por_dia, tick):
    """Sesiones con ráfagas: tramos lentos, rachas sub-ms, pausas largas, retrocesos y empates de precio."""
    r = np.random.default_rng(seed); filas = []; px = 40000
    for d in range(dias):
        dia = T0 + d * DIA_NS
        if pd.Timestamp(dia, unit="ns").weekday() >= 5: continue
        dt = r.choice([5, 20, 60, 150, 900, 3000, 7000], por_dia, p=[.2, .3, .25, .15, .07, .02, .01]).astype(np.int64) * 10**6 + r.integers(0, 10**6, por_dia)
        v = r.choice([1.0, 2, 3], por_dia); paso = r.choice([-1, 0, 1], por_dia); i = 0
        while i < por_dia:                                      # ráfaga: rápida, pesada, direccional, con algún fallo o pausa adentro
            lar = int(r.integers(6, 30)); fin = min(i + lar, por_dia); m = fin - i
            dt[i:fin] = r.integers(0, 3 * 10**6, m); v[i:fin] = r.choice([10.0, 40], m)
            paso[i:fin] = r.choice([-1, 1]) * r.choice([-1, 0, 1, 2], m, p=[.06, .2, .5, .24])
            i = fin + int(r.integers(20, 120))
        pt = px + np.cumsum(paso); px = int(pt[-1])
        filas.append(pd.DataFrame(dict(ts_ns=dia + np.cumsum(dt), px=pt * tick, vol=v)))
    return filas


@pytest.mark.parametrize("seed,tick,dias,por_dia", [(1, .25, 5, 9000), (2, 1.0, 5, 7000), (3, .25, 4, 12000), (4, .25, 9, 6000), (5, .03125, 4, 8000)])
def test_identidad_exacta(seed, tick, dias, por_dia):
    b = ticks(seed, dias, por_dia, tick)
    lento = P.zonas_hft2_lento(b, tick, 25); rapido = P.zonas_hft2(b, tick, 25)
    assert len(lento) > 20
    pd.testing.assert_frame_equal(lento.reset_index(drop=True), rapido.reset_index(drop=True), check_exact=True, check_dtype=False)


def test_tope_del_muestreo_activa_decimacion():
    from edgelab.research import hft2_rapido as R
    vals = np.empty(5); e = np.array([0, 1, 0], np.int64)
    for v in range(1, 12): R._add_nb(vals, e, float(v), 4)
    from edgelab.bridge.indicators.hftzones2 import _Sampler
    s = _Sampler(4)
    for v in range(1, 12): s.add(float(v))
    assert list(vals[:e[2]]) == s.vals and e[0] == s.seen and e[1] == s.stride


def almacen():
    f = Path(__file__).resolve().parents[1] / "tools/kaggle_grilla/almacen_zonas_main.py"
    e = importlib.util.spec_from_file_location("almacen_zonas_main", f); m = importlib.util.module_from_spec(e); e.loader.exec_module(m)
    return m


def test_bloques_cubren_el_periodo_sin_holdout():
    m = almacen(); B = m.bloques(None); assert (B[0][0], B[-1][1]) == (20250701, 20260930) and len(B) == 5
    assert all(b[1] < 20261001 for b in B) and all(a[1] < c[0] for a, c in zip(B, B[1:]))
    assert m.bloques("20260101") == [(20260101, 20260331)]
    with pytest.raises(ValueError): m.bloques("20261001")


def test_cargar_une_bloques(tmp_path):
    for i, d in enumerate(("20250701", "20251001")):
        pd.DataFrame(dict(t_ns=[10 - i, 20 - i], lo=[1.0, 2], hi=[2.0, 3])).to_parquet(tmp_path / f"ZONAS_HFT2_NQ_{d}.parquet")
    Z = P.cargar("HFT2", "NQ", str(tmp_path))
    assert list(Z.t_ns) == [9, 10, 19, 20]
