import numpy as np

from edgelab.research import eventos as EV
from edgelab.research.eventos_datos import EVENTOS


def test_datos_oficiales_basicos():
    fechas = {(k, f) for _, k, f in EVENTOS}
    assert ("FOMC", "2024-05-01") in fechas and ("CPI", "2025-10-24") in fechas and ("NFP", "2025-11-20") in fechas   # cierre 2025
    t = dict(((k, f), t) for t, k, f in EVENTOS)
    assert t[("CPI", "2024-01-11")] == 1704979800                       # 08:30 EST = 13:30 UTC
    assert t[("NFP", "2024-07-05")] == 1720182600                       # 08:30 EDT = 12:30 UTC


def test_cerca_ventana():
    t0 = 1704979800
    m = EV.cerca([t0 - 16 * 60, t0 - 15 * 60, t0, t0 + 15 * 60, t0 + 16 * 60], 15, 15)
    assert m.tolist() == [False, True, True, True, False]
    assert EV.cerca([t0 + 600], 15, 15, tipos=("FOMC",)).tolist() == [False]


def test_diagnostico():
    t0 = 1704979800
    d = EV.diagnostico([t0, t0 + 86400 * 3], [5.0, -1.0])
    assert d["n_cerca"] == 1 and d["pnl_cerca"] == 5.0 and d["media_lejos"] == -1.0
