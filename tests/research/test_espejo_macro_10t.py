"""El detector de 10 ticks separa la montaña lisa del serrucho, y corta la vuelta al 50 %."""
from __future__ import annotations

import numpy as np

from edgelab import costos
from edgelab.research.espejo_macro_10t import VIAJES_EN_LO_QUE_FALTA, ancho_minimo_ticks, detectar, velas_de_ticks


def _tramo(dest, n, ahora):
    return list(np.linspace(ahora, dest, n + 1)[1:])


def _linea(*tramos, start=20000.0):
    c = [start]
    for dest, n in tramos:
        c += _tramo(dest, n, c[-1])
    return np.asarray(c, float)


def test_la_montana_lisa_es_candidata_al_50():
    # 120 ticks de suba en 12 cierres, después 60 ticks de baja (la mitad) en 6 cierres.
    c = _linea((20120, 12), (20060, 6), (20040, 4))
    d = detectar(c, min_w=80, min_ida=8, min_vuelta=4)
    assert len(d) == 1
    uno = d[0]
    assert uno["lado"] == 1 and uno["W"] == 120
    assert uno["B"] - c[uno["k"]] == 60
    assert uno["k"] < len(c) - 1
    visto = detectar(c[:uno["k"] + 1], min_w=80, min_ida=8, min_vuelta=4)
    assert any(x["i0"] == uno["i0"] and x["k"] == uno["k"] for x in visto)
    assert all(x["k"] < uno["k"] for x in detectar(c[:uno["k"]], min_w=80, min_ida=8, min_vuelta=4))


def test_la_baja_lisa_tambien_corta_al_50():
    c = _linea((19880, 12), (19940, 6), (19980, 4))
    d = detectar(c, min_w=80, min_ida=8, min_vuelta=4)
    assert len(d) == 1 and d[0]["lado"] == -1 and d[0]["W"] == 120
    assert c[d[0]["k"]] - d[0]["B"] == 60


def test_un_serrucho_no_es_impulso():
    # Subas de 50 y retrocesos de 30: cada retroceso devuelve más de 0,20 y el precio sigue.
    c = [20000.0]
    for _ in range(6):
        c += _tramo(c[-1] + 50, 4, c[-1])
        c += _tramo(c[-1] - 35, 3, c[-1])
    c += _tramo(c[-1] - 80, 6, c[-1])
    assert detectar(np.asarray(c), min_w=80, min_ida=6, min_vuelta=4) == []


def test_la_vuelta_serruchada_no_cuenta():
    c = _linea((20120, 12))
    for _ in range(4):
        c = np.r_[c, _tramo(c[-1] - 20, 2, c[-1])]
        c = np.r_[c, _tramo(c[-1] + 14, 2, c[-1])]
    c = np.r_[c, _tramo(c[-1] - 40, 4, c[-1])]
    assert detectar(c, min_w=80, min_ida=8, min_vuelta=4) == []


def test_un_retroceso_chico_en_la_ida_sigue_siendo_limpio():
    # 10 % del tramo, recuperado, y después la mitad de vuelta lisa.
    c = _linea((20060, 6), (20048, 2), (20120, 6), (20060, 6))
    d = detectar(c, min_w=80, min_ida=8, min_vuelta=4)
    assert len(d) == 1 and d[0]["retro_ida"] <= 0.20


def test_el_piso_de_nq_cubre_cuarenta_viajes_severos():
    falta = 0.5 * ancho_minimo_ticks("NQ")
    assert falta >= VIAJES_EN_LO_QUE_FALTA * costos.friccion_rt_ticks("NQ", "severo") - 1e-6


def test_la_vela_de_10_ticks_toma_el_cierre_del_decimo():
    px = np.arange(25, dtype=float)
    o, h, l, c, v = velas_de_ticks(px, np.ones(25), 10)
    assert len(c) == 2 and c[0] == 9 and c[1] == 19 and h[0] == 9 and l[0] == 0
