"""ZONAS-GAPS: pruebas de causalidad, paridad entre motor vectorizado y oráculo barra-a-barra, corrección de los 3 bugs de
`ZonasDeGaps.cs` (multi-cluster, filtro de relleno en creación y no auto-disparo en barra creadora), paridad `niveles`/`niveles_lote`
y control con efecto plantado."""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import grilla_generica as GG, indicadores as I, preflight as PF, sintetico, zonas_gaps as ZG


def _ctx(dias: int, seed: int, planta: bool = False):
    return GG.contexto_m1(sintetico.bloques(dias=dias, planta=planta, seed=seed), tick=0.25)


def test_estatico_y_registro_indicador():
    assert PF.estatico(ZG) == []
    notas = I.exigir(ZG.INDICADORES)
    assert any("ZONAS-GAPS" in n and "NATIVO_AGENTE" in n for n in notas)


def test_causal():
    ctx = _ctx(dias=25, seed=7, planta=False)
    D = ZG.disparos(ctx)
    assert len(D) > 200
    assert set(D.esc.unique()) == {0, 1}
    assert set(D.conf.unique()) == {0, 1}
    assert set(D.obj.unique()) == {0, 1}
    assert set(D.mec.unique()) == {0, 1, 2}
    assert I.causal(ZG.disparos, ctx) == []


def test_oraculo_ciclos_vec_igual_a_nb():
    ctx = _ctx(dias=15, seed=19, planta=False)
    o, h, l, c = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c"))
    tpx = np.asarray(ctx["tpx"], float); tstart = np.asarray(ctx["tstart"], np.int64)
    k0, lo0, hi0, cf0 = ZG._gaps_50t_sesion(tpx, tstart, 0, 0.25, ZG.MIN_GAP_TICKS)
    ord_z = np.argsort(k0, kind="mergesort")
    zk, zlo, zhi = k0[ord_z], lo0[ord_z], hi0[ord_z]
    ev_m, ev_lo, ev_hi, ev_obj = ZG._extraer_objetos_nb(
        zk, zlo, zhi, len(c), ZG.MIN_GAPS_CLUSTER, ZG.CLUSTER_HEIGHT_TICKS * 0.25,
        ZG.MAX_FREE_SPACE_TICKS * 0.25, ZG.VIDA_MAX_M1, ZG.DEDUP_PTS
    )
    assert len(ev_m) > 20
    args = (ev_m, ev_lo, ev_hi, ev_obj, h, l, c, 2.5, ZG.VIDA_MAX_M1, ZG.MAX_CICLOS_ZONA, ZG.AH_IMAN_MIN, ZG.X_GIRO, ZG.X_U1)
    r_nb = ZG._ciclos_zonas_nb(*args)
    r_vec = ZG._ciclos_zonas_vec(*args)
    assert len(r_nb[0]) > 30
    for a_nb, a_vec in zip(r_nb, r_vec):
        assert np.allclose(a_nb, a_vec, atol=1e-12, rtol=0.0)


def test_paridad_niveles_y_niveles_lote():
    ctx = _ctx(dias=15, seed=23, planta=False)
    D = ZG.disparos(ctx).iloc[:200].reset_index(drop=True)
    a = GG.ops_por_fila(ZG, D, ctx)
    b = GG._ops_lote(ZG, D, ctx)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    assert np.allclose(a[2], b[2], equal_nan=True)


def test_tres_bugs_cs_corregidos():
    tick = 0.25
    # --- Bug 1: Multi-cluster (el C# original sólo guardaba un único `bestStart..bestEnd` global y borraba los demás) ---
    zi = np.array([5, 6, 7, 8, 20, 21, 22], dtype=np.int64)
    zlo = np.array([100.0, 101.0, 102.0, 103.0, 200.0, 201.0, 202.0], dtype=float)
    zhi = np.array([100.8, 101.8, 102.8, 103.8, 200.8, 201.8, 202.8], dtype=float)
    ev_m, ev_lo, ev_hi, ev_obj = ZG._extraer_objetos_nb(zi, zlo, zhi, 100, 3, 40.0, 8.0, 500, 2.0)
    clusters_lo = ev_lo[ev_obj == 1]
    assert any(abs(x - 100.0) < 1e-6 for x in clusters_lo), "Debe detectar el primer cluster en 100"
    assert any(abs(x - 200.0) < 1e-6 for x in clusters_lo), "Debe detectar también el segundo cluster en 200 (Bug 1 corregido)"

    # --- Bug 2: Confirmación de vacío no rellenado en la propia barra de 50 ticks ---
    # Barra 0: cierra en 100.0. Barra 1: abre en 102.0 (gap +8 ticks), pero camina suavemente hacia abajo hasta 99.5 (se rellena).
    # Barra 2: cierra en 100.0. Barra 3: abre en 102.0 (gap +8 ticks) y todos sus 50 ticks quedan >= 102.0 (vacío puro).
    b0 = np.full(50, 100.0)
    b1 = np.linspace(102.0, 99.5, 50)
    b2 = np.full(50, 100.0)
    b3 = np.full(50, 102.5); b3[0] = 102.0
    tpx = np.concatenate([b0, b1, b2, b3])
    tstart_ses = np.array([0, 50, 100, 150, 200], dtype=np.int64)
    gk, glo, ghi, gcf = ZG._gaps_50t_sesion(tpx, tstart_ses, a_m1=0, tick=tick, min_gap_ticks=4)
    assert 0 in gcf[gk == 1] and 1 not in gcf[gk == 1]
    assert 0 in gcf[gk == 3] and 1 in gcf[gk == 3]

    # --- Bug 3: La barra de creación NO puede activar IsPriceAway ni consumir un toque por sí misma ---
    n = 30
    c = np.full(n, 100.5); h = np.full(n, 100.8); l = np.full(n, 100.2)
    h[5] = 120.0; l[5] = 99.0
    ok, *_ = ZG._ciclos_zonas_nb(
        np.array([5], np.int64), np.array([100.0]), np.array([101.0]), np.array([0], np.int64),
        h, l, c, away_min=2.5, vida_m1=500, max_ciclos=3, ah_iman_min=4.0, x_giro=0.65, x_u1=0.25
    )
    assert len(ok) == 0, "La mecha de la vela creadora m=5 no debe armar IsPriceAway (Bug 3 corregido)"


def test_control_plantado_favor_supera_contra():
    ctx = _ctx(dias=80, seed=3, planta=True)
    D = ZG.disparos(ctx).reset_index(drop=True)
    di, ei, pnl, _, _ = GG.simular_ops(ZG, D, ctx)
    favor = [i for i, e in enumerate(ZG.EJECUCIONES) if e[0] == "FAVOR"]
    contra = [i for i, e in enumerate(ZG.EJECUCIONES) if e[0] == "CONTRA"]
    m_fav = float(np.nanmean(pnl[np.isin(ei, favor)]))
    m_con = float(np.nanmean(pnl[np.isin(ei, contra)]))
    assert m_fav > m_con, f"FAVOR ({m_fav:.4f}) debe superar a CONTRA ({m_con:.4f}) con reversión plantada"
