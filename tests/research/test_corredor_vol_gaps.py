"""CORREDOR-VOL-GAPS: pruebas de causalidad, port de los 4 pilares de `EmaCorridorTrendVolW2.cs` (W1=100% y W2=200%),
ruptura del Rectángulo Amarillo en la dirección del impulso inicial + excursión + regreso (`ANTES_CAJA`, `EN_CAJA_AMARILLA`,
`DESPUES_CAJA_VA`), targets (`MID50`, `MID25`, `ORIG100`), puntaje continuo de gaps (`g_tom`, `g_cam`), paridad
`niveles`/`niveles_lote` y control con efecto plantado."""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import corredor_vol_gaps as CV, grilla_generica as GG, indicadores as I, preflight as PF, sintetico


def _ctx(dias: int, seed: int, planta: bool = False):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=planta, seed=seed), tick=0.25)


def test_estatico_y_registro_indicador():
    assert PF.estatico(CV) == []
    notas = I.exigir(CV.INDICADORES)
    assert any("EmaCorridorTrendVolW2" in n and "NATIVO_AGENTE" in n for n in notas)
    assert any("ZONAS-GAPS" in n and "NATIVO_AGENTE" in n for n in notas)
    assert GG.n_celdas(CV) == 933120


def test_causal():
    ctx = _ctx(dias=25, seed=7, planta=False)
    D = CV.disparos(ctx)
    assert len(D) > 80
    assert set(D.esc.unique()) == {0, 1}
    assert set(D.vw.unique()) == {0, 1}
    assert set(D.pt_reg.unique()) == {0, 1, 2}
    assert I.causal(CV.disparos, ctx) == []


def test_paridad_niveles_y_niveles_lote():
    ctx = _ctx(dias=20, seed=23, planta=False)
    D = CV.disparos(ctx).iloc[:200].reset_index(drop=True)
    assert len(D) > 20
    a = GG.ops_por_fila(CV, D, ctx)
    b = GG._ops_lote(CV, D, ctx)
    assert a.shape == b.shape
    assert np.allclose(a, b, equal_nan=True)


def test_targets_ordenados_y_ejecuciones_distintas():
    ctx = _ctx(dias=25, seed=19, planta=False)
    D = CV.disparos(ctx).reset_index(drop=True)
    di, ei, pnl, _, _ = GG.simular_ops(CV, D, ctx)
    assert GG.ejecuciones_equivalentes(di, ei, pnl, CV.EJECUCIONES) == []
    # Verificar para cada fila que la distancia al objetivo cumple MID50 <= MID25 <= ORIG100
    for r in D.iloc[:50].to_dict("records"):
        nv50 = CV.niveles(r, ("CIERRE", "MID50", "S_EXT"), ctx)
        nv25 = CV.niveles(r, ("CIERRE", "MID25", "S_EXT"), ctx)
        nv100 = CV.niveles(r, ("CIERRE", "ORIG100", "S_EXT"), ctx)
        if nv50 and nv25 and nv100:
            d50 = abs(nv50[5] - nv50[3])
            d25 = abs(nv25[5] - nv25[3])
            d100 = abs(nv100[5] - nv100[3])
            assert d50 <= d25 + 1e-9 and d25 <= d100 + 1e-9


def test_control_plantado_supera_ruido():
    ctx_p = _ctx(dias=50, seed=3, planta=True)
    ctx_r = _ctx(dias=50, seed=3, planta=False)
    _, _, pnl_p, _, _ = GG.simular_ops(CV, CV.disparos(ctx_p).reset_index(drop=True), ctx_p)
    _, _, pnl_r, _, _ = GG.simular_ops(CV, CV.disparos(ctx_r).reset_index(drop=True), ctx_r)
    assert float(np.nanmean(pnl_p)) > float(np.nanmean(pnl_r)) + 1.0


def test_microestructura_v2_exclusion_mutua_y_ciclo_vida_gaps():
    ctx = _ctx(dias=25, seed=11, planta=False)
    D = CV.disparos(ctx)
    assert len(D) > 50
    # 1. Exclusión mutua por barra M1 y Caja Amarilla: en un mismo (k, esc, vw, orig100, mid50, h_am) no se emiten múltiples pt_reg
    dup = D.groupby(["k", "esc", "vw", "orig100", "mid50", "h_am"])["pt_reg"].nunique()
    assert int(dup.max()) == 1
    # 2. Verificar que el contador de épocas de toque respeta AwayDistanceTicks = 10
    h = np.array([100.0, 101.0, 101.2, 101.1, 105.0, 101.0, 106.0, 101.0], dtype=np.float64)
    l = np.array([99.0,  100.5, 100.6, 100.4, 104.0, 100.5, 105.0, 100.5], dtype=np.float64)
    # Barras 1, 2, 3 tocan [100.2, 100.8] sin alejarse >= 2.5 pts -> cuenta como 1 sola época de toque
    t_ep_1 = CV._contar_toques_epoca_nb(0, 4, 100.2, 100.8, h, l, 2.5)
    assert t_ep_1 == 1
    # Barra 4 se aleja (l=104 > 100.8 + 2.5) y barra 5 vuelve a tocar -> 2da época de toque (gap mitigado/muerto)
    t_ep_2 = CV._contar_toques_epoca_nb(0, 6, 100.2, 100.8, h, l, 2.5)
    assert t_ep_2 == 2
