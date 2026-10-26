"""Almacén de zonas (2026-10-26): racimos de AVZP2 por tipo == los del propio indicador; BigTrap2 da zonas rectangulares con fin."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from edgelab.research import sintetico

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def A():
    spec = importlib.util.spec_from_file_location("almacen", ROOT / "tools/kaggle_grilla/almacen_zonas_main.py")
    m = importlib.util.module_from_spec(spec); sys.modules["almacen"] = m
    src = (ROOT / "tools/kaggle_grilla/almacen_zonas_main.py").read_text(encoding="utf-8").replace('if __name__ == "__main__":\n    main()', "")
    exec(compile(src, "almacen", "exec"), m.__dict__)
    return m


def _bloques(libro=False, dias=40):
    rng = np.random.default_rng(0)
    for b in sintetico.bloques(dias=dias, seed=3, planta=False):
        if libro:                                                          # agresor al azar y volumen de futuro líquido
            up = rng.random(len(b)) < 0.5
            b = b.assign(vol=b.vol * 20, bid=np.where(up, b.px - 0.25, b.px), ask=np.where(up, b.px, b.px + 0.25))
        yield b


SUELTO = dict(detection_percentile=50.0, min_samples=5, lookback_sessions=5)   # el sintético no llega a los umbrales de 20 sesiones


def test_racimos_por_tipo_iguales_al_indicador(A):
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators.avolzonepoi2 import run
    from edgelab.bridge.ticks import TickSeries
    bl = list(_bloques()); ts = np.concatenate([b.ts_ns for b in bl]); px = np.concatenate([b.px for b in bl])
    vol = np.concatenate([b.vol for b in bl])
    tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / 0.25).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                    sequence=np.arange(len(ts), dtype=np.int64), tick_size=0.25)
    bars = B.build_tick_bars(tk, 25); fps = B.build_total_footprint_csr_nt8(tk, bars); s = B.session_ids(np.asarray(bars.end_ns))
    p = dict(A.PARAMS, **SUELTO, racimo_min=2, racimo_bars=1000, racimo_altura_ticks=45)
    ref = run(bars, fps, s, p)["clusters"]; zs = sorted(run(bars, fps, s, dict(p, racimo_min=0))["zones"], key=lambda z: z["bar"])
    got = A.racimos_de(zs, p)
    assert len(ref) > 0 and [(c["bar"], c["low0"], c["high0"]) for c in ref] == [(c["bar"], c["low"], c["high"]) for c in got]


def test_bt2_zonas_rectangulares_con_fin(A):
    Z = A.zonas_bt2(_bloques(libro=True, dias=6), 0.25, 1)
    assert len(Z) and (Z.hi > Z.lo).all() and set(Z.lado) <= {1, -1}
    fin = Z.t_fin_ns[Z.t_fin_ns > 0]; assert (fin >= Z.t_ns[Z.t_fin_ns > 0]).all()


def test_avzrg_grilla_completa(A, monkeypatch):
    assert len(A.GRILLA_ZONA) == 36 and len(A.GRILLA_RACIMO) == 12
    monkeypatch.setattr(A, "PARAMS", dict(A.PARAMS, **SUELTO))
    monkeypatch.setattr(A, "GRILLA_ZONA", [dict(detection_percentile=50.0, median_multiplier=2.0, window_bars=10, min_cluster_ticks=2)])
    monkeypatch.setattr(A, "GRILLA_RACIMO", [dict(racimo_min=2, racimo_bars=1000, racimo_altura_ticks=45), dict(racimo_min=8, racimo_bars=500, racimo_altura_ticks=30)])
    Z = A.zonas_avzrg(_bloques(), 0.25, 25)
    assert list(Z.columns) == ["t_ns", "lo", "hi", "zona", "racimo"] and len(Z) and set(Z.zona) == {0} and set(Z.racimo) <= {0, 1}


def test_avzg_zonas_individuales_por_definicion(A, monkeypatch):
    monkeypatch.setattr(A, "PARAMS", dict(A.PARAMS, **SUELTO))
    monkeypatch.setattr(A, "GRILLA_ZONA", [dict(detection_percentile=50.0, median_multiplier=2.0, window_bars=10, min_cluster_ticks=2),
                                           dict(detection_percentile=90.0, median_multiplier=2.0, window_bars=10, min_cluster_ticks=2)])
    Z = A.zonas_avzg(_bloques(), 0.25, 25)
    assert list(Z.columns) == ["t_ns", "lo", "hi", "zona"] and set(Z.zona) <= {0, 1} and (Z.zona == 0).sum() >= (Z.zona == 1).sum() > -1
