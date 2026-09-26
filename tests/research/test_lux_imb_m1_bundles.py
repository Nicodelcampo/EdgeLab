"""Barras M1 desde ticks para LUX-IMB: agrupacion por minuto UTC y union de sesiones."""
import importlib.util
import sys
from pathlib import Path

import numpy as np

SPEC = importlib.util.spec_from_file_location(
    "build_m1", Path(__file__).resolve().parents[2] / "tools" / "build_lux_imb_m1_bundles.py")
M = importlib.util.module_from_spec(SPEC)
sys.modules["build_m1"] = M
SPEC.loader.exec_module(M)
NS = 1_000_000_000


def test_agrupa_por_minuto_utc_con_ohlcv():
    ts = np.array([0, 10, 59, 60, 61, 130], dtype=np.int64) * NS
    px = np.array([100, 102, 99, 98, 101, 105], dtype=np.int64)
    vol = np.array([1, 2, 3, 4, 5, 6])
    t, o, h, l, c, v = M.build_m1(ts, px, vol, 0.25)
    assert list(t) == [0, 60, 120]
    assert list(o) == [25.0, 24.5, 26.25] and list(c) == [24.75, 25.25, 26.25]
    assert list(h) == [25.5, 25.25, 26.25] and list(l) == [24.75, 24.5, 26.25]
    assert list(v) == [6.0, 9.0, 6.0]


def test_desplazamiento_de_ticks_mueve_las_fronteras_de_minuto():
    ts = np.array([10, 40], dtype=np.int64) * NS
    px = np.array([100, 101], dtype=np.int64)
    vol = np.array([1, 1])
    t0, *_ = M.build_m1(ts, px, vol, 1.0)
    t30, *_ = M.build_m1(ts + 30 * NS, px, vol, 1.0)          # el segundo tick pasa al minuto siguiente
    assert list(t0) == [0] and list(t30) == [0, 60]


def test_une_barras_del_mismo_minuto_sin_perder_extremos():
    t = np.array([0, 0, 60], dtype=np.int64)
    o = np.array([10.0, 12.0, 11.0]); h = np.array([11.0, 15.0, 12.0]); l = np.array([9.0, 12.0, 10.0])
    c = np.array([10.5, 13.0, 11.5]); v = np.array([1.0, 2.0, 3.0])
    tt, oo, hh, ll, cc, vv = M.merge_same_minute(t, o, h, l, c, v)
    assert list(tt) == [0, 60] and oo[0] == 10.0 and hh[0] == 15.0 and ll[0] == 9.0 and cc[0] == 13.0 and vv[0] == 3.0


def test_serie_vacia_no_rompe():
    t, *rest = M.build_m1(np.array([], dtype=np.int64), np.array([], dtype=np.int64), np.array([]), 0.25)
    assert len(t) == 0 and all(len(a) == 0 for a in rest)
