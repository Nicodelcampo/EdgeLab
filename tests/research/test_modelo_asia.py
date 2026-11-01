"""MODELO-ASIA (2026-11-01): preflight, causalidad, EMA20 de 5 min, regla literal en una sesión armada a mano, tenencia hasta NY
(más de 240 velas) y paridad lote/escalar. Además, que el tope por defecto del simulador no cambió para el resto."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX, grilla_generica as GG, indicadores as IND, modelo_asia as M, preflight as PF
from edgelab.research.regimen_sesion import minuto_ny

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_paquete_20261031 import T0, ctx_sintetico  # noqa: E402

_C = {}


def _ctx():
    if "c" not in _C: _C["c"] = ctx_sintetico(dias=30, seed=4)
    return _C["c"]


def test_preflight_tamano_y_literal():
    assert PF.estatico(M) == [] and GG.n_celdas(M) == 2 * 7 * 3 * 10
    assert M.EJECUCIONES[M.CELDA_LITERAL[-1]] == ("OPUESTO", "ABIERTO", 960) and M.TOPE_BARRAS > AX.TOPE_OPERACION


def test_causal():
    assert IND.causal(M.disparos, _ctx()) == []


def test_ema_m5_es_la_de_los_cierres_de_5_minutos():
    c = _ctx(); m = minuto_ny(c["t"]); e = M.ema_m5(c["c"], m)
    i5 = np.flatnonzero(m % 5 == 0); ref = pd.Series(c["c"][i5]).ewm(span=20, adjust=False).mean().to_numpy()
    assert np.allclose(e[i5][19:], ref[19:]) and np.isnan(e[i5[18]])
    j = i5[30] + 2; assert e[j] == e[i5[30]]                                # entre cierres de 5 min queda el último


def test_lote_igual_a_escalar():
    ctx = _ctx(); D = M.disparos(ctx)
    assert len(D) and set(D.gat) == {0, 1}
    assert np.array_equal(GG.ops_por_fila(M, D, ctx), GG._ops_lote(M, D, ctx), equal_nan=True)


def _sesion_literal(ancho=200.0, tick=0.25):
    """3 sesiones planas para calentar la EMA y una 4ª: rango 18–20 de `ancho` pts, sobre la EMA a las 20:15, rompe el alto a las
    21:00 y sube despacio hasta las 16:00 del día siguiente."""
    n_s = 1380; ts, cs, ses = [], [], []
    for d in range(4):
        t = T0 + d * 86400 + 60 * np.arange(1, n_s + 1); m = minuto_ny(t); rel = (m - 1080) % 1440
        c = np.full(n_s, 20000.0)
        if d == 3:
            c[(rel > 0) & (rel <= 120)] = 20000.0 + np.where(np.arange(((rel > 0) & (rel <= 120)).sum()) % 2, ancho / 2, -ancho / 2)
            c[(rel > 120) & (rel < 180)] = 20050.0                                  # dentro del rango y sobre la EMA (≈20000)
            sube = rel >= 180; c[sube] = 20000.0 + ancho / 2 + 1 + 0.25 * np.arange(sube.sum())
        ts.append(t); cs.append(np.round(c / tick) * tick); ses.append(np.full(n_s, d, np.int64))
    t, c, ses = np.concatenate(ts), np.concatenate(cs), np.concatenate(ses)
    o = np.r_[c[0], c[:-1]]
    return dict(t=t, o=o, h=np.maximum(o, c), l=np.minimum(o, c), c=c, v=np.ones(len(c)), ses=ses, tick=tick, tpx=np.zeros(0),
                tstart=np.zeros(len(c) + 1, np.int64))


def test_regla_literal_compra_y_queda_abierta_hasta_las_16():
    ctx = _sesion_literal(); D = M.disparos(ctx); m = minuto_ny(ctx["t"])
    d = D[(D.gat == 0) & (D.ses == 3)].iloc[0]; k = int(d.k)
    assert d.lado == 1 and d.sesgo == 1 and 100 <= d.ancho <= 300 and m[k] == 21 * 60
    di, ei, pnl, _, _, _, _, xb = GG.simular_ops(M, D[(D.gat == 0) & (D.ses == 3)].reset_index(drop=True), ctx, devolver_O=True, devolver_barras=True)
    j = int(np.flatnonzero(ei == M.CELDA_LITERAL[-1])[0])
    assert m[xb[j]] == 961 and xb[j] - k > AX.TOPE_OPERACION     # cierre de las 16:00 en la ventana -> sale en la apertura siguiente (16:00:00)
    assert np.isclose(pnl[j], ctx["o"][xb[j]] - ctx["o"][k + 1])
    assert D[(D.ses == 3)].ancho.iloc[0] == 200.0


def test_ancho_cae_en_el_tramo_de_cada_lectura():
    D = M.disparos(_sesion_literal(ancho=60.0)); x = D[D.ses == 3].ancho.iloc[0]
    assert GG.discretizar(D[D.ses == 3], M.VARIABLES, {})[1][0] == 2 and x == 60.0          # 60 pts = 240 ticks: lectura "ticks"
    D2 = M.disparos(_sesion_literal(ancho=200.0)); assert GG.discretizar(D2[D2.ses == 3], M.VARIABLES, {})[1][0] == 4
