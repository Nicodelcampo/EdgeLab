"""Tests unitarios, geométricos y de causalidad estricta para `barreras_hft`, `hft_gc_p10_veto` y `hft_gc_p10_captp`."""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import (
    barreras_hft as BH,
    grilla_generica as GG,
    hft_gc_p10_captp as CAPTP,
    hft_gc_p10_veto as VETO,
    indicadores as I,
    sintetico,
)


def _ctx_mini_m1(n: int = 40, tick: float = 0.10) -> dict:
    t0 = 1_760_047_200
    t = np.arange(t0, t0 + n * 60, 60, dtype=np.int64)
    px = np.full(n, 4000.0, dtype=np.float64)
    ses = np.where(np.arange(n) < 20, 20251009, 20251010).astype(np.int64)
    return dict(
        t=t,
        o=px.copy(),
        h=px + 0.30,
        l=px - 0.30,
        c=px.copy(),
        v=np.full(n, 100.0, dtype=np.float64),
        ses=ses,
        tick=tick,
    )


def test_reloj_activo_y_frontera_5m():
    ctx = _ctx_mini_m1(40, tick=0.10)
    # Zona creada exactamente al cierre de k=10 (t[10]), 3.0 puntos por encima de 4000.0 (lo=4003.0, hi=4004.0)
    zones = pd.DataFrame(dict(
        t_ns=[int(ctx["t"][10]) * 10**9],
        lo=[4003.0],
        hi=[4004.0],
        bucket=[0],
        total_vol=[500.0],
        away_res_code=[1],
        away_dir=[-1],
        t_away_ns=[int(ctx["t"][11]) * 10**9],
    ))
    inv = BH.preparar_inventario_barreras(zones, ctx)

    # En k=15 han pasado exactamente 5 * 60 = 300s (5m): debe estar VIGENTE en antiguedad=0 (5m -> d_libre = 3.0)
    d_5m_en_15 = BH.evaluar_distancia_frontal(
        inv, np.array([15]), np.array([1]), np.array([4000.0]), np.array([2.5]), 0, 0, 0
    )
    assert np.isclose(d_5m_en_15[0], 3.0)

    # En k=16 han pasado 6 * 60 = 360s (> 5m): expira para antiguedad=0 (5m), pero sigue vigente para antiguedad=1 (15m)
    d_5m_en_16 = BH.evaluar_distancia_frontal(
        inv, np.array([16]), np.array([1]), np.array([4000.0]), np.array([2.5]), 0, 0, 0
    )
    d_15m_en_16 = BH.evaluar_distancia_frontal(
        inv, np.array([16]), np.array([1]), np.array([4000.0]), np.array([2.5]), 0, 1, 0
    )
    assert d_5m_en_16[0] >= BH.INF_PX * 0.5
    assert np.isclose(d_15m_en_16[0], 3.0)

    # En k=22 cambió la sesión CME (20251010 != 20251009): antiguedad=4 ('sesion') la descarta, pero 15m (12 min = 720s <= 900s) la ve
    d_ses_en_22 = BH.evaluar_distancia_frontal(
        inv, np.array([22]), np.array([1]), np.array([4000.0]), np.array([2.5]), 0, 4, 0
    )
    d_15m_en_22 = BH.evaluar_distancia_frontal(
        inv, np.array([22]), np.array([1]), np.array([4000.0]), np.array([2.5]), 0, 1, 0
    )
    assert d_ses_en_22[0] >= BH.INF_PX * 0.5
    assert np.isclose(d_15m_en_22[0], 3.0)


def test_mitigacion_virgen_vs_no_atravesada():
    ctx = _ctx_mini_m1(25, tick=0.10)
    # Zona [4003.0, 4005.0] creada en k=2
    # En k=5 el precio sube hasta 4003.5 (toca borde inferior lo=4003.0? No: h=4003.5 y l=4002.8 -> l <= 4003.0 toca `lo`, pero h < 4005.0 no toca `hi`)
    ctx["h"][5] = 4003.5
    ctx["l"][5] = 4002.8
    # En k=8 el precio llega a h=4005.2 (atraviesa el borde superior `hi=4005.0` -> ambos bordes tocados)
    ctx["h"][8] = 4005.2

    zones = pd.DataFrame(dict(
        t_ns=[int(ctx["t"][2]) * 10**9],
        lo=[4003.0],
        hi=[4005.0],
    ))
    inv = BH.preparar_inventario_barreras(zones, ctx)

    # En k=4 (antes de k=5): tanto VIRGEN (0) como NO_ATRAVESADA (1) ven la barrera a 3.0 pts
    assert np.isclose(BH.evaluar_distancia_frontal(inv, [4], [1], [4000.0], [2.5], 0, 2, 0)[0], 3.0)
    assert np.isclose(BH.evaluar_distancia_frontal(inv, [4], [1], [4000.0], [2.5], 0, 2, 1)[0], 3.0)

    # En k=6 (tras toque parcial en k=5): VIRGEN ya no la considera barrera, pero NO_ATRAVESADA sí
    assert BH.evaluar_distancia_frontal(inv, [6], [1], [4000.0], [2.5], 0, 2, 0)[0] >= BH.INF_PX * 0.5
    assert np.isclose(BH.evaluar_distancia_frontal(inv, [6], [1], [4000.0], [2.5], 0, 2, 1)[0], 3.0)

    # En k=9 (tras atravesar ambos bordes en k=8): ninguna de las dos la considera vigente
    assert BH.evaluar_distancia_frontal(inv, [9], [1], [4000.0], [2.5], 0, 2, 1)[0] >= BH.INF_PX * 0.5


def test_borde_gris_opuesto_es_causal_y_direccional():
    ctx = _ctx_mini_m1(25, tick=0.10)
    # Zona superior [4004.0, 4005.0] creada en k=2, pero su alejamiento bajista (-1) recién se confirma en k=7
    zones = pd.DataFrame(dict(
        t_ns=[int(ctx["t"][2]) * 10**9],
        lo=[4004.0],
        hi=[4005.0],
        bucket=[2],
        total_vol=[10.0],
        away_res_code=[1],
        away_dir=[-1],
        t_away_ns=[int(ctx["t"][7]) * 10**9],
    ))
    inv = BH.preparar_inventario_barreras(zones, ctx)

    # En k=5 (antes de que exista el Borde Gris en k=7), tipo_barrera=2 (BORDE_GRIS_OPUESTO) NO puede verla (cero look-ahead)
    assert BH.evaluar_distancia_frontal(inv, [5], [1], [4000.0], [2.5], 2, 2, 1)[0] >= BH.INF_PX * 0.5
    # En k=7 para una compra (s=+1), away_dir == -1 == -s -> ahora sí es barrera gris opuesta a 4.0 pts
    assert np.isclose(BH.evaluar_distancia_frontal(inv, [7], [1], [4000.0], [2.5], 2, 2, 1)[0], 4.0)
    # Si la zona tuviera away_dir == +1 (misma dirección que la compra), no actúa como BORDE_GRIS_OPUESTO
    zones["away_dir"] = [1]
    inv_misma = BH.preparar_inventario_barreras(zones, ctx)
    assert BH.evaluar_distancia_frontal(inv_misma, [7], [1], [4000.0], [2.5], 2, 2, 1)[0] >= BH.INF_PX * 0.5


def test_captp_recorta_dos_ticks_delante_y_veta_cortos():
    ctx = dict(tick=0.10)
    # Compra en 4000.00 con riesgo 3.00 (30 ticks), TP original 3.0R = 4009.00.
    # Barrera frontal a d_lib_px = 6.00 (2.0R -> borde cercano en 4006.00).
    # CAPTP debe adelantar el TP 2 ticks delante (4006.00 - 0.20 = 4005.80).
    fila_ok = dict(k=10, lado=1, mec=1, ent=4000.0, sl=3997.0, riesgo=3.0, d_lib_px=6.0)
    nv = CAPTP.niveles(fila_ok, ("S3_ATR", 3.0), ctx)
    assert nv is not None
    assert np.isclose(nv[5], 4005.80)

    # Si la barrera está a sólo 2.00 pts (0.67R -> tras restar 2 ticks queda 1.80 < max(1.90, 0.85*3.0=2.55)), debe vetar (None)
    fila_corta = dict(k=10, lado=1, mec=1, ent=4000.0, sl=3997.0, riesgo=3.0, d_lib_px=2.0)
    assert CAPTP.niveles(fila_corta, ("S3_ATR", 3.0), ctx) is None


def test_invariancia_causal_y_oraculo_lote_ambas_variantes():
    ctx = GG.contexto_m1(sintetico.bloques(dias=45, planta=False, seed=19, t0_s=VETO.PREFLIGHT_T0_S), tick=0.25)
    for exp in (VETO, CAPTP):
        D = exp.disparos(ctx)
        assert len(D) > 0
        assert I.causal(exp.disparos, ctx) == []
        assert I.causal_por_disparo(exp.disparos, ctx, n=12) == []
        O1 = GG.ops_por_fila(exp, D, ctx)
        O2 = GG._ops_lote(exp, D, ctx)
        assert O1.shape == O2.shape
        assert np.array_equal(O1, O2, equal_nan=True)

