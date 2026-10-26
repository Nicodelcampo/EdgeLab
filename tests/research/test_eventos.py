import numpy as np

from edgelab.research import eventos as EV
from edgelab.research.eventos_datos import EVENTOS


def test_datos_embebidos_al_dia_con_noticias():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import eventos_desde_noticias as G
    assert G.DESTINO.read_text(encoding="utf-8") == G.generar(), "regenerar: python tools/eventos_desde_noticias.py --write"


def test_horarios_canonicos():
    t = {(k, int(ts)) for ts, k, _ in EVENTOS}
    assert ("CPI", 1704979800) in t                                      # 2024-01-11 08:30 EST = 13:30 UTC
    assert ("NFP_EMPLOYMENT_SITUATION", 1720182600) in t                 # 2024-07-05 08:30 EDT = 12:30 UTC


def test_cerca_ventana():
    t0 = 1704979800
    m = EV.cerca([t0 - 16 * 60, t0 - 15 * 60, t0, t0 + 15 * 60, t0 + 16 * 60], 15, 15)
    assert m.tolist() == [False, True, True, True, False]
    assert EV.cerca([t0 + 600], 15, 15, tipos=("FOMC_DECISION",)).tolist() == [False]


def test_diagnostico():
    t0 = 1704979800
    d = EV.diagnostico([t0, t0 + 86400 * 3], [5.0, -1.0])
    assert d["n_cerca"] == 1 and d["pnl_cerca"] == 5.0 and d["media_lejos"] == -1.0
